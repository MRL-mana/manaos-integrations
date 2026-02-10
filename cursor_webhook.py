from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import os
import hmac
import hashlib
import json
import time
import sqlite3
from pathlib import Path
import uuid

# Try to import ManaOS API wrapper used elsewhere in the repo
try:
    import manaos_core_api as manaos
except Exception:
    manaos = None

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=os.getenv("MANAOS_LOG_LEVEL", "INFO"))
logger = logging.getLogger("manaos.cursor_webhook")

# File logging (rotating)
log_path = os.getenv("CURSOR_WEBHOOK_LOG", str(Path(__file__).parent / "logs"))
try:
    log_dir = Path(log_path)
    if log_dir.suffix == ".log":
        # if a file path provided, use its parent
        log_file = log_dir
        log_dir = log_file.parent
    else:
        log_file = log_dir / "cursor_webhook.log"

    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=5)
    handler.setLevel(os.getenv("MANAOS_LOG_LEVEL", "INFO"))
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
except Exception:
    logger.warning("Could not initialize file logging; continuing with console only")


def _verify_hmac(raw_body: bytes, secret: str, signature_header: str) -> bool:
    """Verify HMAC-SHA256 signature.

    signature_header expected format: 'sha256=<hex>'
    """
    try:
        if not secret:
            return False
        if not signature_header:
            return False
        if signature_header.startswith("sha256="):
            sig = signature_header.split("=", 1)[1]
        else:
            sig = signature_header
        mac = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256)
        expected = mac.hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


def _init_nonce_db(db_path: str):
    conn = sqlite3.connect(db_path, timeout=3)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nonces (
            nonce TEXT PRIMARY KEY,
            ts INTEGER
        )
        """
    )
    conn.commit()
    return conn


def _is_nonce_seen(conn: sqlite3.Connection, nonce: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM nonces WHERE nonce = ?", (nonce,))
    return cur.fetchone() is not None


def _add_nonce(conn: sqlite3.Connection, nonce: str, ts: int):
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO nonces(nonce, ts) VALUES(?, ?)", (nonce, ts))
    conn.commit()


def _prune_nonces(conn: sqlite3.Connection, min_ts: int):
    cur = conn.cursor()
    cur.execute("DELETE FROM nonces WHERE ts < ?", (min_ts,))
    conn.commit()


@app.route("/cursor/webhook", methods=["POST"])
def cursor_webhook():
    """Receive Cursor conversation webhook and store to ManaOS unified memory.

    Security: supports HMAC-SHA256 verification via header `X-Cursor-Signature: sha256=<hex>`
    or a bearer token via `Authorization: Bearer <token>` where the token equals
    `CURSOR_WEBHOOK_SECRET`.
    If `CURSOR_WEBHOOK_SECRET` is not set, webhook accepts requests but logs a warning.
    """
    raw = request.get_data() or b""

    # Authentication
    secret = os.getenv("CURSOR_WEBHOOK_SECRET")
    sig_header = request.headers.get("X-Cursor-Signature") or request.headers.get("X-Hub-Signature-256")
    auth_header = request.headers.get("Authorization")
    ts_header = request.headers.get("X-Cursor-Timestamp")
    nonce_header = request.headers.get("X-Cursor-Nonce")

    if secret:
        valid = False
        if sig_header:
            valid = _verify_hmac(raw, secret, sig_header)
        elif auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            valid = hmac.compare_digest(token, secret)

        if not valid:
            logger.warning("Unauthorized webhook attempt")
            return jsonify({"ok": False, "error": "unauthorized"}), 401
    else:
        logger.warning("CURSOR_WEBHOOK_SECRET not set — running webhook in insecure mode")

    # parse JSON
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else None
    except Exception:
        payload = None

    if payload is None:
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    logger.info("Received Cursor webhook: %s", str(payload)[:200])

    if manaos is None:
        logger.warning("manaos_core_api not available; cannot save memory")
        return jsonify({"ok": False, "error": "manaos_unavailable"}), 503

    # Replay prevention: timestamp + nonce
    try:
        max_skew = int(os.getenv("CURSOR_WEBHOOK_MAX_SKEW", "300"))
        nonce_db = os.getenv("CURSOR_WEBHOOK_NONCE_DB", str(Path(__file__).parent / "cursor_webhook_nonces.db"))
        # init db
        conn = _init_nonce_db(nonce_db)
        now = int(time.time())

        if not ts_header or not nonce_header:
            logger.warning("Missing timestamp or nonce headers")
            return jsonify({"ok": False, "error": "missing_timestamp_or_nonce"}), 400

        try:
            ts = int(ts_header)
        except Exception:
            logger.warning("Invalid timestamp header")
            return jsonify({"ok": False, "error": "invalid_timestamp"}), 400

        if abs(now - ts) > max_skew:
            logger.warning("Timestamp skew too large: now=%s ts=%s", now, ts)
            return jsonify({"ok": False, "error": "timestamp_skew"}), 400

        # prune old nonces
        _prune_nonces(conn, now - max_skew - 60)

        if _is_nonce_seen(conn, nonce_header):
            logger.warning("Replay detected for nonce=%s", nonce_header)
            return jsonify({"ok": False, "error": "replay"}), 400

        _add_nonce(conn, nonce_header, ts)
    except Exception as e:
        logger.exception("Nonce DB error: %s", e)
        # don't block on DB error, continue but warn
        pass

    try:
        # normalize payload if needed
        memory_entry = {
            "content": payload.get("content") if isinstance(payload, dict) else payload,
            "metadata": payload.get("metadata", {"source": "cursor"}) if isinstance(payload, dict) else {"source": "cursor"}
        }
        memory_id = manaos.remember(memory_entry, format_type="conversation")
        logger.info("Saved memory id=%s", memory_id)

        # Audit log (minimal, avoid logging secrets)
        try:
            audit = {
                "event": "cursor_webhook_saved",
                "memory_id": str(memory_id),
                "path": request.path,
                "remote_addr": request.remote_addr,
                "timestamp": int(time.time()),
                "headers": {
                    "X-Cursor-Timestamp": ts_header,
                    "X-Cursor-Nonce": nonce_header
                }
            }
            logger.info("AUDIT %s", json.dumps(audit, ensure_ascii=False))
        except Exception:
            logger.exception("Failed to write audit log")

        return jsonify({"ok": True, "memory_id": memory_id}), 200
    except Exception as e:
        logger.exception("Failed to save memory from Cursor webhook")
        try:
            logger.info("AUDIT %s", json.dumps({
                "event": "cursor_webhook_error",
                "error": str(e),
                "path": request.path,
                "remote_addr": request.remote_addr,
                "timestamp": int(time.time())
            }, ensure_ascii=False))
        except Exception:
            pass
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("CURSOR_WEBHOOK_PORT", "9700"))
    host = os.getenv("CURSOR_WEBHOOK_HOST", "127.0.0.1")
    # Use waitress in production/dev where appropriate
    try:
        from waitress import serve

        serve(app, host=host, port=port)
    except Exception:
        # fallback to Flask dev server
        app.run(host=host, port=port, debug=False)
