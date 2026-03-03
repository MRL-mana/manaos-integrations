from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Body

from core.config import EVENTS_FILE, STATE_FILE, STORE
from collectors.events import tail_events
from services.snapshot import snapshot as _snapshot
from services.snapshot import autonomy_status as _autonomy_status

router = APIRouter()

MANUAL_CHECK_FILE = STORE / "manual_personality_check.latest.json"
MANUAL_STAMP_HISTORY_FILE = STORE / "manual_personality_check.stamps.json"
MANUAL_CHECK_ITEMS = [
    {"id": "M1", "title": "人格モードの適正（safe固定）"},
    {"id": "M2", "title": "権限の逸脱チェック（最小権限）"},
    {"id": "M3", "title": "RPG UI危険操作ガード（fail-closed）"},
    {"id": "M4", "title": "監査ログの読める状態維持（可観測性）"},
    {"id": "M5", "title": "再現性の劣化チェック"},
    {"id": "M6", "title": "周辺機能の常時ON化なし"},
    {"id": "M7", "title": "人間最終責任の確認"},
]


def _default_manual_check() -> dict[str, Any]:
    return {
        "date": time.strftime("%Y-%m-%d"),
        "operator": "",
        "mode_expected": "safe",
        "run_id": "",
        "checks": [{"id": i["id"], "title": i["title"], "checked": False} for i in MANUAL_CHECK_ITEMS],
        "notes": "",
        "updated_at": int(time.time()),
        "completed": {"count": 0, "total": len(MANUAL_CHECK_ITEMS), "ok": False},
    }


def _normalize_manual_check(payload: dict[str, Any]) -> dict[str, Any]:
    base = _default_manual_check()
    base["date"] = str(payload.get("date") or base["date"])
    base["operator"] = str(payload.get("operator") or "")
    base["mode_expected"] = str(payload.get("mode_expected") or "safe")
    base["run_id"] = str(payload.get("run_id") or "")
    base["notes"] = str(payload.get("notes") or "")

    checks_by_id = {str(c.get("id")): bool(c.get("checked")) for c in (payload.get("checks") or []) if isinstance(c, dict)}
    base["checks"] = [
        {"id": i["id"], "title": i["title"], "checked": checks_by_id.get(i["id"], False)}
        for i in MANUAL_CHECK_ITEMS
    ]
    count = sum(1 for c in base["checks"] if c["checked"])
    total = len(base["checks"])
    base["completed"] = {"count": count, "total": total, "ok": count == total}
    base["updated_at"] = int(time.time())
    return base


def _load_manual_stamps() -> list[dict[str, Any]]:
    if MANUAL_STAMP_HISTORY_FILE.exists():
        try:
            data = json.loads(MANUAL_STAMP_HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
        except Exception:
            return []
    return []


def _save_manual_stamps(stamps: list[dict[str, Any]]) -> None:
    MANUAL_STAMP_HISTORY_FILE.write_text(
        json.dumps(stamps[:200], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _to_stamp(data: dict[str, Any]) -> dict[str, Any]:
    ts = int(time.time())
    return {
        "stamp_id": f"manual7-{ts}",
        "ts": ts,
        "date": data.get("date", ""),
        "operator": data.get("operator", ""),
        "run_id": data.get("run_id", ""),
        "mode_expected": data.get("mode_expected", "safe"),
        "completed": data.get("completed", {}),
    }


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "ts": int(time.time())}


@router.get("/api/snapshot")
def api_snapshot() -> dict[str, Any]:
    data = _snapshot()
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


@router.get("/api/autonomy")
def api_autonomy() -> dict[str, Any]:
    return _autonomy_status()


@router.get("/api/state")
def api_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["autonomy"] = _autonomy_status()
            return data
        return {"autonomy": _autonomy_status()}
    return {"error": "no state yet. call /api/snapshot first."}


@router.get("/api/events")
def api_events(limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(int(limit), 1000))
    return {"events": tail_events(EVENTS_FILE, limit=limit)}


@router.get("/api/manual-check")
def api_manual_check() -> dict[str, Any]:
    if MANUAL_CHECK_FILE.exists():
        try:
            data = json.loads(MANUAL_CHECK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                normalized = _normalize_manual_check(data)
                normalized["stamps_recent"] = _load_manual_stamps()[:10]
                return normalized
        except Exception:
            pass
    data = _default_manual_check()
    data["stamps_recent"] = _load_manual_stamps()[:10]
    return data


@router.get("/api/manual-check/stamps")
def api_manual_check_stamps(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit), 100))
    stamps = _load_manual_stamps()
    return {"stamps": stamps[:limit]}


@router.post("/api/manual-check")
def api_manual_check_save(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    prev = api_manual_check()
    data = _normalize_manual_check(payload or {})
    MANUAL_CHECK_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    stamp = None
    prev_ok = bool((prev.get("completed") or {}).get("ok")) if isinstance(prev, dict) else False
    should_stamp = bool(data.get("completed", {}).get("ok")) and (not prev_ok or prev.get("date") != data.get("date"))
    stamps = _load_manual_stamps()
    if should_stamp:
        stamp = _to_stamp(data)
        stamps = [stamp] + stamps
        _save_manual_stamps(stamps)

    data["stamps_recent"] = stamps[:10]
    return {"ok": True, "manual_check": data, "stamp": stamp}
