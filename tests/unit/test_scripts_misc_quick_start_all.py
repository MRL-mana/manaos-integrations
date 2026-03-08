"""tests/unit/test_scripts_misc_quick_start_all.py

quick_start_all.py の単体テスト
"""
import pytest

import scripts.misc.quick_start_all as _mod


class TestCheckOllama:
    def test_returns_true_when_healthy(self, monkeypatch):
        import httpx
        mock_resp = type("R", (), {
            "status_code": 200,
            "json": lambda self: {"models": ["llama3", "mistral"]},
        })()
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        result = _mod.check_ollama()
        assert result is True

    def test_returns_false_on_connection_error(self, monkeypatch):
        import httpx
        def _raise(*a, **kw): raise httpx.ConnectError("refused")
        monkeypatch.setattr(httpx, "get", _raise)
        result = _mod.check_ollama()
        assert result is False

    def test_returns_false_when_not_200(self, monkeypatch):
        import httpx
        mock_resp = type("R", (), {
            "status_code": 503,
            "json": lambda self: {},
        })()
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        result = _mod.check_ollama()
        # status != 200 falls through the try without explicit return → None
        assert not result

    def test_returns_false_on_timeout(self, monkeypatch):
        import httpx
        def _raise(*a, **kw): raise httpx.TimeoutException("timeout")
        monkeypatch.setattr(httpx, "get", _raise)
        result = _mod.check_ollama()
        assert result is False
