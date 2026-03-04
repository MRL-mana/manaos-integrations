from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body

from core.config import EVENTS_FILE, REPO_ROOT, STATE_FILE, STORE
from collectors.events import tail_events
from services.snapshot import snapshot as _snapshot
from services.snapshot import autonomy_status as _autonomy_status

router = APIRouter()

MANUAL_CHECK_FILE = STORE / "manual_personality_check.latest.json"
MANUAL_STAMP_HISTORY_FILE = STORE / "manual_personality_check.stamps.json"
_SNAPSHOT_CACHE_LOCK = Lock()
_SNAPSHOT_CACHE_AT_MONO = 0.0
_SNAPSHOT_CACHE_DATA: dict[str, Any] | None = None
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
        "checks": [
            {"id": item["id"], "title": item["title"], "checked": False}
            for item in MANUAL_CHECK_ITEMS
        ],
        "notes": "",
        "updated_at": int(time.time()),
        "completed": {
            "count": 0,
            "total": len(MANUAL_CHECK_ITEMS),
            "ok": False,
        },
    }


def _normalize_manual_check(payload: dict[str, Any]) -> dict[str, Any]:
    base = _default_manual_check()
    base["date"] = str(payload.get("date") or base["date"])
    base["operator"] = str(payload.get("operator") or "")
    base["mode_expected"] = str(payload.get("mode_expected") or "safe")
    base["run_id"] = str(payload.get("run_id") or "")
    base["notes"] = str(payload.get("notes") or "")

    checks_by_id = {
        str(check.get("id")): bool(check.get("checked"))
        for check in (payload.get("checks") or [])
        if isinstance(check, dict)
    }
    base["checks"] = [
        {
            "id": item["id"],
            "title": item["title"],
            "checked": checks_by_id.get(item["id"], False),
        }
        for item in MANUAL_CHECK_ITEMS
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


def _snapshot_cache_ttl_sec() -> int:
    raw = os.getenv("MANAOS_RPG_SNAPSHOT_CACHE_TTL_SEC", "30")
    try:
        ttl = int(raw)
    except Exception:
        ttl = 30
    return max(0, min(ttl, 300))


def _snapshot_cached(force_refresh: bool = False) -> dict[str, Any]:
    global _SNAPSHOT_CACHE_AT_MONO, _SNAPSHOT_CACHE_DATA

    now_mono = time.monotonic()
    ttl = _snapshot_cache_ttl_sec()

    if (not force_refresh) and ttl > 0:
        with _SNAPSHOT_CACHE_LOCK:
            if _SNAPSHOT_CACHE_DATA is not None and (now_mono - _SNAPSHOT_CACHE_AT_MONO) <= ttl:
                return _SNAPSHOT_CACHE_DATA

    data = _snapshot()
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if ttl > 0:
        with _SNAPSHOT_CACHE_LOCK:
            _SNAPSHOT_CACHE_DATA = data
            _SNAPSHOT_CACHE_AT_MONO = now_mono

    return data


def _pick_google_file(repo_root: Path, file_name: str) -> Path:
    desktop = Path(os.path.expandvars(r"%USERPROFILE%/Desktop")).resolve()
    candidates = [
        desktop / file_name,
        repo_root / file_name,
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue
    return candidates[0]


def _load_google_access_token(repo_root: Path) -> str:
    token_path = _pick_google_file(repo_root, "token.json")
    if not token_path.exists():
        return ""
    try:
        payload = json.loads(token_path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(payload, dict):
            return ""
        return str(payload.get("access_token") or payload.get("token") or "").strip()
    except Exception:
        return ""


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "ts": int(time.time())}


@router.get("/api/snapshot")
def api_snapshot(force: int = 0) -> dict[str, Any]:
    force_refresh = int(force or 0) == 1
    return _snapshot_cached(force_refresh=force_refresh)


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
    data = _snapshot_cached(force_refresh=False)
    data["autonomy"] = _autonomy_status()
    return data


@router.get("/api/events")
def api_events(limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(int(limit), 1000))
    return {"events": tail_events(EVENTS_FILE, limit=limit)}


@router.post("/api/google/tasks/complete")
def api_google_task_complete(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    task_list_id = str(payload.get("task_list_id") or "").strip()
    task_id = str(payload.get("task_id") or "").strip()
    if not task_list_id or not task_id:
        return {"ok": False, "reason": "invalid_params", "detail": "task_list_id and task_id are required"}

    access_token = _load_google_access_token(REPO_ROOT)
    if not access_token:
        return {"ok": False, "reason": "auth_missing", "detail": "google access token not found"}

    url = (
        "https://tasks.googleapis.com/tasks/v1/lists/"
        f"{quote(task_list_id, safe='')}/tasks/{quote(task_id, safe='')}"
    )
    body = {
        "status": "completed",
        "completed": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="PATCH",
        data=raw,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "manaos-rpg/0.1",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            body_raw = resp.read(2 * 1024 * 1024)
            data = json.loads(body_raw.decode("utf-8", errors="replace")) if body_raw else {}
    except urllib.error.HTTPError as e:
        try:
            err_raw = e.read(128 * 1024)
            err_text = err_raw.decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        err_lower = err_text.lower()
        if ("insufficient authentication scopes" in err_lower) or ("insufficientpermissions" in err_lower):
            return {
                "ok": False,
                "reason": "scope_missing",
                "status": int(getattr(e, "code", 0) or 0),
                "detail": "tasks scope is required",
                "error": err_text[:400],
            }
        return {
            "ok": False,
            "reason": "api_error",
            "status": int(getattr(e, "code", 0) or 0),
            "error": err_text[:400],
        }
    except Exception as e:
        return {"ok": False, "reason": "request_failed", "error": str(e)}

    _snapshot_cached(force_refresh=True)
    return {
        "ok": True,
        "reason": "completed",
        "task": {
            "id": str(data.get("id") or task_id),
            "status": str(data.get("status") or "completed"),
            "completed": str(data.get("completed") or body["completed"]),
        },
    }


@router.post("/api/google/tasks/create")
def api_google_task_create(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    notes = str(payload.get("notes") or "").strip()
    due = str(payload.get("due") or "").strip()
    task_list_id = str(payload.get("task_list_id") or "").strip()
    if not title:
        return {"ok": False, "reason": "invalid_params", "detail": "title is required"}

    access_token = _load_google_access_token(REPO_ROOT)
    if not access_token:
        return {"ok": False, "reason": "auth_missing", "detail": "google access token not found"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "manaos-rpg/0.1",
    }

    if not task_list_id:
        list_req = urllib.request.Request(
            "https://tasks.googleapis.com/tasks/v1/users/@me/lists?maxResults=20",
            method="GET",
            headers={
                "Authorization": headers["Authorization"],
                "User-Agent": headers["User-Agent"],
            },
        )
        try:
            with urllib.request.urlopen(list_req, timeout=8.0) as resp:
                raw = resp.read(2 * 1024 * 1024)
                list_data = json.loads(raw.decode("utf-8", errors="replace")) if raw else {}
            items = list_data.get("items") if isinstance(list_data, dict) else None
            if isinstance(items, list) and items:
                first = items[0] if isinstance(items[0], dict) else {}
                task_list_id = str(first.get("id") or "").strip()
        except urllib.error.HTTPError as e:
            try:
                err_raw = e.read(128 * 1024)
                err_text = err_raw.decode("utf-8", errors="replace")
            except Exception:
                err_text = ""
            err_lower = err_text.lower()
            if ("insufficient authentication scopes" in err_lower) or ("insufficientpermissions" in err_lower):
                return {
                    "ok": False,
                    "reason": "scope_missing",
                    "status": int(getattr(e, "code", 0) or 0),
                    "detail": "tasks scope is required",
                    "error": err_text[:400],
                }
            return {
                "ok": False,
                "reason": "api_error",
                "status": int(getattr(e, "code", 0) or 0),
                "error": err_text[:400],
            }
        except Exception as e:
            return {"ok": False, "reason": "request_failed", "error": str(e)}

    if not task_list_id:
        return {"ok": False, "reason": "tasklist_not_found", "detail": "task list is not available"}

    body: dict[str, Any] = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://tasks.googleapis.com/tasks/v1/lists/{quote(task_list_id, safe='')}/tasks",
        method="POST",
        data=raw,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            body_raw = resp.read(2 * 1024 * 1024)
            data = json.loads(body_raw.decode("utf-8", errors="replace")) if body_raw else {}
    except urllib.error.HTTPError as e:
        try:
            err_raw = e.read(128 * 1024)
            err_text = err_raw.decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        err_lower = err_text.lower()
        if ("insufficient authentication scopes" in err_lower) or ("insufficientpermissions" in err_lower):
            return {
                "ok": False,
                "reason": "scope_missing",
                "status": int(getattr(e, "code", 0) or 0),
                "detail": "tasks scope is required",
                "error": err_text[:400],
            }
        return {
            "ok": False,
            "reason": "api_error",
            "status": int(getattr(e, "code", 0) or 0),
            "error": err_text[:400],
        }
    except Exception as e:
        return {"ok": False, "reason": "request_failed", "error": str(e)}

    _snapshot_cached(force_refresh=True)
    return {
        "ok": True,
        "reason": "created",
        "task": {
            "id": str(data.get("id") or ""),
            "title": str(data.get("title") or title),
            "status": str(data.get("status") or "needsAction"),
            "task_list_id": task_list_id,
            "due": str(data.get("due") or ""),
        },
    }


@router.post("/api/google/calendar/create")
def api_google_calendar_create(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    summary = str(payload.get("summary") or "").strip()
    start_iso = str(payload.get("start") or "").strip()
    end_iso = str(payload.get("end") or "").strip()
    if not summary:
        return {"ok": False, "reason": "invalid_params", "detail": "summary is required"}

    access_token = _load_google_access_token(REPO_ROOT)
    if not access_token:
        return {"ok": False, "reason": "auth_missing", "detail": "google access token not found"}

    now = datetime.now(timezone.utc)
    if not start_iso:
        start_iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not end_iso:
        end_iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        try:
            end_iso = (datetime.fromisoformat(start_iso.replace("Z", "+00:00")) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
        except Exception:
            pass

    body = {
        "summary": summary,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        method="POST",
        data=raw,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "manaos-rpg/0.1",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            body_raw = resp.read(2 * 1024 * 1024)
            data = json.loads(body_raw.decode("utf-8", errors="replace")) if body_raw else {}
    except urllib.error.HTTPError as e:
        try:
            err_raw = e.read(128 * 1024)
            err_text = err_raw.decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        err_lower = err_text.lower()
        if ("insufficient authentication scopes" in err_lower) or ("insufficientpermissions" in err_lower):
            return {
                "ok": False,
                "reason": "scope_missing",
                "status": int(getattr(e, "code", 0) or 0),
                "detail": "calendar scope is required",
                "error": err_text[:400],
            }
        return {
            "ok": False,
            "reason": "api_error",
            "status": int(getattr(e, "code", 0) or 0),
            "error": err_text[:400],
        }
    except Exception as e:
        return {"ok": False, "reason": "request_failed", "error": str(e)}

    _snapshot_cached(force_refresh=True)
    return {
        "ok": True,
        "reason": "created",
        "event": {
            "id": str(data.get("id") or ""),
            "summary": str(data.get("summary") or summary),
            "start": str(((data.get("start") or {}).get("dateTime") or (data.get("start") or {}).get("date") or start_iso)),
            "end": str(((data.get("end") or {}).get("dateTime") or (data.get("end") or {}).get("date") or end_iso)),
        },
    }


@router.post("/api/google/calendar/delete")
def api_google_calendar_delete(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    event_id = str(payload.get("event_id") or "").strip()
    if not event_id:
        return {"ok": False, "reason": "invalid_params", "detail": "event_id is required"}

    access_token = _load_google_access_token(REPO_ROOT)
    if not access_token:
        return {"ok": False, "reason": "auth_missing", "detail": "google access token not found"}

    req = urllib.request.Request(
        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{quote(event_id, safe='')}",
        method="DELETE",
        headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "manaos-rpg/0.1",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=8.0):
            pass
    except urllib.error.HTTPError as e:
        if int(getattr(e, "code", 0) or 0) == 404:
            _snapshot_cached(force_refresh=True)
            return {"ok": True, "reason": "already_missing", "event": {"id": event_id}}
        try:
            err_raw = e.read(128 * 1024)
            err_text = err_raw.decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        err_lower = err_text.lower()
        if ("insufficient authentication scopes" in err_lower) or ("insufficientpermissions" in err_lower):
            return {
                "ok": False,
                "reason": "scope_missing",
                "status": int(getattr(e, "code", 0) or 0),
                "detail": "calendar scope is required",
                "error": err_text[:400],
            }
        return {
            "ok": False,
            "reason": "api_error",
            "status": int(getattr(e, "code", 0) or 0),
            "error": err_text[:400],
        }
    except Exception as e:
        return {"ok": False, "reason": "request_failed", "error": str(e)}

    _snapshot_cached(force_refresh=True)
    return {
        "ok": True,
        "reason": "deleted",
        "event": {
            "id": event_id,
        },
    }


@router.post("/api/google/gmail/mark-read")
def api_google_gmail_mark_read(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    message_id = str(payload.get("message_id") or "").strip()
    if not message_id:
        return {"ok": False, "reason": "invalid_params", "detail": "message_id is required"}

    access_token = _load_google_access_token(REPO_ROOT)
    if not access_token:
        return {"ok": False, "reason": "auth_missing", "detail": "google access token not found"}

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{quote(message_id, safe='')}/modify"
    body = {
        "removeLabelIds": ["UNREAD"],
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="POST",
        data=raw,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "manaos-rpg/0.1",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            body_raw = resp.read(2 * 1024 * 1024)
            data = json.loads(body_raw.decode("utf-8", errors="replace")) if body_raw else {}
    except urllib.error.HTTPError as e:
        try:
            err_raw = e.read(128 * 1024)
            err_text = err_raw.decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        err_lower = err_text.lower()
        if ("insufficient authentication scopes" in err_lower) or ("insufficientpermissions" in err_lower):
            return {
                "ok": False,
                "reason": "scope_missing",
                "status": int(getattr(e, "code", 0) or 0),
                "detail": "gmail.modify scope is required",
                "error": err_text[:400],
            }
        return {
            "ok": False,
            "reason": "api_error",
            "status": int(getattr(e, "code", 0) or 0),
            "error": err_text[:400],
        }
    except Exception as e:
        return {"ok": False, "reason": "request_failed", "error": str(e)}

    _snapshot_cached(force_refresh=True)
    return {
        "ok": True,
        "reason": "marked_read",
        "message": {
            "id": str(data.get("id") or message_id),
        },
    }


@router.get("/api/manual-check")
def api_manual_check() -> dict[str, Any]:
    if MANUAL_CHECK_FILE.exists():
        try:
            data = json.loads(MANUAL_CHECK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                normalized = _normalize_manual_check(data)
                normalized["stamps_recent"] = _load_manual_stamps()[:10]
                return normalized
        except (JSONDecodeError, OSError, TypeError, ValueError):
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
