from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def get_pm2_processes() -> list[dict[str, Any]]:
    if not shutil.which("pm2"):
        return []
    try:
        completed = subprocess.run(
            ["pm2", "jlist"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.5,
        )
        text = (completed.stdout or "").strip()
        if not text:
            return []
        payload = json.loads(text)
        if not isinstance(payload, list):
            return []
        return payload
    except Exception:
        return []


def get_pm2_runtime_by_name(name: str) -> dict[str, Any] | None:
    if not name:
        return None

    procs = get_pm2_processes()
    for p in procs:
        if str(p.get("name") or "") != name:
            continue

        env = p.get("pm2_env") or {}
        status = env.get("status")
        restart_time = env.get("restart_time")
        pm_uptime = env.get("pm_uptime")
        pm_id = p.get("pm_id")
        return {
            "pm2_found": True,
            "pm2_id": pm_id,
            "pm2_status": status,  # online|stopped|errored|...
            "restart_count": int(restart_time) if restart_time is not None else None,
            "pm_uptime": pm_uptime,
        }

    return {"pm2_found": False, "pm2_id": None, "pm2_status": None, "restart_count": None, "pm_uptime": None}
