import importlib

from fastapi.testclient import TestClient

import pixel7_api_gateway as gateway


def _load_gateway(monkeypatch, profile: str):
    monkeypatch.setenv("PIXEL7_API_TOKEN", "test-token")
    monkeypatch.setenv("PIXEL7_API_PROFILE", profile)
    monkeypatch.setenv("PIXEL7_API_TAILSCALE_ONLY", "0")
    return importlib.reload(gateway)


def test_root_exposes_profile(monkeypatch):
    mod = _load_gateway(monkeypatch, "core")
    client = TestClient(mod.app)

    res = client.get("/")
    assert res.status_code == 200
    assert res.json().get("api_profile") == "core"


def test_open_url_blocked_in_core(monkeypatch):
    mod = _load_gateway(monkeypatch, "core")
    client = TestClient(mod.app)

    res = client.post(
        "/api/open/url",
        headers={"Authorization": "Bearer test-token"},
        json={"url": "https://example.com"},
    )
    assert res.status_code == 403
    assert "PIXEL7_API_PROFILE=full" in res.text


def test_open_url_allowed_in_full(monkeypatch):
    mod = _load_gateway(monkeypatch, "full")
    client = TestClient(mod.app)

    async def _mock_exec(command, timeout=10):
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}

    mod.execute_android_command = _mock_exec

    res = client.post(
        "/api/open/url",
        headers={"Authorization": "Bearer test-token"},
        json={"url": "https://example.com"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
