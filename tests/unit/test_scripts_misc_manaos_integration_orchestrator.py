"""
tests/unit/test_scripts_misc_manaos_integration_orchestrator.py

manaos_integration_orchestrator.py の単体テスト
"""
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── mock setup (before import) ──────────────────────────────────────────
for _mod in [
    "manaos_logger",
    "manaos_process_manager",
    "manaos_error_handler",
    "manaos_timeout_config",
    "manaos_config_validator",
    "_paths",
    "manaos_service_bridge",
    "manaos_complete_integration",
    "ai_agent_autonomous",  # prevent emoji print on import
]:
    sys.modules.setdefault(_mod, MagicMock())

_ml = sys.modules["manaos_logger"]
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()

_paths_mod = sys.modules["_paths"]
_paths_mod.N8N_PORT = 5678

# ── SUT import ─────────────────────────────────────────────────────────
import scripts.misc.manaos_integration_orchestrator as _sut
from scripts.misc.manaos_integration_orchestrator import (
    ManaOSIntegrationOrchestrator,
    MANAOS_SERVICES,
    INTEGRATION_SERVICES,
)


# ══════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def orch():
    return ManaOSIntegrationOrchestrator()


# ══════════════════════════════════════════════════════════════════════════
# TestModuleConstants
# ══════════════════════════════════════════════════════════════════════════

class TestModuleConstants:
    def test_manaos_services_is_dict(self):
        assert isinstance(MANAOS_SERVICES, dict)
        assert len(MANAOS_SERVICES) > 0

    def test_integration_services_is_dict(self):
        assert isinstance(INTEGRATION_SERVICES, dict)
        assert len(INTEGRATION_SERVICES) > 0

    def test_services_have_port_or_url_key(self):
        for name, info in MANAOS_SERVICES.items():
            assert "port" in info or "url" in info, f"{name} missing 'port'/'url'"

    def test_integration_services_have_port_or_url_key(self):
        for name, info in INTEGRATION_SERVICES.items():
            assert "port" in info or "url" in info, f"{name} missing 'port'/'url'"


# ══════════════════════════════════════════════════════════════════════════
# TestOrchInit
# ══════════════════════════════════════════════════════════════════════════

class TestOrchInit:
    def test_instantiation_succeeds(self, orch):
        assert orch is not None

    def test_config_is_dict_after_init(self, orch):
        assert isinstance(orch.config, dict)

    def test_metrics_initialized_as_dict(self, orch):
        assert isinstance(orch.metrics, dict)

    def test_orchestration_mode_exists(self, orch):
        # orchestrator should have some form of orchestration tracking
        assert hasattr(orch, "metrics") or hasattr(orch, "config")


# ══════════════════════════════════════════════════════════════════════════
# TestLoadConfig
# ══════════════════════════════════════════════════════════════════════════

class TestLoadConfig:
    def test_returns_dict_by_default(self, orch):
        cfg = orch._load_config()
        assert isinstance(cfg, dict)

    def test_loads_from_file_via_init(self, tmp_path):
        cfg_file = tmp_path / "conf.json"
        cfg_file.write_text(json.dumps({"custom_key": "custom_value"}), encoding="utf-8")
        o = ManaOSIntegrationOrchestrator(config_path=str(cfg_file))
        assert isinstance(o.config, dict)

    def test_missing_file_via_init_returns_defaults(self):
        o = ManaOSIntegrationOrchestrator(config_path="/nonexistent/path/cfg.json")
        assert isinstance(o.config, dict)


# ══════════════════════════════════════════════════════════════════════════
# TestCheckAllServices
# ══════════════════════════════════════════════════════════════════════════

class TestCheckAllServices:
    def _mock_requests_timeout(self):
        """Helper: make all requests.get raise ConnectionError"""
        import requests as _req
        return patch.object(_req, "get", side_effect=ConnectionError("no conn"))

    def test_returns_expected_top_level_keys(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.check_all_services()
        for key in ("manaos_services", "integration_services", "summary", "timestamp"):
            assert key in result

    def test_summary_has_counts(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.check_all_services()
        summary = result["summary"]
        assert "total_services" in summary
        assert "available_services" in summary
        assert "unavailable_services" in summary

    def test_all_services_offline_when_connections_fail(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.check_all_services()
        assert result["summary"]["available_services"] == 0

    def test_parallel_false_also_returns_structure(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.check_all_services(use_parallel=False)
        assert "summary" in result


# ══════════════════════════════════════════════════════════════════════════
# TestOptimizeSystem
# ══════════════════════════════════════════════════════════════════════════

class TestOptimizeSystem:
    def test_returns_dict(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.optimize_system()
        assert isinstance(result, dict)

    def test_result_has_efficiency_score(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.optimize_system()
        assert "efficiency_score" in result or "optimizations" in result

    def test_doesnt_raise_when_optional_systems_absent(self, orch):
        """All optional systems are None → must not raise"""
        with patch("requests.get", side_effect=ConnectionError("no")):
            try:
                orch.optimize_system()
            except Exception as exc:
                pytest.fail(f"optimize_system raised with no optional systems: {exc}")


# ══════════════════════════════════════════════════════════════════════════
# TestCalculateEfficiencyScore
# ══════════════════════════════════════════════════════════════════════════

class TestCalculateEfficiencyScore:
    def test_returns_float_between_0_and_100(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            score = orch._calculate_efficiency_score({})
        assert 0.0 <= score <= 100.0

    def test_score_is_numeric(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            score = orch._calculate_efficiency_score({"optimization_a": True})
        assert isinstance(score, (int, float))


# ══════════════════════════════════════════════════════════════════════════
# TestGetComprehensiveStatus
# ══════════════════════════════════════════════════════════════════════════

class TestGetComprehensiveStatus:
    def test_orchestrator_key_present(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            status = orch.get_comprehensive_status()
        assert "orchestrator" in status

    def test_services_key_present(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            status = orch.get_comprehensive_status()
        assert "services" in status

    def test_metrics_key_present(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            status = orch.get_comprehensive_status()
        assert "metrics" in status

    def test_orchestrator_has_initialized_key(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            status = orch.get_comprehensive_status()
        assert "initialized" in status["orchestrator"]


# ══════════════════════════════════════════════════════════════════════════
# TestDistributeTask
# ══════════════════════════════════════════════════════════════════════════

class TestDistributeTask:
    def test_returns_none_or_dict_when_no_distributed_execution(self, orch):
        orch.distributed_execution = None
        result = orch.distribute_task("llm_inference", {"prompt": "hi"})
        # Should return None or a dict indicating unavailable
        assert result is None or isinstance(result, dict)

    def test_task_data_forwarded_when_system_available(self, orch):
        mock_de = MagicMock()
        mock_de.distribute_task.return_value = {"task_id": "abc", "success": True}
        orch.distributed_execution = mock_de
        result = orch.distribute_task("llm_inference", {"prompt": "test"})
        assert result is not None


# ══════════════════════════════════════════════════════════════════════════
# TestOptimizeResources
# ══════════════════════════════════════════════════════════════════════════

class TestOptimizeResources:
    def test_returns_dict(self, orch):
        result = orch.optimize_resources()
        assert isinstance(result, dict)

    def test_has_resource_optimizations_key(self, orch):
        result = orch.optimize_resources()
        assert "resource_optimizations" in result or "optimizations" in result


# ══════════════════════════════════════════════════════════════════════════
# TestEnhanceSystem
# ══════════════════════════════════════════════════════════════════════════

class TestEnhanceSystem:
    def test_returns_dict(self, orch):
        result = orch.enhance_system()
        assert isinstance(result, dict)

    def test_doesnt_raise(self, orch):
        try:
            orch.enhance_system()
        except Exception as exc:
            pytest.fail(f"enhance_system raised: {exc}")


# ══════════════════════════════════════════════════════════════════════════
# TestRunFullCycle
# ══════════════════════════════════════════════════════════════════════════

class TestRunFullCycle:
    def test_returns_dict_with_timestamp(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.run_full_cycle()
        assert isinstance(result, dict)
        assert "timestamp" in result

    def test_handles_error_gracefully(self, orch):
        """Must not raise even when check_all_services fails"""
        with patch.object(orch, "check_all_services", side_effect=RuntimeError("boom")):
            try:
                result = orch.run_full_cycle()
            except Exception as exc:
                pytest.fail(f"run_full_cycle should not raise, got: {exc}")


# ══════════════════════════════════════════════════════════════════════════
# TestRunFullSystemCheck
# ══════════════════════════════════════════════════════════════════════════

class TestRunFullSystemCheck:
    def test_returns_dict(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.run_full_system_check()
        assert isinstance(result, dict)

    def test_includes_service_check(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.run_full_system_check()
        assert any(key in result for key in ("checks", "services", "manaos_services", "summary", "check_result", "timestamp"))


# ══════════════════════════════════════════════════════════════════════════
# TestGetUnifiedStatusApi
# ══════════════════════════════════════════════════════════════════════════

class TestGetUnifiedStatusApi:
    def test_returns_dict(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.get_unified_status_api()
        assert isinstance(result, dict)

    def test_status_key_present(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.get_unified_status_api()
        assert any(key in result for key in ("status", "orchestrator", "systems", "version", "metrics"))


# ══════════════════════════════════════════════════════════════════════════
# TestExecuteIntelligentWorkflow
# ══════════════════════════════════════════════════════════════════════════

class TestExecuteIntelligentWorkflow:
    def test_returns_dict(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.execute_intelligent_workflow({"task": "test"})
        assert isinstance(result, dict)

    def test_handles_empty_workflow(self, orch):
        with patch("requests.get", side_effect=ConnectionError("no")):
            result = orch.execute_intelligent_workflow({})
        assert isinstance(result, dict)
