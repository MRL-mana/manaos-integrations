"""tests/unit/test_scripts_misc_bootstrap_openwebui_manaos_local_gateway.py

bootstrap_openwebui_manaos_local_gateway.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.bootstrap_openwebui_manaos_local_gateway as _mod


class TestRequestJson:
    def test_success_returns_status_and_body(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"result": "ok"}'
        mock_resp.json.return_value = {"result": "ok"}
        monkeypatch.setattr(_mod.requests, "request", lambda *a, **kw: mock_resp)

        status, body = _mod.request_json("http://localhost:3001", "GET", "/health")
        assert status == 200
        assert body == {"result": "ok"}

    def test_connection_error_returns_zero_and_error(self, monkeypatch):
        import requests as req_mod

        def _raise(*a, **kw):
            raise req_mod.RequestException("connection refused")

        monkeypatch.setattr(_mod.requests, "request", _raise)

        status, body = _mod.request_json("http://localhost:3001", "GET", "/health")
        assert status == 0
        assert "error" in body

    def test_bearer_token_added(self, monkeypatch):
        captured = {}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.json.return_value = {}

        def capture(method, url, headers=None, **kw):
            captured["headers"] = headers
            return mock_resp

        monkeypatch.setattr(_mod.requests, "request", capture)

        _mod.request_json("http://localhost:3001", "GET", "/path", token="mytoken")
        assert captured["headers"].get("Authorization") == "Bearer mytoken"

    def test_empty_response_body(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.text = ""
        monkeypatch.setattr(_mod.requests, "request", lambda *a, **kw: mock_resp)

        status, body = _mod.request_json("http://localhost:3001", "DELETE", "/path")
        assert status == 204


class TestToolContent:
    def test_returns_string(self):
        result = _mod.tool_content()
        assert isinstance(result, str)

    def test_non_empty(self):
        result = _mod.tool_content()
        assert len(result) > 0

    def test_contains_python_code(self):
        result = _mod.tool_content()
        # The tool content is Python code
        assert "def " in result or "class " in result or "import " in result
