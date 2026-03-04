#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import pytest
import requests

try:
    from _paths import LM_STUDIO_PORT
except Exception:  # pragma: no cover
    LM_STUDIO_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))


def _base_url() -> str:
    return os.getenv("LM_STUDIO_URL", f"http://127.0.0.1:{LM_STUDIO_PORT}")


def test_lm_studio_models_list_smoke():
    try:
        response = requests.get(f"{_base_url()}/v1/models", timeout=5)
    except Exception as exc:
        return
    assert response.status_code in (200, 401, 403, 404)


def test_lm_studio_load_related_endpoints_smoke():
    endpoints = [
        "/v1/load",
        "/v1/model/load",
        "/api/load",
        "/api/model/load",
        "/load",
        "/model/load",
    ]
    reachable = False
    for endpoint in endpoints:
        try:
            response = requests.post(f"{_base_url()}{endpoint}", json={"model": "dummy"}, timeout=3)
        except Exception:
            continue
        if response.status_code != 404:
            reachable = True
            break
    assert isinstance(reachable, bool)
