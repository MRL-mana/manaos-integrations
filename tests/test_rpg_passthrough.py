"""
RPG backend の unified_passthrough ルートに対するユニットテスト

テスト対象エンドポイント:
  GET  /api/unified/gtd/status
  GET  /api/unified/gtd/morning
  GET  /api/unified/gtd/inbox/list
  POST /api/unified/gtd/capture
  POST /api/unified/gtd/process
  GET  /api/unified/integrations/status
  POST /api/unified/sd-prompt/generate
  GET  /api/unified/pixel7/health
  GET  /api/unified/pixel7/status
  POST /api/unified/pixel7/execute
  POST /api/unified/pixel7/open/url
  POST /api/unified/pixel7/macro/broadcast
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# RPG backend を sys.path に追加
# ---------------------------------------------------------------------------
_RPG_BACKEND = Path(__file__).resolve().parents[1] / "manaos-rpg" / "backend"
if str(_RPG_BACKEND) not in sys.path:
    sys.path.insert(0, str(_RPG_BACKEND))


# ---------------------------------------------------------------------------
# Fixture: TestClient + 環境変数セットアップ
# ---------------------------------------------------------------------------

@pytest.fixture()
def rpg_client(monkeypatch):
    """unified_passthrough 依存の HTTP を完全モックし TestClient を返す"""
    monkeypatch.setenv("MANAOS_RPG_ENABLE_UNIFIED_WRITE", "1")

    from fastapi.testclient import TestClient
    import app as rpg_app

    client = TestClient(rpg_app.app, raise_server_exceptions=False)
    return client


@pytest.fixture()
def rpg_client_readonly(monkeypatch):
    """write 無効の TestClient"""
    monkeypatch.delenv("MANAOS_RPG_ENABLE_UNIFIED_WRITE", raising=False)
    monkeypatch.setenv("MANAOS_RPG_ENABLE_UNIFIED_WRITE", "0")

    from fastapi.testclient import TestClient
    import app as rpg_app

    client = TestClient(rpg_app.app, raise_server_exceptions=False)
    return client


# ---------------------------------------------------------------------------
# ヘルパー: HTTP モックレスポンス
# ---------------------------------------------------------------------------

def _ok_response(data: Any = None) -> dict:
    return {"ok": True, "status": 200, "data": data or {}}


def _err_response(status: int = 503) -> dict:
    return {"ok": False, "status": status, "error": "unavailable", "data": None}


# ---------------------------------------------------------------------------
# GTD status
# ---------------------------------------------------------------------------

def test_gtd_status_ok(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_ok_response({"status": "ok"})):
        r = rpg_client.get("/api/unified/gtd/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


def test_gtd_status_upstream_error(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_err_response(503)):
        r = rpg_client.get("/api/unified/gtd/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False


# ---------------------------------------------------------------------------
# GTD morning
# ---------------------------------------------------------------------------

def test_gtd_morning_ok(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_ok_response("本日の優先事項...")):
        r = rpg_client.get("/api/unified/gtd/morning")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GTD inbox/list
# ---------------------------------------------------------------------------

def test_gtd_inbox_list_ok(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_ok_response({"data": ["20990101_0000_a.md"]})):
        r = rpg_client.get("/api/unified/gtd/inbox/list")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ---------------------------------------------------------------------------
# GTD capture (POST)
# ---------------------------------------------------------------------------

def test_gtd_capture_ok(rpg_client):
    with patch("core.unified_client._http_json_post", return_value=_ok_response({"filename": "20990101_0000_test.md"})):
        r = rpg_client.post("/api/unified/gtd/capture", json={"text": "テストタスク", "type": "メモ"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_gtd_capture_requires_text(rpg_client):
    r = rpg_client.post("/api/unified/gtd/capture", json={"type": "メモ"})
    assert r.status_code == 400
    assert "text" in r.json().get("detail", "")


def test_gtd_capture_write_disabled(rpg_client_readonly):
    r = rpg_client_readonly.post("/api/unified/gtd/capture", json={"text": "タスク"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# GTD process (POST)
# ---------------------------------------------------------------------------

def test_gtd_process_ok(rpg_client):
    with patch("core.unified_client._http_json_post", return_value=_ok_response({"processed": True})):
        r = rpg_client.post("/api/unified/gtd/process", json={"filename": "20990101_0000_test.md"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_gtd_process_requires_filename(rpg_client):
    r = rpg_client.post("/api/unified/gtd/process", json={"next_action": "確認する"})
    assert r.status_code == 400
    assert "filename" in r.json().get("detail", "")


# ---------------------------------------------------------------------------
# integrations/status
# ---------------------------------------------------------------------------

def test_integrations_status_ok(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_ok_response({"modules": []})):
        r = rpg_client.get("/api/unified/integrations/status")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ---------------------------------------------------------------------------
# SD Prompt generate (POST)
# ---------------------------------------------------------------------------

def test_sd_prompt_generate_ok(rpg_client):
    with patch("core.unified_client._http_json_post", return_value=_ok_response({"prompt": "blue sky, white clouds"})):
        r = rpg_client.post("/api/unified/sd-prompt/generate", json={"description": "\u9752\u3044\u7a7a"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_sd_prompt_requires_body(rpg_client):
    # FastAPI \u306f dict \u578b\u4ee5\u5916\u3092 422 \u3067\u62d2\u5426\u3059\u308b
    r = rpg_client.post("/api/unified/sd-prompt/generate", json=[])
    assert r.status_code >= 400


def test_sd_prompt_write_disabled(rpg_client_readonly):
    r = rpg_client_readonly.post("/api/unified/sd-prompt/generate", json={"description": "空"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Pixel7 health (GET)
# ---------------------------------------------------------------------------

def test_pixel7_health_ok(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_ok_response({"status": "ok"})):
        r = rpg_client.get("/api/unified/pixel7/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_pixel7_health_unreachable(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_err_response(503)):
        r = rpg_client.get("/api/unified/pixel7/health")
    assert r.status_code == 200
    assert r.json()["ok"] is False


# ---------------------------------------------------------------------------
# Pixel7 status (GET)
# ---------------------------------------------------------------------------

def test_pixel7_status_ok(rpg_client):
    with patch("core.unified_client._http_json_get", return_value=_ok_response({"adb_connected": True})):
        r = rpg_client.get("/api/unified/pixel7/status")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ---------------------------------------------------------------------------
# Pixel7 execute (POST)
# ---------------------------------------------------------------------------

def test_pixel7_execute_ok(rpg_client):
    with patch("core.unified_client._http_json_post", return_value=_ok_response({"result": "ok"})):
        r = rpg_client.post("/api/unified/pixel7/execute", json={"command": "screenshot"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_pixel7_execute_write_disabled(rpg_client_readonly):
    r = rpg_client_readonly.post("/api/unified/pixel7/execute", json={"command": "screenshot"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Pixel7 open/url (POST)
# ---------------------------------------------------------------------------

def test_pixel7_open_url_ok(rpg_client):
    with patch("core.unified_client._http_json_post", return_value=_ok_response({})):
        r = rpg_client.post("/api/unified/pixel7/open/url", json={"url": "https://example.com"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_pixel7_open_url_requires_url(rpg_client):
    r = rpg_client.post("/api/unified/pixel7/open/url", json={"note": "なし"})
    assert r.status_code == 400
    assert "url" in r.json().get("detail", "")


def test_pixel7_open_url_write_disabled(rpg_client_readonly):
    r = rpg_client_readonly.post("/api/unified/pixel7/open/url", json={"url": "https://example.com"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Pixel7 macro/broadcast (POST)
# ---------------------------------------------------------------------------

def test_pixel7_macro_broadcast_ok(rpg_client):
    with patch("core.unified_client._http_json_post", return_value=_ok_response({})):
        r = rpg_client.post("/api/unified/pixel7/macro/broadcast", json={"name": "wake_up"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_pixel7_macro_broadcast_write_disabled(rpg_client_readonly):
    r = rpg_client_readonly.post("/api/unified/pixel7/macro/broadcast", json={"name": "wake_up"})
    assert r.status_code == 403
