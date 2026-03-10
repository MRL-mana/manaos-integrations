"""
Unit tests for scripts/misc/personality_autonomy_secretary_integration.py
All external system classes are mocked at import time.
"""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

# ── Standard mocks ────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
sys.modules.setdefault("manaos_error_handler", _eh)

# ── Sub-system mocks ──────────────────────────────────────────────────────────
# PersonalitySystem mock
_ps_inst = MagicMock()
_ps_inst.get_current_persona.return_value = {
    "name": "Remi",
    "tone": "friendly",
    "response_style": "casual",
    "traits": ["empathetic", "curious"],
}
_ps_mod = MagicMock()
_ps_mod.PersonalitySystem.return_value = _ps_inst

# AutonomySystem mock
_as_inst = MagicMock()
_as_inst.autonomy_level = MagicMock(value="semi_auto")
_as_inst.tasks = []
_as_mod = MagicMock()
_as_mod.AutonomySystem.return_value = _as_inst

# SecretarySystemOptimized mock
_ss_inst = MagicMock()
_ss_inst.get_pending_reminders.return_value = []
_ss_inst.get_recent_reports.return_value = []
_ss_mod = MagicMock()
_ss_mod.SecretarySystemOptimized.return_value = _ss_inst
_ss_mod.Reminder = MagicMock
_ss_mod.ReminderType = MagicMock(side_effect=lambda x: x)

# LearningMemoryIntegration mock
_lm_inst = MagicMock()
_lm_inst.get_integrated_stats.return_value = {
    "learning": {"total_actions": 5},
    "memory": {"total_entries": 10},
}
_lm_inst.record_and_learn = MagicMock()
_lm_inst.analyze_and_optimize = MagicMock(return_value={"recommendations": []})
_lm_mod = MagicMock()
_lm_mod.LearningMemoryIntegration.return_value = _lm_inst

# unified_cache_system mock
_uc = MagicMock()
_uc.get_unified_cache.return_value = MagicMock()

# Install stubs (save originals to restore after SUT import)
_orig_ps = sys.modules.pop("personality_system", None)
_orig_as = sys.modules.pop("autonomy_system", None)
_orig_ss = sys.modules.pop("secretary_system_optimized", None)
_orig_lm = sys.modules.pop("learning_memory_integration", None)
_orig_uc = sys.modules.pop("unified_cache_system", None)
sys.modules["personality_system"] = _ps_mod
sys.modules["autonomy_system"] = _as_mod
sys.modules["secretary_system_optimized"] = _ss_mod
sys.modules["learning_memory_integration"] = _lm_mod
sys.modules["unified_cache_system"] = _uc

# ── Import target ─────────────────────────────────────────────────────────────
sys.modules.pop("scripts.misc.personality_autonomy_secretary_integration", None)
from scripts.misc.personality_autonomy_secretary_integration import (  # noqa: E402
    PersonalityAutonomySecretaryIntegration,
)
# Restore real modules; SUT already captured stub class references.
# If a module wasn't in sys.modules originally (_orig is None), it means the
# real module doesn't exist on this system – keep the mock so lazy imports
# inside SUT methods (e.g. `from secretary_system_optimized import Report`)
# can resolve correctly during tests.
for _name, _orig in [
    ("personality_system", _orig_ps),
    ("autonomy_system", _orig_as),
    ("secretary_system_optimized", _orig_ss),
    ("learning_memory_integration", _orig_lm),
    ("unified_cache_system", _orig_uc),
]:
    if _orig is not None:
        sys.modules[_name] = _orig
    # else: keep our mock – the real module does not exist


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def integration():
    return PersonalityAutonomySecretaryIntegration()


# ── TestGetPersonaDisplay ─────────────────────────────────────────────────────
class TestGetPersonaDisplay:
    def test_returns_simple_namespace(self, integration):
        persona = integration._get_persona_display()
        assert hasattr(persona, "name")
        assert hasattr(persona, "tone")
        assert hasattr(persona, "response_style")
        assert hasattr(persona, "traits")

    def test_name_from_dict(self, integration):
        persona = integration._get_persona_display()
        assert persona.name == "Remi"

    def test_tone_from_dict(self, integration):
        persona = integration._get_persona_display()
        assert persona.tone == "friendly"

    def test_traits_are_list(self, integration):
        persona = integration._get_persona_display()
        assert isinstance(persona.traits, list)

    def test_traits_are_strings(self, integration):
        persona = integration._get_persona_display()
        for t in persona.traits:
            assert isinstance(t, str)

    def test_object_persona_pass_through(self, integration):
        """get_current_persona がオブジェクト（非 dict）を返す場合も動作する"""
        obj_persona = SimpleNamespace(
            name="RemiObj",
            tone="warm",
            response_style="detailed",
            traits=["precise"],
        )
        integration.personality.get_current_persona.return_value = obj_persona
        persona = integration._get_persona_display()
        # Should return the object directly when it's not a dict
        assert persona.name == "RemiObj"
        # Restore
        integration.personality.get_current_persona.return_value = {
            "name": "Remi",
            "tone": "friendly",
            "response_style": "casual",
            "traits": ["empathetic", "curious"],
        }


# ── TestExecuteWithPersonality ────────────────────────────────────────────────
class TestExecuteWithPersonality:
    def test_returns_dict(self, integration):
        result = integration.execute_with_personality("greet", {"user": "Alice"})
        assert isinstance(result, dict)

    def test_action_in_result(self, integration):
        result = integration.execute_with_personality("greet", {})
        assert result["action"] == "greet"

    def test_context_in_result(self, integration):
        ctx = {"key": "value"}
        result = integration.execute_with_personality("test", ctx)
        assert result["context"] == ctx

    def test_personality_subdict_present(self, integration):
        result = integration.execute_with_personality("test", {})
        assert "personality" in result
        assert "name" in result["personality"]
        assert result["personality"]["name"] == "Remi"

    def test_timestamp_present(self, integration):
        result = integration.execute_with_personality("test", {})
        assert "timestamp" in result

    def test_record_and_learn_called(self, integration):
        integration.learning_memory.record_and_learn.reset_mock()
        integration.execute_with_personality("greet", {})
        integration.learning_memory.record_and_learn.assert_called_once()


# ── TestExecuteAutonomousTask ─────────────────────────────────────────────────
class TestExecuteAutonomousTask:
    def test_disabled_level_returns_disabled(self, integration):
        from unittest.mock import MagicMock
        integration.autonomy = MagicMock()
        integration.autonomy.autonomy_level = MagicMock(value="disabled")
        result = integration.execute_autonomous_task("check", {}, {})
        assert result["status"] == "disabled"

    def test_enabled_level_returns_success(self, integration):
        from unittest.mock import MagicMock
        integration.autonomy = MagicMock()
        integration.autonomy.autonomy_level = MagicMock(value="semi_auto")
        result = integration.execute_autonomous_task("check", {"cond": True}, {"action": "run"})
        assert result["status"] == "success"

    def test_task_type_in_result(self, integration):
        from unittest.mock import MagicMock
        integration.autonomy = MagicMock()
        integration.autonomy.autonomy_level = MagicMock(value="full_auto")
        result = integration.execute_autonomous_task("file_scan", {}, {})
        assert result["task_type"] == "file_scan"

    def test_timestamp_present(self, integration):
        result = integration.execute_autonomous_task("check", {}, {})
        assert "timestamp" in result

    def test_record_and_learn_called(self, integration):
        from unittest.mock import MagicMock
        integration.autonomy = MagicMock()
        integration.autonomy.autonomy_level = MagicMock(value="semi_auto")
        integration.learning_memory.record_and_learn.reset_mock()
        integration.execute_autonomous_task("ping", {}, {})
        integration.learning_memory.record_and_learn.assert_called_once()


# ── TestGeneratePersonalityReport ─────────────────────────────────────────────
class TestGeneratePersonalityReport:
    def test_returns_dict(self, integration):
        result = integration.generate_personality_report()
        assert isinstance(result, dict)

    def test_has_required_keys(self, integration):
        result = integration.generate_personality_report()
        assert "report_id" in result
        assert "content" in result
        assert "personality" in result

    def test_daily_report_type(self, integration):
        result = integration.generate_personality_report("daily")
        assert isinstance(result, dict)
        assert result["personality"] == "Remi"

    def test_weekly_report_type(self, integration):
        result = integration.generate_personality_report("weekly")
        assert isinstance(result, dict)
        assert result["personality"] == "Remi"


# ── TestGetIntegratedStatus ───────────────────────────────────────────────────
class TestGetIntegratedStatus:
    def test_returns_dict(self, integration):
        result = integration.get_integrated_status()
        assert isinstance(result, dict)

    def test_has_personality_key(self, integration):
        result = integration.get_integrated_status()
        assert "personality" in result
        assert result["personality"]["current_persona"] == "Remi"

    def test_has_autonomy_key(self, integration):
        result = integration.get_integrated_status()
        assert "autonomy" in result
        assert "level" in result["autonomy"]

    def test_has_secretary_key(self, integration):
        result = integration.get_integrated_status()
        assert "secretary" in result

    def test_has_learning_memory_key(self, integration):
        result = integration.get_integrated_status()
        assert "learning_memory" in result

    def test_has_timestamp(self, integration):
        result = integration.get_integrated_status()
        assert "timestamp" in result


# ── TestOptimizeBasedOnLearning ───────────────────────────────────────────────
class TestOptimizeBasedOnLearning:
    def test_returns_dict(self, integration):
        result = integration.optimize_based_on_learning()
        assert isinstance(result, dict)

    def test_has_optimizations_key(self, integration):
        result = integration.optimize_based_on_learning()
        assert "optimizations" in result
        assert isinstance(result["optimizations"], list)

    def test_empty_recommendations_gives_no_optimizations(self, integration):
        integration.learning_memory.analyze_and_optimize.return_value = {
            "recommendations": []
        }
        result = integration.optimize_based_on_learning()
        assert result["optimizations"] == []

    def test_personality_recommendation_included(self, integration):
        integration.learning_memory.analyze_and_optimize.return_value = {
            "recommendations": ["personality"]
        }
        result = integration.optimize_based_on_learning()
        systems = [opt["system"] for opt in result["optimizations"]]
        assert "personality" in systems

    def test_autonomy_recommendation_included(self, integration):
        integration.learning_memory.analyze_and_optimize.return_value = {
            "recommendations": ["autonomy"]
        }
        result = integration.optimize_based_on_learning()
        systems = [opt["system"] for opt in result["optimizations"]]
        assert "autonomy" in systems

    def test_has_timestamp(self, integration):
        result = integration.optimize_based_on_learning()
        assert "timestamp" in result
