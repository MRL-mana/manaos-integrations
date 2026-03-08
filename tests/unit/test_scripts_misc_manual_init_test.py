"""Tests for scripts/misc/manual_init_test.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_unified_api_stub(status="not_started", n_integrations=0):
    mod = types.ModuleType("unified_api_server")
    mod.integrations = {}
    mod.initialization_status = {"status": status, "completed": [], "failed": [], "pending": []}
    mod.initialize_integrations = MagicMock(
        side_effect=lambda: mod.initialization_status.update({"status": "ready", "completed": ["x"]})
    )
    return mod


def _prep(monkeypatch, status="not_started"):
    sys.modules.pop("manual_init_test", None)
    unified_mod = _make_unified_api_stub(status)
    monkeypatch.setitem(sys.modules, "unified_api_server", unified_mod)
    monkeypatch.syspath_prepend(str(_MISC))
    with patch("builtins.print"):
        import manual_init_test  # noqa
    return unified_mod


class TestManualInitTest:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "manual_init_test" in sys.modules

    def test_initialize_integrations_called(self, monkeypatch):
        unified_mod = _prep(monkeypatch)
        unified_mod.initialize_integrations.assert_called_once()

    def test_prints_are_made(self, monkeypatch):
        sys.modules.pop("manual_init_test", None)
        unified_mod = _make_unified_api_stub()
        monkeypatch.setitem(sys.modules, "unified_api_server", unified_mod)
        monkeypatch.syspath_prepend(str(_MISC))
        printed = []
        with patch("builtins.print", side_effect=lambda *a: printed.append(str(a))):
            import manual_init_test  # noqa
        assert len(printed) > 0

    def test_import_error_handled(self, monkeypatch):
        sys.modules.pop("manual_init_test", None)
        sys.modules.pop("unified_api_server", None)
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"):
            import manual_init_test  # noqa – ImportError path, should not raise
