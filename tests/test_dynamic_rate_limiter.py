#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_dynamic_rate_limiter.py
DynamicRateLimiter の単体テスト
"""

import sys
import json
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# sys.path に scripts/misc を追加
MISC_DIR = Path(__file__).parent.parent / "scripts" / "misc"
sys.path.insert(0, str(MISC_DIR))

# 依存モジュールをモック化
mock_logger = MagicMock()
mock_error_handler_instance = MagicMock()
mock_timeout_config = MagicMock()

# psutil もモック化
mock_psutil = MagicMock()
mock_psutil.cpu_percent.return_value = 10.0  # 低 CPU
mock_vm = MagicMock()
mock_vm.percent = 30.0
mock_psutil.virtual_memory.return_value = mock_vm

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
    "psutil": mock_psutil,
}):
    import dynamic_rate_limiter


Priority = dynamic_rate_limiter.Priority
RateLimitConfig = dynamic_rate_limiter.RateLimitConfig
RateLimitInfo = dynamic_rate_limiter.RateLimitInfo
DynamicRateLimiter = dynamic_rate_limiter.DynamicRateLimiter


# ============================================================
# Priority
# ============================================================

class TestPriority(unittest.TestCase):

    def test_values(self):
        self.assertEqual(Priority.LOW.value, "low")
        self.assertEqual(Priority.MEDIUM.value, "medium")
        self.assertEqual(Priority.HIGH.value, "high")
        self.assertEqual(Priority.URGENT.value, "urgent")

    def test_from_string(self):
        self.assertEqual(Priority("medium"), Priority.MEDIUM)
        self.assertEqual(Priority("urgent"), Priority.URGENT)


# ============================================================
# RateLimitConfig
# ============================================================

class TestRateLimitConfig(unittest.TestCase):

    def test_required_fields(self):
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1)
        self.assertEqual(cfg.base_rate, 10)
        self.assertEqual(cfg.max_rate, 100)
        self.assertEqual(cfg.min_rate, 1)

    def test_cpu_threshold_default(self):
        cfg = RateLimitConfig(base_rate=5, max_rate=50, min_rate=1)
        self.assertAlmostEqual(cfg.cpu_threshold, 0.8)
        self.assertAlmostEqual(cfg.memory_threshold, 0.8)

    def test_priority_multiplier_defaults(self):
        cfg = RateLimitConfig(base_rate=5, max_rate=50, min_rate=1)
        self.assertIsNotNone(cfg.priority_multiplier)
        self.assertAlmostEqual(cfg.priority_multiplier["low"], 0.5)
        self.assertAlmostEqual(cfg.priority_multiplier["medium"], 1.0)
        self.assertAlmostEqual(cfg.priority_multiplier["high"], 1.5)
        self.assertAlmostEqual(cfg.priority_multiplier["urgent"], 2.0)

    def test_none_multiplier_gets_defaults(self):
        cfg = RateLimitConfig(base_rate=5, max_rate=50, min_rate=1, priority_multiplier=None)
        self.assertIsNotNone(cfg.priority_multiplier)

    def test_custom_multiplier_preserved(self):
        custom = {"low": 0.3, "medium": 1.0}
        cfg = RateLimitConfig(base_rate=5, max_rate=50, min_rate=1, priority_multiplier=custom)
        self.assertEqual(cfg.priority_multiplier["low"], 0.3)


# ============================================================
# RateLimitInfo
# ============================================================

class TestRateLimitInfo(unittest.TestCase):

    def test_basic_fields(self):
        info = RateLimitInfo(
            user_id="user1",
            priority=Priority.HIGH,
            current_rate=15.0,
            allowed_requests=15,
            window_start=datetime.now(),
            request_count=3,
        )
        self.assertEqual(info.user_id, "user1")
        self.assertEqual(info.priority, Priority.HIGH)
        self.assertEqual(info.request_count, 3)

    def test_default_request_count(self):
        info = RateLimitInfo(
            user_id="u",
            priority=Priority.LOW,
            current_rate=5.0,
            allowed_requests=5,
            window_start=datetime.now(),
        )
        self.assertEqual(info.request_count, 0)


# ============================================================
# DynamicRateLimiter — 初期化
# ============================================================

def _make_limiter(base_rate=10, max_rate=100, min_rate=1):
    """テスト用 DynamicRateLimiter を生成（設定ファイルなし）"""
    cfg = RateLimitConfig(base_rate=base_rate, max_rate=max_rate, min_rate=min_rate)
    return DynamicRateLimiter(config=cfg)


class TestDynamicRateLimiterInit(unittest.TestCase):

    def test_init_with_config(self):
        cfg = RateLimitConfig(base_rate=5, max_rate=50, min_rate=1)
        rl = DynamicRateLimiter(config=cfg)
        self.assertEqual(rl.config.base_rate, 5)

    def test_default_user_limits_empty(self):
        rl = _make_limiter()
        self.assertEqual(len(rl.user_limits), 0)

    def test_default_monitoring_false(self):
        rl = _make_limiter()
        self.assertFalse(rl.monitoring)


# ============================================================
# DynamicRateLimiter — _calculate_dynamic_rate
# ============================================================

class TestCalculateDynamicRate(unittest.TestCase):

    def test_low_resource_returns_base_rate(self):
        """CPU/メモリ共に低い場合 → base_rate がそのまま返る（最大・最小制限内で）"""
        mock_psutil.cpu_percent.return_value = 20.0   # 20%
        mock_vm.percent = 40.0
        rl = _make_limiter(base_rate=10, max_rate=100, min_rate=1)
        rate = rl._calculate_dynamic_rate()
        # cpu 0.2 < threshold 0.8 → resource_factor = 1.0 → dynamic_rate = 10
        self.assertAlmostEqual(rate, 10.0)

    def test_high_cpu_reduces_rate(self):
        """CPU 使用率が閾値超え → レートが下がる"""
        mock_psutil.cpu_percent.return_value = 90.0   # 90%
        mock_vm.percent = 30.0
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1, cpu_threshold=0.8)
        rl = DynamicRateLimiter(config=cfg)
        rate = rl._calculate_dynamic_rate()
        self.assertLess(rate, 10.0)

    def test_high_memory_reduces_rate(self):
        """メモリ使用率が閾値超え → レートが下がる"""
        mock_psutil.cpu_percent.return_value = 10.0
        mock_vm.percent = 95.0   # 95%
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=1, memory_threshold=0.8)
        rl = DynamicRateLimiter(config=cfg)
        rate = rl._calculate_dynamic_rate()
        self.assertLess(rate, 10.0)

    def test_rate_never_below_min_rate(self):
        """レートは min_rate を下回らない"""
        mock_psutil.cpu_percent.return_value = 99.0
        mock_vm.percent = 99.0
        cfg = RateLimitConfig(base_rate=10, max_rate=100, min_rate=5, cpu_threshold=0.8, memory_threshold=0.8)
        rl = DynamicRateLimiter(config=cfg)
        rate = rl._calculate_dynamic_rate()
        self.assertGreaterEqual(rate, 5.0)

    def test_rate_never_above_max_rate(self):
        """レートは max_rate を超えない"""
        mock_psutil.cpu_percent.return_value = 0.0
        mock_vm.percent = 0.0
        cfg = RateLimitConfig(base_rate=10, max_rate=8, min_rate=1)
        rl = DynamicRateLimiter(config=cfg)
        rate = rl._calculate_dynamic_rate()
        self.assertLessEqual(rate, 8.0)

    def test_cpu_and_memory_usage_stored(self):
        """現在の CPU/メモリ使用率がインスタンスに保存される"""
        mock_psutil.cpu_percent.return_value = 50.0
        mock_vm.percent = 60.0
        rl = _make_limiter()
        rl._calculate_dynamic_rate()
        self.assertAlmostEqual(rl.current_cpu_usage, 0.5)
        self.assertAlmostEqual(rl.current_memory_usage, 0.6)


# ============================================================
# DynamicRateLimiter — check_rate_limit
# ============================================================

class TestCheckRateLimit(unittest.TestCase):

    def setUp(self):
        mock_psutil.cpu_percent.return_value = 10.0
        mock_vm.percent = 30.0

    def test_first_request_allowed(self):
        rl = _make_limiter(base_rate=5, max_rate=5)
        self.assertTrue(rl.check_rate_limit("user1", Priority.MEDIUM))

    def test_requests_within_limit_allowed(self):
        rl = _make_limiter(base_rate=5, max_rate=5)
        for _ in range(5):
            result = rl.check_rate_limit("user_a", Priority.MEDIUM)
        # 最後のリクエストまで通るはず（5件以内）
        self.assertTrue(result)

    def test_request_count_increments(self):
        rl = _make_limiter(base_rate=10, max_rate=10)
        rl.check_rate_limit("user2", Priority.MEDIUM)
        rl.check_rate_limit("user2", Priority.MEDIUM)
        self.assertEqual(rl.user_limits["user2"].request_count, 2)

    def test_exceeding_limit_blocked(self):
        """allowed_requests を超えたリクエストは拒否"""
        rl = _make_limiter(base_rate=2, max_rate=2)
        rl.check_rate_limit("blocked_user", Priority.MEDIUM)
        rl.check_rate_limit("blocked_user", Priority.MEDIUM)
        # allowed は int(base_rate * priority_multiplier) = int(2 * 1.0) = 2
        # 3 件目はブロックされるはず
        result = rl.check_rate_limit("blocked_user", Priority.MEDIUM)
        self.assertFalse(result)

    def test_different_users_independent_limits(self):
        rl = _make_limiter(base_rate=1, max_rate=1)
        self.assertTrue(rl.check_rate_limit("u1", Priority.MEDIUM))
        # u1 の制限に関係なく u2 は許可される
        self.assertTrue(rl.check_rate_limit("u2", Priority.MEDIUM))


# ============================================================
# DynamicRateLimiter — get_rate_limit_info
# ============================================================

class TestGetRateLimitInfo(unittest.TestCase):

    def setUp(self):
        mock_psutil.cpu_percent.return_value = 10.0
        mock_vm.percent = 30.0
        self.rl = _make_limiter()

    def test_unknown_user_returns_none(self):
        self.assertIsNone(self.rl.get_rate_limit_info("nobody"))

    def test_known_user_returns_dict(self):
        self.rl.check_rate_limit("user_x", Priority.HIGH)
        info = self.rl.get_rate_limit_info("user_x")
        self.assertIsNotNone(info)
        self.assertIsInstance(info, dict)

    def test_info_structure(self):
        self.rl.check_rate_limit("user_s", Priority.LOW)
        info = self.rl.get_rate_limit_info("user_s")
        self.assertIn("user_id", info)
        self.assertIn("priority", info)
        self.assertIn("current_rate", info)
        self.assertIn("allowed_requests", info)
        self.assertIn("request_count", info)
        self.assertIn("remaining_requests", info)
        self.assertIn("window_start", info)
        self.assertIn("cpu_usage", info)
        self.assertIn("memory_usage", info)

    def test_request_count_reflects_usage(self):
        self.rl.check_rate_limit("user_c", Priority.MEDIUM)
        self.rl.check_rate_limit("user_c", Priority.MEDIUM)
        info = self.rl.get_rate_limit_info("user_c")
        self.assertEqual(info["request_count"], 2)

    def test_remaining_requests_decreases(self):
        self.rl.check_rate_limit("user_r", Priority.MEDIUM)
        info = self.rl.get_rate_limit_info("user_r")
        self.assertEqual(info["remaining_requests"], info["allowed_requests"] - 1)


# ============================================================
# DynamicRateLimiter — _load_config（ファイルあり・なし）
# ============================================================

class TestLoadConfig(unittest.TestCase):

    def test_fallback_when_no_file(self):
        rl = DynamicRateLimiter(config_path=Path("nonexistent_path.json"))
        # フォールバック値が設定される
        self.assertEqual(rl.config.base_rate, 10)
        self.assertEqual(rl.config.max_rate, 100)
        self.assertEqual(rl.config.min_rate, 1)

    def test_loads_from_file(self, tmp_path=None):
        """設定ファイルが存在する場合は読み込む"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump({"base_rate": 20, "max_rate": 200, "min_rate": 2}, f)
            tmp_file = Path(f.name)
        try:
            rl = DynamicRateLimiter(config_path=tmp_file)
            self.assertEqual(rl.config.base_rate, 20)
            self.assertEqual(rl.config.max_rate, 200)
        finally:
            tmp_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
