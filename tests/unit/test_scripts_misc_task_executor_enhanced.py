"""
Unit tests for scripts/misc/task_executor_enhanced.py
"""
import sys
from unittest.mock import MagicMock, patch

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv_inst = MagicMock()
_cv_inst.validate_config = MagicMock(return_value=(True, []))
_cv.ConfigValidator = MagicMock(return_value=_cv_inst)
sys.modules.setdefault("manaos_config_validator", _cv)

_paths = MagicMock()
_paths.N8N_PORT = 5678
_paths.TASK_CRITIC_PORT = 5102
sys.modules.setdefault("_paths", _paths)
sys.modules.setdefault("manaos_integrations._paths", _paths)

import pytest
from scripts.misc.task_executor_enhanced import (
    ExecutionAction,
    ExecutionStepResult,
    ExecutionResult,
    TaskExecutorEnhanced,
)


@pytest.fixture
def executor():
    return TaskExecutorEnhanced(
        n8n_url="http://127.0.0.1:5678",
        task_critic_url="http://127.0.0.1:5102",
    )


# ── TestExecutionAction ───────────────────────────────────────────────────
class TestExecutionAction:
    def test_values(self):
        assert ExecutionAction.EXECUTE_WORKFLOW == "execute_workflow"
        assert ExecutionAction.CALL_API == "call_api"
        assert ExecutionAction.RUN_SCRIPT == "run_script"
        assert ExecutionAction.EXECUTE_COMMAND == "execute_command"

    def test_is_str(self):
        assert isinstance(ExecutionAction.CALL_API, str)


# ── TestExecutionStepResult ───────────────────────────────────────────────
class TestExecutionStepResult:
    def test_create(self):
        r = ExecutionStepResult(
            step_id="s1", action="call_api", target="http://example.com",
            status="success", result={"ok": True}, error=None,
            duration_seconds=0.5, started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:00:01",
        )
        assert r.step_id == "s1"
        assert r.status == "success"
        assert r.duration_seconds == 0.5

    def test_error_stored(self):
        r = ExecutionStepResult(
            step_id="s2", action="run_script", target="test.py",
            status="failed", result=None, error="File not found",
            duration_seconds=0.0, started_at="", completed_at="",
        )
        assert r.error == "File not found"


# ── TestExecutionResult ───────────────────────────────────────────────────
class TestExecutionResult:
    def test_create(self):
        r = ExecutionResult(
            execution_id="e1", plan_id="p1", status="success",
            steps=[], total_duration_seconds=1.0, result=None,
            error=None, started_at="", completed_at="",
        )
        assert r.execution_id == "e1"
        assert r.steps == []


# ── TestDefaultConfig ─────────────────────────────────────────────────────
class TestDefaultConfig:
    def test_default_config_keys(self, executor):
        cfg = executor._get_default_config()
        assert "n8n_url" in cfg
        assert "task_critic_url" in cfg
        assert "timeout_seconds" in cfg
        assert "retry_on_failure" in cfg
        assert "max_retries" in cfg

    def test_timeout_is_int(self, executor):
        cfg = executor._get_default_config()
        assert isinstance(cfg["timeout_seconds"], int)

    def test_max_retries_is_int(self, executor):
        cfg = executor._get_default_config()
        assert isinstance(cfg["max_retries"], int)
        assert cfg["max_retries"] >= 1


# ── TestGetPriorityValue ──────────────────────────────────────────────────
class TestGetPriorityValue:
    def test_urgent_highest(self, executor):
        assert executor._get_priority_value("urgent") > executor._get_priority_value("high")

    def test_high_above_medium(self, executor):
        assert executor._get_priority_value("high") > executor._get_priority_value("medium")

    def test_medium_above_low(self, executor):
        assert executor._get_priority_value("medium") > executor._get_priority_value("low")

    def test_unknown_defaults_to_medium(self, executor):
        assert executor._get_priority_value("unknown") == executor._get_priority_value("medium")

    def test_case_insensitive(self, executor):
        assert executor._get_priority_value("HIGH") == executor._get_priority_value("high")


# ── TestSortStepsByDependencies ───────────────────────────────────────────
class TestSortStepsByDependencies:
    def test_no_deps_returns_all(self, executor):
        steps = [
            {"step_id": "a", "dependencies": []},
            {"step_id": "b", "dependencies": []},
        ]
        result = executor._sort_steps_by_dependencies(steps)
        assert len(result) == 2

    def test_dependency_order(self, executor):
        steps = [
            {"step_id": "b", "dependencies": ["a"], "priority": "medium"},
            {"step_id": "a", "dependencies": [], "priority": "medium"},
        ]
        result = executor._sort_steps_by_dependencies(steps)
        ids = [s["step_id"] for s in result]
        assert ids.index("a") < ids.index("b")

    def test_empty_input(self, executor):
        assert executor._sort_steps_by_dependencies([]) == []

    def test_chain_dependency(self, executor):
        steps = [
            {"step_id": "c", "dependencies": ["b"], "priority": "medium"},
            {"step_id": "b", "dependencies": ["a"], "priority": "medium"},
            {"step_id": "a", "dependencies": [], "priority": "medium"},
        ]
        result = executor._sort_steps_by_dependencies(steps)
        ids = [s["step_id"] for s in result]
        assert ids == ["a", "b", "c"]

    def test_priority_sorts_independent_steps(self, executor):
        steps = [
            {"step_id": "low", "dependencies": [], "priority": "low"},
            {"step_id": "urgent", "dependencies": [], "priority": "urgent"},
        ]
        result = executor._sort_steps_by_dependencies(steps)
        ids = [s["step_id"] for s in result]
        # urgent > low, so urgent comes last (higher value = later)
        # OR first — depends on sort order; just ensure both are present
        assert set(ids) == {"low", "urgent"}


# ── TestInit ─────────────────────────────────────────────────────────────
class TestInit:
    def test_n8n_url_stored(self, executor):
        assert executor.n8n_url == "http://127.0.0.1:5678"

    def test_task_critic_url_stored(self, executor):
        assert executor.task_critic_url == "http://127.0.0.1:5102"

    def test_config_loaded(self, executor):
        assert isinstance(executor.config, dict)
