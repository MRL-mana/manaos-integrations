"""
Unit tests for scripts/misc/task_queue_system.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from queue import PriorityQueue
from unittest.mock import MagicMock

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
_tc_mod.get_timeout_config = MagicMock(return_value={"api_call": 10.0})
sys.modules.setdefault("manaos_timeout_config", _tc_mod)

_cv_mod = MagicMock()
_cv_mod.ConfigValidator = MagicMock(return_value=MagicMock(
    validate_config=MagicMock(return_value=(True, []))
))
sys.modules.setdefault("manaos_config_validator", _cv_mod)

_flask = MagicMock()
_flask.Flask.return_value = MagicMock()
_flask.jsonify = MagicMock(side_effect=lambda x: x)
_flask.request = MagicMock()
sys.modules.setdefault("flask", _flask)

_flask_cors = MagicMock()
sys.modules.setdefault("flask_cors", _flask_cors)

import pytest  # noqa: E402
from scripts.misc.task_queue_system import (  # noqa: E402
    Task,
    TaskPriority,
    TaskStatus,
    RateLimitRule,
    TaskQueueSystem,
)


# ── helpers ────────────────────────────────────────────────────────────────
_MINIMAL_CONFIG = {
    "worker_count": 2,
    "max_queue_size": 100,
    "default_priority": "medium",
    "default_max_retries": 3,
    "rate_limit_rules": {},
}


def make_queue_sys(tmp_path: Path) -> TaskQueueSystem:
    """ファイルI/O・スレッドをバイパスした TaskQueueSystem"""
    tqs = TaskQueueSystem.__new__(TaskQueueSystem)
    tqs.use_redis = False
    tqs.config = _MINIMAL_CONFIG.copy()
    tqs.db_path = tmp_path / "test.db"
    tqs._init_database()
    tqs.priority_queue = PriorityQueue()
    tqs.rate_limit_rules = {}
    tqs.workers = []
    tqs.running = False
    tqs.worker_count = 2
    tqs.task_handlers = {}
    return tqs


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def tqs(tmp_path):
    return make_queue_sys(tmp_path)


def make_task(**kwargs) -> Task:
    defaults = dict(
        task_id="t1",
        task_type="test",
        payload={"key": "val"},
        priority=TaskPriority.MEDIUM,
    )
    defaults.update(kwargs)
    return Task(**defaults)  # type: ignore[arg-type]


# ── TestTaskPriority ───────────────────────────────────────────────────────
class TestTaskPriority:
    def test_low_value(self):
        assert TaskPriority.LOW.value == 1

    def test_urgent_highest(self):
        assert TaskPriority.URGENT.value > TaskPriority.HIGH.value

    def test_ordering(self):
        assert TaskPriority.LOW < TaskPriority.MEDIUM < TaskPriority.HIGH < TaskPriority.URGENT


# ── TestTaskStatus ─────────────────────────────────────────────────────────
class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"


# ── TestTask ───────────────────────────────────────────────────────────────
class TestTask:
    def test_created_at_auto_set(self):
        t = make_task()
        assert t.created_at != ""

    def test_metadata_defaults_to_empty_dict(self):
        t = make_task()
        assert t.metadata == {}

    def test_default_status_pending(self):
        t = make_task()
        assert t.status == TaskStatus.PENDING

    def test_lt_priority_order(self):
        low = make_task(task_id="a", priority=TaskPriority.LOW)
        high = make_task(task_id="b", priority=TaskPriority.HIGH)
        # lower priority value means __lt__ is True (HIGH > LOW, so LOW < HIGH as int)
        assert low < high


# ── TestRateLimitRule ──────────────────────────────────────────────────────
class TestRateLimitRule:
    def test_window_start_auto_set(self):
        rule = RateLimitRule("api_call", max_requests=10, window_seconds=60)
        assert rule.window_start != ""

    def test_fields(self):
        rule = RateLimitRule("api_call", max_requests=10, window_seconds=60)
        assert rule.max_requests == 10
        assert rule.window_seconds == 60
        assert rule.current_requests == 0


# ── TestGetDefaultConfig ───────────────────────────────────────────────────
class TestGetDefaultConfig:
    def test_has_required_keys(self, tqs):
        cfg = tqs._get_default_config()
        for key in ("worker_count", "max_queue_size", "default_priority",
                    "default_max_retries", "rate_limit_rules"):
            assert key in cfg

    def test_rate_limit_rules_is_dict(self, tqs):
        cfg = tqs._get_default_config()
        assert isinstance(cfg["rate_limit_rules"], dict)


# ── TestCheckRateLimit ─────────────────────────────────────────────────────
class TestCheckRateLimit:
    def test_no_rule_returns_true(self, tqs):
        assert tqs._check_rate_limit("unknown_type") is True

    def test_within_limit_returns_true(self, tqs):
        tqs.rate_limit_rules["mytype"] = RateLimitRule("mytype", max_requests=10, window_seconds=60)
        assert tqs._check_rate_limit("mytype") is True

    def test_increments_counter(self, tqs):
        tqs.rate_limit_rules["mytype"] = RateLimitRule("mytype", max_requests=10, window_seconds=60)
        tqs._check_rate_limit("mytype")
        assert tqs.rate_limit_rules["mytype"].current_requests == 1

    def test_at_limit_returns_false(self, tqs):
        tqs.rate_limit_rules["mytype"] = RateLimitRule("mytype", max_requests=2, window_seconds=60)
        tqs._check_rate_limit("mytype")
        tqs._check_rate_limit("mytype")
        assert tqs._check_rate_limit("mytype") is False

    def test_expired_window_resets(self, tqs):
        rule = RateLimitRule("mytype", max_requests=2, window_seconds=1)
        rule.current_requests = 2
        # Set window_start to 2 seconds ago to simulate expiry
        old_time = (datetime.now() - timedelta(seconds=2)).isoformat()
        rule.window_start = old_time
        tqs.rate_limit_rules["mytype"] = rule
        # After expiry, counter should reset
        assert tqs._check_rate_limit("mytype") is True
        assert rule.current_requests == 1


# ── TestRegisterHandler ────────────────────────────────────────────────────
class TestRegisterHandler:
    def test_handler_registered(self, tqs):
        def handler(p):
            return {"done": True}
        tqs.register_handler("my_task", handler)
        assert "my_task" in tqs.task_handlers

    def test_correct_handler_stored(self, tqs):
        def handler(p):
            return {"result": "ok"}
        tqs.register_handler("my_task", handler)
        assert tqs.task_handlers["my_task"] is handler


# ── TestEnqueue ────────────────────────────────────────────────────────────
class TestEnqueue:
    def test_returns_task(self, tqs):
        task = tqs.enqueue("api_call", {"url": "http://example.com"})
        assert isinstance(task, Task)

    def test_task_in_queue(self, tqs):
        tqs.enqueue("api_call", {"url": "http://a.com"})
        assert tqs.priority_queue.qsize() == 1

    def test_task_saved_to_db(self, tqs):
        task = tqs.enqueue("api_call", {"data": 1})
        fetched = tqs.get_task(task.task_id)
        assert fetched is not None
        assert fetched.task_id == task.task_id

    def test_custom_priority_used(self, tqs):
        task = tqs.enqueue("api_call", {}, priority=TaskPriority.URGENT)
        assert task.priority == TaskPriority.URGENT

    def test_default_priority_medium(self, tqs):
        task = tqs.enqueue("api_call", {})
        assert task.priority == TaskPriority.MEDIUM

    def test_rate_limited_raises(self, tqs):
        tqs.rate_limit_rules["api_call"] = RateLimitRule(
            "api_call", max_requests=1, window_seconds=60
        )
        tqs.enqueue("api_call", {})  # OK
        with pytest.raises(Exception, match="レート制限"):
            tqs.enqueue("api_call", {})
            tqs.enqueue("api_call", {})  # Second at-limit call


# ── TestGetTask ────────────────────────────────────────────────────────────
class TestGetTask:
    def test_existing_task(self, tqs):
        task = tqs.enqueue("api_call", {"x": 1})
        result = tqs.get_task(task.task_id)
        assert result is not None
        assert result.task_id == task.task_id

    def test_nonexistent_returns_none(self, tqs):
        assert tqs.get_task("nonexistent_id") is None

    def test_payload_preserved(self, tqs):
        task = tqs.enqueue("api_call", {"key": "value"})
        fetched = tqs.get_task(task.task_id)
        assert fetched.payload == {"key": "value"}

    def test_priority_preserved(self, tqs):
        task = tqs.enqueue("api_call", {}, priority=TaskPriority.HIGH)
        fetched = tqs.get_task(task.task_id)
        assert fetched.priority == TaskPriority.HIGH


# ── TestGetQueueStatus ─────────────────────────────────────────────────────
class TestGetQueueStatus:
    def test_returns_dict(self, tqs):
        assert isinstance(tqs.get_queue_status(), dict)

    def test_required_keys(self, tqs):
        status = tqs.get_queue_status()
        for key in ("queue_size", "status_counts", "priority_counts",
                    "worker_count", "running"):
            assert key in status

    def test_queue_size_correct(self, tqs):
        tqs.enqueue("api_call", {})
        tqs.enqueue("api_call", {})
        status = tqs.get_queue_status()
        assert status["queue_size"] == 2

    def test_running_false_initially(self, tqs):
        assert tqs.get_queue_status()["running"] is False


# ── TestExecuteTask ────────────────────────────────────────────────────────
class TestExecuteTask:
    def test_success_marks_completed(self, tqs):
        tqs.register_handler("api_call", lambda p: {"result": "ok"})
        task = tqs.enqueue("api_call", {"x": 1})
        tqs._execute_task(task, worker_id=1)
        fetched = tqs.get_task(task.task_id)
        assert fetched.status == TaskStatus.COMPLETED

    def test_no_handler_retries(self, tqs):
        task = tqs.enqueue("unknown_type", {})
        tqs._execute_task(task, worker_id=1)
        # Should requeue since retry_count < max_retries
        assert tqs.priority_queue.qsize() >= 1

    def test_failure_increments_retry_count(self, tqs):
        tqs.register_handler("fail_task", lambda p: (_ for _ in ()).throw(ValueError("fail")))
        task = tqs.enqueue("fail_task", {})
        tqs._execute_task(task, worker_id=1)
        assert task.retry_count == 1

    def test_max_retries_marks_failed(self, tqs):
        tqs.register_handler("bad_task", lambda p: (_ for _ in ()).throw(ValueError("error")))
        task = tqs.enqueue("bad_task", {}, max_retries=0)
        task.max_retries = 0
        tqs._execute_task(task, worker_id=1)
        fetched = tqs.get_task(task.task_id)
        assert fetched.status == TaskStatus.FAILED
