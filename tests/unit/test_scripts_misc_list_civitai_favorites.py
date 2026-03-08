"""Tests for scripts/misc/list_civitai_favorites.py"""
import sys
import types
import os
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_civitai_stub(models=None):
    mod = types.ModuleType("civitai_integration")
    inst = MagicMock()
    inst.get_favorites.return_value = models or [
        {"id": "100", "name": "TestModel", "type": "Checkpoint"},
        {"id": "200", "name": "AnotherModel", "type": "LORA"},
    ]
    mod.CivitAIIntegration = MagicMock(return_value=inst)
    return mod, inst


def _prep(monkeypatch, models=None, has_api_key=True):
    sys.modules.pop("list_civitai_favorites", None)
    civitai_mod, inst = _make_civitai_stub(models)
    monkeypatch.setitem(sys.modules, "civitai_integration", civitai_mod)
    if has_api_key:
        monkeypatch.setenv("CIVITAI_API_KEY", "test_key")
    else:
        monkeypatch.delenv("CIVITAI_API_KEY", raising=False)
    monkeypatch.syspath_prepend(str(_MISC))
    with patch("builtins.print"):
        import list_civitai_favorites  # noqa
    return inst


class TestListCivitaiFavorites:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "list_civitai_favorites" in sys.modules

    def test_no_api_key_still_imports(self, monkeypatch):
        _prep(monkeypatch, has_api_key=False)
        assert "list_civitai_favorites" in sys.modules

    def test_civitai_integration_instantiated(self, monkeypatch):
        sys.modules.pop("list_civitai_favorites", None)
        civitai_mod, inst = _make_civitai_stub()
        monkeypatch.setitem(sys.modules, "civitai_integration", civitai_mod)
        monkeypatch.setenv("CIVITAI_API_KEY", "key123")
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"):
            import list_civitai_favorites  # noqa
        civitai_mod.CivitAIIntegration.assert_called()

    def test_missing_module_exits(self, monkeypatch):
        sys.modules.pop("list_civitai_favorites", None)
        # Remove civitai_integration so ImportError is raised
        if "civitai_integration" in sys.modules:
            del sys.modules["civitai_integration"]
        monkeypatch.syspath_prepend(str(_MISC))
        mock_exit = MagicMock(side_effect=SystemExit(1))
        with patch("builtins.print"), patch("sys.exit", mock_exit):
            with pytest.raises((ImportError, SystemExit, ModuleNotFoundError)):
                import list_civitai_favorites  # noqa
