"""Tests for scripts/misc/analyze_failure_reasons.py"""
import sys
import types
import importlib
from unittest.mock import MagicMock, patch
import pytest


def _make_paths_stub():
    mod = types.ModuleType("_paths")
    mod.COMFYUI_PORT = 8188
    return mod


def _patch_and_import(monkeypatch):
    sys.modules.pop("analyze_failure_reasons", None)
    sys.modules.setdefault("_paths", _make_paths_stub())
    monkeypatch.syspath_prepend(
        str(__import__("pathlib").Path(__file__).parent.parent.parent / "scripts" / "misc")
    )


class TestAnalyzeFailureReasonsImport:
    def test_module_imports_without_network(self, monkeypatch):
        """モジュールがネットワークなしでインポートできる（requests を mock）"""
        _patch_and_import(monkeypatch)
        mock_requests = MagicMock()
        mock_requests.get.return_value = MagicMock(status_code=200, json=lambda: {"history": {}})
        monkeypatch.setitem(sys.modules, "requests", mock_requests)
        # run-level code is at module level; wrap import
        with patch("builtins.print"):
            import analyze_failure_reasons  # noqa: F401 – smoke import
        assert "analyze_failure_reasons" in sys.modules

    def test_comfyui_url_env_override(self, monkeypatch):
        """COMFYUI_URL 環境変数が優先される"""
        sys.modules.pop("analyze_failure_reasons", None)
        monkeypatch.setenv("COMFYUI_URL", "http://custom:9999")
        monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub())
        monkeypatch.syspath_prepend(
            str(__import__("pathlib").Path(__file__).parent.parent.parent / "scripts" / "misc")
        )
        mock_requests = MagicMock()
        mock_requests.get.return_value = MagicMock(status_code=200, json=lambda: {"history": {}})
        monkeypatch.setitem(sys.modules, "requests", mock_requests)
        with patch("builtins.print"):
            import analyze_failure_reasons as m  # noqa: F401
        assert m.COMFYUI_URL == "http://custom:9999"


class TestAnalyzeFailureReasonsLogic:
    def test_error_prompt_ids_non_empty(self, monkeypatch):
        """error_prompt_ids が空でないことを確認"""
        _patch_and_import(monkeypatch)
        mock_requests = MagicMock()
        mock_requests.get.return_value = MagicMock(status_code=200, json=lambda: {"history": {}})
        monkeypatch.setitem(sys.modules, "requests", mock_requests)
        with patch("builtins.print"):
            import analyze_failure_reasons as m
        assert isinstance(m.error_prompt_ids, list)
        assert len(m.error_prompt_ids) > 0

    def test_all_prompt_ids_are_strings(self, monkeypatch):
        """全 prompt ID が文字列であること"""
        _patch_and_import(monkeypatch)
        mock_requests = MagicMock()
        mock_requests.get.return_value = MagicMock(status_code=200, json=lambda: {"history": {}})
        monkeypatch.setitem(sys.modules, "requests", mock_requests)
        with patch("builtins.print"):
            import analyze_failure_reasons as m
        for pid in m.error_prompt_ids:
            assert isinstance(pid, str)

    def test_requests_called_for_each_prompt(self, monkeypatch):
        """各 prompt ID に対して requests.get が呼ばれる"""
        _patch_and_import(monkeypatch)
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {}
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response
        monkeypatch.setitem(sys.modules, "requests", mock_requests)
        with patch("builtins.print"):
            import analyze_failure_reasons as m
        assert mock_requests.get.call_count >= len(m.error_prompt_ids)

    def test_comfyui_url_default_format(self, monkeypatch):
        """デフォルト COMFYUI_URL が正しい形式"""
        sys.modules.pop("analyze_failure_reasons", None)
        monkeypatch.delenv("COMFYUI_URL", raising=False)
        monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub())
        monkeypatch.syspath_prepend(
            str(__import__("pathlib").Path(__file__).parent.parent.parent / "scripts" / "misc")
        )
        mock_requests = MagicMock()
        mock_requests.get.return_value = MagicMock(status_code=200, json=lambda: {})
        monkeypatch.setitem(sys.modules, "requests", mock_requests)
        with patch("builtins.print"):
            import analyze_failure_reasons as m
        assert m.COMFYUI_URL.startswith("http://")
        assert "8188" in m.COMFYUI_URL
