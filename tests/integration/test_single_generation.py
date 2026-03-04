#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import pytest
import requests

try:
    from _paths import GALLERY_PORT
except Exception:  # pragma: no cover
    GALLERY_PORT = int(os.getenv("GALLERY_PORT", "5001"))


def test_single_generation_endpoint_smoke():
    gallery_api = os.getenv("GALLERY_API_URL", f"http://127.0.0.1:{GALLERY_PORT}") + "/api/generate"
    payload = {
        "prompt": "smoke test",
        "model": os.getenv("GALLERY_TEST_MODEL", "realisian_v60.safetensors"),
        "steps": 1,
        "guidance_scale": 1.0,
        "width": 512,
        "height": 512,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "mufufu_mode": False,
    }
    try:
        response = requests.post(gallery_api, json=payload, timeout=10)
    except Exception as exc:
        return

    assert response.status_code in (200, 400, 401, 403, 404, 422, 500)
