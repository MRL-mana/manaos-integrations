"""
Lightweight, dependency-free mock API server for MVP. Uses only stdlib so it
can run without pip building native wheels (avoids pydantic-core / Rust build).

Endpoints mirror the FastAPI spec for the frontend to consume.
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def mk_status(state, message, since=None, details=None):
    return {"state": state, "since": since or iso_now(), "message": message, "details": details or {}}

# In-memory data
DEVICES = {
    "pixel7": {
        "id": "pixel7",
        "label": "Pixel 7 (ops)",
        "state": mk_status("ok", "connected"),
        "heartbeat": {"last_seen": iso_now(), "age_sec": 2},
        "battery": {"pct": 73, "charging": True, "temp_c": 33.1},
        "network": {"tailscale": {"state": "ok", "ip": "100.64.0.10", "rtt_ms": 42}},
        "adb": {"state": "ok", "serial": "ABCDEF0123", "transport": "usb", "details": {"authorized": True}},
        "scrcpy": {"state": "warn", "session_id": "scrcpy-8f2a", "started_at": iso_now(), "details": {"fps": 8, "resolution": "1080x2400"}},
    },
    "pixel7-guest": {
        "id": "pixel7-guest",
        "label": "Pixel 7 (guest)",
        "state": mk_status("warn", "heartbeat stale"),
        "heartbeat": {"last_seen": iso_now(), "age_sec": 312},
        "battery": {"pct": 41, "charging": False, "temp_c": 35.0},
        "network": {"tailscale": {"state": "ok", "ip": "100.64.0.11", "rtt_ms": 88}},
        "adb": {"state": "warn", "serial": "GUEST0001", "transport": "wifi", "details": {"authorized": True}},
        "scrcpy": {"state": "down", "session_id": None, "started_at": None, "details": {}},
    },
}

RECOVERY_LOGS = [
    {"ts": iso_now(), "level": "WARN", "component": "scrcpy-watch", "event": "RECONNECT_ATTEMPT", "message": "scrcpy reconnect attempt #2", "meta": {"device_id": "pixel7", "session_id": "scrcpy-8f2a"}},
    {"ts": iso_now(), "level": "INFO", "component": "scrcpy-watch", "event": "RECONNECT_OK", "message": "scrcpy connected", "meta": {"device_id": "pixel7", "session_id": "scrcpy-9b11"}},
    {"ts": iso_now(), "level": "ERROR", "component": "adb", "event": "DEVICE_OFFLINE", "message": "device offline detected", "meta": {"device_id": "pixel7"}},
]

RECOVERY_JSONL_PATH = Path(__file__).resolve().parent.parent / "logs" / "recovery.jsonl"
TRIGGER_DIR = Path(__file__).resolve().parent.parent / "logs" / "triggers"
WATCHER_PID_PATH = Path(__file__).resolve().parent.parent / "logs" / "watcher.pid"
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"


def load_recovery_items(limit: int) -> list[dict]:
    if not RECOVERY_JSONL_PATH.exists():
        return RECOVERY_LOGS[:limit]

    try:
        lines = RECOVERY_JSONL_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return RECOVERY_LOGS[:limit]

    items: list[dict] = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(items) >= limit:
            break

    if not items:
        return RECOVERY_LOGS[:limit]
    return list(reversed(items))


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_watcher_recovery_metrics(minutes: int = 5) -> dict:
    if not RECOVERY_JSONL_PATH.exists():
        return {"last_event_ts": None, "error_count_recent": 0, "window_minutes": minutes}

    try:
        lines = RECOVERY_JSONL_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"last_event_ts": None, "error_count_recent": 0, "window_minutes": minutes}

    last_event_ts: str | None = None
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=minutes)
    error_count_recent = 0

    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        if item.get("component") != "scrcpy-watch":
            continue

        ts_value = item.get("ts")
        ts_dt = parse_iso_timestamp(ts_value)
        if ts_dt and ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)

        if last_event_ts is None:
            last_event_ts = ts_value

        if ts_dt and ts_dt.astimezone(timezone.utc) >= threshold and item.get("level") == "ERROR":
            error_count_recent += 1

        if ts_dt and ts_dt.astimezone(timezone.utc) < threshold and last_event_ts is not None:
            break

    return {
        "last_event_ts": last_event_ts,
        "error_count_recent": error_count_recent,
        "window_minutes": minutes,
    }


def get_watcher_status() -> dict:
    metrics = get_watcher_recovery_metrics(minutes=5)

    if not WATCHER_PID_PATH.exists():
        return {
            "generated_at": iso_now(),
            "watcher": {
                "state": "down",
                "since": iso_now(),
                "message": "pid file not found",
                "details": {"pid": None, "pid_file": str(WATCHER_PID_PATH), **metrics},
            },
        }

    try:
        pid_text = WATCHER_PID_PATH.read_text(encoding="utf-8").strip()
        pid = int(pid_text)
    except (OSError, ValueError):
        return {
            "generated_at": iso_now(),
            "watcher": {
                "state": "warn",
                "since": iso_now(),
                "message": "invalid pid file",
                "details": {"pid": None, "pid_file": str(WATCHER_PID_PATH), **metrics},
            },
        }

    running = False
    try:
        tasklist = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if tasklist.returncode == 0:
            line = tasklist.stdout.strip()
            running = bool(line and "No tasks are running" not in line)
    except (subprocess.SubprocessError, FileNotFoundError):
        running = False

    state = "ok" if running else "down"
    message = "watcher running" if running else "watcher process not found"
    if state == "ok" and metrics.get("error_count_recent", 0) > 0:
        state = "warn"
        message = "watcher running with recent errors"
    return {
        "generated_at": iso_now(),
        "watcher": {
            "state": state,
            "since": iso_now(),
            "message": message,
            "details": {"pid": pid, "pid_file": str(WATCHER_PID_PATH), **metrics},
        },
    }


def run_watcher_script(action: str, *, device_id: str | None, dry_run: bool) -> tuple[bool, str]:
    script_name = "start_watcher.ps1" if action == "start" else "stop_watcher.ps1"
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        return False, f"script not found: {script_path}"

    command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
    if action == "start":
        command += ["-DeviceId", device_id or "pixel7"]
        if dry_run:
            command += ["-DryRun"]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        return False, str(exc)

    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return False, output or f"exit code {completed.returncode}"

    return True, output or "ok"

SERVICES = {
    "unified_api": {**mk_status("ok", "healthy", details={"url":"http://127.0.0.1:9502/policy/status","latency_ms":18}), "port": 9502},
    "comfyui": {**mk_status("down", "connection refused", details={"url":"http://127.0.0.1:8188/"}), "port": 8188},
    "n8n": {**mk_status("warn", "slow response", details={"latency_ms": 950}), "port": 5678},
    "adb": mk_status("ok", "devices=2", details={"devices": list(DEVICES.keys()), "adb_server":"running"}),
    "scrcpy": mk_status("warn", "connected but fps low", details={"session_id": "scrcpy-8f2a", "fps": 8}),
}

IMAGEGEN_METRICS = {
    "date": "2026-03-03",
    "counts": {"requests_total": 42, "success": 39, "failed": 3},
    "rates": {"fail_rate": 0.0714},
    "latency_ms": {"avg": 18340, "p95": 29500},
    "cost_estimate_yen": {"total": 128, "unit_avg": 3.3, "basis": "local_estimate_v1"},
    "sources": {"comfyui_calls": 42, "log_path": "logs/imagegen_calls.jsonl"},
}

JOBS = {}
SUPPORTED_CMDS = {"reconnect_scrcpy", "restart_adb", "restart_unified", "restart_comfyui", "reboot_all", "start_watcher", "stop_watcher"}
ACTION_LOCK = {"locked": False}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        qs = parse_qs(u.query)

        if path == "/api/status/overview":
            return self._send_json({"generated_at": iso_now(), "host": {"name": "mothership", "uptime_sec": int(time.time()) % 999999, "load": {"cpu_pct": 22.3, "mem_pct": 61.2}}, "services": SERVICES})

        if path.startswith("/api/status/device/"):
            device_id = path.split("/")[-1]
            dev = DEVICES.get(device_id)
            if not dev:
                return self._send_json({"error": {"code": "DEVICE_NOT_FOUND", "message": "unknown device_id"}}, status=404)
            payload = {"generated_at": iso_now(), "device": {"id": dev["id"], "label": dev["label"], **dev["state"]}}
            for k, v in dev.items():
                if k not in ("id", "label", "state"):
                    payload[k] = v
            return self._send_json(payload)

        if path == "/api/logs/recovery":
            try:
                limit = int(qs.get("limit", [3])[0])
            except:
                limit = 3
            limit = max(1, min(limit, 50))
            return self._send_json({"generated_at": iso_now(), "items": load_recovery_items(limit)})

        if path == "/api/metrics/imagegen/today":
            return self._send_json({"generated_at": iso_now(), **IMAGEGEN_METRICS})

        if path == "/api/status/watcher":
            return self._send_json(get_watcher_status())

        if path.startswith("/api/action/jobs/"):
            job_id = path.split("/")[-1]
            job = JOBS.get(job_id)
            if not job:
                return self._send_json({"error": {"code": "JOB_NOT_FOUND", "message": "unknown job_id"}}, status=404)
            return self._send_json(job)

        # default
        self._send_json({"error": {"code": "NOT_FOUND", "message": "unknown endpoint"}}, status=404)

    def do_POST(self):
        u = urlparse(self.path)
        path = u.path
        if path.startswith("/api/action/"):
            cmd = path.split("/")[-1]
            if cmd not in SUPPORTED_CMDS:
                return self._send_json({"error": {"code": "INVALID_CMD", "message": "cmd not supported", "hint": "|".join(sorted(SUPPORTED_CMDS))}}, status=404)
            if ACTION_LOCK["locked"]:
                return self._send_json({"error": {"code": "ACTION_LOCKED", "message": "another action is running"}}, status=409)

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                j = json.loads(body)
            except:
                j = {}

            device_id = j.get("device_id")
            dry_run = bool(j.get("dry_run", False))
            reason = j.get("reason", "manual_from_dashboard")

            if cmd in {"reconnect_scrcpy", "restart_adb"} and not device_id:
                return self._send_json({"error": {"code": "DEVICE_ID_REQUIRED", "message": "device_id is required for this cmd"}}, status=400)

            job_id = f"job-{uuid.uuid4().hex[:8]}"
            started_at = iso_now()
            job = {"job_id": job_id, "cmd": cmd, "device_id": device_id, "state": "queued", "started_at": started_at, "finished_at": None, "stdout_tail": [], "exit_code": None, "dry_run": dry_run, "reason": reason}
            JOBS[job_id] = job

            if dry_run:
                job["state"] = "done"
                job["finished_at"] = iso_now()
                job["stdout_tail"] = [f"[DRY_RUN] would execute {cmd} for {device_id or 'all'}"]
                job["exit_code"] = 0
            else:
                ACTION_LOCK["locked"] = True
                job["state"] = "running"
                job["stdout_tail"] = [f"running {cmd}..."]

                if cmd == "reconnect_scrcpy" and device_id:
                    TRIGGER_DIR.mkdir(parents=True, exist_ok=True)
                    trigger_path = TRIGGER_DIR / f"manual_retry_{device_id}.flag"
                    trigger_path.write_text(f"{iso_now()} manual retry\n", encoding="utf-8")
                    job["stdout_tail"].append(f"manual retry trigger written: {trigger_path}")

                if cmd == "start_watcher":
                    ok, output = run_watcher_script("start", device_id=device_id, dry_run=dry_run)
                    job["stdout_tail"].append(output)
                    if not ok:
                        job["state"] = "failed"
                        job["exit_code"] = 1
                        job["finished_at"] = iso_now()
                        ACTION_LOCK["locked"] = False
                        return self._send_json({"accepted": False, "job_id": job_id, "started_at": started_at, "result": job["state"], "summary": f"{cmd} failed", "next": {"poll": f"/api/action/jobs/{job_id}"}}, status=500)

                if cmd == "stop_watcher":
                    ok, output = run_watcher_script("stop", device_id=device_id, dry_run=dry_run)
                    job["stdout_tail"].append(output)
                    if not ok:
                        job["state"] = "failed"
                        job["exit_code"] = 1
                        job["finished_at"] = iso_now()
                        ACTION_LOCK["locked"] = False
                        return self._send_json({"accepted": False, "job_id": job_id, "started_at": started_at, "result": job["state"], "summary": f"{cmd} failed", "next": {"poll": f"/api/action/jobs/{job_id}"}}, status=500)

                # immediate finish for MVP
                job["stdout_tail"].append("ok")
                job["exit_code"] = 0
                job["state"] = "done"
                job["finished_at"] = iso_now()
                ACTION_LOCK["locked"] = False

            return self._send_json({"accepted": True, "job_id": job_id, "started_at": started_at, "result": job["state"], "summary": f"{cmd} for {device_id or 'all'}", "next": {"poll": f"/api/action/jobs/{job_id}"}})

        self._send_json({"error": {"code": "NOT_FOUND", "message": "unknown endpoint"}}, status=404)


def run(port=9640):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Starting mock ops-dashboard API on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
