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

    mod.execute_android_command = _mock_exec  # type: ignore

    res = client.post(
        "/api/open/url",
        headers={"Authorization": "Bearer test-token"},
        json={"url": "https://example.com"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True


# ---------------------------------------------------------------------------
# /api/batch
# ---------------------------------------------------------------------------

def test_batch_blocked_in_core_profile(monkeypatch):
    """core プロファイルでは /api/batch を 403 で弾く"""
    mod = _load_gateway(monkeypatch, "core")
    monkeypatch.setenv("PIXEL7_API_ALLOW_EXEC", "1")
    client = TestClient(mod.app)

    res = client.post(
        "/api/batch",
        headers={"Authorization": "Bearer test-token"},
        json={"commands": [{"command": "echo hi"}]},
    )
    assert res.status_code == 403


def test_batch_blocked_without_allow_exec(monkeypatch):
    """PIXEL7_API_ALLOW_EXEC=0 のとき /api/batch を 403 で弾く"""
    mod = _load_gateway(monkeypatch, "full")
    monkeypatch.setenv("PIXEL7_API_ALLOW_EXEC", "0")
    mod = importlib.reload(mod)
    client = TestClient(mod.app)

    res = client.post(
        "/api/batch",
        headers={"Authorization": "Bearer test-token"},
        json={"commands": [{"command": "echo hi"}]},
    )
    assert res.status_code == 403


def test_batch_parallel_execution(monkeypatch):
    """PIXEL7_API_ALLOW_EXEC=1 + full プロファイルで並列実行できる"""
    mod = _load_gateway(monkeypatch, "full")
    monkeypatch.setenv("PIXEL7_API_ALLOW_EXEC", "1")
    mod = importlib.reload(mod)

    async def _mock_exec(command, timeout=30):
        return {"exit_code": 0, "stdout": f"ok:{command}", "stderr": ""}

    mod.execute_android_command = _mock_exec  # type: ignore

    client = TestClient(mod.app)
    res = client.post(
        "/api/batch",
        headers={"Authorization": "Bearer test-token"},
        json={
            "commands": [
                {"command": "echo a", "id": "cmd_a"},
                {"command": "echo b", "id": "cmd_b"},
            ],
            "max_parallel": 2,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    ids = {r["id"] for r in body["results"]}
    assert ids == {"cmd_a", "cmd_b"}
    for r in body["results"]:
        assert r["exit_code"] == 0


def test_batch_caps_at_20_commands(monkeypatch):
    """コマンド数が 20 を超えても最大 20 件に制限される"""
    mod = _load_gateway(monkeypatch, "full")
    monkeypatch.setenv("PIXEL7_API_ALLOW_EXEC", "1")
    mod = importlib.reload(mod)

    call_count = 0

    async def _mock_exec(command, timeout=30):
        nonlocal call_count
        call_count += 1
        return {"exit_code": 0, "stdout": "", "stderr": ""}

    mod.execute_android_command = _mock_exec  # type: ignore

    client = TestClient(mod.app)
    cmds = [{"command": f"echo {i}"} for i in range(25)]
    res = client.post(
        "/api/batch",
        headers={"Authorization": "Bearer test-token"},
        json={"commands": cmds},
    )
    assert res.status_code == 200
    assert res.json()["total"] == 20
    assert call_count == 20
