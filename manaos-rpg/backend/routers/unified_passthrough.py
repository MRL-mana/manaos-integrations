from __future__ import annotations

import json
import urllib.parse
from typing import Any

from fastapi import APIRouter, HTTPException

from core.config import DEFAULT_MRL_MEMORY_BASE
from core.http_client import _http_json_post
from core.unified_client import (
    _expand_item_uris,
    _require_unified_write,
    _unified_get,
    _unified_post,
    _validate_proxy_body,
)

router = APIRouter()


def _mrl_post(
    path: str,
    payload: dict[str, Any],
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    path = str(path or "").strip()
    if not path.startswith("/"):
        path = "/" + path
    url = f"{DEFAULT_MRL_MEMORY_BASE}{path}"
    r = _http_json_post(
        url,
        payload=payload,
        timeout_s=timeout_s,
        headers={},
    )
    if not r.get("ok"):
        return {
            "ok": False,
            "url": url,
            "status": r.get("status"),
            "error": r.get("error"),
            "via": "mrl-memory",
        }
    return {
        "ok": True,
        "url": url,
        "status": r.get("status"),
        "data": r.get("data"),
        "via": "mrl-memory",
    }


def _looks_like_unified_memory_unavailable(resp: dict[str, Any]) -> bool:
    if not isinstance(resp, dict):
        return False
    status = int(resp.get("status") or 0)
    if status != 503:
        return False
    err = resp.get("error")
    if err is None:
        return True

    # error が JSON 文字列の場合（例: {"error":"\\u7d71..."}）を復号して判定する
    if isinstance(err, str):
        s = err.strip()
        if s.startswith("{") and "\"error\"" in s:
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    err = parsed.get("error") or parsed.get("detail") or err
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        if isinstance(err, str):
            lowered = err.lower()
            return (
                ("統一記憶" in err)
                or ("memory" in lowered)
                or ("unavailable" in lowered)
            )

    # 503 は（統一記憶未搭載/停止など）で返るケースが多いのでフォールバック対象にする
    return True


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

    # 互換: 旧Unified(/api/memory/recall) → 404 の場合は MCP(/api/memory/search)
    qs = urllib.parse.urlencode(
        {"query": q, "scope": scope_s, "limit": str(limit_i)}
    )
    r = _unified_get(f"/api/memory/recall?{qs}", timeout_s=12.0)
    if _looks_like_unified_memory_unavailable(r):
        mrl_payload: dict[str, Any] = {"query": q, "limit": limit_i}
        return _mrl_post(
            "/api/memory/search",
            payload=mrl_payload,
            timeout_s=12.0,
        )
    if int(r.get("status") or 0) == 404:
        payload: dict[str, Any] = {"query": q, "limit": limit_i}
        if scope_s and scope_s != "all":
            payload["scope"] = scope_s
        return _unified_post(
            "/api/memory/search",
            payload=payload,
            timeout_s=12.0,
        )
    return r


@router.get("/api/unified/notify/job/{job_id}")
def api_unified_notify_job(job_id: str) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise HTTPException(status_code=400, detail="job_id is required")
    # 互換: 旧Unified(/notify/job/<id>) → 404 の場合は MCP(/api/ops/job/<id>)
    r = _unified_get(
        f"/notify/job/{urllib.parse.quote(jid, safe='')}",
        timeout_s=8.0,
    )
    if int(r.get("status") or 0) == 404:
        return _unified_get(
            f"/api/ops/job/{urllib.parse.quote(jid, safe='')}",
            timeout_s=8.0,
        )
    return r


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
        raise HTTPException(
            status_code=400,
            detail="message (or text) is required",
        )
    # 互換: 旧Unified(/api/notification/send) → 404 の場合は MCP(/api/ops/notify)
    r = _unified_post(
        "/api/notification/send",
        payload=payload,
        timeout_s=30.0,
    )
    if int(r.get("status") or 0) == 404:
        return _unified_post(
            "/api/ops/notify",
            payload=payload,
            timeout_s=30.0,
        )
    return r


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
        raise HTTPException(
            status_code=400,
            detail="metadata must be an object",
        )
    # 互換: 旧Unified(/api/memory/store) → 404 の場合は MCP(/api/memory/write)
    r = _unified_post("/api/memory/store", payload=payload, timeout_s=20.0)
    if _looks_like_unified_memory_unavailable(r):
        text = str(payload.get("content") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="content is required")
        mrl_payload: dict[str, Any] = {
            "text": text,
            "source": str(payload.get("source") or "manaos-rpg"),
            "enable_rehearsal": True,
            "enable_promotion": False,
        }
        return _mrl_post(
            "/api/memory/process",
            payload=mrl_payload,
            timeout_s=20.0,
        )
    if int(r.get("status") or 0) == 404:
        return _unified_post(
            "/api/memory/write",
            payload=payload,
            timeout_s=20.0,
        )
    return r


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
    return _unified_post(
        "/api/ltx2/generate",
        payload=payload,
        timeout_s=180.0,
    )


@router.post("/api/unified/ltx2-infinity/generate")
def api_unified_ltx2_infinity_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _expand_item_uris(_validate_proxy_body(body))
    return _unified_post(
        "/api/ltx2-infinity/generate",
        payload=payload,
        timeout_s=300.0,
    )


# ---------------------------------------------------------------------------
# GTD (Getting Things Done)
# ---------------------------------------------------------------------------

@router.get("/api/unified/gtd/status")
def api_unified_gtd_status() -> dict[str, Any]:
    return _unified_get("/api/gtd/status", timeout_s=8.0)


@router.get("/api/unified/gtd/morning")
def api_unified_gtd_morning() -> dict[str, Any]:
    return _unified_get("/api/gtd/morning", timeout_s=8.0)


@router.get("/api/unified/gtd/inbox/list")
def api_unified_gtd_inbox_list() -> dict[str, Any]:
    return _unified_get("/api/gtd/inbox/list", timeout_s=8.0)


@router.post("/api/unified/gtd/capture")
def api_unified_gtd_capture(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    return _unified_post("/api/gtd/capture", payload=payload, timeout_s=12.0)


@router.post("/api/unified/gtd/process")
def api_unified_gtd_process(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    if not payload.get("filename"):
        raise HTTPException(status_code=400, detail="filename is required")
    return _unified_post("/api/gtd/process", payload=payload, timeout_s=12.0)


# ---------------------------------------------------------------------------
# 統合モジュール ステータス
# ---------------------------------------------------------------------------

@router.get("/api/unified/integrations/status")
def api_unified_integrations_status() -> dict[str, Any]:
    return _unified_get("/api/integrations/status", timeout_s=12.0)


# ---------------------------------------------------------------------------
# SD Prompt 生成
# ---------------------------------------------------------------------------

@router.post("/api/unified/sd-prompt/generate")
def api_unified_sd_prompt_generate(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    return _unified_post("/api/sd-prompt/generate", payload=payload, timeout_s=30.0)


# ---------------------------------------------------------------------------
# Pixel7 API Gateway（直接）
# ---------------------------------------------------------------------------

@router.get("/api/unified/pixel7/health")
def api_unified_pixel7_health() -> dict[str, Any]:
    return _unified_get("/api/pixel7/health", timeout_s=8.0)


@router.get("/api/unified/pixel7/status")
def api_unified_pixel7_status() -> dict[str, Any]:
    return _unified_get("/api/pixel7/status", timeout_s=8.0)


@router.get("/api/unified/pixel7/system/info")
def api_unified_pixel7_system_info() -> dict[str, Any]:
    return _unified_get("/api/pixel7/system/info", timeout_s=8.0)


@router.get("/api/unified/pixel7/system/resources")
def api_unified_pixel7_system_resources() -> dict[str, Any]:
    return _unified_get("/api/pixel7/system/resources", timeout_s=8.0)


@router.get("/api/unified/pixel7/macro/commands")
def api_unified_pixel7_macro_commands() -> dict[str, Any]:
    return _unified_get("/api/pixel7/macro/commands", timeout_s=8.0)


@router.post("/api/unified/pixel7/execute")
def api_unified_pixel7_execute(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    return _unified_post("/api/pixel7/execute", payload=payload, timeout_s=12.0)


@router.post("/api/unified/pixel7/batch")
def api_unified_pixel7_batch(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    return _unified_post("/api/pixel7/batch", payload=payload, timeout_s=15.0)


@router.post("/api/unified/pixel7/open/url")
def api_unified_pixel7_open_url(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    url = str(payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    return _unified_post("/api/pixel7/open/url", payload=payload, timeout_s=12.0)


@router.post("/api/unified/pixel7/macro/broadcast")
def api_unified_pixel7_macro_broadcast(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    return _unified_post("/api/pixel7/macro/broadcast", payload=payload, timeout_s=12.0)


# ---------------------------------------------------------------------------
# X280 API Gateway（直接）
# ---------------------------------------------------------------------------

@router.get("/api/unified/x280/health")
def api_unified_x280_health() -> dict[str, Any]:
    return _unified_get("/api/x280/health", timeout_s=8.0)


@router.get("/api/unified/x280/status")
def api_unified_x280_status() -> dict[str, Any]:
    return _unified_get("/api/x280/status", timeout_s=8.0)


@router.get("/api/unified/x280/adb/devices")
def api_unified_x280_adb_devices() -> dict[str, Any]:
    return _unified_get("/api/x280/adb/devices", timeout_s=10.0)


@router.post("/api/unified/x280/adb/setup")
def api_unified_x280_adb_setup(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    return _unified_post("/api/x280/adb/setup", payload=payload, timeout_s=15.0)


@router.post("/api/unified/x280/adb/connect")
def api_unified_x280_adb_connect(body: dict[str, Any]) -> dict[str, Any]:
    _require_unified_write()
    payload = _validate_proxy_body(body)
    return _unified_post("/api/x280/adb/connect", payload=payload, timeout_s=12.0)

