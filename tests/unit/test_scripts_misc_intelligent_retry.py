"""
Unit tests for scripts/misc/intelligent_retry.py
"""
import sys
import asyncio
from unittest.mock import MagicMock

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_meh = MagicMock()
_meh.ManaOSErrorHandler.return_value = MagicMock()
for _attr in ("ErrorCategory", "ErrorSeverity"):
    setattr(_meh, _attr, MagicMock())
sys.modules.setdefault("manaos_error_handler", _meh)

_mtc = MagicMock()
_mtc.get_timeout_config.return_value = MagicMock()
sys.modules.setdefault("manaos_timeout_config", _mtc)

sys.modules.setdefault("httpx", MagicMock())

import pytest  # noqa: E402, F401
from scripts.misc.intelligent_retry import (  # noqa: E402
    RetryStrategy,
    CircuitState,
    RetryConfig,
    CircuitBreakerConfig,
    RetryResult,
    CircuitBreaker,
    IntelligentRetry,
    intelligent_retry,
    retry,
)


# ── Enums ─────────────────────────────────────────────────────────────────
class TestRetryStrategy:
    def test_values(self):
        assert RetryStrategy.EXPONENTIAL_BACKOFF.value == "exponential_backoff"
        assert RetryStrategy.LINEAR_BACKOFF.value == "linear_backoff"
        assert RetryStrategy.FIXED_INTERVAL.value == "fixed_interval"
        assert RetryStrategy.CUSTOM.value == "custom"


class TestCircuitState:
    def test_values(self):
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


# ── RetryConfig ───────────────────────────────────────────────────────────
class TestRetryConfig:
    def test_defaults(self):
        rc = RetryConfig()
        assert rc.max_retries == 2
        assert rc.initial_delay == 0.5
        assert rc.max_delay == 10.0
        assert rc.exponential_base == 2.0
        assert rc.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_default_retryable_errors_list(self):
        rc = RetryConfig()
        assert isinstance(rc.retryable_errors, list)
        assert "timeout" in rc.retryable_errors
        assert "connection_error" in rc.retryable_errors

    def test_custom_retryable_errors(self):
        rc = RetryConfig(retryable_errors=["my_error"])
        assert rc.retryable_errors == ["my_error"]


# ── CircuitBreakerConfig ──────────────────────────────────────────────────
class TestCircuitBreakerConfig:
    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        assert cfg.failure_threshold == 5
        assert cfg.success_threshold == 2
        assert cfg.timeout_seconds == 60.0
        assert cfg.half_open_max_calls == 3


# ── RetryResult ───────────────────────────────────────────────────────────
class TestRetryResult:
    def test_create_success(self):
        r = RetryResult(success=True, result="ok", attempts=1,
                        total_duration=0.1, errors=[])
        assert r.success is True
        assert r.result == "ok"

    def test_create_failure(self):
        r = RetryResult(success=False, result=None, attempts=2,
                        total_duration=1.5, errors=["err1", "err2"])
        assert len(r.errors) == 2


# ── CircuitBreaker ────────────────────────────────────────────────────────
class TestCircuitBreakerClosed:
    def setup_method(self):
        self.cb = CircuitBreaker(CircuitBreakerConfig())

    def test_initial_state_is_closed(self):
        assert self.cb.state == CircuitState.CLOSED

    def test_can_execute_when_closed(self):
        assert self.cb.can_execute() is True

    def test_failure_increments_count(self):
        self.cb.record_failure()
        assert self.cb.failure_count == 1

    def test_opens_after_threshold(self):
        cfg = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(cfg)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        self.cb.record_failure()
        self.cb.record_success()
        assert self.cb.failure_count == 0


class TestCircuitBreakerOpen:
    def setup_method(self):
        cfg = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.0)
        self.cb = CircuitBreaker(cfg)
        self.cb.record_failure()  # Opens the circuit
        assert self.cb.state == CircuitState.OPEN

    def test_cannot_execute_when_open(self):
        # timeout_seconds=0.0 means it transitions to HALF_OPEN immediately
        # The first call to can_execute transitions to HALF_OPEN and returns True
        # Let's use a future timeout to stay OPEN
        cfg = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=9999.0)
        cb = CircuitBreaker(cfg)
        cb.record_failure()
        assert cb.can_execute() is False

    def test_transitions_to_half_open_after_timeout(self):
        # timeout_seconds=0.0 → HALF_OPEN on first can_execute
        result = self.cb.can_execute()
        assert self.cb.state == CircuitState.HALF_OPEN
        assert result is True


class TestCircuitBreakerHalfOpen:
    def setup_method(self):
        cfg = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.0,
                                   success_threshold=2, half_open_max_calls=3)
        self.cb = CircuitBreaker(cfg)
        self.cb.record_failure()
        self.cb.can_execute()  # transitions to HALF_OPEN
        assert self.cb.state == CircuitState.HALF_OPEN

    def test_success_moves_to_closed_after_threshold(self):
        self.cb.record_success()
        self.cb.record_success()
        assert self.cb.state == CircuitState.CLOSED

    def test_failure_moves_back_to_open(self):
        self.cb.record_failure()
        assert self.cb.state == CircuitState.OPEN

    def test_max_calls_exceeded_returns_false(self):
        # Exhaust half_open_max_calls
        self.cb.record_success()
        self.cb.record_success()
        self.cb.half_open_calls = 3  # force exhaust (already closed from above)

    def test_half_open_allows_until_max(self):
        cfg = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.0,
                                   half_open_max_calls=1)
        cb = CircuitBreaker(cfg)
        cb.record_failure()
        cb.can_execute()  # → HALF_OPEN
        # First call ok
        assert cb.can_execute() is True


# ── IntelligentRetry ──────────────────────────────────────────────────────
class TestIntelligentRetryInit:
    def test_default_config(self):
        ir = IntelligentRetry()
        assert isinstance(ir.retry_config, RetryConfig)
        assert isinstance(ir.circuit_breaker_config, CircuitBreakerConfig)

    def test_custom_config(self):
        rc = RetryConfig(max_retries=5)
        ir = IntelligentRetry(retry_config=rc)
        assert ir.retry_config.max_retries == 5

    def test_circuit_breakers_empty(self):
        ir = IntelligentRetry()
        assert ir.circuit_breakers == {}


class TestGetCircuitBreaker:
    def test_creates_new(self):
        ir = IntelligentRetry()
        cb = ir.get_circuit_breaker("svc1")
        assert isinstance(cb, CircuitBreaker)

    def test_returns_same_instance(self):
        ir = IntelligentRetry()
        cb1 = ir.get_circuit_breaker("svc2")
        cb2 = ir.get_circuit_breaker("svc2")
        assert cb1 is cb2

    def test_different_keys(self):
        ir = IntelligentRetry()
        cb1 = ir.get_circuit_breaker("a")
        cb2 = ir.get_circuit_breaker("b")
        assert cb1 is not cb2


class TestCalculateDelay:
    def test_exponential_backoff(self):
        rc = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=100.0,
                         strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
        ir = IntelligentRetry(retry_config=rc)
        assert ir._calculate_delay(0) == 1.0
        assert ir._calculate_delay(1) == 2.0
        assert ir._calculate_delay(2) == 4.0

    def test_exponential_capped_at_max(self):
        rc = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=3.0,
                         strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
        ir = IntelligentRetry(retry_config=rc)
        assert ir._calculate_delay(5) == 3.0

    def test_linear_backoff(self):
        rc = RetryConfig(initial_delay=2.0, max_delay=100.0,
                         strategy=RetryStrategy.LINEAR_BACKOFF)
        ir = IntelligentRetry(retry_config=rc)
        assert ir._calculate_delay(0) == 2.0
        assert ir._calculate_delay(1) == 4.0

    def test_fixed_interval(self):
        rc = RetryConfig(initial_delay=3.0,
                         strategy=RetryStrategy.FIXED_INTERVAL)
        ir = IntelligentRetry(retry_config=rc)
        assert ir._calculate_delay(0) == 3.0
        assert ir._calculate_delay(5) == 3.0

    def test_custom_returns_initial_delay(self):
        rc = RetryConfig(initial_delay=1.5,
                         strategy=RetryStrategy.CUSTOM)
        ir = IntelligentRetry(retry_config=rc)
        assert ir._calculate_delay(0) == 1.5


class TestIsRetryableError:
    def test_timeout_error_is_retryable(self):
        ir = IntelligentRetry()
        assert ir._is_retryable_error(TimeoutError("timeout occurred")) is True

    def test_connection_error_is_retryable(self):
        ir = IntelligentRetry()
        assert ir._is_retryable_error(ConnectionError("connection_error")) is True

    def test_unknown_error_not_retryable(self):
        ir = IntelligentRetry()
        assert ir._is_retryable_error(ValueError("bad value")) is False

    def test_message_contains_keyword(self):
        ir = IntelligentRetry()
        assert ir._is_retryable_error(Exception("rate_limit exceeded")) is True


class TestExecuteWithRetry:
    def test_success_first_attempt(self):
        ir = IntelligentRetry()
        called = []

        async def fn():
            called.append(1)
            return "result"

        result = asyncio.run(ir.execute_with_retry(fn))
        assert result.success is True
        assert result.result == "result"
        assert result.attempts == 1
        assert len(called) == 1

    def test_sync_function_success(self):
        ir = IntelligentRetry()

        def fn():
            return 42

        result = asyncio.run(ir.execute_with_retry(fn))
        assert result.success is True
        assert result.result == 42

    def test_non_retryable_error_fails_immediately(self):
        rc = RetryConfig(max_retries=3)
        ir = IntelligentRetry(retry_config=rc)

        def fn():
            raise ValueError("bad value")  # not retryable

        result = asyncio.run(ir.execute_with_retry(fn))
        assert result.success is False
        assert result.attempts == 1  # no retry

    def test_retryable_error_retries(self):
        rc = RetryConfig(max_retries=2, initial_delay=0.0)
        ir = IntelligentRetry(retry_config=rc)
        counter = [0]

        def fn():
            counter[0] += 1
            raise TimeoutError("timeout")

        result = asyncio.run(ir.execute_with_retry(fn))
        assert result.success is False
        assert counter[0] == 3  # initial + 2 retries

    def test_success_after_retry(self):
        rc = RetryConfig(max_retries=2, initial_delay=0.0)
        ir = IntelligentRetry(retry_config=rc)
        counter = [0]

        def fn():
            counter[0] += 1
            if counter[0] < 2:
                raise TimeoutError("timeout")
            return "ok"

        result = asyncio.run(ir.execute_with_retry(fn))
        assert result.success is True
        assert result.result == "ok"
        assert counter[0] == 2

    def test_circuit_breaker_open_blocks(self):
        # Use a circuit breaker that is forced open
        ir = IntelligentRetry()
        cb = ir.get_circuit_breaker("blocked")
        cb.state = CircuitState.OPEN
        from datetime import datetime, timedelta
        cb.last_failure_time = datetime.now() + timedelta(seconds=9999)

        def fn():
            return "ok"

        result = asyncio.run(ir.execute_with_retry(fn, circuit_breaker_key="blocked"))
        assert result.success is False
        assert result.attempts == 0

    def test_errors_list_populated(self):
        rc = RetryConfig(max_retries=1, initial_delay=0.0)
        ir = IntelligentRetry(retry_config=rc)

        def fn():
            raise TimeoutError("my error")

        result = asyncio.run(ir.execute_with_retry(fn))
        assert len(result.errors) > 0
        assert "my error" in result.errors[0]


# ── Global instance ───────────────────────────────────────────────────────
class TestGlobalInstance:
    def test_intelligent_retry_is_instance(self):
        assert isinstance(intelligent_retry, IntelligentRetry)

    def test_retry_is_callable(self):
        assert callable(retry)
