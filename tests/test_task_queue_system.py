#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: task_queue_system.py
TaskPriority / TaskStatus / Task / RateLimitRule / TaskQueueSystem の単体テスト
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from queue import PriorityQueue
from unittest.mock import MagicMock, patch

import pytest

# ---- 依存モジュールをモック化 -------------------------------------------
_mock_logger = MagicMock()
_mock_service_logger = MagicMock(return_value=_mock_logger)
_mock_eh_cls = MagicMock()
_mock_eh_inst = MagicMock()
_mock_eh_cls.return_value = _mock_eh_inst
_mock_eh_inst.handle_exception.return_value = MagicMock(message="err")

import sys
sys.modules.setdefault("manaos_logger", MagicMock(
    get_logger=MagicMock(return_value=_mock_logger),
    get_service_logger=_mock_service_logger,
))
sys.modules.setdefault("manaos_error_handler", MagicMock(
    ManaOSErrorHandler=_mock_eh_cls,
    ErrorCategory=MagicMock(),
    ErrorSeverity=MagicMock(),
))
_mock_timeout = MagicMock()
_mock_timeout.get_timeout_config.return_value = MagicMock()
sys.modules.setdefault("manaos_timeout_config", MagicMock(
    get_timeout_config=MagicMock(return_value=MagicMock()),
))
sys.modules.setdefault("manaos_config_validator", MagicMock(
    ConfigValidator=MagicMock(return_value=MagicMock(
        validate_config=MagicMock(return_value=(True, []))
    ))
))

from task_queue_system import (  # noqa: E402
    TaskPriority,
    TaskStatus,
    Task,
    RateLimitRule,
    TaskQueueSystem,
)


# =========================================================================
# TaskPriority Enum
# =========================================================================
class TestTaskPriority:

    def test_values(self):
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.MEDIUM.value == 5
        assert TaskPriority.HIGH.value == 10
        assert TaskPriority.URGENT.value == 20

    def test_ordering(self):
        assert TaskPriority.URGENT.value > TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value > TaskPriority.MEDIUM.value
        assert TaskPriority.MEDIUM.value > TaskPriority.LOW.value


# =========================================================================
# TaskStatus Enum
# =========================================================================
class TestTaskStatus:

    def test_string_values(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_queued(self):
        assert TaskStatus.QUEUED == "queued"


# =========================================================================
# Task dataclass
# =========================================================================
class TestTask:

    def test_basic_fields(self):
        t = Task(
            task_id="t001",
            task_type="api_call",
            payload={"key": "val"},
            priority=TaskPriority.HIGH,
        )
        assert t.task_id == "t001"
        assert t.task_type == "api_call"
        assert t.priority == TaskPriority.HIGH
        assert t.status == TaskStatus.PENDING

    def test_created_at_auto_set(self):
        t = Task(
            task_id="t002",
            task_type="test",
            payload={},
            priority=TaskPriority.LOW,
        )
        assert t.created_at != ""
        # ISO形式の日時文字列か確認
        dt = datetime.fromisoformat(t.created_at)
        assert isinstance(dt, datetime)

    def test_metadata_default_empty(self):
        t = Task(
            task_id="t003",
            task_type="test",
            payload={},
            priority=TaskPriority.MEDIUM,
        )
        assert t.metadata == {}

    def test_lt_by_priority(self):
        high = Task("h", "t", {}, TaskPriority.HIGH)
        low = Task("l", "t", {}, TaskPriority.LOW)
        # priority.value が小さい方が "小さい" (PriorityQueue は最小値を先に取り出す)
        assert low < high  # LOW.value(1) < HIGH.value(10)

    def test_max_retries_default(self):
        t = Task("t", "test", {}, TaskPriority.MEDIUM)
        assert t.max_retries == 3

    def test_retry_count_default(self):
        t = Task("t", "test", {}, TaskPriority.MEDIUM)
        assert t.retry_count == 0


# =========================================================================
# RateLimitRule dataclass
# =========================================================================
class TestRateLimitRule:

    def test_basic_fields(self):
        rule = RateLimitRule(
            task_type="api_call",
            max_requests=100,
            window_seconds=60,
        )
        assert rule.task_type == "api_call"
        assert rule.max_requests == 100
        assert rule.window_seconds == 60

    def test_window_start_auto_set(self):
        rule = RateLimitRule("test", 10, 30)
        assert rule.window_start != ""
        dt = datetime.fromisoformat(rule.window_start)
        assert isinstance(dt, datetime)

    def test_current_requests_default(self):
        rule = RateLimitRule("test", 10, 30)
        assert rule.current_requests == 0


# =========================================================================
# TaskQueueSystem init
# =========================================================================
class TestTaskQueueSystemInit:

    def test_init_creates_db(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        assert (tmp_path / "tq.db").exists()

    def test_init_worker_count_default(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        assert qs.worker_count == 3

    def test_init_not_running(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        assert qs.running is False

    def test_init_empty_handlers(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        assert qs.task_handlers == {}

    def test_init_rate_limit_rules_loaded(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        # デフォルト設定に api_call, image_generation, workflow_execution が入る
        assert "api_call" in qs.rate_limit_rules
        assert "image_generation" in qs.rate_limit_rules


# =========================================================================
# register_handler
# =========================================================================
class TestRegisterHandler:

    def test_register_handler(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        handler = lambda p: {"ok": True}
        qs.register_handler("my_task", handler)
        assert "my_task" in qs.task_handlers

    def test_registered_handler_callable(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("ping", lambda p: "pong")
        assert qs.task_handlers["ping"]({"x": 1}) == "pong"


# =========================================================================
# enqueue
# =========================================================================
class TestEnqueue:

    def test_enqueue_returns_task(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("api_call", lambda p: {})
        task = qs.enqueue("api_call", {"url": "http://test"})
        assert isinstance(task, Task)

    def test_enqueue_task_in_db(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("api_call", lambda p: {})
        task = qs.enqueue("api_call", {"data": "x"})
        fetched = qs.get_task(task.task_id)
        assert fetched is not None
        assert fetched.task_id == task.task_id

    def test_enqueue_with_priority(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("workflow_execution", lambda p: {})
        task = qs.enqueue("workflow_execution", {}, priority=TaskPriority.URGENT)
        assert task.priority == TaskPriority.URGENT

    def test_enqueue_with_custom_max_retries(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("api_call", lambda p: {})
        task = qs.enqueue("api_call", {}, max_retries=5)
        assert task.max_retries == 5

    def test_enqueue_rate_limited_raises(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("api_call", lambda p: {})
        # レート制限ルールを最大1に設定
        from task_queue_system import RateLimitRule
        qs.rate_limit_rules["api_call"] = RateLimitRule("api_call", 1, 60)
        qs.enqueue("api_call", {"first": True})  # 1回目 OK
        with pytest.raises(Exception, match="レート制限"):
            qs.enqueue("api_call", {"second": True})  # 2回目 NG


# =========================================================================
# _check_rate_limit
# =========================================================================
class TestCheckRateLimit:

    def test_no_rule_always_allowed(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        assert qs._check_rate_limit("unknown_type") is True

    def test_within_limit_allowed(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.rate_limit_rules["test"] = RateLimitRule("test", 10, 60)
        for _ in range(10):
            result = qs._check_rate_limit("test")
        assert result is True  # 10回目もOK  # type: ignore[possibly-unbound]

    def test_exceeds_limit_blocked(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.rate_limit_rules["test"] = RateLimitRule("test", 2, 60)
        qs._check_rate_limit("test")
        qs._check_rate_limit("test")
        assert qs._check_rate_limit("test") is False  # 3回目でブロック

    def test_window_reset_allows_again(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        rule = RateLimitRule("test", 1, 1)
        # 窓を過去に設定(期限切れ)
        rule.window_start = (datetime.now() - timedelta(seconds=10)).isoformat()
        rule.current_requests = 99
        qs.rate_limit_rules["test"] = rule
        # リセットされるはず
        assert qs._check_rate_limit("test") is True


# =========================================================================
# get_task / get_queue_status
# =========================================================================
class TestGetTask:

    def test_get_task_existing(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("api_call", lambda p: {})
        task = qs.enqueue("api_call", {"k": "v"})
        result = qs.get_task(task.task_id)
        assert result is not None
        assert result.task_type == "api_call"

    def test_get_task_nonexistent_returns_none(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        assert qs.get_task("fake_id") is None

    def test_get_queue_status_structure(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("api_call", lambda p: {})
        qs.enqueue("api_call", {})
        status = qs.get_queue_status()
        assert isinstance(status, dict)


# =========================================================================
# start_workers / stop_workers
# =========================================================================
class TestWorkers:

    def test_start_workers_sets_running(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.start_workers()
        assert qs.running is True
        qs.stop_workers()

    def test_stop_workers_clears_running(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.start_workers()
        qs.stop_workers()
        assert qs.running is False

    def test_double_start_is_idempotent(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.start_workers()
        qs.start_workers()  # 2回目は無視される
        assert qs.running is True
        qs.stop_workers()

    def test_worker_count_threads_created(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.worker_count = 2
        qs.start_workers()
        assert len(qs.workers) == 2
        qs.stop_workers()


# =========================================================================
# _execute_task (単独実行)
# =========================================================================
class TestExecuteTask:

    def test_execute_task_calls_handler(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        called = []
        qs.register_handler("my_task", lambda p: called.append(p) or {"ok": True})
        task = qs.enqueue("my_task", {"ping": "pong"})
        qs._execute_task(task, worker_id=0)
        assert len(called) == 1
        assert called[0]["ping"] == "pong"

    def test_execute_task_sets_completed(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        qs.register_handler("my_task", lambda p: {"done": True})
        task = qs.enqueue("my_task", {})
        qs._execute_task(task, worker_id=0)
        assert task.status == TaskStatus.COMPLETED

    def test_execute_task_no_handler_retries(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        task = qs.enqueue("unknown_type", {})
        qs._execute_task(task, worker_id=0)
        # ハンドラーなし → リトライキューへ (retry_count増加)
        assert task.retry_count == 1

    def test_execute_task_exceeds_retries_sets_failed(self, tmp_path):
        qs = TaskQueueSystem(db_path=tmp_path / "tq.db")
        # enqueue の `max_retries or default` で 0 が上書きされるため、
        # retry_count を上限まで事前設定して FAILED 遷移を確認する
        task = qs.enqueue("unknown_type", {}, max_retries=1)
        task.retry_count = task.max_retries  # 上限に設定
        qs._execute_task(task, worker_id=0)
        assert task.status == TaskStatus.FAILED
