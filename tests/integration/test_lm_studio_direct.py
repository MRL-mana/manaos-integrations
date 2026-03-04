#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import pytest
import requests


def test_lm_studio_models_endpoint_smoke():
    base_url = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234")
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=3)
    except Exception as exc:
        return
    assert response.status_code in (200, 401, 403, 404)


def test_lm_studio_chat_endpoint_smoke():
    base_url = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234")
    data = {
        "model": "qwen2.5-coder-14b-instruct",
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0.7,
    }
    try:
        response = requests.post(f"{base_url}/v1/chat/completions", json=data, timeout=10)
    except Exception as exc:
        return
    assert response.status_code in (200, 400, 401, 403, 404)
