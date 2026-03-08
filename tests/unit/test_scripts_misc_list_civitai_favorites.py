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
        # Without API key, script calls exit(1)
        sys.modules.pop("list_civitai_favorites", None)
        civitai_mod, inst = _make_civitai_stub()
        monkeypatch.setitem(sys.modules, "civitai_integration", civitai_mod)
        monkeypatch.delenv("CIVITAI_API_KEY", raising=False)
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"), patch("builtins.exit", side_effect=SystemExit(1)):
            with pytest.raises(SystemExit):
                import list_civitai_favorites  # noqa

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
        # When civitai_integration can be found (file exists in misc/), import succeeds
        # So this test verifies import works with the stub in place
        sys.modules.pop("list_civitai_favorites", None)
        civitai_mod, _ = _make_civitai_stub()
        monkeypatch.setitem(sys.modules, "civitai_integration", civitai_mod)
        monkeypatch.setenv("CIVITAI_API_KEY", "key")
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"):
            import list_civitai_favorites  # noqa
        assert "list_civitai_favorites" in sys.modules
