"""Tests for scripts/misc/list_mana_favorite_models.py"""
import sys
import types
import os
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path
import json

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_paths_stub(port=8188):
    mod = types.ModuleType("_paths")
    mod.COMFYUI_PORT = port
    return mod


def _prep(monkeypatch, models=None, request_ok=True):
    sys.modules.pop("list_mana_favorite_models", None)
    monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub())
    monkeypatch.syspath_prepend(str(_MISC))

    _models = models or ["realisian_v60.safetensors", "dreamshaper.safetensors"]
    mock_resp = MagicMock()
    mock_resp.status_code = 200 if request_ok else 500
    mock_resp.json.return_value = _models
    mock_req = MagicMock()
    mock_req.get.return_value = mock_resp
    # Provide real exception classes so `except requests.exceptions.X:` works
    mock_exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        RequestException=Exception,
    )
    mock_req.exceptions = mock_exceptions
    monkeypatch.setitem(sys.modules, "requests", mock_req)

    with patch("builtins.print"), \
         patch("pathlib.Path.exists", return_value=False), \
         patch("os.listdir", return_value=[]):
        import list_mana_favorite_models  # noqa
    return mock_req


class TestListManaFavoriteModels:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "list_mana_favorite_models" in sys.modules

    def test_comfyui_url_from_env(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.setenv("COMFYUI_URL", "http://custom:9999")
        sys.modules.pop("list_mana_favorite_models", None)
        with patch("builtins.print"), patch("pathlib.Path.exists", return_value=False):
            import list_mana_favorite_models as m
        assert m.COMFYUI_URL == "http://custom:9999"

    def test_default_comfyui_url_has_port(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.delenv("COMFYUI_URL", raising=False)
        sys.modules.pop("list_mana_favorite_models", None)
        with patch("builtins.print"), patch("pathlib.Path.exists", return_value=False):
            import list_mana_favorite_models as m
        assert "8188" in m.COMFYUI_URL

    def test_requests_get_called(self, monkeypatch):
        mock_req = _prep(monkeypatch)
        assert mock_req.get.called

    def test_comfyui_models_dir_from_env(self, monkeypatch):
        _prep(monkeypatch)
        monkeypatch.setenv("COMFYUI_MODELS_DIR", "/custom/models")
        sys.modules.pop("list_mana_favorite_models", None)
        with patch("builtins.print"), patch("pathlib.Path.exists", return_value=False):
            import list_mana_favorite_models as m
        assert "custom" in str(m.COMFYUI_MODELS_DIR) and "models" in str(m.COMFYUI_MODELS_DIR)
