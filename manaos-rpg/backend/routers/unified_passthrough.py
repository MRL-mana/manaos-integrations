from __future__ import annotations

import urllib.parse
from typing import Any

from fastapi import APIRouter, HTTPException

from core.unified_client import (
    _expand_item_uris,
    _require_unified_write,
    _unified_get,
    _unified_post,
    _validate_proxy_body,
)

router = APIRouter()


# --- GET passthrough ---

@router.get("/api/unified/comfyui/queue")
def api_unified_comfyui_queue() -> dict[str, Any]:
    return _unified_get("/api/comfyui/queue", timeout_s=8.0)


@router.get("/api/unified/comfyui/history")
def api_unified_comfyui_history() -> dict[str, Any]:
    return _unified_get("/api/comfyui/history", timeout_s=12.0)


@router.get("/api/unified/svi/queue")
def api_unified_svi_queue() -> dict[str, Any]:
    return _unified_get("/api/svi/queue", timeout_s=8.0)


@router.get("/api/unified/svi/history")
def api_unified_svi_history() -> dict[str, Any]:
    return _unified_get("/api/svi/history", timeout_s=12.0)


@router.get("/api/unified/ltx2/queue")
def api_unified_ltx2_queue() -> dict[str, Any]:
    return _unified_get("/api/ltx2/queue", timeout_s=8.0)


@router.get("/api/unified/ltx2/history")
def api_unified_ltx2_history() -> dict[str, Any]:
    return _unified_get("/api/ltx2/history", timeout_s=12.0)


@router.get("/api/unified/images/recent")
def api_unified_images_recent(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit), 200))
    return _unified_get(f"/api/images/recent?limit={limit}", timeout_s=8.0)


@router.get("/api/unified/llm/health")
def api_unified_llm_health() -> dict[str, Any]:
    return _unified_get("/api/llm/health", timeout_s=8.0)


@router.get("/api/unified/llm/models-enhanced")
def api_unified_llm_models_enhanced() -> dict[str, Any]:
    return _unified_get("/api/llm/models-enhanced", timeout_s=12.0)


@router.get("/api/unified/openapi")
def api_unified_openapi() -> dict[str, Any]:
    return _unified_get("/openapi.json", timeout_s=12.0)


@router.get("/api/unified/memory/recall")
def api_unified_memory_recall(
    query: str,
    scope: str = "all",
    limit: int = 10,
) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    scope_s = str(scope or "all").strip() or "all"
    limit_i = max(1, min(int(limit), 50))

    # Unified の実体が MCP API Server の場合、/api/memory/recall は存在しない。
    # read-only で使える /api/memory/search へ寄せる。
    payload: dict[str, Any] = {"query": q, "limit": limit_i}
    if scope_s and scope_s != "all":
        payload["scope"] = scope_s
    return _unified_post("/api/memory/search", payload=payload, timeout_s=12.0)


@router.get("/api/unified/notify/job/{job_id}")
def api_unified_notify_job(job_id: str) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise HTTPException(status_code=400, detail="job_id is required")
    # MCP API Server: /api/ops/job/{job_id}
    return _unified_get(
        f"/api/ops/job/{urllib.parse.quote(jid, safe='')}",
        timeout_s=8.0,
    )


# --- POST passthrough ---

@router.post("/api/unified/llm/route-enhanced")
def api_unified_llm_route_enhanced(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    return _unified_post(
        "/api/llm/route-enhanced",
        payload=payload,
        timeout_s=60.0,
    )


@router.post("/api/unified/llm/analyze")
def api_unified_llm_analyze(body: dict[str, Any]) -> dict[str, Any]:
    payload = _validate_proxy_body(body)
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    return _unified_post(
        "/api/llm/analyze",
        payload=payload,
        timeout_s=12.0,
    )


@router.post("/api/unified/notify/send")
def api_unified_notify_send(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    message = str(payload.get("message") or payload.get("text") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message (or text) is required")
    # MCP API Server: /api/ops/notify
    return _unified_post("/api/ops/notify", payload=payload, timeout_s=30.0)


@router.post("/api/unified/memory/store")
def api_unified_memory_store(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    # UIは content を送る。互換のため text も許容。
    if payload.get("content") is None and payload.get("text") is not None:
        payload["content"] = payload.get("text")
    if payload.get("content") is None:
        raise HTTPException(status_code=400, detail="content is required")
    meta = payload.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        raise HTTPException(status_code=400, detail="metadata must be an object")
    # MCP API Server: /api/memory/write
    return _unified_post("/api/memory/write", payload=payload, timeout_s=20.0)


@router.post("/api/unified/svi/generate")
def api_unified_svi_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/svi/generate", payload=payload, timeout_s=30.0)


@router.post("/api/unified/svi/extend")
def api_unified_svi_extend(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/svi/extend", payload=payload, timeout_s=30.0)


@router.post("/api/unified/ltx2/generate")
def api_unified_ltx2_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/ltx2/generate", payload=payload, timeout_s=180.0)


@router.post("/api/unified/ltx2-infinity/generate")
def api_unified_ltx2_infinity_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post("/api/ltx2-infinity/generate", payload=payload, timeout_s=300.0)
