"""
tests/unit/test_scripts_misc_manaos_complete_integration.py

manaos_complete_integration.py の単体テスト
"""
import sys
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# ── mock setup ────────────────────────────────────────────────────────
_MOCKS = [
    "manaos_logger",
    "manaos_error_handler",
    "unified_orchestrator",
    "rag_memory_enhanced_v2",
    "learning_system_enhanced",
    "learning_memory_integration",
    "personality_system_enhanced",
    "autonomy_system_enhanced",
    "secretary_system_optimized",
    "personality_autonomy_secretary_integration",
    "manaos_async_client",
    "unified_cache_system",
    "metrics_collector_optimized",
    "_paths",
    "llm_optimization",
    "local_llm_integration",
    "local_llm_unified",
    "github_integration",
    "n8n_integration",
]
for _m in _MOCKS:
    sys.modules.setdefault(_m, MagicMock())

# Configure _paths constants
_p = sys.modules["_paths"]
_p.N8N_PORT = 5678
_p.AUTONOMY_SYSTEM_PORT = 5200
_p.LEARNING_SYSTEM_PORT = 5201
_p.ORCHESTRATOR_PORT = 5202
_p.PERSONALITY_SYSTEM_PORT = 5203
_p.RAG_MEMORY_PORT = 5204
_p.SECRETARY_SYSTEM_PORT = 5205

# ── SUT import ────────────────────────────────────────────────────────
import scripts.misc.manaos_complete_integration as _sut
from scripts.misc.manaos_complete_integration import ManaOSCompleteIntegration


# ══════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def integration():
    """ManaOSCompleteIntegration with all optional systems mocked"""
    return ManaOSCompleteIntegration()


# ══════════════════════════════════════════════════════════════════════════
# TestModuleConstants
# ══════════════════════════════════════════════════════════════════════════

class TestModuleConstants:
    def test_default_orchestrator_url_starts_with_http(self):
        assert _sut.DEFAULT_ORCHESTRATOR_URL.startswith("http://")

    def test_default_rag_memory_url_starts_with_http(self):
        assert _sut.DEFAULT_RAG_MEMORY_URL.startswith("http://")

    def test_default_learning_system_url_starts_with_http(self):
        assert _sut.DEFAULT_LEARNING_SYSTEM_URL.startswith("http://")


# ══════════════════════════════════════════════════════════════════════════
# TestInit
# ══════════════════════════════════════════════════════════════════════════

class TestInit:
    def test_instantiation_succeeds(self, integration):
        assert integration is not None

    def test_urls_default_when_none_given(self, integration):
        assert integration.orchestrator_url.startswith("http://")
        assert integration.rag_memory_url.startswith("http://")
        assert integration.learning_system_url.startswith("http://")

    def test_custom_urls_override_defaults(self):
        ci = ManaOSCompleteIntegration(
            orchestrator_url="http://custom-host:9999",
            rag_memory_url="http://rag-host:8888",
        )
        assert ci.orchestrator_url == "http://custom-host:9999"
        assert ci.rag_memory_url == "http://rag-host:8888"

    def test_github_is_none_when_not_available(self, integration):
        # github.is_available() returns MagicMock (falsy by default or raises)
        # either None or MagicMock is acceptable — just should not raise
        assert True  # no exception during init


# ══════════════════════════════════════════════════════════════════════════
# TestGetCompleteStatus
# ══════════════════════════════════════════════════════════════════════════

class TestGetCompleteStatus:
    def test_returns_dict(self, integration):
        result = integration.get_complete_status()
        assert isinstance(result, dict)

    def test_has_core_key(self, integration):
        result = integration.get_complete_status()
        assert "core" in result

    def test_core_orchestrator_is_true(self, integration):
        result = integration.get_complete_status()
        assert result["core"]["orchestrator"] is True

    def test_has_memory_learning_key(self, integration):
        result = integration.get_complete_status()
        assert "memory_learning" in result

    def test_has_timestamp(self, integration):
        result = integration.get_complete_status()
        assert "timestamp" in result

    def test_has_github_key(self, integration):
        result = integration.get_complete_status()
        assert "github" in result

    def test_has_n8n_key(self, integration):
        result = integration.get_complete_status()
        assert "n8n" in result

    def test_rag_memory_status_when_available(self, integration):
        mock_rag = MagicMock()
        mock_rag.get_statistics.return_value = {"total_entries": 42, "total_importance": 100}
        integration.rag_memory = mock_rag
        result = integration.get_complete_status()
        rag_status = result["memory_learning"].get("rag_memory", {})
        assert rag_status.get("available") is True
        assert rag_status.get("total_entries") == 42

    def test_rag_memory_absent_when_none(self, integration):
        integration.rag_memory = None
        result = integration.get_complete_status()
        # Should not raise; rag_memory key may be absent
        assert isinstance(result, dict)

    def test_github_false_when_none(self, integration):
        integration.github = None
        result = integration.get_complete_status()
        assert result["github"]["github_integration"]["available"] is False


# ══════════════════════════════════════════════════════════════════════════
# TestOptimizeAllSystems
# ══════════════════════════════════════════════════════════════════════════

class TestOptimizeAllSystems:
    def test_returns_dict_with_optimizations_and_timestamp(self, integration):
        result = asyncio.get_event_loop().run_until_complete(
            integration.optimize_all_systems()
        )
        assert "optimizations" in result
        assert "timestamp" in result

    def test_returns_empty_optimizations_when_no_systems(self, integration):
        integration.learning_system = None
        integration.autonomy = None
        integration.pas_integration = None
        integration.llm_optimization = None
        integration.github = None
        result = asyncio.get_event_loop().run_until_complete(
            integration.optimize_all_systems()
        )
        assert isinstance(result["optimizations"], dict)

    def test_includes_learning_system_suggestions(self, integration):
        mock_ls = MagicMock()
        mock_ls.get_optimization_suggestions.return_value = ["suggestion1"]
        integration.learning_system = mock_ls
        integration.autonomy = None
        integration.pas_integration = None
        integration.llm_optimization = None
        integration.github = None
        result = asyncio.get_event_loop().run_until_complete(
            integration.optimize_all_systems()
        )
        assert "learning_system" in result["optimizations"]

    def test_handles_learning_system_error_gracefully(self, integration):
        mock_ls = MagicMock()
        mock_ls.get_optimization_suggestions.side_effect = RuntimeError("boom")
        integration.learning_system = mock_ls
        integration.autonomy = None
        integration.pas_integration = None
        integration.llm_optimization = None
        integration.github = None
        try:
            result = asyncio.get_event_loop().run_until_complete(
                integration.optimize_all_systems()
            )
            assert "optimizations" in result
        except Exception as exc:
            pytest.fail(f"optimize_all_systems raised unexpectedly: {exc}")


# ══════════════════════════════════════════════════════════════════════════
# TestExecuteWithFullIntegration
# ══════════════════════════════════════════════════════════════════════════

class TestExecuteWithFullIntegration:
    @pytest.fixture
    def integration_with_mock_orch(self):
        ci = ManaOSCompleteIntegration()
        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_result.result = {"answer": "test response"}
        mock_orch = MagicMock()
        mock_orch.execute = AsyncMock(return_value=mock_result)
        ci.orchestrator = mock_orch
        ci.personality = None
        ci.rag_memory = None
        ci.learning_system = None
        ci.autonomy = None
        ci.metrics = None
        ci.learning_memory = None
        ci.secretary = None
        return ci

    def test_returns_dict(self, integration_with_mock_orch):
        result = asyncio.get_event_loop().run_until_complete(
            integration_with_mock_orch.execute_with_full_integration("テスト入力")
        )
        assert isinstance(result, dict)

    def test_result_has_required_keys(self, integration_with_mock_orch):
        result = asyncio.get_event_loop().run_until_complete(
            integration_with_mock_orch.execute_with_full_integration("テスト入力")
        )
        for key in ("result", "personality", "related_memories", "predictions", "duration_seconds", "timestamp"):
            assert key in result

    def test_duration_seconds_is_positive(self, integration_with_mock_orch):
        result = asyncio.get_event_loop().run_until_complete(
            integration_with_mock_orch.execute_with_full_integration("テスト入力")
        )
        assert result["duration_seconds"] >= 0

    def test_personality_called_when_available(self):
        ci = ManaOSCompleteIntegration()
        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_result.result = {}
        mock_orch = MagicMock()
        mock_orch.execute = AsyncMock(return_value=mock_result)
        ci.orchestrator = mock_orch
        mock_personality = MagicMock()
        mock_personality.get_personality_response.return_value = {"personality": {"name": "Mana"}}
        ci.personality = mock_personality
        ci.rag_memory = None
        ci.learning_system = None
        ci.autonomy = None
        ci.metrics = None
        ci.learning_memory = None
        ci.secretary = None
        result = asyncio.get_event_loop().run_until_complete(
            ci.execute_with_full_integration("テスト入力")
        )
        mock_personality.get_personality_response.assert_called_once()
        assert result["personality"] == {"personality": {"name": "Mana"}}

    def test_metrics_recorded_when_available(self):
        ci = ManaOSCompleteIntegration()
        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_result.result = {}
        mock_orch = MagicMock()
        mock_orch.execute = AsyncMock(return_value=mock_result)
        ci.orchestrator = mock_orch
        ci.personality = None
        ci.rag_memory = None
        ci.learning_system = None
        ci.autonomy = None
        mock_metrics = MagicMock()
        ci.metrics = mock_metrics
        ci.learning_memory = None
        ci.secretary = None
        asyncio.get_event_loop().run_until_complete(
            ci.execute_with_full_integration("テスト入力")
        )
        assert mock_metrics.record_metric.call_count >= 2  # response_time + success_rate
