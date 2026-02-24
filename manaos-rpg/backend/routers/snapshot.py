from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter

from core.config import EVENTS_FILE, STATE_FILE
from collectors.events import tail_events
from services.snapshot import snapshot as _snapshot

router = APIRouter()


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "ts": int(time.time())}


@router.get("/api/snapshot")
def api_snapshot() -> dict[str, Any]:
    data = _snapshot()
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


@router.get("/api/state")
def api_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"error": "no state yet. call /api/snapshot first."}


@router.get("/api/events")
def api_events(limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(int(limit), 1000))
    return {"events": tail_events(EVENTS_FILE, limit=limit)}
