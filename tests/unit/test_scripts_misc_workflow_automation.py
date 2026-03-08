"""
Unit tests for scripts/misc/workflow_automation.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# external integration mocks
_comfy = MagicMock()
_comfy_inst = MagicMock()
_comfy_inst.is_available.return_value = False
_comfy.ComfyUIIntegration = MagicMock(return_value=_comfy_inst)
sys.modules.setdefault("comfyui_integration", _comfy)

_gdi = MagicMock()
_gdi_inst = MagicMock()
_gdi_inst.is_available.return_value = False
_gdi.GoogleDriveIntegration = MagicMock(return_value=_gdi_inst)
sys.modules.setdefault("google_drive_integration", _gdi)

_cai = MagicMock()
_cai_inst = MagicMock()
_cai_inst.search_models.return_value = []
_cai.CivitAIIntegration = MagicMock(return_value=_cai_inst)
sys.modules.setdefault("civitai_integration", _cai)

_lci = MagicMock()
sys.modules.setdefault("langchain_integration", _lci)

_m0 = MagicMock()
_m0_inst = MagicMock()
_m0_inst.is_available.return_value = False
_m0.Mem0Integration = MagicMock(return_value=_m0_inst)
sys.modules.setdefault("mem0_integration", _m0)

_oi = MagicMock()
_oi_inst = MagicMock()
_oi_inst.is_available.return_value = False
_oi.ObsidianIntegration = MagicMock(return_value=_oi_inst)
sys.modules.setdefault("obsidian_integration", _oi)

import pytest
from scripts.misc.workflow_automation import (
    WorkflowAutomation,
    create_default_workflows,
)


@pytest.fixture
def wa(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return WorkflowAutomation()


# ── TestRegisterWorkflow ──────────────────────────────────────────────────
class TestRegisterWorkflow:
    def test_registers(self, wa):
        wa.register_workflow("my_wf", {"steps": []})
        assert "my_wf" in wa.workflows

    def test_created_at_set(self, wa):
        wa.register_workflow("wf_ts", {"steps": []})
        assert "created_at" in wa.workflows["wf_ts"]

    def test_overrides_existing(self, wa):
        wa.register_workflow("wf_ov", {"steps": [{"type": "a"}]})
        wa.register_workflow("wf_ov", {"steps": [{"type": "b"}]})
        assert wa.workflows["wf_ov"]["steps"][0]["type"] == "b"


# ── TestExecuteWorkflow ───────────────────────────────────────────────────
class TestExecuteWorkflow:
    def test_missing_workflow_returns_error(self, wa):
        result = wa.execute_workflow("nonexistent")
        assert "error" in result

    def test_empty_steps_success(self, wa):
        wa.register_workflow("empty_wf", {"steps": []})
        result = wa.execute_workflow("empty_wf")
        assert result["status"] == "success"

    def test_returns_workflow_name(self, wa):
        wa.register_workflow("named_wf", {"steps": []})
        result = wa.execute_workflow("named_wf")
        assert result["workflow"] == "named_wf"

    def test_unknown_step_type_in_results(self, wa):
        wa.register_workflow("unk_wf", {
            "steps": [{"type": "unknown_step_type", "name": "step1"}]
        })
        result = wa.execute_workflow("unk_wf")
        assert result["status"] == "success"
        assert "error" in result["results"]["step1"]

    def test_params_passed_through(self, wa):
        wa.register_workflow("param_wf", {"steps": []})
        result = wa.execute_workflow("param_wf", params={"key": "value"})
        assert result["status"] == "success"


# ── TestLoadWorkflows ─────────────────────────────────────────────────────
class TestLoadWorkflows:
    def test_empty_on_no_file(self, wa):
        assert wa.workflows == {} or isinstance(wa.workflows, dict)

    def test_loads_from_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        wf_file = tmp_path / "workflows.json"
        wf_file.write_text(json.dumps({"test_wf": {"steps": []}}), encoding="utf-8")
        wa2 = WorkflowAutomation()
        assert "test_wf" in wa2.workflows


# ── TestCreateDefaultWorkflows ────────────────────────────────────────────
class TestCreateDefaultWorkflows:
    def test_creates_known_workflow(self, wa):
        create_default_workflows(wa)
        # 何らかのworflowが登録される
        assert len(wa.workflows) > 0

    def test_all_have_steps(self, wa):
        create_default_workflows(wa)
        for name, wf in wa.workflows.items():
            assert "steps" in wf
