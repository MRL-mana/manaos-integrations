from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def get_docker_container_runtime(container: str) -> dict[str, Any] | None:
    if not container:
        return None
    if not shutil.which("docker"):
        return None

    try:
        completed = subprocess.run(
            ["docker", "inspect", container],
            check=False,
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        if completed.returncode != 0:
            return {
                "docker_found": False,
                "docker_status": None,
                "docker_health": None,
                "restart_count": None,
                "started_at": None,
                "finished_at": None,
            }

        payload = json.loads((completed.stdout or "").strip() or "[]")
        if not isinstance(payload, list) or not payload:
            return None
        info = payload[0]

        state = info.get("State") or {}
        status = state.get("Status")
        health = (state.get("Health") or {}).get("Status")
        restart_count = info.get("RestartCount")

        started_at = state.get("StartedAt")
        finished_at = state.get("FinishedAt")

        return {
            "docker_found": True,
            "docker_status": status,
            "docker_health": health,  # healthy|unhealthy|starting|None
            "restart_count": int(restart_count) if restart_count is not None else None,
            "started_at": started_at,
            "finished_at": finished_at,
        }
    except Exception:
        return None
