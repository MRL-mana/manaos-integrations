from __future__ import annotations

import json
import time
from typing import Any

from core.config import (
    DEFAULT_UNIFIED_API_BASE,
    REG,
    UNIFIED_DOCTOR_CACHE_FILE,
    UNIFIED_DOCTOR_CACHE_TTL_S,
)
from core.helpers import load_yaml
from core.http_client import _http_status
from core.unified_client import _unified_api_key, _unified_headers


def _load_unified_proxy_rules() -> list[dict[str, Any]]:
    y = load_yaml(REG / "unified_proxy.yaml")
    raw = y.get("rules") or []
    if not isinstance(raw, list):
        return []

    out: list[dict[str, Any]] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "").strip()
        method = str(r.get("method") or "").strip().upper()
        path = str(r.get("path") or "").strip()
        if not rid or method not in {"GET", "POST"} or not path.startswith("/"):
            continue
        gate = str(r.get("gate") or "read").strip().lower() or "read"
        if gate not in {"read", "write", "danger"}:
            gate = "read"

        enabled_raw = r.get("enabled")
        if enabled_raw is None:
            enabled = True
        elif isinstance(enabled_raw, bool):
            enabled = enabled_raw
        elif isinstance(enabled_raw, (int, float)):
            enabled = bool(int(enabled_raw))
        elif isinstance(enabled_raw, str):
            v = enabled_raw.strip().lower()
            if v in {"0", "false", "no", "off"}:
                enabled = False
            elif v in {"1", "true", "yes", "on"}:
                enabled = True
            else:
                enabled = True
        else:
            enabled = True

        label = str(r.get("label") or rid).strip() or rid
        try:
            timeout_s = float(r.get("timeout_s") or 12)
        except Exception:
            timeout_s = 12.0
        timeout_s = float(max(1.0, min(timeout_s, 300.0)))

        out.append(
            {
                "id": rid,
                "label": label,
                "method": method,
                "path": path,
                "gate": gate,
                "enabled": enabled,
                "timeout_s": timeout_s,
            }
        )
    return out


def _load_unified_doctor_cache() -> dict[str, Any]:
    if not UNIFIED_DOCTOR_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(UNIFIED_DOCTOR_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_unified_doctor_cache(data: dict[str, Any]) -> None:
    try:
        UNIFIED_DOCTOR_CACHE_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        return


def _probe_unified_proxy_rules(
    *,
    limit: int = 60,
    include_disabled: bool = False,
    probe_timeout_s: float = 1.2,
    max_total_s: float = 3.0,
) -> dict[str, Any]:
    limit_i = max(1, min(int(limit), 500))
    rules_all = _load_unified_proxy_rules()
    rules = [r for r in rules_all if include_disabled or bool(r.get("enabled", True))][:limit_i]

    try:
        probe_timeout_s_f = float(probe_timeout_s)
    except Exception:
        probe_timeout_s_f = 1.2
    probe_timeout_s_f = float(max(0.2, min(probe_timeout_s_f, 6.0)))

    try:
        max_total_s_f = float(max_total_s)
    except Exception:
        max_total_s_f = 3.0
    max_total_s_f = float(max(0.5, min(max_total_s_f, 60.0)))

    started = time.monotonic()
    out: list[dict[str, Any]] = []

    counts = {
        "total": 0,
        "skipped": 0,
        "skipped_post": 0,
        "conn_error": 0,
        "auth": 0,
        "not_found_get": 0,
        "post_probe_unknown": 0,
    }

    for r in rules:
        if (time.monotonic() - started) > max_total_s_f:
            break

        rid = str(r.get("id"))
        enabled = bool(r.get("enabled", True))
        method = str(r.get("method") or "GET").upper()
        path = str(r.get("path") or "")
        gate = str(r.get("gate") or "read")

        counts["total"] += 1

        if method == "POST":
            counts["skipped_post"] += 1
            counts["skipped"] += 1
            out.append(
                {
                    "id": rid,
                    "enabled": enabled,
                    "method": method,
                    "path": path,
                    "gate": gate,
                    "probe_method": None,
                    "status": None,
                    "exists": None,
                    "note": "post_probe_skipped",
                }
            )
            continue

        if "{" in path and "}" in path:
            counts["skipped"] += 1
            out.append(
                {
                    "id": rid,
                    "enabled": enabled,
                    "method": method,
                    "path": path,
                    "gate": gate,
                    "probe_method": "GET",
                    "status": None,
                    "exists": None,
                    "note": "needs_path_param",
                }
            )
            continue

        url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
        st = _http_status("GET", url, timeout_s=probe_timeout_s_f, headers=_unified_headers())
        status = int(st.get("status") or 0)

        note = None
        exists: bool | None
        if status in {200, 201, 202, 204, 400, 401, 403, 405, 422}:
            exists = True
        elif status == 404 and method == "POST":
            exists = None
        else:
            exists = False

        if status == 0:
            note = "conn_error"
            counts["conn_error"] += 1
        elif status in {401, 403}:
            note = "auth"
            counts["auth"] += 1
        elif status == 404 and method == "GET":
            note = "not_found"
            counts["not_found_get"] += 1
        elif status == 404 and method == "POST":
            note = "probe_get_404_for_post (unknown)"
            counts["post_probe_unknown"] += 1
        elif status == 405:
            note = "method_not_allowed (exists)"

        recommend_action_id = None
        if enabled and status == 404 and method == "GET":
            recommend_action_id = "unified_proxy_disable_404"

        out.append(
            {
                "id": rid,
                "enabled": enabled,
                "method": method,
                "path": path,
                "gate": gate,
                "probe_method": "GET",
                "status": status,
                "exists": exists,
                "note": note,
                "recommend_action_id": recommend_action_id,
                "auth_configured": bool(_unified_api_key()),
            }
        )

    return {
        "ok": True,
        "ts": int(time.time()),
        "base": DEFAULT_UNIFIED_API_BASE,
        "probe_timeout_s": probe_timeout_s_f,
        "max_total_s": max_total_s_f,
        "count": len(out),
        "counts": counts,
        "results": out,
    }


def _maybe_refresh_unified_doctor_cache() -> dict[str, Any]:
    cache = _load_unified_doctor_cache()
    ts = int(cache.get("ts") or 0)
    if ts > 0 and (int(time.time()) - ts) < UNIFIED_DOCTOR_CACHE_TTL_S:
        return cache

    try:
        fresh = _probe_unified_proxy_rules(
            limit=60,
            include_disabled=False,
            probe_timeout_s=1.2,
            max_total_s=3.0,
        )
        _save_unified_doctor_cache(fresh)
        return fresh
    except Exception as e:
        cache["ok"] = False
        cache["error"] = str(e)
        return cache
