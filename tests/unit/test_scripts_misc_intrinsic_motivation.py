"""
Unit tests for scripts/misc/intrinsic_motivation.py
"""
import sys
import json
from datetime import datetime, timedelta
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

_paths = MagicMock()
_paths.LEARNING_SYSTEM_PORT = 8080
_paths.METRICS_COLLECTOR_PORT = 8081
_paths.ORCHESTRATOR_PORT = 8100
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.intrinsic_motivation import (
    IntrinsicMotivation,
    IntrinsicTask,
    TaskCategory,
)


@pytest.fixture
def im(tmp_path):
    cfg = tmp_path / "im_config.json"
    metrics = tmp_path / "im_metrics.json"
    inst = IntrinsicMotivation(config_path=cfg)
    inst.metrics_storage_path = metrics
    return inst


def _task(
    task_id: str = "t1",
    category: TaskCategory = TaskCategory.MEMORY_ORGANIZATION,
    priority: int = 5,
    duration: int = 60,
) -> IntrinsicTask:
    return IntrinsicTask(
        task_id=task_id,
        title="テストタスク",
        description="説明",
        category=category,
        priority=priority,
        estimated_duration_minutes=duration,
        long_term_goal_alignment="テスト",
    )


# ── TestTaskCategory ───────────────────────────────────────────────────────
class TestTaskCategory:
    def test_values(self):
        assert TaskCategory.MEMORY_ORGANIZATION.value == "memory_organization"
        assert TaskCategory.KNOWLEDGE_ACQUISITION.value == "knowledge_acquisition"
        assert TaskCategory.PERFORMANCE_IMPROVEMENT.value == "performance_improvement"
        assert TaskCategory.PATTERN_ANALYSIS.value == "pattern_analysis"
        assert TaskCategory.DOCUMENTATION.value == "documentation"

    def test_is_str_subclass(self):
        assert isinstance(TaskCategory.MEMORY_ORGANIZATION, str)


# ── TestIntrinsicTask ──────────────────────────────────────────────────────
class TestIntrinsicTask:
    def test_created_at_auto_set(self):
        t = _task()
        assert t.created_at  # 空でない

    def test_safety_check_default_false(self):
        t = _task()
        assert t.safety_check_passed is False

    def test_explicit_created_at(self):
        t = IntrinsicTask(
            task_id="x",
            title="T",
            description="D",
            category=TaskCategory.DOCUMENTATION,
            priority=3,
            estimated_duration_minutes=30,
            long_term_goal_alignment="G",
            created_at="2026-01-01T00:00:00",
        )
        assert t.created_at == "2026-01-01T00:00:00"


# ── TestClassVars ─────────────────────────────────────────────────────────
class TestClassVars:
    def test_long_term_goal_is_string(self):
        assert isinstance(IntrinsicMotivation.LONG_TERM_GOAL, str)
        assert len(IntrinsicMotivation.LONG_TERM_GOAL) > 0

    def test_safety_charter_has_5_items(self):
        assert len(IntrinsicMotivation.SAFETY_CHARTER) == 5

    def test_safety_charter_all_strings(self):
        for item in IntrinsicMotivation.SAFETY_CHARTER:
            assert isinstance(item, str)


# ── TestIsIdle ────────────────────────────────────────────────────────────
class TestIsIdle:
    def test_idle_when_no_external_task(self, im):
        im.last_external_task_time = None
        assert im.is_idle() is True

    def test_idle_after_threshold(self, im):
        im.idle_threshold_minutes = 5
        im.last_external_task_time = datetime.now() - timedelta(minutes=10)
        assert im.is_idle() is True

    def test_not_idle_within_threshold(self, im):
        im.idle_threshold_minutes = 30
        im.last_external_task_time = datetime.now() - timedelta(minutes=5)
        assert im.is_idle() is False


# ── TestRecordExternalTask ────────────────────────────────────────────────
class TestRecordExternalTask:
    def test_updates_last_time(self, im):
        before = datetime.now()
        im.record_external_task()
        assert im.last_external_task_time is not None
        assert im.last_external_task_time >= before

    def test_not_idle_after_record(self, im):
        im.idle_threshold_minutes = 30
        im.record_external_task()
        assert im.is_idle() is False


# ── TestPassesQualityFilter ───────────────────────────────────────────────
class TestPassesQualityFilter:
    def test_empty_config_passes_all(self, im):
        t = _task(category=TaskCategory.DOCUMENTATION, duration=60)
        assert im._passes_quality_filter(t, {}) is True

    def test_banned_category_fails(self, im):
        t = _task(category=TaskCategory.DOCUMENTATION, duration=60)
        cfg = {"banned_categories": ["documentation"]}
        assert im._passes_quality_filter(t, cfg) is False

    def test_non_banned_category_passes(self, im):
        t = _task(category=TaskCategory.MEMORY_ORGANIZATION, duration=60)
        cfg = {"banned_categories": ["documentation"]}
        assert im._passes_quality_filter(t, cfg) is True

    def test_min_granularity_high_allows_short(self, im):
        # high = duration < 30 min → 「high」粒度
        t = _task(duration=20)
        cfg = {"min_granularity": "high"}
        assert im._passes_quality_filter(t, cfg) is True

    def test_min_granularity_high_rejects_long(self, im):
        # low = duration > 120 min → 「low」粒度 < 「high」 = fail
        t = _task(duration=200)
        cfg = {"min_granularity": "high"}
        assert im._passes_quality_filter(t, cfg) is False

    def test_min_granularity_medium_allows_medium(self, im):
        t = _task(duration=60)  # medium
        cfg = {"min_granularity": "medium"}
        assert im._passes_quality_filter(t, cfg) is True
