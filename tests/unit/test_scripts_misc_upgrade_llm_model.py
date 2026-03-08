"""tests/unit/test_scripts_misc_upgrade_llm_model.py

upgrade_llm_model.py の単体テスト
"""
import json
from unittest.mock import MagicMock
import pytest
import httpx

import scripts.misc.upgrade_llm_model as _mod


# ---------------------------------------------------------------------------
# TestCheckAvailableModels
# ---------------------------------------------------------------------------
class TestCheckAvailableModels:
    def test_success_returns_model_names(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "qwen2.5:7b"},
                {"name": "unknown-model"},
            ]
        }
        monkeypatch.setattr(_mod.httpx, "get", lambda *a, **kw: mock_resp)

        result = _mod.check_available_models()

        assert result == ["llama3.2:3b", "qwen2.5:7b", "unknown-model"]
        out = capsys.readouterr().out
        assert "3" in out  # model count

    def test_known_model_shown_with_level(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "qwen2.5:14b"}]
        }
        monkeypatch.setattr(_mod.httpx, "get", lambda *a, **kw: mock_resp)

        _mod.check_available_models()

        out = capsys.readouterr().out
        assert "qwen2.5:14b" in out

    def test_non_200_returns_empty(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        monkeypatch.setattr(_mod.httpx, "get", lambda *a, **kw: mock_resp)

        result = _mod.check_available_models()

        assert result == []
        out = capsys.readouterr().out
        assert "500" in out

    def test_connect_error_returns_empty(self, monkeypatch, capsys):
        def _raise(*a, **kw):
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(_mod.httpx, "get", _raise)

        result = _mod.check_available_models()

        assert result == []
        out = capsys.readouterr().out
        assert "接続不可" in out

    def test_generic_exception_returns_empty(self, monkeypatch, capsys):
        def _raise(*a, **kw):
            raise RuntimeError("unexpected")

        monkeypatch.setattr(_mod.httpx, "get", _raise)

        result = _mod.check_available_models()

        assert result == []

    def test_empty_models_list(self, monkeypatch, capsys):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": []}
        monkeypatch.setattr(_mod.httpx, "get", lambda *a, **kw: mock_resp)

        result = _mod.check_available_models()

        assert result == []


# ---------------------------------------------------------------------------
# TestSuggestUpgrade
# ---------------------------------------------------------------------------
class TestSuggestUpgrade:
    def test_default_model_prints_upgrades(self, capsys):
        _mod.suggest_upgrade()

        out = capsys.readouterr().out
        assert "llama3.2:3b" in out
        assert "qwen2.5" in out

    def test_custom_model_shows_in_output(self, capsys):
        _mod.suggest_upgrade(current_model="qwen2.5:7b")

        out = capsys.readouterr().out
        assert "qwen2.5:7b" in out

    def test_returns_none(self):
        result = _mod.suggest_upgrade("llama3.1:8b")
        assert result is None


# ---------------------------------------------------------------------------
# TestShowCurrentUsage
# ---------------------------------------------------------------------------
class TestShowCurrentUsage:
    def test_prints_usage_table(self, capsys):
        _mod.show_current_usage()

        out = capsys.readouterr().out
        assert "llama3.2:3b" in out

    def test_returns_none(self):
        result = _mod.show_current_usage()
        assert result is None
