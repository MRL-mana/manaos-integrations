"""Tests for scripts/misc/quick_start.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_stubs(monkeypatch):
    paths_mod = types.ModuleType("_paths")
    paths_mod.UNIFIED_API_PORT = 9502
    monkeypatch.setitem(sys.modules, "_paths", paths_mod)
    monkeypatch.setitem(sys.modules, "manaos_integrations._paths", paths_mod)

    # unified_api_server
    flask_app = MagicMock()
    flask_app.run = MagicMock()
    unified_mod = types.ModuleType("unified_api_server")
    unified_mod.app = flask_app
    unified_mod.initialize_integrations = MagicMock()
    unified_mod.integrations = {}
    monkeypatch.setitem(sys.modules, "unified_api_server", unified_mod)

    # workflow_automation
    wf_inst = MagicMock()
    wf_inst.workflows = {"generate_and_backup": MagicMock()}
    wf_inst.execute_workflow = MagicMock(return_value={"status": "ok"})
    wf_mod = types.ModuleType("workflow_automation")
    wf_mod.WorkflowAutomation = MagicMock(return_value=wf_inst)
    wf_mod.create_default_workflows = MagicMock()
    monkeypatch.setitem(sys.modules, "workflow_automation", wf_mod)

    # enhanced_civitai_downloader
    dl_inst = MagicMock()
    dl_inst.download_with_enhancements = MagicMock(return_value={"download_success": True})
    dl_inst.search_and_download = MagicMock(return_value=[])
    dl_mod = types.ModuleType("enhanced_civitai_downloader")
    dl_mod.EnhancedCivitaiDownloader = MagicMock(return_value=dl_inst)
    monkeypatch.setitem(sys.modules, "enhanced_civitai_downloader", dl_mod)

    # manaos_service_bridge
    sb_inst = MagicMock()
    sb_mod = types.ModuleType("manaos_service_bridge")
    sb_mod.ManaOSServiceBridge = MagicMock(return_value=sb_inst)
    monkeypatch.setitem(sys.modules, "manaos_service_bridge", sb_mod)

    return unified_mod, wf_inst, dl_inst


def _prep(monkeypatch):
    sys.modules.pop("quick_start", None)
    stubs = _make_stubs(monkeypatch)
    monkeypatch.syspath_prepend(str(_MISC))
    import quick_start as m
    return m, stubs


class TestQuickStartImport:
    def test_imports(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "quick_start" in sys.modules

    def test_has_functions(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        for fn in ("print_banner", "print_menu", "start_api_server",
                   "test_workflow_automation", "use_enhanced_downloader"):
            assert callable(getattr(m, fn))


class TestPrintBanner:
    def test_runs_without_error(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            m.print_banner()


class TestPrintMenu:
    def test_runs_without_error(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        with patch("builtins.print"):
            m.print_menu()


class TestStartApiServer:
    def test_calls_initialize_integrations(self, monkeypatch):
        m, (unified_mod, *_) = _prep(monkeypatch)
        with patch("builtins.print"):
            # app.run would block; patch it
            unified_mod.app.run.return_value = None
            m.start_api_server()
        unified_mod.initialize_integrations.assert_called_once()

    def test_calls_app_run(self, monkeypatch):
        m, (unified_mod, *_) = _prep(monkeypatch)
        with patch("builtins.print"):
            m.start_api_server()
        unified_mod.app.run.assert_called_once()


class TestTestWorkflowAutomation:
    def test_create_default_called(self, monkeypatch):
        m, (_, wf_inst, *_) = _prep(monkeypatch)
        import workflow_automation
        with patch("builtins.print"):
            m.test_workflow_automation()
        workflow_automation.create_default_workflows.assert_called_once()

    def test_execute_workflow_called(self, monkeypatch):
        m, (_, wf_inst, *_) = _prep(monkeypatch)
        with patch("builtins.print"):
            m.test_workflow_automation()
        wf_inst.execute_workflow.assert_called_once()


class TestUseEnhancedDownloader:
    def test_download_with_model_id(self, monkeypatch):
        m, (_, _, dl_inst) = _prep(monkeypatch)
        with patch("builtins.input", side_effect=["999", ""]), \
             patch("builtins.print"):
            m.use_enhanced_downloader()
        dl_inst.download_with_enhancements.assert_called_once()

    def test_search_with_query(self, monkeypatch):
        m, (_, _, dl_inst) = _prep(monkeypatch)
        with patch("builtins.input", side_effect=["", "anime lora"]), \
             patch("builtins.print"):
            m.use_enhanced_downloader()
        dl_inst.search_and_download.assert_called_once()

    def test_skip_both_no_download(self, monkeypatch):
        m, (_, _, dl_inst) = _prep(monkeypatch)
        with patch("builtins.input", side_effect=["", ""]), \
             patch("builtins.print"):
            m.use_enhanced_downloader()
        dl_inst.download_with_enhancements.assert_not_called()
        dl_inst.search_and_download.assert_not_called()
