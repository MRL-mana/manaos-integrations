from __future__ import annotations

import json
import sys
import time
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from core.config import (
    DEFAULT_MRL_MEMORY_BASE,
    DEFAULT_UNIFIED_API_BASE,
    EVENTS_FILE,
    REG,
    REPO_ROOT,
    STATE_FILE,
)
from core.helpers import load_yaml, _append_next_action, _append_next_action_hint
from core.unified_client import (
    _unified_api_key,
    _unified_dangerous_enabled,
    _unified_write_enabled,
    get_unified_integrations_status,
)
from core.http_client import _http_json_get
from collectors.events import append_event
from collectors.host_stats import get_host_stats
from collectors.items_collector import resolve_item_roots, scan_items
from collectors.ollama_runtime import get_ollama_ps_models
from collectors.services_runtime import compute_services_status
from services.actions import _actions_enabled, _load_actions


# ── RLAnything 統合 (安全インポート) ──
def _get_rl_dashboard() -> dict | None:
    """RLAnything のダッシュボード情報を安全に取得"""
    try:
        _repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
        if _repo_root not in sys.path:
            sys.path.insert(0, _repo_root)
        from rl_anything.orchestrator import RLAnythingOrchestrator
        rl = RLAnythingOrchestrator()
        dash = rl.get_dashboard()
        dash["skills"] = [s.to_dict() for s in rl.evolution.skills]
        dash["enabled"] = True
        return dash
    except Exception:
        return {"enabled": False, "error": "rl_anything not available"}


# ── 教訓サマリー (安全インポート) ──
def _get_lessons_summary() -> dict:
    """lessons_recorder.stats() のサマリーを安全に取得"""
    try:
        _misc = str(REPO_ROOT / "scripts" / "misc")
        if _misc not in sys.path:
            sys.path.insert(0, _misc)
        from lessons_recorder import get_lessons_recorder
        return get_lessons_recorder().stats()
    except Exception:
        return {"total": 0, "by_category": {}, "top_repeated": []}


# ── エージェントサマリー (安全インポート) ──
def _get_agents_summary() -> dict:
    """agent_tracker.stats() のサマリーを安全に取得"""
    try:
        _misc = str(REPO_ROOT / "scripts" / "misc")
        if _misc not in sys.path:
            sys.path.insert(0, _misc)
        from agent_tracker import get_agent_tracker
        return get_agent_tracker().stats()
    except Exception:
        return {"total": 0, "by_rank": {}, "ns_count": 0}
from services.unified_doctor import (
    _load_unified_proxy_rules,
    _maybe_refresh_unified_doctor_cache,
)


def _build_storage_status(host: dict[str, Any], item_roots: list[Any], items_recent: list[dict[str, Any]]) -> dict[str, Any]:
    root_map: dict[str, dict[str, Any]] = {}
    for root in item_roots:
        rid = str(getattr(root, "id", "") or "")
        if not rid:
            continue
        root_map[rid] = {
            "root_id": rid,
            "label": str(getattr(root, "label", rid) or rid),
            "path": str(getattr(root, "path", "") or ""),
            "recent_count": 0,
            "recent_size_bytes": 0,
            "images": 0,
            "videos": 0,
        }

    for item in items_recent:
        rid = str(item.get("root_id") or "")
        if not rid:
            continue
        if rid not in root_map:
            root_map[rid] = {
                "root_id": rid,
                "label": rid,
                "path": "",
                "recent_count": 0,
                "recent_size_bytes": 0,
                "images": 0,
                "videos": 0,
            }
        row = root_map[rid]
        row["recent_count"] += 1
        row["recent_size_bytes"] += int(item.get("size_bytes") or 0)
        kind = str(item.get("kind") or "")
        if kind == "image":
            row["images"] += 1
        elif kind == "video":
            row["videos"] += 1

    roots = sorted(root_map.values(), key=lambda x: str(x.get("label") or x.get("root_id") or ""))
    total_recent_size = sum(int(r.get("recent_size_bytes") or 0) for r in roots)
    total_recent_count = sum(int(r.get("recent_count") or 0) for r in roots)
    disk = host.get("disk") if isinstance(host, dict) else {}
    disk_free = float((disk or {}).get("free_gb") or 0)
    disk_total = float((disk or {}).get("total_gb") or 0)
    disk_used = max(0.0, disk_total - disk_free)
    disk_used_pct = (disk_used / disk_total * 100.0) if disk_total > 0 else None

    return {
        "disk": {
            "root": (host.get("host") or {}).get("disk_root") if isinstance(host, dict) else None,
            "free_gb": disk_free,
            "total_gb": disk_total,
            "used_gb": round(disk_used, 1),
            "used_percent": round(disk_used_pct, 1) if isinstance(disk_used_pct, float) else None,
        },
        "item_roots": roots,
        "recent_total_count": total_recent_count,
        "recent_total_size_bytes": total_recent_size,
    }


def _build_google_status(repo_root: Path) -> dict[str, Any]:
    desktop = Path(os.path.expandvars(r"%USERPROFILE%/Desktop")).resolve()
    file_candidates: dict[str, list[Path]] = {
        "credentials_json": [
            desktop / "credentials.json",
            repo_root / "credentials.json",
        ],
        "token_json": [
            desktop / "token.json",
            repo_root / "token.json",
        ],
        "google_drive_sync_config": [
            desktop / "google_drive_sync_config.json",
            repo_root / "google_drive_sync_config.json",
        ],
    }

    def _pick_existing(candidates: list[Path]) -> Path:
        for candidate in candidates:
            try:
                if candidate.exists():
                    return candidate
            except Exception:
                continue
        return candidates[0] if candidates else Path()

    files: dict[str, Any] = {}
    for key, candidates in file_candidates.items():
        path = _pick_existing(candidates)
        exists = path.exists()
        files[key] = {
            "exists": exists,
            "path": str(path),
            "mtime": int(path.stat().st_mtime) if exists else None,
        }

    integration_dir = repo_root / "google_drive_integration.py"
    setup_script = repo_root / "setup_google_drive.ps1"
    test_script = repo_root / "test_google_drive_integration.py"

    services = {
        "integration_module": {
            "exists": integration_dir.exists(),
            "path": str(integration_dir),
        },
        "setup_script": {
            "exists": setup_script.exists(),
            "path": str(setup_script),
        },
        "test_script": {
            "exists": test_script.exists(),
            "path": str(test_script),
        },
    }

    drive_ready = bool(files["credentials_json"]["exists"] and files["token_json"]["exists"])

    token_scopes: list[str] = []
    access_token = ""
    token_expiry_iso = ""
    token_expired: bool | None = None
    if files["token_json"]["exists"]:
        try:
            token_payload = json.loads(Path(files["token_json"]["path"]).read_text(encoding="utf-8", errors="replace"))
            if isinstance(token_payload, dict):
                raw_scopes = token_payload.get("scopes")
                if isinstance(raw_scopes, list):
                    token_scopes = [str(x).strip() for x in raw_scopes if str(x).strip()]
                elif isinstance(token_payload.get("scope"), str):
                    token_scopes = [s.strip() for s in str(token_payload.get("scope") or "").split(" ") if s.strip()]
                access_token = str(
                    token_payload.get("access_token")
                    or token_payload.get("token")
                    or ""
                ).strip()
                token_expiry_iso = str(token_payload.get("expiry") or "").strip()
        except Exception:
            token_scopes = []

    if token_expiry_iso:
        try:
            iso = token_expiry_iso.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            token_expired = now >= dt
        except Exception:
            token_expired = None

    def _scope_ready(required_fragments: list[str]) -> bool | None:
        if not token_scopes:
            return None
        lowered = [s.lower() for s in token_scopes]
        for frag in required_fragments:
            key = str(frag or "").lower()
            if key and any(key in s for s in lowered):
                return True
        return False

    capabilities_def = [
        {
            "id": "drive",
            "label": "Google Drive",
            "module_paths": [
                repo_root / "scripts" / "google" / "google_drive_integration.py",
                repo_root / "google_drive_integration.py",
            ],
            "scope_fragments": ["drive"],
            "module_required": False,
        },
        {
            "id": "calendar",
            "label": "Google Calendar",
            "module_paths": [
                repo_root / "scripts" / "google" / "google_calendar_tasks_sheets_integration.py",
            ],
            "scope_fragments": ["calendar"],
            "module_required": False,
        },
        {
            "id": "tasks",
            "label": "Google Tasks (TODO)",
            "module_paths": [
                repo_root / "scripts" / "google" / "google_calendar_tasks_sheets_integration.py",
            ],
            "scope_fragments": ["tasks"],
            "module_required": False,
        },
        {
            "id": "gmail",
            "label": "Gmail",
            "module_paths": [
                repo_root / "scripts" / "google" / "google_gmail_integration.py",
                repo_root / "gmail_integration.py",
            ],
            "scope_fragments": ["gmail"],
            "module_required": False,
        },
        {
            "id": "sheets",
            "label": "Google Sheets",
            "module_paths": [
                repo_root / "scripts" / "google" / "google_calendar_tasks_sheets_integration.py",
                repo_root / "scripts" / "document_processing" / "excel_to_google_sheets.py",
            ],
            "scope_fragments": ["spreadsheets", "sheets"],
            "module_required": False,
        },
        {
            "id": "photos",
            "label": "Google Photos",
            "module_paths": [
                repo_root / "scripts" / "google" / "google_photos_integration.py",
                repo_root / "google_photos_integration.py",
            ],
            "scope_fragments": ["photoslibrary"],
            "module_required": False,
        },
    ]

    capabilities: list[dict[str, Any]] = []
    for cap in capabilities_def:
        module_exists = any(path.exists() for path in cap["module_paths"])
        module_required = bool(cap.get("module_required", False))
        scope_status = _scope_ready(cap["scope_fragments"])
        usable = bool(drive_ready and (token_expired is not True) and (scope_status is True) and (module_exists or not module_required))
        if not drive_ready:
            reason = "auth_missing"
        elif token_expired is True:
            reason = "token_expired"
        elif not module_exists:
            reason = "module_missing" if module_required else "ready_no_local_module"
        elif scope_status is False:
            reason = "scope_missing"
        elif scope_status is None:
            reason = "scope_unknown"
        else:
            reason = "ready"

        capabilities.append(
            {
                "id": cap["id"],
                "label": cap["label"],
                "usable": usable,
                "reason": reason,
                "module_exists": module_exists,
                "module_required": module_required,
                "scope_ready": scope_status,
            }
        )

    usable_count = sum(1 for c in capabilities if bool(c.get("usable")))

    next_steps: list[str] = []
    if not files.get("credentials_json", {}).get("exists"):
        next_steps.append("credentials.json を配置（Desktop または manaos_integrations 直下）")
    if not files.get("token_json", {}).get("exists"):
        next_steps.append("token.json を作成（Google認証を実行）")
    if token_expired is True:
        next_steps.append("token が期限切れ：google_auth_reauth.py で再認証")
    if any(c.get("reason") == "scope_missing" for c in capabilities):
        next_steps.append("必要scope不足：再認証時に Calendar/Tasks/Gmail/Sheets scope を付与")

    drive_scope_ready = _scope_ready(["drive"])
    gmail_scope_ready = _scope_ready(["gmail"])
    gmail_modify_scope_ready = _scope_ready(["gmail.modify"])
    calendar_scope_ready = _scope_ready(["calendar"])
    tasks_scope_ready = _scope_ready(["tasks"])
    if gmail_modify_scope_ready is False:
        next_steps.append("Gmail既読操作には gmail.modify scope が必要（google_auth_reauth_full.py で再認証）")

    live_preview: dict[str, Any] = {
        "drive_files": {
            "ok": False,
            "reason": "not_attempted",
            "files": [],
        },
        "gmail_profile": {
            "ok": False,
            "reason": "not_attempted",
            "can_mark_read": False,
            "email": "",
            "messages_total": None,
            "threads_total": None,
            "unread_messages": [],
        },
        "calendar_events": {
            "ok": False,
            "reason": "not_attempted",
            "events": [],
        },
        "tasks_open": {
            "ok": False,
            "reason": "not_attempted",
            "tasks": [],
        },
    }

    can_probe = bool(drive_ready and access_token and (token_expired is not True))
    auth_headers = {"Authorization": f"Bearer {access_token}"} if can_probe else {}

    if can_probe and (drive_scope_ready is True):
        drive_res = _http_json_get(
            "https://www.googleapis.com/drive/v3/files?pageSize=8&fields=files(id,name,mimeType,modifiedTime)&orderBy=modifiedTime%20desc",
            timeout_s=3.5,
            headers=auth_headers,
        )
        if drive_res.get("ok"):
            data = drive_res.get("data") if isinstance(drive_res.get("data"), dict) else {}
            files_list = data.get("files") if isinstance(data.get("files"), list) else []
            live_preview["drive_files"] = {
                "ok": True,
                "reason": "ready",
                "files": [
                    {
                        "id": str(x.get("id") or ""),
                        "name": str(x.get("name") or ""),
                        "mimeType": str(x.get("mimeType") or ""),
                        "modifiedTime": str(x.get("modifiedTime") or ""),
                    }
                    for x in files_list
                    if isinstance(x, dict)
                ],
            }
        else:
            live_preview["drive_files"] = {
                "ok": False,
                "reason": "api_error",
                "status": drive_res.get("status"),
                "error": str(drive_res.get("error") or "")[:240],
                "files": [],
            }
    elif drive_scope_ready is False:
        live_preview["drive_files"]["reason"] = "scope_missing"
    elif not drive_ready:
        live_preview["drive_files"]["reason"] = "auth_missing"
    elif token_expired is True:
        live_preview["drive_files"]["reason"] = "token_expired"

    if can_probe and (gmail_scope_ready is True):
        gmail_res = _http_json_get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            timeout_s=3.5,
            headers=auth_headers,
        )
        if gmail_res.get("ok"):
            data = gmail_res.get("data") if isinstance(gmail_res.get("data"), dict) else {}
            unread_messages: list[dict[str, Any]] = []
            unread_list_res = _http_json_get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages?q=is%3Aunread&maxResults=3",
                timeout_s=3.5,
                headers=auth_headers,
            )
            if unread_list_res.get("ok"):
                list_data = unread_list_res.get("data") if isinstance(unread_list_res.get("data"), dict) else {}
                msgs = list_data.get("messages") if isinstance(list_data.get("messages"), list) else []
                for msg in msgs:
                    if not isinstance(msg, dict):
                        continue
                    msg_id = str(msg.get("id") or "").strip()
                    if not msg_id:
                        continue
                    detail_res = _http_json_get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{quote(msg_id, safe='')}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date",
                        timeout_s=3.5,
                        headers=auth_headers,
                    )
                    if not detail_res.get("ok"):
                        continue
                    detail = detail_res.get("data") if isinstance(detail_res.get("data"), dict) else {}
                    payload = detail.get("payload") if isinstance(detail.get("payload"), dict) else {}
                    headers = payload.get("headers") if isinstance(payload.get("headers"), list) else []
                    subject = ""
                    sender = ""
                    date_raw = ""
                    for header in headers:
                        if not isinstance(header, dict):
                            continue
                        name = str(header.get("name") or "").lower()
                        value = str(header.get("value") or "")
                        if name == "subject":
                            subject = value
                        elif name == "from":
                            sender = value
                        elif name == "date":
                            date_raw = value
                    unread_messages.append(
                        {
                            "id": msg_id,
                            "subject": subject,
                            "from": sender,
                            "date": date_raw,
                        }
                    )
            live_preview["gmail_profile"] = {
                "ok": True,
                "reason": "ready",
                "can_mark_read": gmail_modify_scope_ready is True,
                "email": str(data.get("emailAddress") or ""),
                "messages_total": data.get("messagesTotal"),
                "threads_total": data.get("threadsTotal"),
                "unread_messages": unread_messages,
            }
        else:
            live_preview["gmail_profile"] = {
                "ok": False,
                "reason": "api_error",
                "can_mark_read": gmail_modify_scope_ready is True,
                "status": gmail_res.get("status"),
                "error": str(gmail_res.get("error") or "")[:240],
                "email": "",
                "messages_total": None,
                "threads_total": None,
                "unread_messages": [],
            }
    elif gmail_scope_ready is False:
        live_preview["gmail_profile"]["reason"] = "scope_missing"
    elif not drive_ready:
        live_preview["gmail_profile"]["reason"] = "auth_missing"
    elif token_expired is True:
        live_preview["gmail_profile"]["reason"] = "token_expired"

    if can_probe and (calendar_scope_ready is True):
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        calendar_url = (
            "https://www.googleapis.com/calendar/v3/calendars/primary/events"
            f"?maxResults=5&singleEvents=true&orderBy=startTime&timeMin={quote(now_iso, safe='')}"
        )
        calendar_res = _http_json_get(
            calendar_url,
            timeout_s=3.5,
            headers=auth_headers,
        )
        if calendar_res.get("ok"):
            data = calendar_res.get("data") if isinstance(calendar_res.get("data"), dict) else {}
            event_items = data.get("items") if isinstance(data.get("items"), list) else []
            live_preview["calendar_events"] = {
                "ok": True,
                "reason": "ready",
                "events": [
                    {
                        "id": str(x.get("id") or ""),
                        "summary": str(x.get("summary") or ""),
                        "start": str(((x.get("start") or {}).get("dateTime") or (x.get("start") or {}).get("date") or "")),
                    }
                    for x in event_items
                    if isinstance(x, dict)
                ],
            }
        else:
            live_preview["calendar_events"] = {
                "ok": False,
                "reason": "api_error",
                "status": calendar_res.get("status"),
                "error": str(calendar_res.get("error") or "")[:240],
                "events": [],
            }
    elif calendar_scope_ready is False:
        live_preview["calendar_events"]["reason"] = "scope_missing"
    elif not drive_ready:
        live_preview["calendar_events"]["reason"] = "auth_missing"
    elif token_expired is True:
        live_preview["calendar_events"]["reason"] = "token_expired"

    if can_probe and (tasks_scope_ready is True):
        lists_res = _http_json_get(
            "https://tasks.googleapis.com/tasks/v1/users/@me/lists?maxResults=1",
            timeout_s=3.5,
            headers=auth_headers,
        )
        if lists_res.get("ok"):
            data = lists_res.get("data") if isinstance(lists_res.get("data"), dict) else {}
            task_lists = data.get("items") if isinstance(data.get("items"), list) else []
            task_list_id = ""
            if task_lists and isinstance(task_lists[0], dict):
                task_list_id = str(task_lists[0].get("id") or "")

            if task_list_id:
                tasks_res = _http_json_get(
                    f"https://tasks.googleapis.com/tasks/v1/lists/{quote(task_list_id, safe='')}/tasks?showCompleted=false&maxResults=5",
                    timeout_s=3.5,
                    headers=auth_headers,
                )
                if tasks_res.get("ok"):
                    tdata = tasks_res.get("data") if isinstance(tasks_res.get("data"), dict) else {}
                    task_items = tdata.get("items") if isinstance(tdata.get("items"), list) else []
                    live_preview["tasks_open"] = {
                        "ok": True,
                        "reason": "ready",
                        "tasks": [
                            {
                                "id": str(x.get("id") or ""),
                                "task_list_id": task_list_id,
                                "title": str(x.get("title") or ""),
                                "due": str(x.get("due") or ""),
                            }
                            for x in task_items
                            if isinstance(x, dict)
                        ],
                    }
                else:
                    live_preview["tasks_open"] = {
                        "ok": False,
                        "reason": "api_error",
                        "status": tasks_res.get("status"),
                        "error": str(tasks_res.get("error") or "")[:240],
                        "tasks": [],
                    }
            else:
                live_preview["tasks_open"] = {
                    "ok": True,
                    "reason": "ready",
                    "tasks": [],
                }
        else:
            live_preview["tasks_open"] = {
                "ok": False,
                "reason": "api_error",
                "status": lists_res.get("status"),
                "error": str(lists_res.get("error") or "")[:240],
                "tasks": [],
            }
    elif tasks_scope_ready is False:
        live_preview["tasks_open"]["reason"] = "scope_missing"
    elif not drive_ready:
        live_preview["tasks_open"]["reason"] = "auth_missing"
    elif token_expired is True:
        live_preview["tasks_open"]["reason"] = "token_expired"

    return {
        "drive_ready": drive_ready,
        "auth_ready": drive_ready,
        "files": files,
        "services": services,
        "token_scopes": token_scopes,
        "token": {
            "has_access_token": bool(access_token),
            "expiry": token_expiry_iso or None,
            "expired": token_expired,
        },
        "capabilities": capabilities,
        "capabilities_summary": {
            "usable": usable_count,
            "total": len(capabilities),
        },
        "next_steps": next_steps,
        "live_preview": live_preview,
    }


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _age_seconds_from_iso(ts_value: Any) -> int | None:
    if not isinstance(ts_value, str) or not ts_value.strip():
        return None
    try:
        dt = datetime.fromisoformat(ts_value)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        return max(0, int((now - dt).total_seconds()))
    except Exception:
        return None


def _build_chain_history_stats(history_path: Path, recent_n: int = 20) -> dict[str, Any]:
    day_seconds = 24 * 60 * 60
    total_24h = 0
    ok_24h = 0
    recent_flags: list[bool] = []

    try:
        if history_path.exists():
            lines = history_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for raw in reversed(lines):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                ok_flag = bool(obj.get("ok"))
                if len(recent_flags) < recent_n:
                    recent_flags.append(ok_flag)

                ts_value = obj.get("ts")
                age_sec = _age_seconds_from_iso(ts_value)
                if age_sec is not None and age_sec <= day_seconds:
                    total_24h += 1
                    if ok_flag:
                        ok_24h += 1
    except Exception:
        pass

    recent_total = len(recent_flags)
    recent_ok = sum(1 for value in recent_flags if value)

    rate_24h = (ok_24h / total_24h * 100.0) if total_24h > 0 else None
    rate_recent = (recent_ok / recent_total * 100.0) if recent_total > 0 else None

    return {
        "window_hours": 24,
        "recent_window": recent_n,
        "count24h": total_24h,
        "ok24h": ok_24h,
        "rate24h": round(rate_24h, 1) if rate_24h is not None else None,
        "countRecent": recent_total,
        "okRecent": recent_ok,
        "rateRecent": round(rate_recent, 1) if rate_recent is not None else None,
    }


def _overall_level(chain_ok: bool, scheduler_ok: bool, llm_ok: bool, history_stats: dict[str, Any]) -> tuple[str, str]:
    rate_recent = history_stats.get("rateRecent")
    rate_24h = history_stats.get("rate24h")

    if not chain_ok or not scheduler_ok or not llm_ok:
        return "ALERT", "component_down"

    rates: list[float] = []
    for value in (rate_recent, rate_24h):
        if isinstance(value, (int, float)):
            rates.append(float(value))

    if not rates:
        return "WATCH", "no_history_data"

    min_rate = min(rates)
    if min_rate >= 95.0:
        return "OK", "all_green"
    if min_rate >= 80.0:
        return "WATCH", "success_rate_caution"
    return "ALERT", "success_rate_low"


def _build_autonomy_status() -> dict[str, Any]:
    logs_dir = REPO_ROOT / "logs"
    chain_latest_path = logs_dir / "rpg_full_health_chain.latest.json"
    chain_history_path = logs_dir / "rpg_full_health_chain.history.jsonl"
    lifecycle_latest_path = logs_dir / "rpg_full_health_chain_task_lifecycle.latest.json"

    chain_latest = _read_json_file(chain_latest_path) or {}
    lifecycle_latest = _read_json_file(lifecycle_latest_path) or {}

    llm_health = _http_json_get(f"{DEFAULT_UNIFIED_API_BASE}/api/llm/health", timeout_s=3.5)
    policy_status = _http_json_get(f"{DEFAULT_UNIFIED_API_BASE}/api/llm/policy/status", timeout_s=3.5)

    llm_data = llm_health.get("data") if isinstance(llm_health.get("data"), dict) else {}
    policy_data = policy_status.get("data") if isinstance(policy_status.get("data"), dict) else {}
    models = llm_data.get("models") if isinstance(llm_data.get("models"), list) else []
    status_summary = lifecycle_latest.get("status_summary") if isinstance(lifecycle_latest.get("status_summary"), list) else []

    chain_ok = bool(chain_latest.get("ok"))
    scheduler_ok = bool(lifecycle_latest.get("ok"))
    llm_ok = bool(llm_health.get("ok"))
    overall_ok = chain_ok and scheduler_ok and llm_ok
    summary_text = (
        f"chain={'PASS' if chain_ok else 'FAIL'}"
        f" / scheduler={'OK' if scheduler_ok else 'NG'}"
        f" / llm={'ONLINE' if llm_ok else 'OFFLINE'}"
    )
    history_stats = _build_chain_history_stats(chain_history_path, recent_n=20)
    overall_level, overall_reason = _overall_level(chain_ok, scheduler_ok, llm_ok, history_stats)

    return {
        "rpg_health_chain": {
            "found": bool(chain_latest),
            "path": str(chain_latest_path),
            "ok": bool(chain_latest.get("ok")),
            "ok_reason": chain_latest.get("ok_reason"),
            "last_ts": chain_latest.get("ts"),
            "age_sec": _age_seconds_from_iso(chain_latest.get("ts")),
            "failed_step_count": int(chain_latest.get("failed_step_count") or 0),
            "failed_steps": chain_latest.get("failed_steps") if isinstance(chain_latest.get("failed_steps"), list) else [],
        },
        "scheduler": {
            "found": bool(lifecycle_latest),
            "path": str(lifecycle_latest_path),
            "ok": bool(lifecycle_latest.get("ok")),
            "ok_reason": lifecycle_latest.get("ok_reason"),
            "task_name": lifecycle_latest.get("task_name"),
            "interval_minutes": lifecycle_latest.get("interval_minutes"),
            "last_ts": lifecycle_latest.get("ts"),
            "age_sec": _age_seconds_from_iso(lifecycle_latest.get("ts")),
            "status_summary": status_summary,
        },
        "unified_llm": {
            "ok": bool(llm_health.get("ok")),
            "status": llm_health.get("status"),
            "error": llm_health.get("error"),
            "llm_server": llm_data.get("llm_server"),
            "available_models": llm_data.get("available_models"),
            "models": models,
            "policy_ok": bool(policy_status.get("ok")),
            "policy_status": policy_status.get("status"),
            "policy_error": policy_status.get("error"),
            "policy_fail_closed": policy_data.get("fail_closed"),
            "policy_guard_enabled": policy_data.get("guard_enabled"),
        },
        "overall": {
            "ok": overall_ok,
            "level": overall_level,
            "reason": overall_reason,
            "summary": summary_text,
        },
        "history_stats": history_stats,
    }


def autonomy_status() -> dict[str, Any]:
    return _build_autonomy_status()


def compute_danger(host: dict, services: list[dict]) -> int:
    danger = 0
    cpu = float(host.get("cpu", {}).get("percent") or 0)
    mem = float(host.get("mem", {}).get("percent") or 0)
    disk_free = float(host.get("disk", {}).get("free_gb") or 0)

    if cpu > 90:
        danger += 2
    if mem > 90:
        danger += 2
    if disk_free < 20:
        danger += 2

    nvidia = host.get("gpu", {}).get("nvidia") or []
    try:
        for g in nvidia:
            t = g.get("temperature_c")
            u = g.get("utilization_gpu")
            used = g.get("mem_used_mb")
            total = g.get("mem_total_mb")
            if t is not None and int(t) >= 85:
                danger += 2
            if u is not None and int(u) >= 95:
                danger += 1
            if used is not None and total is not None and int(total) > 0:
                vram_pct = int(round((int(used) / int(total)) * 100))
                if vram_pct >= 95:
                    danger += 2
                elif vram_pct >= 90:
                    danger += 1
    except Exception:
        pass

    always_on_down = any((not s.get("alive")) and ("always_on" in (s.get("tags") or [])) for s in services)
    if always_on_down:
        danger += 3

    try:
        for s in services:
            tags = s.get("tags") or []
            if "always_on" not in tags:
                continue
            if s.get("degraded"):
                danger += 1
            if s.get("docker_health") == "unhealthy":
                danger += 2
            rc = s.get("restart_count")
            if isinstance(rc, int) and rc >= 5:
                danger += 1
            if isinstance(rc, int) and rc >= 10:
                danger += 1
    except Exception:
        pass

    return int(danger)


def snapshot() -> dict[str, Any]:
    services_yaml = load_yaml(REG / "services.yaml")
    models_yaml = load_yaml(REG / "models.yaml")
    menu_yaml = load_yaml(REG / "features.yaml")
    devices_yaml = load_yaml(REG / "devices.yaml")
    quests_yaml = load_yaml(REG / "quests.yaml")
    skills_yaml = load_yaml(REG / "skills.yaml")
    items_yaml = load_yaml(REG / "items.yaml")
    prompts_yaml = load_yaml(REG / "prompts.yaml")
    actions = _load_actions()

    services = list(services_yaml.get("services") or [])
    models = list(models_yaml.get("models") or [])
    menu = list(menu_yaml.get("menu") or [])
    devices = list(devices_yaml.get("devices") or [])
    quests = list(quests_yaml.get("quests") or [])
    skills = list(skills_yaml.get("skills") or [])

    prompts = prompts_yaml.get("prompts") or {}
    if not isinstance(prompts, dict):
        prompts = {}

    unified_proxy_rules = _load_unified_proxy_rules()

    item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
    items_recent = scan_items(item_roots)

    host = get_host_stats()
    services_status = compute_services_status(services)
    danger = compute_danger(host, services_status)

    unified_alive = any(str(s.get("id")) == "unified_api_server" and bool(s.get("alive")) for s in services_status)
    if unified_alive:
        unified_integrations = get_unified_integrations_status()
    else:
        unified_integrations = {
            "ok": False,
            "url": f"{DEFAULT_UNIFIED_API_BASE}/api/integrations/status",
            "status": 0,
            "error": "unified_api_down",
            "auth_configured": bool(_unified_api_key()),
        }

    # mrl-memory (Unified memory未搭載時のフォールバック先)
    mrl_health = _http_json_get(f"{DEFAULT_MRL_MEMORY_BASE}/health", timeout_s=1.0)
    mrl_metrics = _http_json_get(f"{DEFAULT_MRL_MEMORY_BASE}/api/metrics", timeout_s=1.0)
    mrl_status: dict[str, Any] = {
        "ok": bool(mrl_health.get("ok")),
        "base": DEFAULT_MRL_MEMORY_BASE,
        "health": mrl_health.get("data") if mrl_health.get("ok") else None,
        "metrics": mrl_metrics.get("data") if mrl_metrics.get("ok") else None,
        "checks": {
            "health": {
                "url": f"{DEFAULT_MRL_MEMORY_BASE}/health",
                "ok": bool(mrl_health.get("ok")),
                "status": mrl_health.get("status"),
                "error": mrl_health.get("error"),
            },
            "metrics": {
                "url": f"{DEFAULT_MRL_MEMORY_BASE}/api/metrics",
                "ok": bool(mrl_metrics.get("ok")),
                "status": mrl_metrics.get("status"),
                "error": mrl_metrics.get("error"),
            },
        },
    }

    prev_state: dict[str, Any] = {}
    if STATE_FILE.exists():
        try:
            prev_state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            prev_state = {}

    prev_services = prev_state.get("services") or []
    prev_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(prev_services, list):
        for ps in prev_services:
            sid = ps.get("id")
            if sid:
                prev_by_id[str(sid)] = ps

    alive_map = {str(s.get("id")): bool(s.get("alive")) for s in services_status}
    for s in services_status:
        sid = str(s.get("id"))
        deps = list(s.get("depends_on") or [])
        deps_down = [d for d in deps if not alive_map.get(str(d), False)]
        s["deps_down"] = deps_down
        s["blocked"] = len(deps_down) > 0

        prev_blocked = bool((prev_by_id.get(sid) or {}).get("blocked"))
        now_blocked = bool(s.get("blocked"))
        if now_blocked and not prev_blocked:
            append_event(EVENTS_FILE, "blocked", "依存関係によりブロックされました", {"service": sid, "deps_down": deps_down})
        if (not now_blocked) and prev_blocked:
            append_event(EVENTS_FILE, "unblocked", "ブロックが解除されました", {"service": sid})

        prev_health = (prev_by_id.get(sid) or {}).get("docker_health")
        now_health = s.get("docker_health")
        if now_health and now_health != prev_health:
            if now_health == "unhealthy":
                append_event(EVENTS_FILE, "unhealthy", "Docker health が UNHEALTHY になりました", {"service": sid})
            if prev_health == "unhealthy" and now_health == "healthy":
                append_event(EVENTS_FILE, "healthy", "Docker health が HEALTHY に復帰しました", {"service": sid})

        prev_rc = (prev_by_id.get(sid) or {}).get("restart_count")
        now_rc = s.get("restart_count")
        if isinstance(now_rc, int):
            try:
                prev_rc_int = int(prev_rc) if prev_rc is not None else None
            except Exception:
                prev_rc_int = None

            if prev_rc_int is not None and now_rc > prev_rc_int:
                delta = now_rc - prev_rc_int
                append_event(
                    EVENTS_FILE,
                    "restart_increase",
                    "再起動回数が増加しました（ループ兆候）",
                    {"service": sid, "restart_count": now_rc, "delta": delta},
                )

    ollama_loaded = set(get_ollama_ps_models())
    models_enriched: list[dict[str, Any]] = []
    for m in models:
        m2 = dict(m)
        key = None
        if isinstance(m.get("ollama"), str):
            key = m.get("ollama")
        runtime = m.get("runtime")
        if key is None and isinstance(runtime, dict) and isinstance(runtime.get("ollama"), str):
            key = runtime.get("ollama")
        if key:
            m2["loaded"] = key in ollama_loaded
        models_enriched.append(m2)

    next_actions: list[str] = []
    next_action_hints: list[dict[str, Any]] = []
    disk_free = float(host.get("disk", {}).get("free_gb") or 0)
    if disk_free and disk_free < 50:
        next_actions.append("空き容量が少なめ：古いログ/モデル/生成物の退避や削除")
    try:
        disks = host.get("disks") if isinstance(host, dict) else None
        if isinstance(disks, list):
            disk_alert = []
            disk_watch = []
            for d in disks:
                if not isinstance(d, dict):
                    continue
                root = str(d.get("root") or "")
                used_pct_raw = d.get("used_percent")
                try:
                    used_pct = float(used_pct_raw)
                except Exception:
                    continue
                if used_pct >= 90:
                    disk_alert.append(f"{root}({used_pct:.1f}%)")
                elif used_pct >= 80:
                    disk_watch.append(f"{root}({used_pct:.1f}%)")
            if disk_alert:
                _append_next_action(
                    next_actions,
                    f"ストレージ逼迫(ALERT)：{', '.join(disk_alert)} / 大容量ファイル整理・退避を推奨",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：逼迫ドライブ大容量ファイル Top10（自動判定）",
                    action_id="disk_top_hot",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：C(OS)/D(AI)整理候補レポート（削除なし）",
                    action_id="disk_tidy_c_d_report",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：CのAI生成物をD(AI)へ整理移動",
                    action_id="organize_c_ai_to_d",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：Google DriveへD(AI)最近生成物をバックアップ",
                    action_id="google_drive_backup_recent",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：Google Driveへバックアップ後にDへ退避",
                    action_id="google_drive_backup_and_stage",
                )
                if any(str(x).startswith("D:\\") for x in (disk_alert + disk_watch)):
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：Dドライブ大容量ファイル Top10",
                        action_id="disk_top10_d",
                    )
                if any(str(x).startswith("H:\\") for x in (disk_alert + disk_watch)):
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：Hドライブ大容量ファイル Top10",
                        action_id="disk_top10_h",
                    )
            elif disk_watch:
                _append_next_action(
                    next_actions,
                    f"ストレージ高負荷(WATCH)：{', '.join(disk_watch)} / 早めのクリーンアップを推奨",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：逼迫ドライブ大容量ファイル Top10（自動判定）",
                    action_id="disk_top_hot",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：C(OS)/D(AI)整理候補レポート（削除なし）",
                    action_id="disk_tidy_c_d_report",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：CのAI生成物をD(AI)へ整理移動",
                    action_id="organize_c_ai_to_d",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：Google DriveへD(AI)最近生成物をバックアップ",
                    action_id="google_drive_backup_recent",
                )
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：Google Driveへバックアップ後にDへ退避",
                    action_id="google_drive_backup_and_stage",
                )
                if any(str(x).startswith("D:\\") for x in disk_watch):
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：Dドライブ大容量ファイル Top10",
                        action_id="disk_top10_d",
                    )
                if any(str(x).startswith("H:\\") for x in disk_watch):
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：Hドライブ大容量ファイル Top10",
                        action_id="disk_top10_h",
                    )
    except Exception:
        pass
    cpu = float(host.get("cpu", {}).get("percent") or 0)
    if cpu > 90:
        next_actions.append("CPU高負荷：重い処理を止める/再起動/並列数を下げる")
    mem = float(host.get("mem", {}).get("percent") or 0)
    if mem > 90:
        next_actions.append("RAM逼迫：常駐を減らす/キャッシュを削る/再起動")
    try:
        for g in (host.get("gpu", {}).get("nvidia") or []):
            t = g.get("temperature_c")
            u = g.get("utilization_gpu")
            used = g.get("mem_used_mb")
            total = g.get("mem_total_mb")
            power = g.get("power_draw_w")
            if t is not None and int(t) >= 85:
                next_actions.append("GPU温度高い：生成を止める/冷却強化/ファン確認")
                break
            if u is not None and int(u) >= 98:
                next_actions.append("GPU使用率ほぼ100%：キュー詰まりなら停止/再起動を検討")
            if used is not None and total is not None and int(total) > 0:
                vram_pct = int(round((int(used) / int(total)) * 100))
                if vram_pct >= 95:
                    next_actions.append("VRAM逼迫（95%+）：モデル/生成を止める、不要プロセス終了")
                    break
                if vram_pct >= 90:
                    next_actions.append("VRAM高め（90%+）：キューや常駐を整理")
            if power is not None and int(power) >= 300:
                next_actions.append("GPU電力高め：負荷が常時高いなら生成/学習の見直し")
                break
    except Exception:
        pass

    apps = host.get("gpu", {}).get("apps") or []
    if isinstance(apps, list) and apps:
        top = apps[:5]
        offenders = []
        for a in top:
            nm = a.get("process_name")
            pid = a.get("pid")
            mb = a.get("used_gpu_memory_mb")
            if mb is None:
                continue
            offenders.append(f"{nm}(pid={pid})={mb}MB")
        if offenders:
            next_actions.append("VRAM犯人: " + "; ".join(offenders))

    always_on_down = [s.get("id") for s in services_status if (not s.get("alive")) and ("always_on" in (s.get("tags") or []))]
    if always_on_down:
        next_actions.append(f"常駐が落ちてる：{', '.join([str(x) for x in always_on_down])} を復旧")

    try:
        if mrl_status.get("ok") and isinstance(mrl_status.get("metrics"), dict):
            cfg = mrl_status.get("metrics", {}).get("config")
            if isinstance(cfg, dict):
                write_mode = str(cfg.get("write_mode") or "").strip().lower()
                write_enabled = str(cfg.get("write_enabled") or "").strip()
                if write_mode == "readonly" or write_enabled in {"0", "false", "no"}:
                    next_actions.append(
                        "mrl-memory が readonly：memory store は readonly_mode（永続化したいなら MRL_FWPKM_WRITE_ENABLED=1 を明示）"
                    )
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：mrl-memory 書き込みON（full / recreate）",
                        action_id="mrl_memory_write_on_full",
                    )
                else:
                    _append_next_action_hint(
                        next_action_hints,
                        label="実行：mrl-memory 書き込みOFF（readonly / recreate）",
                        action_id="mrl_memory_write_off",
                    )
    except Exception:
        pass

    unhealthy = [
        str(s.get("id"))
        for s in services_status
        if ("always_on" in (s.get("tags") or [])) and (s.get("docker_health") == "unhealthy")
    ]
    if unhealthy:
        next_actions.append(f"UNHEALTHY：{', '.join(unhealthy)} の依存先/ヘルスURL/ログ確認")

    restart_loop = [
        str(s.get("id"))
        for s in services_status
        if ("always_on" in (s.get("tags") or [])) and isinstance(s.get("restart_count"), int) and int(s.get("restart_count")) >= 5
    ]
    if restart_loop:
        next_actions.append(f"再起動多い：{', '.join(restart_loop)}（設定変更/依存/ログを確認）")

    blocked_svcs = [str(s.get("id")) for s in services_status if bool(s.get("blocked"))]
    if blocked_svcs:
        next_actions.append(f"blocked解除：依存サービスを先に復旧 → {', '.join(blocked_svcs)} を再確認")

    if unified_alive:
        d = _maybe_refresh_unified_doctor_cache()
        counts = d.get("counts") if isinstance(d, dict) else None
        d_results = d.get("results") if isinstance(d, dict) else None
        if not isinstance(d_results, list):
            d_results = []

        has_enabled_get_rule = any(
            isinstance(r, dict)
            and bool(r.get("enabled", True))
            and str(r.get("method") or "GET").upper() == "GET"
            and isinstance(r.get("path"), str)
            and ("{" not in str(r.get("path")))
            for r in unified_proxy_rules
        )

        if any(
            isinstance(r, dict) and str(r.get("recommend_action_id") or "") == "unified_proxy_disable_404"
            for r in d_results
        ):
            _append_next_action_hint(
                next_action_hints,
                label="実行：Unified allowlist 404自動無効化（台帳掃除 / GETのみ）",
                action_id="unified_proxy_disable_404",
            )

        if isinstance(counts, dict):
            try:
                total = int(counts.get("total") or 0)
            except Exception:
                total = 0
            try:
                skipped = int(counts.get("skipped") or 0)
            except Exception:
                skipped = 0
            try:
                not_found_get = int(counts.get("not_found_get") or 0)
            except Exception:
                not_found_get = 0
            try:
                conn_err = int(counts.get("conn_error") or 0)
            except Exception:
                conn_err = 0
            try:
                auth_cnt = int(counts.get("auth") or 0)
            except Exception:
                auth_cnt = 0

            can_act_on_unified = conn_err == 0

            openapi_paths_count = None
            if isinstance(unified_integrations, dict):
                od = unified_integrations.get("data") if isinstance(unified_integrations.get("data"), dict) else {}
                oo = od.get("openapi") if isinstance(od.get("openapi"), dict) else {}
                pc = oo.get("paths_count")
                if isinstance(pc, int):
                    openapi_paths_count = pc
                else:
                    try:
                        openapi_paths_count = int(pc) if pc is not None else None
                    except Exception:
                        openapi_paths_count = None

            rules_count = len(unified_proxy_rules)
            sync_likely_useful = (
                total == 0
                or not_found_get >= 1
                or (isinstance(openapi_paths_count, int) and openapi_paths_count >= 1 and rules_count < openapi_paths_count)
            )

            if can_act_on_unified and sync_likely_useful:
                _append_next_action_hint(
                    next_action_hints,
                    label="実行：Unified allowlist 同期（OpenAPI→unified_proxy.yaml）",
                    action_id="unified_proxy_sync",
                )

            if conn_err >= 8:
                _append_next_action(
                    next_actions,
                    "Unified API到達エラー多数：unified_api_server(9502) の起動/復旧を確認",
                )

            if total >= 1 and skipped >= total:
                if int(counts.get("skipped_post") or 0) >= 1:
                    _append_next_action(
                        next_actions,
                        "Unified allowlist が POST中心のため安全probeができない：OpenAPI/実行結果ベースで運用（必要ならinclude_disabledで一覧確認）",
                    )
                    if can_act_on_unified and (not has_enabled_get_rule):
                        get_no_params_cnt = None
                        if isinstance(unified_integrations, dict):
                            od2 = unified_integrations.get("data") if isinstance(unified_integrations.get("data"), dict) else {}
                            oo2 = od2.get("openapi") if isinstance(od2.get("openapi"), dict) else {}
                            get_no_params_cnt = oo2.get("get_paths_no_params_count")
                        try:
                            get_no_params_cnt_i = int(get_no_params_cnt) if get_no_params_cnt is not None else 0
                        except Exception:
                            get_no_params_cnt_i = 0

                        if get_no_params_cnt_i >= 1:
                            _append_next_action_hint(
                                next_action_hints,
                                label="実行：Unified allowlist コアread有効化（安全なGETのみ）",
                                action_id="unified_proxy_enable_core_read",
                            )
                else:
                    _append_next_action(
                        next_actions,
                        "Unified allowlistの有効ルールが少ない/パスパラメータ必須のみ：『Proxy Doctor（include_disabled=true）』で確認→同期/有効化を検討",
                    )

            if auth_cnt >= 1 and not bool(_unified_api_key()):
                _append_next_action(
                    next_actions,
                    "Unified API認証が必要：環境変数 MANAOS_UNIFIED_API_KEY（read-only可）を設定",
                )

            if not_found_get >= 1:
                _append_next_action(
                    next_actions,
                    "Unified allowlistにGET 404が残存：クエスト『Unified allowlist 404自動無効化（台帳掃除）』を実行",
                )

    down_now = [
        str(s.get("id"))
        for s in services_status
        if (not s.get("alive")) and ("always_on" in (s.get("tags") or []))
    ]
    down_prev: list[str] = list(prev_state.get("always_on_down") or [])

    newly_down = sorted(list(set(down_now) - set(down_prev)))
    recovered = sorted(list(set(down_prev) - set(down_now)))
    if newly_down:
        append_event(EVENTS_FILE, "service_down", "always_on が停止しました", {"services": newly_down})
    if recovered:
        append_event(EVENTS_FILE, "service_recovered", "always_on が復旧しました", {"services": recovered})

    autonomy = _build_autonomy_status()
    storage_status = _build_storage_status(host, item_roots, items_recent)
    google_status = _build_google_status(REPO_ROOT)

    return {
        "ts": int(time.time()),
        "menu": menu,
        "host": host,
        "services": services_status,
        "unified": {
            "base": DEFAULT_UNIFIED_API_BASE,
            "integrations": unified_integrations,
            "mrl_memory": mrl_status,
            "proxy": {
                "enabled": True,
                "rules": unified_proxy_rules,
                "write_enabled": _unified_write_enabled(),
                "dangerous_enabled": _unified_dangerous_enabled(),
            },
        },
        "models": models_enriched,
        "devices": devices,
        "quests": quests,
        "skills": skills,
        "prompts": prompts,
        "items": {
            "roots": [{"id": r.id, "label": r.label} for r in item_roots],
            "recent": items_recent,
        },
        "storage": storage_status,
        "google": google_status,
        "actions": [{"id": a.get("id"), "label": a.get("label"), "tags": a.get("tags") or []} for a in actions],
        "actions_enabled": _actions_enabled(),
        "danger": danger,
        "next_actions": next_actions,
        "next_action_hints": next_action_hints,
        "always_on_down": down_now,
        "rl_anything": _get_rl_dashboard(),
        "autonomy": autonomy,
        "lessons": _get_lessons_summary(),
        "agents": _get_agents_summary(),
    }
