"""
Unit tests for scripts/misc/dynamic_rate_limiter.py
"""
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime

# ── external module mocks ──────────────────────────────────────────────────
_psutil = MagicMock()
_psutil.cpu_percent.return_value = 30.0
_psutil.virtual_memory.return_value = MagicMock(percent=40.0)
sys.modules.setdefault("psutil", _psutil)

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

import pytest  # noqa: E402
from scripts.misc.dynamic_rate_limiter import (  # noqa: E402
    Priority,
    RateLimitConfig,
    RateLimitInfo,
    DynamicRateLimiter,
    dynamic_rate_limiter,
    rate_limit,
)


# ── Priority ──────────────────────────────────────────────────────────────
class TestPriority:
    def test_values(self):
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.URGENT.value == "urgent"

    def test_is_str_enum(self):
        assert isinstance(Priority.MEDIUM, str)


# ── RateLimitConfig ───────────────────────────────────────────────────────
class TestRateLimitConfig:
    def test_default_priority_multiplier(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
        assert cfg.priority_multiplier["low"] == 0.5
        assert cfg.priority_multiplier["medium"] == 1.0
        assert cfg.priority_multiplier["high"] == 1.5
        assert cfg.priority_multiplier["urgent"] == 2.0

    def test_custom_multiplier(self):
        m = {"low": 0.1, "medium": 0.5, "high": 1.0, "urgent": 1.5}
        cfg = RateLimitConfig(base_rate=5, max_rate=50, min_rate=1,
                              priority_multiplier=m)
        assert cfg.priority_multiplier == m

    def test_default_thresholds(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
        assert cfg.cpu_threshold == 0.8
        assert cfg.memory_threshold == 0.8


# ── RateLimitInfo ─────────────────────────────────────────────────────────
class TestRateLimitInfo:
    def test_create(self):
        info = RateLimitInfo(
            user_id="u1",
            priority=Priority.HIGH,
            current_rate=15.0,
            allowed_requests=15,
            window_start=datetime.now(),
        )
        assert info.user_id == "u1"
        assert info.priority == Priority.HIGH
        assert info.request_count == 0


# ── DynamicRateLimiter with direct config ────────────────────────────────
@pytest.fixture
def drl():
    cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
    limiter = DynamicRateLimiter(config=cfg)
    return limiter


class TestDynamicRateLimiterInit:
    def test_config_stored(self, drl):
        assert drl.config.base_rate == 10
        assert drl.config.max_rate == 100

    def test_user_limits_empty(self, drl):
        assert drl.user_limits == {}

    def test_monitoring_false_initially(self, drl):
        assert drl.monitoring is False


class TestCalculateDynamicRate:
    def test_low_usage_returns_base_rate(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 20.0
            p.virtual_memory.return_value = MagicMock(percent=30.0)
            rate = limiter._calculate_dynamic_rate()
        assert 1.0 <= rate <= 100.0

    def test_high_cpu_reduces_rate(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1,
                              cpu_threshold=0.8)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 90.0  # 90% > 80% threshold
            p.virtual_memory.return_value = MagicMock(percent=20.0)
            rate = limiter._calculate_dynamic_rate()
        assert rate < 10.0  # reduced

    def test_rate_clamped_to_min(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=2)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 99.0
            p.virtual_memory.return_value = MagicMock(percent=99.0)
            rate = limiter._calculate_dynamic_rate()
        assert rate >= 2.0


class TestCheckRateLimit:
    def test_first_request_allowed(self, drl):
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            result = drl.check_rate_limit("user1", Priority.MEDIUM)
        assert result is True

    def test_creates_user_limit(self, drl):
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            drl.check_rate_limit("user2", Priority.HIGH)
        assert "user2" in drl.user_limits

    def test_default_user_id(self, drl):
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            drl.check_rate_limit()
        assert "default" in drl.user_limits

    def test_exceeds_limit_returns_false(self):
        cfg = RateLimitConfig(base_rate=1, max_rate=1, min_rate=1)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            # allowed=1: first OK, second should fail
            limiter.check_rate_limit("u", Priority.MEDIUM)
            result = limiter.check_rate_limit("u", Priority.MEDIUM)
        assert result is False

    def test_request_count_increments(self, drl):
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            drl.check_rate_limit("u3", Priority.LOW)
        assert drl.user_limits["u3"].request_count == 1


class TestGetRateLimitInfo:
    def test_none_for_unknown_user(self, drl):
        assert drl.get_rate_limit_info("unknown") is None

    def test_returns_dict_after_check(self, drl):
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            drl.check_rate_limit("info_user", Priority.HIGH)
        info = drl.get_rate_limit_info("info_user")
        assert isinstance(info, dict)

    def test_info_keys(self, drl):
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            drl.check_rate_limit("ki", Priority.MEDIUM)
        info = drl.get_rate_limit_info("ki")
        for key in ("user_id", "priority", "current_rate", "allowed_requests",
                    "request_count", "remaining_requests", "window_start"):
            assert key in info

    def test_remaining_requests(self, drl):
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            drl.check_rate_limit("rr", Priority.MEDIUM)
        info = drl.get_rate_limit_info("rr")
        assert info["remaining_requests"] == info["allowed_requests"] - info["request_count"]


class TestResourceMonitoring:
    def test_start_monitoring(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            limiter.start_resource_monitoring()
            assert limiter.monitoring is True
            limiter.stop_resource_monitoring()

    def test_double_start_noop(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            limiter.start_resource_monitoring()
            thread1 = limiter.resource_monitor_thread
            limiter.start_resource_monitoring()  # should be noop
            assert limiter.resource_monitor_thread is thread1
            limiter.stop_resource_monitoring()

    def test_stop_monitoring(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            limiter.start_resource_monitoring()
            limiter.stop_resource_monitoring()
        assert limiter.monitoring is False


class TestRateLimitDecorator:
    def test_sync_function_allowed(self, drl):
        @drl.rate_limit_decorator(user_id_key="user_id")
        def my_fn(**kwargs):
            return "ok"

        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            result = my_fn(user_id="dec_user", priority="medium")
        assert result == "ok"

    def test_sync_function_blocked(self):
        cfg = RateLimitConfig(base_rate=1, max_rate=1, min_rate=1)
        limiter = DynamicRateLimiter(config=cfg)
        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            # exhaust the limit
            limiter.check_rate_limit("blocked_dec", Priority.MEDIUM)

        @limiter.rate_limit_decorator(user_id_key="user_id")
        def my_fn(**kwargs):
            return "ok"

        with patch("scripts.misc.dynamic_rate_limiter.psutil") as p:
            p.cpu_percent.return_value = 30.0
            p.virtual_memory.return_value = MagicMock(percent=40.0)
            with pytest.raises(Exception, match="レート制限"):
                my_fn(user_id="blocked_dec", priority="medium")


# ── Global instance ───────────────────────────────────────────────────────
class TestGlobalInstance:
    def test_dynamic_rate_limiter_is_instance(self):
        assert isinstance(dynamic_rate_limiter, DynamicRateLimiter)

    def test_rate_limit_is_callable(self):
        assert callable(rate_limit)
