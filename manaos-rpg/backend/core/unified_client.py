from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any

from fastapi import HTTPException

from core.config import DEFAULT_UNIFIED_API_BASE, REG, REPO_ROOT
from core.helpers import load_yaml
from core.http_client import _http_json_get, _http_json_post
from collectors.items_collector import resolve_item_roots, safe_resolve_under_root


def _unified_dangerous_enabled() -> bool:
    v = str(os.environ.get("MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS", "0")).strip().lower()
    return v in {"1", "true", "yes", "on"}


def _unified_write_enabled() -> bool:
    v = str(os.environ.get("MANAOS_RPG_ENABLE_UNIFIED_WRITE", "0")).strip().lower()
    return v in {"1", "true", "yes", "on"}


def _unified_api_key() -> str:
    keys = [
        os.environ.get("MANAOS_UNIFIED_API_KEY"),
        os.environ.get("MANAOS_INTEGRATION_READONLY_API_KEY"),
        os.environ.get("MANAOS_INTEGRATION_OPS_API_KEY"),
        os.environ.get("MANAOS_INTEGRATION_API_KEY"),
        os.environ.get("API_KEY"),
    ]
    for k in keys:
        if k and str(k).strip():
            return str(k).strip()
    return ""


def _unified_headers() -> dict[str, str]:
    api_key = _unified_api_key()
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


def get_unified_integrations_status() -> dict[str, Any]:
    api_key = _unified_api_key()
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key

    health_url = f"{DEFAULT_UNIFIED_API_BASE}/health"
    openapi_url = f"{DEFAULT_UNIFIED_API_BASE}/openapi.json"

    h = _http_json_get(health_url, timeout_s=8.0, headers=headers)
    o = _http_json_get(openapi_url, timeout_s=8.0, headers=headers)

    ok = bool(o.get("ok"))

    openapi_summary: dict[str, Any] = {
        "ok": bool(o.get("ok")),
        "status": o.get("status"),
    }
    if o.get("ok") and isinstance(o.get("data"), dict):
        spec = o.get("data") or {}
        paths = spec.get("paths") if isinstance(spec.get("paths"), dict) else {}
        path_names = list(paths.keys()) if isinstance(paths, dict) else []

        get_paths = []
        post_paths = []
        for p, ops in (paths or {}).items():
            if not isinstance(ops, dict):
                continue
            if isinstance(ops.get("get"), dict):
                get_paths.append(str(p))
            if isinstance(ops.get("post"), dict):
                post_paths.append(str(p))

        get_no_params = [p for p in get_paths if ("{" not in p and "}" not in p)]
        openapi_summary.update(
            {
                "title": spec.get("info", {}).get("title") if isinstance(spec.get("info"), dict) else None,
                "version": spec.get("info", {}).get("version") if isinstance(spec.get("info"), dict) else None,
                "paths_count": len(path_names),
                "paths_sample": sorted([str(p) for p in path_names])[:20],
                "get_paths_count": len(get_paths),
                "get_paths_no_params_count": len(get_no_params),
                "post_paths_count": len(post_paths),
            }
        )

    return {
        "ok": ok,
        "url": health_url,
        "status": h.get("status"),
        "auth_configured": bool(api_key),
        "data": {
            "health": h.get("data") if h.get("ok") else None,
            "openapi": openapi_summary,
        },
        "checks": {
            "health": {"url": health_url, "status": h.get("status"), "ok": bool(h.get("ok")), "error": h.get("error")},
            "openapi": {"url": openapi_url, "status": o.get("status"), "ok": bool(o.get("ok")), "error": o.get("error")},
        },
    }


def _unified_get(path: str, timeout_s: float = 8.0) -> dict[str, Any]:
    path = str(path or "").strip()
    if not path.startswith("/"):
        path = "/" + path
    url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
    r = _http_json_get(url, timeout_s=timeout_s, headers=_unified_headers())
    if not r.get("ok"):
        return {
            "ok": False,
            "url": url,
            "status": r.get("status"),
            "error": r.get("error"),
            "auth_configured": bool(_unified_api_key()),
        }
    return {
        "ok": True,
        "url": url,
        "status": r.get("status"),
        "auth_configured": bool(_unified_api_key()),
        "data": r.get("data"),
    }


def _unified_post(path: str, payload: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
    path = str(path or "").strip()
    if not path.startswith("/"):
        path = "/" + path
    url = f"{DEFAULT_UNIFIED_API_BASE}{path}"
    r = _http_json_post(url, payload=payload, timeout_s=timeout_s, headers=_unified_headers())
    if not r.get("ok"):
        return {
            "ok": False,
            "url": url,
            "status": r.get("status"),
            "error": r.get("error"),
            "auth_configured": bool(_unified_api_key()),
        }
    return {
        "ok": True,
        "url": url,
        "status": r.get("status"),
        "auth_configured": bool(_unified_api_key()),
        "data": r.get("data"),
    }


def _validate_proxy_body(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object is required")
    try:
        raw = json.dumps(body, ensure_ascii=False)
        if len(raw) > 200_000:
            raise HTTPException(status_code=413, detail="payload too large")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")
    return body


def _require_unified_write() -> None:
    if not _unified_write_enabled():
        raise HTTPException(status_code=403, detail="unified write disabled. set MANAOS_RPG_ENABLE_UNIFIED_WRITE=1")


def _expand_item_uris(obj: Any) -> Any:
    try:
        items_yaml = load_yaml(REG / "items.yaml")
        item_roots = resolve_item_roots(REPO_ROOT, items_yaml)
        roots_by_id = {r.id: r for r in item_roots}
    except Exception:
        roots_by_id = {}

    def _expand(v: Any) -> Any:
        if isinstance(v, str) and v.startswith("item://"):
            rest = v[len("item://"):]
            if "/" not in rest:
                return v
            root_id, rel = rest.split("/", 1)
            root = roots_by_id.get(root_id)
            if root is None:
                return v
            p = safe_resolve_under_root(root.path, rel)
            if p is None or (not p.exists()) or (not p.is_file()):
                return v
            return str(p)
        if isinstance(v, list):
            return [_expand(x) for x in v]
        if isinstance(v, dict):
            return {str(k): _expand(x) for k, x in v.items()}
        return v

    return _expand(obj)
