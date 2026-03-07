"""
Unit tests for scripts/misc/task_planner.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

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
_paths.INTENT_ROUTER_PORT = 8090
_paths.OLLAMA_PORT = 11434
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.task_planner import (
    ExecutionPlan,
    TaskPlanner,
    TaskPriority,
    TaskStatus,
    TaskStep,
)


@pytest.fixture
def tp(tmp_path):
    cfg = tmp_path / "task_planner_config.json"
    return TaskPlanner(config_path=cfg, model="test-model")


# ── TestTaskStatus ────────────────────────────────────────────────────────
class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_is_str_subclass(self):
        assert isinstance(TaskStatus.PENDING, str)


# ── TestTaskPriority ──────────────────────────────────────────────────────
class TestTaskPriority:
    def test_values(self):
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.URGENT.value == "urgent"


# ── TestTaskStep ──────────────────────────────────────────────────────────
class TestTaskStep:
    def test_default_status_pending(self):
        step = TaskStep(
            step_id="s1",
            description="test step",
            action="call_api",
            target="api",
            parameters={},
            dependencies=[],
            estimated_duration=30,
            priority=TaskPriority.MEDIUM,
        )
        assert step.status == TaskStatus.PENDING
        assert step.result is None
        assert step.error is None

    def test_explicit_fields(self):
        step = TaskStep(
            step_id="s2",
            description="desc",
            action="run_script",
            target="/path/to/script",
            parameters={"arg": 1},
            dependencies=["s1"],
            estimated_duration=60,
            priority=TaskPriority.HIGH,
            status=TaskStatus.COMPLETED,
        )
        assert step.priority == TaskPriority.HIGH
        assert step.status == TaskStatus.COMPLETED
        assert step.parameters == {"arg": 1}
        assert step.dependencies == ["s1"]


# ── TestExecutionPlan ─────────────────────────────────────────────────────
class TestExecutionPlan:
    def test_default_status_pending(self):
        plan = ExecutionPlan(
            plan_id="plan1",
            intent_type="image_generation",
            original_input="画像を作って",
            steps=[],
            total_estimated_duration=0,
            priority=TaskPriority.MEDIUM,
            created_at="2026-01-01",
        )
        assert plan.status == TaskStatus.PENDING
        assert plan.completed_at is None

    def test_fields_stored(self):
        plan = ExecutionPlan(
            plan_id="p2",
            intent_type="code_generation",
            original_input="コードを書いて",
            steps=[],
            total_estimated_duration=120,
            priority=TaskPriority.HIGH,
            created_at="2026-03-01",
        )
        assert plan.plan_id == "p2"
        assert plan.total_estimated_duration == 120


# ── TestTaskPlannerInit ───────────────────────────────────────────────────
class TestTaskPlannerInit:
    def test_model_set(self, tp):
        assert tp.model == "test-model"

    def test_config_has_default_keys(self, tp):
        assert "model" in tp.config
        assert "max_steps" in tp.config
        assert "default_priority" in tp.config

    def test_action_templates_present(self, tp):
        assert isinstance(tp.action_templates, dict)
        assert len(tp.action_templates) > 0

    def test_planning_prompt_template_string(self, tp):
        assert isinstance(tp.planning_prompt_template, str)
        assert len(tp.planning_prompt_template) > 0


# ── TestGetDefaultConfig ──────────────────────────────────────────────────
class TestGetDefaultConfig:
    def test_returns_dict(self, tp):
        cfg = tp._get_default_config()
        assert isinstance(cfg, dict)

    def test_model_in_config(self, tp):
        cfg = tp._get_default_config()
        assert cfg["model"] == "qwen2.5:14b"

    def test_max_steps_is_10(self, tp):
        cfg = tp._get_default_config()
        assert cfg["max_steps"] == 10


# ── TestGetDefaultActionTemplates ────────────────────────────────────────
class TestGetDefaultActionTemplates:
    def test_contains_image_generation(self, tp):
        templates = tp._get_default_action_templates()
        assert "image_generation" in templates

    def test_contains_code_generation(self, tp):
        templates = tp._get_default_action_templates()
        assert "code_generation" in templates

    def test_template_has_action_key(self, tp):
        templates = tp._get_default_action_templates()
        for name, tmpl in templates.items():
            assert "action" in tmpl, f"{name} missing 'action'"


# ── TestGetDefaultPlanningPromptTemplate ─────────────────────────────────
class TestGetDefaultPlanningPromptTemplate:
    def test_returns_nonempty_string(self, tp):
        tpl = tp._get_default_planning_prompt_template()
        assert isinstance(tpl, str)
        assert len(tpl) > 50

    def test_contains_placeholder(self, tp):
        tpl = tp._get_default_planning_prompt_template()
        assert "{intent_type}" in tpl or "intent_type" in tpl


# ── TestLoadConfig ────────────────────────────────────────────────────────
class TestLoadConfig:
    def test_missing_config_uses_defaults(self, tmp_path):
        tp2 = TaskPlanner(config_path=tmp_path / "missing.json")
        assert tp2.config.get("max_steps") == 10

    def test_existing_config_loaded(self, tmp_path):
        cfg = tmp_path / "custom.json"
        cfg.write_text(
            json.dumps({"model": "custom-model", "max_steps": 5}),
            encoding="utf-8",
        )
        tp3 = TaskPlanner(config_path=cfg)
        # config dict には読み込んだ値が入る
        assert tp3.config.get("max_steps") == 5
