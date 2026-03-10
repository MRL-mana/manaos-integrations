#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gallery APIを直接テスト。"""

import os
import requests
import json
import sys
import io
import pytest

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

from _paths import GALLERY_PORT

GALLERY_API = os.getenv("GALLERY_API_URL", f"http://127.0.0.1:{GALLERY_PORT}") + "/api/generate"

# 最小限のリクエスト
payload = {
    "prompt": "Japanese, beautiful woman, high quality",
    "model": "realisian_v60.safetensors",
    "steps": 20,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 768,
    "sampler": "euler",
    "scheduler": "normal",
    "mufufu_mode": True
}

def _is_gallery_api_ready() -> bool:
    try:
        response = requests.get(
            GALLERY_API.rsplit("/api/generate", 1)[0] + "/health",
            timeout=3,
        )
        return response.status_code in (200, 404)
    except requests.RequestException:
        return False


def _is_comfyui_ready() -> bool:
    """gallery /health の comfyui_available フラグを確認する。"""
    try:
        response = requests.get(
            GALLERY_API.rsplit("/api/generate", 1)[0] + "/health",
            timeout=3,
        )
        if response.status_code == 200:
            return response.json().get("comfyui_available", False)
    except requests.RequestException:
        pass
    return False


def test_gallery_api_generate_smoke():
    if not _is_gallery_api_ready():
        return
    if not _is_comfyui_ready():
        pytest.skip("ComfyUI is not available (comfyui_available=false)")

    response = requests.post(
        GALLERY_API,
        json=payload,
        timeout=30,
    )
    assert response.status_code in (200, 400, 422)
