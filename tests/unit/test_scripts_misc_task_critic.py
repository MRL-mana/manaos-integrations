"""
Unit tests for scripts/misc/task_critic.py
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_mock_err = MagicMock()
_mock_err.message = "mock error"
_eh_mod = MagicMock()
_eh_mod.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=_mock_err)
))
_eh_mod.ErrorCategory = MagicMock()
_eh_mod.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh_mod)

_tc_mod = MagicMock()
_tc_mod.get_timeout_config = MagicMock(return_value={"llm_call": 30.0})
sys.modules.setdefault("manaos_timeout_config", _tc_mod)

_cv_mod = MagicMock()
_cv_mod.ConfigValidator = MagicMock(return_value=MagicMock(
    validate_config=MagicMock(return_value=(True, []))
))
sys.modules.setdefault("manaos_config_validator", _cv_mod)

_paths_mod = MagicMock()
_paths_mod.OLLAMA_PORT = 11434
sys.modules.setdefault("_paths", _paths_mod)

import pytest  # noqa: E402
from scripts.misc.task_critic import (  # noqa: E402
    EvaluationResult,
    FailureReason,
    CriticResult,
    TaskCritic,
)


# ── helpers ────────────────────────────────────────────────────────────────
def make_critic() -> TaskCritic:
    tc = TaskCritic.__new__(TaskCritic)
    tc.ollama_url = "http://localhost:11434"
    tc.model = "qwen2.5:14b"
    tc.config = {"success_threshold": 0.7, "partial_success_threshold": 0.4}
    tc.evaluation_prompt_template = tc._get_default_evaluation_prompt_template()
    tc.evaluation_criteria = tc._get_default_evaluation_criteria()
    return tc


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def critic():
    return make_critic()


# ── TestEvaluationResult ───────────────────────────────────────────────────
class TestEvaluationResult:
    def test_values(self):
        assert EvaluationResult.SUCCESS == "success"
        assert EvaluationResult.FAILURE == "failure"
        assert EvaluationResult.PARTIAL_SUCCESS == "partial_success"
        assert EvaluationResult.UNCERTAIN == "uncertain"


# ── TestFailureReason ──────────────────────────────────────────────────────
class TestFailureReason:
    def test_values(self):
        assert FailureReason.TIMEOUT == "timeout"
        assert FailureReason.ERROR == "error"
        assert FailureReason.INVALID_OUTPUT == "invalid_output"
        assert FailureReason.INCOMPLETE == "incomplete"
        assert FailureReason.UNKNOWN == "unknown"


# ── TestCriticResult ───────────────────────────────────────────────────────
class TestCriticResult:
    def make_result(self, **kwargs):
        defaults = dict(
            evaluation=EvaluationResult.SUCCESS,
            score=0.8,
            failure_reason=None,
            issues=[],
            improvements=[],
            confidence=0.9,
            reasoning="ok",
            timestamp=datetime.now().isoformat(),
        )
        defaults.update(kwargs)
        return CriticResult(**defaults)

    def test_fields_accessible(self):
        r = self.make_result()
        assert r.evaluation == EvaluationResult.SUCCESS
        assert r.score == 0.8
        assert r.confidence == 0.9
        assert r.issues == []

    def test_failure_reason_none_allowed(self):
        r = self.make_result(failure_reason=None)
        assert r.failure_reason is None


# ── TestGetDefaultConfig ───────────────────────────────────────────────────
class TestGetDefaultConfig:
    def test_has_required_keys(self, critic):
        cfg = critic._get_default_config()
        for key in ("ollama_url", "model", "evaluation_criteria",
                    "success_threshold", "partial_success_threshold"):
            assert key in cfg

    def test_success_threshold(self, critic):
        assert critic._get_default_config()["success_threshold"] == 0.7


# ── TestGetDefaultEvaluationCriteria ──────────────────────────────────────
class TestGetDefaultEvaluationCriteria:
    def test_has_three_tiers(self, critic):
        crit = critic._get_default_evaluation_criteria()
        assert "success" in crit
        assert "partial_success" in crit
        assert "failure" in crit

    def test_each_tier_has_conditions(self, critic):
        crit = critic._get_default_evaluation_criteria()
        for tier in ("success", "partial_success", "failure"):
            assert "conditions" in crit[tier]


# ── TestEvaluateWithRules ──────────────────────────────────────────────────
class TestEvaluateWithRules:
    def test_failed_status_returns_failure(self, critic):
        result = critic._evaluate_with_rules("failed", None, None, None)
        assert result is not None
        assert result.evaluation == EvaluationResult.FAILURE

    def test_error_returns_failure(self, critic):
        result = critic._evaluate_with_rules("completed", "some error", None, None)
        assert result.evaluation == EvaluationResult.FAILURE

    def test_error_sets_reason_error(self, critic):
        result = critic._evaluate_with_rules("completed", "boom", None, None)
        assert result.failure_reason == FailureReason.ERROR

    def test_timeout_too_long(self, critic):
        result = critic._evaluate_with_rules("running", None, {"data": 1}, 400.0)
        assert result.evaluation == EvaluationResult.FAILURE
        assert result.failure_reason == FailureReason.TIMEOUT

    def test_no_output_returns_invalid_output(self, critic):
        result = critic._evaluate_with_rules("completed", None, None, None)
        assert result.failure_reason == FailureReason.INVALID_OUTPUT

    def test_success_when_completed_with_output(self, critic):
        result = critic._evaluate_with_rules("completed", None, {"data": "ok"}, 10.0)
        assert result is not None
        assert result.evaluation == EvaluationResult.SUCCESS

    def test_success_has_high_score(self, critic):
        result = critic._evaluate_with_rules("completed", None, {"x": 1}, 5.0)
        assert result.score >= 0.7

    def test_failure_error_message_included(self, critic):
        result = critic._evaluate_with_rules("failed", "connection refused", None, None)
        assert "connection refused" in result.issues

    def test_none_for_ambiguous_case(self, critic):
        # status not "completed" or "failed", no error, has output, acceptable duration
        result = critic._evaluate_with_rules("running", None, {"x": 1}, 10.0)
        # Running with output - rule doesn't match any explicit pattern → None
        assert result is None


# ── TestIsSimpleEvaluation ─────────────────────────────────────────────────
class TestIsSimpleEvaluation:
    def test_conversation_is_simple(self, critic):
        assert critic._is_simple_evaluation("conversation", "completed", None, {"x": 1}) is True

    def test_file_search_is_simple(self, critic):
        assert critic._is_simple_evaluation("file_search", "completed", None, {}) is True

    def test_completed_with_output_is_simple(self, critic):
        result = critic._is_simple_evaluation("complex_task", "completed", None, {"result": "ok"})
        assert result is True

    def test_failed_is_simple(self, critic):
        assert critic._is_simple_evaluation("complex_task", "failed", "error!", None) is True

    def test_short_output_is_simple(self, critic):
        assert critic._is_simple_evaluation("complex_task", "running", None, "short") is True

    def test_long_output_not_simple(self, critic):
        long_output = "x" * 1000
        assert critic._is_simple_evaluation("complex_task", "running", None, long_output) is False


# ── TestCreateFallbackEvaluation ───────────────────────────────────────────
class TestCreateFallbackEvaluation:
    def test_completed_no_error_is_success(self, critic):
        result = critic._create_fallback_evaluation("completed", None)
        assert result.evaluation == EvaluationResult.SUCCESS

    def test_failed_is_failure(self, critic):
        result = critic._create_fallback_evaluation("failed", "some error")
        assert result.evaluation == EvaluationResult.FAILURE

    def test_completed_with_error_is_failure(self, critic):
        result = critic._create_fallback_evaluation("completed", "error!")
        assert result.evaluation == EvaluationResult.FAILURE

    def test_fallback_has_moderate_confidence(self, critic):
        result = critic._create_fallback_evaluation("completed", None)
        assert 0.0 < result.confidence <= 1.0


# ── TestEvaluate ───────────────────────────────────────────────────────────
class TestEvaluate:
    def test_rule_based_high_confidence_returned(self, critic):
        # status=failed → rule returns FAILURE with confidence=0.9 → should return immediately
        result = critic.evaluate(
            intent_type="api_call",
            original_input="do something",
            plan={},
            status="failed",
            error=None
        )
        assert result.evaluation == EvaluationResult.FAILURE

    def test_returns_critic_result(self, critic):
        result = critic.evaluate("test", "input", {}, "failed")
        assert isinstance(result, CriticResult)

    def test_llm_fallback_when_rules_return_none(self, critic):
        # Ambiguous case → rules return None, LLM is called
        with patch.object(critic, "_evaluate_with_llm") as mock_llm:
            mock_llm.return_value = CriticResult(
                evaluation=EvaluationResult.PARTIAL_SUCCESS,
                score=0.5,
                failure_reason=None,
                issues=[],
                improvements=[],
                confidence=0.6,
                reasoning="partial",
                timestamp=datetime.now().isoformat(),
            )
            result = critic.evaluate(
                "complex",
                "do long task",
                {},
                "running",
                output={"x": 1},
                duration=60.0,
            )
            mock_llm.assert_called_once()
            assert result.evaluation == EvaluationResult.PARTIAL_SUCCESS
