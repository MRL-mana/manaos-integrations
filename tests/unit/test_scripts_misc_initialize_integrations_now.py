"""Tests for scripts/misc/initialize_integrations_now.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_paths_stub():
    mod = types.ModuleType("_paths")
    mod.N8N_PORT = 5678  # type: ignore
    return mod


def _make_unified_api_stub(status="ready"):
    mod = types.ModuleType("unified_api_server")
    mod.integrations = {}  # type: ignore
    mod.initialization_status = {"status": status, "completed": ["n8n"], "failed": [], "pending": []}  # type: ignore
    mod.initialize_integrations = MagicMock()  # type: ignore
    return mod


def _prep(monkeypatch, status="ready"):
    sys.modules.pop("initialize_integrations_now", None)
    sys.modules.pop("manaos_integrations._paths", None)
    monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub())
    monkeypatch.setitem(sys.modules, "unified_api_server", _make_unified_api_stub(status))
    monkeypatch.syspath_prepend(str(_MISC))
    with patch("builtins.print"), patch("time.sleep"):
        import initialize_integrations_now  # noqa
    return sys.modules["initialize_integrations_now"], sys.modules["unified_api_server"]


class TestInitializeIntegrationsNow:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "initialize_integrations_now" in sys.modules

    def test_initialize_integrations_called(self, monkeypatch):
        _, unified = _prep(monkeypatch)
        unified.initialize_integrations.assert_called_once()

    def test_n8n_base_url_set_when_missing(self, monkeypatch):
        sys.modules.pop("initialize_integrations_now", None)
        monkeypatch.delenv("N8N_BASE_URL", raising=False)
        monkeypatch.setitem(sys.modules, "_paths", _make_paths_stub())
        monkeypatch.setitem(sys.modules, "unified_api_server", _make_unified_api_stub())
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"), patch("time.sleep"):
            import initialize_integrations_now  # noqa
        import os
        assert os.getenv("N8N_BASE_URL") is not None
        assert "5678" in os.getenv("N8N_BASE_URL")  # type: ignore

    def test_n8n_base_url_not_overwritten_when_present(self, monkeypatch):
        sys.modules.pop("initialize_integrations_now", None)
        monkeypatch.setenv("N8N_BASE_URL", "http://custom-n8n:9999")
        sys.modules.setdefault("_paths", _make_paths_stub())
        monkeypatch.setitem(sys.modules, "unified_api_server", _make_unified_api_stub())
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"), patch("time.sleep"):
            import initialize_integrations_now  # noqa
        import os
        assert os.getenv("N8N_BASE_URL") == "http://custom-n8n:9999"

    def test_import_error_handled(self, monkeypatch):
        sys.modules.pop("initialize_integrations_now", None)
        sys.modules.pop("unified_api_server", None)
        # Don't inject unified_api_server stub → ImportError path
        sys.modules.setdefault("_paths", _make_paths_stub())
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"), patch("time.sleep"):
            import initialize_integrations_now  # noqa – error branch
