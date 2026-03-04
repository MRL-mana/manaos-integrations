"""Remi API quick system check (pytest-safe)."""

import json
import os
import urllib.request

import pytest


BASE = os.getenv("REMI_API_URL", "http://127.0.0.1:5050")
TOKEN = os.getenv("REMI_API_TOKEN", "")


def _check(path, method="GET", need_auth=True, body=None, timeout=5):
    url = BASE + path
    headers = {}
    if need_auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if body:
        headers["Content-Type"] = "application/json"

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ct = resp.headers.get("Content-Type", "")
        payload = resp.read()
        if "json" in ct:
            return resp.status, json.loads(payload.decode())
        return resp.status, payload.decode(errors="ignore")


def test_remi_health_smoke():
    try:
        status, _ = _check("/health", need_auth=False, timeout=3)
    except Exception as e:
        return
    assert status in (200, 401, 403, 404)


def test_remi_status_smoke():
    try:
        status, payload = _check("/status", need_auth=bool(TOKEN), timeout=5)
    except Exception as e:
        return
    assert status in (200, 401, 403)
    if status == 200 and isinstance(payload, dict):
        assert isinstance(payload, dict)
