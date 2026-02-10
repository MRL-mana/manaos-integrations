import os
import time
import json
import hmac
import hashlib
import tempfile
import uuid

import pytest
import sys
from pathlib import Path

# Ensure repo root is on sys.path so tests can import local modules
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import cursor_webhook as cw


class DummyMana:
    def remember(self, entry, format_type=None):
        return "dummy-memory-id"


@pytest.fixture(autouse=True)
def set_env(tmp_path, monkeypatch):
    # set a temporary nonce DB and secret
    db_path = tmp_path / "nonces.db"
    monkeypatch.setenv("CURSOR_WEBHOOK_NONCE_DB", str(db_path))
    monkeypatch.setenv("CURSOR_WEBHOOK_MAX_SKEW", "300")
    secret = "testsecret"
    monkeypatch.setenv("CURSOR_WEBHOOK_SECRET", secret)
    # inject dummy manaos
    cw.manaos = DummyMana()
    return secret


def make_sig(secret: str, raw: bytes) -> str:
    mac = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def test_webhook_success(set_env=set_env):
    # use Flask test client
    app = cw.app
    secret = os.getenv("CURSOR_WEBHOOK_SECRET")
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex
    body = {"content": "pytest test", "metadata": {"source": "cursor"}}
    raw = json.dumps(body).encode("utf-8")
    sig = make_sig(secret, raw)

    with app.test_client() as client:
        resp = client.post(
            "/cursor/webhook",
            data=raw,
            headers={
                "Content-Type": "application/json",
                "X-Cursor-Timestamp": ts,
                "X-Cursor-Nonce": nonce,
                "X-Cursor-Signature": sig,
            },
        )
        assert resp.status_code == 200
        j = resp.get_json()
        assert j["ok"] is True
        assert j["memory_id"] == "dummy-memory-id"


def test_replay_detection(set_env=set_env):
    app = cw.app
    secret = os.getenv("CURSOR_WEBHOOK_SECRET")
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex
    body = {"content": "pytest replay test", "metadata": {"source": "cursor"}}
    raw = json.dumps(body).encode("utf-8")
    sig = make_sig(secret, raw)

    with app.test_client() as client:
        # first call should succeed
        r1 = client.post(
            "/cursor/webhook",
            data=raw,
            headers={
                "Content-Type": "application/json",
                "X-Cursor-Timestamp": ts,
                "X-Cursor-Nonce": nonce,
                "X-Cursor-Signature": sig,
            },
        )
        assert r1.status_code == 200

        # second call with same nonce should be detected as replay
        r2 = client.post(
            "/cursor/webhook",
            data=raw,
            headers={
                "Content-Type": "application/json",
                "X-Cursor-Timestamp": ts,
                "X-Cursor-Nonce": nonce,
                "X-Cursor-Signature": sig,
            },
        )
        assert r2.status_code == 400
        j2 = r2.get_json()
        assert j2.get("error") == "replay"
