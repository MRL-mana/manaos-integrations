from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from core.auth import _require_token
from core.config import DEFAULT_UNIFIED_API_BASE, EVENTS_FILE
from core.http_client import _http_json_post
from core.unified_client import _unified_headers
from collectors.events import append_event

router = APIRouter()


@router.post("/api/generate/image", dependencies=[Depends(_require_token)])
def api_generate_image(body: dict[str, Any]) -> dict[str, Any]:
    prompt = str(body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    width = int(body.get("width") or 768)
    height = int(body.get("height") or 768)
    steps = int(body.get("steps") or 20)
    negative = str(body.get("negative_prompt") or "")

    payload = {
        "prompt": prompt,
        "width": max(64, min(width, 2048)),
        "height": max(64, min(height, 2048)),
        "steps": max(1, min(steps, 80)),
        "negative_prompt": negative,
        "seed": int(body.get("seed") or -1),
        "mufufu_mode": False,
        "lab_mode": False,
    }

    url = f"{DEFAULT_UNIFIED_API_BASE}/api/comfyui/generate"
    r = _http_json_post(url, payload=payload, timeout_s=60.0, headers=_unified_headers())
    if not r.get("ok"):
        return {"ok": False, "url": url, "status": r.get("status"), "error": r.get("error")}

    data = r.get("data") or {}
    append_event(EVENTS_FILE, "image_generate", "Image generate queued", {"status": data.get("status"), "prompt": prompt[:80]})
    return {"ok": True, "url": url, "data": data}
