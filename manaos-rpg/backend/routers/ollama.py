from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import _require_token
from core.config import DEFAULT_OLLAMA_BASE, EVENTS_FILE
from core.http_client import _http_json_get, _http_json_post
from collectors.events import append_event

router = APIRouter()


@router.get("/api/ollama/tags")
def api_ollama_tags() -> dict[str, Any]:
    url = f"{DEFAULT_OLLAMA_BASE}/api/tags"
    r = _http_json_get(url, timeout_s=5.0)
    if not r.get("ok"):
        return {"ok": False, "url": url, "status": r.get("status"), "error": r.get("error")}
    return {"ok": True, "url": url, "data": r.get("data")}


@router.post("/api/ollama/generate", dependencies=[Depends(_require_token)])
def api_ollama_generate(body: dict[str, Any]) -> dict[str, Any]:
    model = str(body.get("model") or "").strip()
    prompt = str(body.get("prompt") or "").strip()
    if not model:
        raise HTTPException(status_code=400, detail="model is required")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    url = f"{DEFAULT_OLLAMA_BASE}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    r = _http_json_post(url, payload=payload, timeout_s=120.0)
    if not r.get("ok"):
        return {"ok": False, "url": url, "status": r.get("status"), "error": r.get("error")}

    data = r.get("data") or {}
    text = str(data.get("response") or "")
    append_event(EVENTS_FILE, "ollama_generate", "Ollama generate", {"model": model, "chars": len(text)})
    return {"ok": True, "url": url, "model": model, "response": text, "raw": data}
