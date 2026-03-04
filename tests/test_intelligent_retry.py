#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_intelligent_retry.py
IntelligentRetry / CircuitBreaker の単体テスト
"""

import sys
import asyncio
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# sys.path に scripts/misc を追加
MISC_DIR = Path(__file__).parent.parent / "scripts" / "misc"
sys.path.insert(0, str(MISC_DIR))

# 依存モジュールをモック化してインポート
mock_logger = MagicMock()
mock_error_handler_instance = MagicMock()
mock_timeout_config = MagicMock()

with patch.dict("sys.modules", {
    "manaos_logger": MagicMock(
        get_logger=MagicMock(return_value=mock_logger),
        get_service_logger=MagicMock(return_value=mock_logger),
    ),
    "manaos_error_handler": MagicMock(
        ManaOSErrorHandler=MagicMock(return_value=mock_error_handler_instance),
        ErrorCategory=MagicMock(),
        ErrorSeverity=MagicMock(),
    ),
    "manaos_timeout_config": MagicMock(
        get_timeout_config=MagicMock(return_value=mock_timeout_config),
    ),
    "httpx": MagicMock(),
}):
    import intelligent_retry


RetryStrategy = intelligent_retry.RetryStrategy
CircuitState = intelligent_retry.CircuitState
RetryConfig = intelligent_retry.RetryConfig
CircuitBreakerConfig = intelligent_retry.CircuitBreakerConfig
RetryResult = intelligent_retry.RetryResult
CircuitBreaker = intelligent_retry.CircuitBreaker
IntelligentRetry = intelligent_retry.IntelligentRetry


# ============================================================
# RetryConfig
# ============================================================

class TestRetryConfig(unittest.TestCase):

    def test_defaults(self):
        cfg = RetryConfig()
        self.assertEqual(cfg.max_retries, 2)
        self.assertAlmostEqual(cfg.initial_delay, 0.5)
        self.assertAlmostEqual(cfg.max_delay, 10.0)
        self.assertAlmostEqual(cfg.exponential_base, 2.0)
        self.assertEqual(cfg.strategy, RetryStrategy.EXPONENTIAL_BACKOFF)

    def test_retryable_errors_defaults(self):
        cfg = RetryConfig()
        self.assertIsNotNone(cfg.retryable_errors)
        self.assertIn("timeout", cfg.retryable_errors)
        self.assertIn("connection_error", cfg.retryable_errors)

    def test_custom_values(self):
        cfg = RetryConfig(max_retries=5, initial_delay=1.0, max_delay=30.0)
        self.assertEqual(cfg.max_retries, 5)
        self.assertAlmostEqual(cfg.initial_delay, 1.0)
        self.assertAlmostEqual(cfg.max_delay, 30.0)

    def test_none_retryable_errors_gets_defaults(self):
        cfg = RetryConfig(retryable_errors=None)
        self.assertIsNotNone(cfg.retryable_errors)
        self.assertIsInstance(cfg.retryable_errors, list)


# ============================================================
# CircuitBreakerConfig
# ============================================================

class TestCircuitBreakerConfig(unittest.TestCase):

    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        self.assertEqual(cfg.failure_threshold, 5)
        self.assertEqual(cfg.success_threshold, 2)
        self.assertAlmostEqual(cfg.timeout_seconds, 60.0)
        self.assertEqual(cfg.half_open_max_calls, 3)

    def test_custom_values(self):
        cfg = CircuitBreakerConfig(failure_threshold=3, success_threshold=1, timeout_seconds=10.0)
        self.assertEqual(cfg.failure_threshold, 3)
        self.assertEqual(cfg.success_threshold, 1)


# ============================================================
# RetryResult
# ============================================================

class TestRetryResult(unittest.TestCase):

    def test_success_result(self):
        r = RetryResult(success=True, result=42, attempts=1, total_duration=0.5, errors=[])
        self.assertTrue(r.success)
        self.assertEqual(r.result, 42)

    def test_failure_result(self):
        r = RetryResult(success=False, result=None, attempts=3, total_duration=2.0, errors=["err1", "err2"])
        self.assertFalse(r.success)
        self.assertEqual(len(r.errors), 2)


# ============================================================
# CircuitBreaker — 初期状態
# ============================================================

class TestCircuitBreakerInitial(unittest.TestCase):

    def setUp(self):
        self.cfg = CircuitBreakerConfig(failure_threshold=3, success_threshold=2, timeout_seconds=5.0)
        self.cb = CircuitBreaker(self.cfg)

    def test_initial_state_closed(self):
        self.assertEqual(self.cb.state, CircuitState.CLOSED)

    def test_can_execute_when_closed(self):
        self.assertTrue(self.cb.can_execute())

    def test_initial_counts_zero(self):
        self.assertEqual(self.cb.failure_count, 0)
        self.assertEqual(self.cb.success_count, 0)


# ============================================================
# CircuitBreaker — CLOSED → OPEN
# ============================================================

class TestCircuitBreakerCLOSEDtoOPEN(unittest.TestCase):

    def setUp(self):
        self.cfg = CircuitBreakerConfig(failure_threshold=3, success_threshold=2, timeout_seconds=5.0)
        self.cb = CircuitBreaker(self.cfg)

    def test_success_in_closed_resets_failure_count(self):
        self.cb.failure_count = 2
        self.cb.record_success()
        self.assertEqual(self.cb.failure_count, 0)

    def test_failure_increments_count(self):
        self.cb.record_failure()
        self.assertEqual(self.cb.failure_count, 1)
        self.assertEqual(self.cb.state, CircuitState.CLOSED)

    def test_reaches_threshold_opens_circuit(self):
        for _ in range(3):
            self.cb.record_failure()
        self.assertEqual(self.cb.state, CircuitState.OPEN)

    def test_cannot_execute_when_open(self):
        for _ in range(3):
            self.cb.record_failure()
        self.assertFalse(self.cb.can_execute())

    def test_last_failure_time_set_on_failure(self):
        before = datetime.now()
        self.cb.record_failure()
        self.assertIsNotNone(self.cb.last_failure_time)
        self.assertGreaterEqual(self.cb.last_failure_time, before)


# ============================================================
# CircuitBreaker — OPEN → HALF_OPEN（タイムアウト後）
# ============================================================

class TestCircuitBreakerOPENtoHALFOPEN(unittest.TestCase):

    def setUp(self):
        self.cfg = CircuitBreakerConfig(failure_threshold=1, success_threshold=2, timeout_seconds=5.0)
        self.cb = CircuitBreaker(self.cfg)
        self.cb.record_failure()  # → OPEN
        self.assertEqual(self.cb.state, CircuitState.OPEN)

    def test_cannot_execute_before_timeout(self):
        self.assertFalse(self.cb.can_execute())

    def test_transitions_to_half_open_after_timeout(self):
        # last_failure_time を十分前に設定
        self.cb.last_failure_time = datetime.now() - timedelta(seconds=10)
        result = self.cb.can_execute()
        self.assertTrue(result)
        self.assertEqual(self.cb.state, CircuitState.HALF_OPEN)

    def test_half_open_calls_reset_on_transition(self):
        self.cb.last_failure_time = datetime.now() - timedelta(seconds=10)
        self.cb.can_execute()
        self.assertEqual(self.cb.half_open_calls, 0)


# ============================================================
# CircuitBreaker — HALF_OPEN → CLOSED（成功）
# ============================================================

class TestCircuitBreakerHALFOPENtoCLOSED(unittest.TestCase):

    def setUp(self):
        self.cfg = CircuitBreakerConfig(failure_threshold=1, success_threshold=2, timeout_seconds=0.01)
        self.cb = CircuitBreaker(self.cfg)
        # OPEN に遷移させた後タイムアウトして HALF_OPEN に
        self.cb.record_failure()
        self.cb.last_failure_time = datetime.now() - timedelta(seconds=1)
        self.cb.can_execute()  # → HALF_OPEN
        self.assertEqual(self.cb.state, CircuitState.HALF_OPEN)

    def test_success_in_half_open_counts(self):
        self.cb.record_success()
        self.assertEqual(self.cb.success_count, 1)

    def test_enough_successes_closes_circuit(self):
        self.cb.record_success()
        self.cb.record_success()
        self.assertEqual(self.cb.state, CircuitState.CLOSED)

    def test_closed_resets_failure_count(self):
        self.cb.record_success()
        self.cb.record_success()
        self.assertEqual(self.cb.failure_count, 0)


# ============================================================
# CircuitBreaker — HALF_OPEN → OPEN（失敗）
# ============================================================

class TestCircuitBreakerHALFOPENtoOPEN(unittest.TestCase):

    def setUp(self):
        self.cfg = CircuitBreakerConfig(failure_threshold=1, success_threshold=2, timeout_seconds=0.01)
        self.cb = CircuitBreaker(self.cfg)
        self.cb.record_failure()  # → OPEN
        self.cb.last_failure_time = datetime.now() - timedelta(seconds=1)
        self.cb.can_execute()  # → HALF_OPEN

    def test_failure_in_half_open_reopens(self):
        self.cb.record_failure()
        self.assertEqual(self.cb.state, CircuitState.OPEN)

    def test_half_open_max_calls_limits_execution(self):
        self.cfg.half_open_max_calls = 2
        # まず 2 回実行可能にする
        self.assertTrue(self.cb.can_execute())
        self.cb.half_open_calls = 2  # 手動で max に到達させる
        self.assertFalse(self.cb.can_execute())


# ============================================================
# IntelligentRetry — _calculate_delay
# ============================================================

class TestCalculateDelay(unittest.TestCase):

    def test_exponential_backoff_increases(self):
        retry = IntelligentRetry()
        d0 = retry._calculate_delay(0)
        d1 = retry._calculate_delay(1)
        d2 = retry._calculate_delay(2)
        self.assertLess(d0, d1)
        self.assertLess(d1, d2)

    def test_exponential_backoff_capped_at_max_delay(self):
        retry = IntelligentRetry()
        # attempt 100 は max_delay を超えるはず
        delay = retry._calculate_delay(100)
        self.assertLessEqual(delay, retry.retry_config.max_delay)

    def test_linear_backoff(self):
        cfg = RetryConfig(strategy=RetryStrategy.LINEAR_BACKOFF, initial_delay=1.0)
        retry = IntelligentRetry(retry_config=cfg)
        d0 = retry._calculate_delay(0)  # 1.0 * 1
        d1 = retry._calculate_delay(1)  # 1.0 * 2
        self.assertAlmostEqual(d0, 1.0)
        self.assertAlmostEqual(d1, 2.0)

    def test_fixed_interval_is_constant(self):
        cfg = RetryConfig(strategy=RetryStrategy.FIXED_INTERVAL, initial_delay=0.5)
        retry = IntelligentRetry(retry_config=cfg)
        for i in range(5):
            self.assertAlmostEqual(retry._calculate_delay(i), 0.5)

    def test_custom_strategy_returns_initial_delay(self):
        cfg = RetryConfig(strategy=RetryStrategy.CUSTOM, initial_delay=0.3)
        retry = IntelligentRetry(retry_config=cfg)
        self.assertAlmostEqual(retry._calculate_delay(5), 0.3)


# ============================================================
# IntelligentRetry — _is_retryable_error
# ============================================================

class TestIsRetryableError(unittest.TestCase):

    def setUp(self):
        self.retry = IntelligentRetry()

    def test_timeout_error_is_retryable(self):
        e = TimeoutError("timeout occurred")
        self.assertTrue(self.retry._is_retryable_error(e))

    def test_connection_error_is_retryable(self):
        e = ConnectionError("connection_error")
        self.assertTrue(self.retry._is_retryable_error(e))

    def test_rate_limit_in_message_is_retryable(self):
        e = Exception("rate_limit exceeded")
        self.assertTrue(self.retry._is_retryable_error(e))

    def test_non_retryable_error(self):
        e = ValueError("validation error, not retryable")
        self.assertFalse(self.retry._is_retryable_error(e))

    def test_server_error_is_retryable(self):
        e = Exception("server_error happened")
        self.assertTrue(self.retry._is_retryable_error(e))


# ============================================================
# IntelligentRetry — get_circuit_breaker
# ============================================================

class TestGetCircuitBreaker(unittest.TestCase):

    def setUp(self):
        self.retry = IntelligentRetry()

    def test_creates_new_breaker(self):
        cb = self.retry.get_circuit_breaker("service_a")
        self.assertIsNotNone(cb)
        self.assertIsInstance(cb, CircuitBreaker)

    def test_same_key_returns_same_instance(self):
        cb1 = self.retry.get_circuit_breaker("svc")
        cb2 = self.retry.get_circuit_breaker("svc")
        self.assertIs(cb1, cb2)

    def test_different_keys_different_instances(self):
        cb1 = self.retry.get_circuit_breaker("svc_a")
        cb2 = self.retry.get_circuit_breaker("svc_b")
        self.assertIsNot(cb1, cb2)


# ============================================================
# IntelligentRetry — execute_with_retry（同期関数）
# ============================================================

class TestExecuteWithRetry(unittest.IsolatedAsyncioTestCase):

    async def test_sync_function_success(self):
        retry = IntelligentRetry()
        result = await retry.execute_with_retry(lambda: 42)
        self.assertTrue(result.success)
        self.assertEqual(result.result, 42)
        self.assertEqual(result.attempts, 1)

    async def test_async_function_success(self):
        async def async_fn():
            return "hello"
        retry = IntelligentRetry()
        result = await retry.execute_with_retry(async_fn)
        self.assertTrue(result.success)
        self.assertEqual(result.result, "hello")

    async def test_open_circuit_breaker_blocks_execution(self):
        retry = IntelligentRetry()
        cb = retry.get_circuit_breaker("blocked")
        # failure_threshold 回失敗させて OPEN に
        for _ in range(retry.circuit_breaker_config.failure_threshold):
            cb.record_failure()
        result = await retry.execute_with_retry(lambda: 1, circuit_breaker_key="blocked")
        self.assertFalse(result.success)
        self.assertEqual(result.attempts, 0)

    async def test_non_retryable_error_fails_immediately(self):
        """リトライ不可能なエラーは最大回数を待たず失敗"""
        call_count = 0

        def failing():
            nonlocal call_count
            call_count += 1
            raise ValueError("validation error")

        cfg = RetryConfig(max_retries=2)
        retry = IntelligentRetry(retry_config=cfg)
        result = await retry.execute_with_retry(failing)
        self.assertFalse(result.success)
        # retryable ではないので 1 回で終了
        self.assertEqual(call_count, 1)


if __name__ == "__main__":
    unittest.main()
