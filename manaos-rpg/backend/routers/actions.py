from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import _require_token
from core.config import ACTION_LAST_FILE, EVENTS_FILE
from collectors.events import append_event
from services.actions import _actions_enabled, _load_actions, _run_action

router = APIRouter()


@router.get("/api/actions")
def api_actions() -> dict[str, Any]:
    actions = _load_actions()
    return {
        "enabled": _actions_enabled(),
        "actions": [
            {"id": a.get("id"), "label": a.get("label"), "kind": a.get("kind"), "tags": a.get("tags") or []}
            for a in actions
        ],
    }


@router.post("/api/actions/{action_id}/run", dependencies=[Depends(_require_token)])
def api_run_action(action_id: str) -> dict[str, Any]:
    if not _actions_enabled():
        raise HTTPException(status_code=403, detail="actions disabled. set MANAOS_RPG_ENABLE_ACTIONS=1")

    actions = _load_actions()
    action = next((a for a in actions if str(a.get("id")) == action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="unknown action")

    started = int(time.time())
    result = _run_action(action)
    ended = int(time.time())

    payload = {
        "ts": ended,
        "action_id": action_id,
        "label": action.get("label"),
        "result": result,
        "duration_sec": max(0, ended - started),
    }
    ACTION_LAST_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    append_event(
        EVENTS_FILE,
        "action_run",
        f"action {action_id} {'OK' if result.get('ok') else 'NG'}",
        {"action_id": action_id, "ok": bool(result.get('ok')), "exit_code": result.get('exit_code')},
    )
    return payload


@router.get("/api/actions/last")
def api_last_action() -> dict[str, Any]:
    if ACTION_LAST_FILE.exists():
        return json.loads(ACTION_LAST_FILE.read_text(encoding="utf-8"))
    return {"error": "no action run yet"}
