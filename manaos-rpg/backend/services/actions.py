from __future__ import annotations

import os
import subprocess
from typing import Any

from core.config import REG, REPO_ROOT
from core.helpers import load_yaml
from collectors.items_collector import safe_resolve_under_root


def _actions_enabled() -> bool:
    v = str(os.environ.get("MANAOS_RPG_ENABLE_ACTIONS", "0")).strip().lower()
    return v in {"1", "true", "yes", "on"}


def _load_actions() -> list[dict[str, Any]]:
    actions_yaml = load_yaml(REG / "actions.yaml")
    raw = actions_yaml.get("actions") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for a in raw:
        if isinstance(a, dict) and a.get("id"):
            out.append(a)
    return out


def _run_action(action: dict[str, Any]) -> dict[str, Any]:
    kind = str(action.get("kind") or "").strip()
    if kind != "pwsh_file":
        return {"ok": False, "error": f"unsupported kind: {kind}"}

    rel = str(action.get("path") or "").strip()
    if not rel:
        return {"ok": False, "error": "missing path"}

    script = safe_resolve_under_root(REPO_ROOT, rel)
    if script is None or (not script.exists()) or (not script.is_file()):
        return {"ok": False, "error": "script not found/forbidden"}

    timeout_sec = int(action.get("timeout_sec") or 60)
    timeout_sec = max(1, min(timeout_sec, 600))

    cwd_raw = str(action.get("cwd") or ".").strip() or "."
    cwd_path = safe_resolve_under_root(REPO_ROOT, cwd_raw) or REPO_ROOT

    cmd = [
        "pwsh",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]

    args = action.get("args")
    if isinstance(args, list):
        for a in args:
            if a is None:
                continue
            cmd.append(str(a))

    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=float(timeout_sec),
            cwd=str(cwd_path),
        )

        stdout = (completed.stdout or "").strip()[-20000:]
        stderr = (completed.stderr or "").strip()[-20000:]
        return {
            "ok": completed.returncode == 0,
            "exit_code": int(completed.returncode),
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
