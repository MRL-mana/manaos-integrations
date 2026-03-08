"""
tests/unit/test_scripts_misc_ultimate_integration_system.py
Unit tests for scripts/misc/ultimate_integration_system.py
"""
import sys
import types
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


def _make_integration(available: bool = True) -> MagicMock:
    """Return a MagicMock integration that exposes is_available() and get_status()."""
    m = MagicMock()
    m.is_available.return_value = available
    m.get_status.return_value = {"status": "ok"}
    return m


# ---------------------------------------------------------------------------
# Stub ALL hard-import modules before importing the SUT
# ---------------------------------------------------------------------------
_STUBS = [
    "comfyui_integration",
    "google_drive_integration",
    "civitai_integration",
    "langchain_integration",
    "mem0_integration",
    "obsidian_integration",
    "crewai_integration",
    "workflow_automation",
    "ai_agent_autonomous",
    "predictive_maintenance",
    "auto_optimization",
    "learning_system",
    "multimodal_integration",
    "distributed_execution",
    "security_monitor",
    "notification_system",
    "backup_recovery",
    "performance_analytics",
    "cost_optimization",
    "streaming_processing",
    "batch_processing",
    "database_integration",
    "cloud_integration",
]

for _mod_name in _STUBS:
    if _mod_name not in sys.modules:
        _m = types.ModuleType(_mod_name)
        # Create a class attribute per known class name
        for _cls_name in [
            "ComfyUIIntegration",
            "GoogleDriveIntegration",
            "CivitAIIntegration",
            "LangChainIntegration",
            "LangGraphIntegration",
            "Mem0Integration",
            "ObsidianIntegration",
            "CrewAIIntegration",
            "WorkflowAutomation",
            "AutonomousAgent",
            "PredictiveMaintenance",
            "AutoOptimization",
            "LearningSystem",
            "MultimodalIntegration",
            "DistributedExecution",
            "SecurityMonitor",
            "NotificationSystem",
            "BackupRecovery",
            "PerformanceAnalytics",
            "CostOptimization",
            "StreamingProcessor",
            "BatchProcessor",
            "DatabaseIntegration",
            "CloudIntegration",
        ]:
            setattr(_m, _cls_name, MagicMock(return_value=_make_integration()))
        sys.modules[_mod_name] = _m

import scripts.misc.ultimate_integration_system as _sut


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_system() -> "_sut.UltimateIntegrationSystem":
    """
    Build an UltimateIntegrationSystem with all sub-integrations mocked.
    Patches Path.exists to return False (no state file / no vault).
    """
    with patch.object(Path, "exists", return_value=False):
        sys_obj = _sut.UltimateIntegrationSystem()
    return sys_obj


# ---------------------------------------------------------------------------
# Class: UltimateIntegrationSystem
# ---------------------------------------------------------------------------
class TestUltimateIntegrationSystemInit:
    def test_instantiation_succeeds(self):
        obj = _make_system()
        assert isinstance(obj, _sut.UltimateIntegrationSystem)

    def test_has_storage_path(self):
        obj = _make_system()
        assert isinstance(obj.storage_path, Path)

    def test_comfyui_attr_set(self):
        obj = _make_system()
        assert obj.comfyui is not None

    def test_drive_attr_set(self):
        obj = _make_system()
        assert obj.drive is not None

    def test_security_attr_set(self):
        obj = _make_system()
        assert obj.security is not None


class TestSaveState:
    def test_save_creates_temp_then_replaces(self):
        obj = _make_system()
        with patch("builtins.open", mock_open()) as m_open, \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "replace") as m_replace, \
             patch.object(Path, "with_suffix", return_value=Path("state.tmp")):
            obj._save_state()
            assert m_open.called
            assert m_replace.called

    def test_save_state_retries_on_error(self):
        obj = _make_system()
        call_count = [0]

        def failing_open(*a, **kw):
            call_count[0] += 1
            raise OSError("disk full")

        with patch("builtins.open", side_effect=failing_open), \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "with_suffix", return_value=Path("state.tmp")):
            # Should not raise; logs warning after max_retries
            obj._save_state(max_retries=2)

        assert call_count[0] == 2


class TestGetComprehensiveStatus:
    def test_returns_dict(self):
        obj = _make_system()
        status = obj.get_comprehensive_status()
        assert isinstance(status, dict)

    def test_has_basic_integrations_key(self):
        obj = _make_system()
        status = obj.get_comprehensive_status()
        assert "basic_integrations" in status

    def test_has_advanced_features_key(self):
        obj = _make_system()
        status = obj.get_comprehensive_status()
        assert "advanced_features" in status

    def test_has_agent_status_key(self):
        obj = _make_system()
        status = obj.get_comprehensive_status()
        assert "agent_status" in status

    def test_has_security_status_key(self):
        obj = _make_system()
        status = obj.get_comprehensive_status()
        assert "security_status" in status

    def test_has_timestamp(self):
        obj = _make_system()
        status = obj.get_comprehensive_status()
        assert "timestamp" in status
        assert isinstance(status["timestamp"], str)

    def test_basic_integrations_comfyui_present(self):
        obj = _make_system()
        status = obj.get_comprehensive_status()
        assert "comfyui" in status["basic_integrations"]


class TestExecuteIntelligentWorkflow:
    def test_returns_dict(self):
        obj = _make_system()
        result = obj.execute_intelligent_workflow("テスト")
        assert isinstance(result, dict)

    def test_result_has_request_key(self):
        obj = _make_system()
        result = obj.execute_intelligent_workflow("hello")
        assert result["request"] == "hello"

    def test_result_has_steps_list(self):
        obj = _make_system()
        result = obj.execute_intelligent_workflow("hello")
        assert isinstance(result["steps"], list)

    def test_security_check_passes(self):
        from unittest.mock import MagicMock
        obj = _make_system()
        obj.security = MagicMock()
        obj.security.check_request_security.return_value = {"allowed": True}
        obj.security.get_security_status.return_value = {}
        result = obj.execute_intelligent_workflow("test")
        assert result.get("error") is None

    def test_security_check_blocks(self):
        from unittest.mock import MagicMock
        obj = _make_system()
        obj.security = MagicMock()
        obj.security.check_request_security.return_value = {"allowed": False}
        obj.security.get_security_status.return_value = {}
        obj.langchain = MagicMock()
        obj.langchain.is_available.return_value = False
        result = obj.execute_intelligent_workflow("attack")
        assert "error" in result
        assert result["success"] is False


class TestRunFullSystemCheck:
    def test_returns_dict(self):
        obj = _make_system()
        result = obj.run_full_system_check()
        assert isinstance(result, dict)

    def test_has_timestamp(self):
        obj = _make_system()
        result = obj.run_full_system_check()
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    def test_has_checks_key(self):
        obj = _make_system()
        result = obj.run_full_system_check()
        assert "checks" in result

    def test_checks_has_basic_integrations(self):
        obj = _make_system()
        result = obj.run_full_system_check()
        assert "basic_integrations" in result["checks"]

    def test_checks_has_advanced_features(self):
        obj = _make_system()
        result = obj.run_full_system_check()
        assert "advanced_features" in result["checks"]

    def test_checks_has_security(self):
        obj = _make_system()
        result = obj.run_full_system_check()
        assert "security" in result["checks"]
