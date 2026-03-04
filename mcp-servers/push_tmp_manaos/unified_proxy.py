from __future__ import annotations

import time
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import _require_token
from core.config import DEFAULT_UNIFIED_API_BASE
from core.http_client import _http_status
from core.unified_client import (
    _expand_item_uris,
    _require_unified_write,
    _unified_api_key,
    _unified_dangerous_enabled,
    _unified_get,
    _unified_headers,
    _unified_post,
    _validate_proxy_body,
)
from services.unified_doctor import _load_unified_proxy_rules

router = APIRouter()


@router.post("/api/unified/proxy/run", dependencies=[Depends(_require_token)])
def api_unified_proxy_run(body: dict[str, Any]) -> dict[str, Any]:
    payload = _validate_proxy_body(body)
    rid = str(payload.get("id") or "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail="id is required")

    rules = _load_unified_proxy_rules()
    rule = next((r for r in rules if str(r.get("id")) == rid), None)
    if rule is None:
        raise HTTPException(status_code=404, detail="unknown proxy id")

    if not bool(rule.get("enabled", True)):
        raise HTTPException(status_code=403, detail="proxy rule disabled")

    gate = str(rule.get("gate") or "read")
    if gate == "write":
        _require_unified_write()
    if gate == "danger":
        _require_unified_write()
        if not _unified_dangerous_enabled():
            raise HTTPException(
                status_code=403,
                detail="dangerous unified ops disabled. set MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS=1",
            )

    method = str(rule.get("method") or "GET").upper()
    path = str(rule.get("path") or "").strip()
    timeout_s = float(rule.get("timeout_s") or 12.0)

    q = payload.get("query")
    if q is None:
        q = {}
    if not isinstance(q, dict):
        raise HTTPException(status_code=400, detail="query must be an object")

    if "{" in path and "}" in path:
        for k, v in list(q.items()):
            token = "{" + str(k) + "}"
            if token in path:
                path = path.replace(token, urllib.parse.quote(str(v), safe=""))
                q.pop(k, None)

    if q:
        qs = urllib.parse.urlencode({str(k): str(v) for k, v in q.items()})
        if "?" in path:
            path = path + "&" + qs
        else:
            path = path + "?" + qs

    if method == "GET":
        return _unified_get(path, timeout_s=timeout_s)

    if method == "POST":
        b = payload.get("body")
        if b is None:
            b = {}
        if not isinstance(b, dict):
            raise HTTPException(status_code=400, detail="body must be an object")
        b2 = _expand_item_uris(b)
        return _unified_post(path, payload=b2, timeout_s=timeout_s)

    raise HTTPException(status_code=400, detail="unsupported method")


@router.get("/api/unified/proxy/doctor")
def api_unified_proxy_doctor(
    limit: int = 80,
    include_disabled: bool = True,
    probe_timeout_s: float = 1.5,
    max_total_s: float = 8.0,
) -> dict[str, Any]:
    limit_i = max(1, min(int(limit), 500))
    rules_all = _load_unified_proxy_rules()
    rules = [r for r in rules_all if include_disabled or bool(r.get("enabled", True))][:limit_i]

    try:
        probe_timeout_s_f = float(probe_timeout_s)
    except Exception:
        probe_timeout_s_f = 1.5
    probe_timeout_s_f = float(max(0.2, min(probe_timeout_s_f, 6.0)))

    try:
        max_total_s_f = float(max_total_s)
    except Exception:
        max_total_s_f = 8.0
    max_total_s_f = float(max(1.0, min(max_total_s_f, 60.0)))

    started = time.monotonic()

    out: list[dict[str, Any]] = []
    for r in rules:
        if (time.monotonic() - started) > max_total_s_f:
            break

        rid = str(r.get("id"))
        enabled = bool(r.get("enabled", True))
        method = str(r.get("method") or "GET").upper()
        path = str(r.get("path") or "")
        gate = str(r.get("gate") or "read")
        timeout_s = probe_timeout_s_f

        if "{" in path and "}" in path:
            out.append(
                {
                    "id": rid,
                    "enabled": enabled,
                    "method": method,
                    "path": path,
                    "gate": gate,
                    "probe_method": "GET",
                    "status": None,
                    "ok": False,
                    "note": "needs_path_param",
                }
            )
            continue

        url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
        probe_method = "GET"
        st = _http_status(probe_method, url, timeout_s=timeout_s, headers=_unified_headers())

        status = int(st.get("status") or 0)
        err_raw = st.get("error")
        err_s = None
        if isinstance(err_raw, str) and err_raw.strip():
            err_s = err_raw.strip()[:300]
        note = None
        if status == 405:
            note = "method_not_allowed (exists)"
        if status in {401, 403}:
            note = "auth"
        if status == 404:
            if method == "POST":
                note = "probe_get_404_for_post (unknown)"
            else:
                note = "not_found"
        if status == 0 and err_s:
            note = "conn_error"

        recommend = None
        recommend_action_id = None
        if enabled and status == 404 and method != "POST":
            recommend = "run_unified_proxy_disable_404"
            recommend_action_id = "unified_proxy_disable_404"

        exists: bool | None
        if status in {200, 201, 202, 204, 400, 401, 403, 405, 422}:
            exists = True
        elif status == 404 and method == "POST":
            exists = None
        else:
            exists = False

        out.append(
            {
                "id": rid,
                "enabled": enabled,
                "method": method,
                "path": path,
                "gate": gate,
                "probe_method": probe_method,
                "status": status,
                "ok": bool(st.get("ok")) or status in {400, 401, 403, 405, 422},
                "exists": exists,
                "note": note,
                "error": err_s,
                "recommend": recommend,
                "recommend_action_id": recommend_action_id,
                "auth_configured": bool(_unified_api_key()),
            }
        )

    return {
        "ok": True,
        "base": DEFAULT_UNIFIED_API_BASE,
        "truncated": len(out) < len(rules),
        "max_total_s": max_total_s_f,
        "probe_timeout_s": probe_timeout_s_f,
        "count": len(out),
        "results": out,
    }
