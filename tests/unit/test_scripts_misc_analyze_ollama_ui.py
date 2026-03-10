"""Tests for scripts/misc/analyze_ollama_ui.py"""
import sys
import types
import os
from unittest.mock import MagicMock, patch
import pytest


def _make_paths_stub():
    mod = types.ModuleType("_paths")
    mod.OLLAMA_PORT = 11434  # type: ignore
    mod.UNIFIED_API_PORT = 9502  # type: ignore
    return mod


def _prep(monkeypatch):
    sys.modules.pop("analyze_ollama_ui", None)
    sys.modules.pop("manaos_integrations._paths", None)
    monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub())
    monkeypatch.syspath_prepend(
        str(__import__("pathlib").Path(__file__).parent.parent.parent / "scripts" / "misc")
    )
    mock_requests = MagicMock()
    mock_requests.get.return_value = MagicMock(status_code=200, json=lambda: {"models": []})
    monkeypatch.setitem(sys.modules, "requests", mock_requests)
    mock_subprocess = MagicMock()
    monkeypatch.setitem(sys.modules, "subprocess", mock_subprocess)
    return mock_requests, mock_subprocess


class TestAnalyzeOllamaUiImport:
    def test_module_imports(self, monkeypatch):
        mock_req, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            import analyze_ollama_ui  # noqa
        assert "analyze_ollama_ui" in sys.modules

    def test_ollama_url_from_env(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.setenv("OLLAMA_URL", "http://test-ollama:5555")
        sys.modules.pop("analyze_ollama_ui", None)
        with patch("builtins.print"):
            import analyze_ollama_ui as m
        assert m.DEFAULT_OLLAMA_URL == "http://test-ollama:5555"

    def test_unified_api_url_from_env(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.setenv("UNIFIED_API_URL", "http://custom-api:9000")
        sys.modules.pop("analyze_ollama_ui", None)
        with patch("builtins.print"):
            import analyze_ollama_ui as m
        assert m.DEFAULT_UNIFIED_API_URL == "http://custom-api:9000"

    def test_default_urls_contain_ports(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        monkeypatch.delenv("UNIFIED_API_URL", raising=False)
        sys.modules.pop("analyze_ollama_ui", None)
        with patch("builtins.print"):
            import analyze_ollama_ui as m
        assert "11434" in m.DEFAULT_OLLAMA_URL
        assert "9502" in m.DEFAULT_UNIFIED_API_URL

    def test_requests_get_called(self, monkeypatch):
        mock_req, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            import analyze_ollama_ui  # noqa
        # script uses requests.post (for Ollama API calls)
        assert mock_req.post.called or mock_req.get.called or mock_req.called
