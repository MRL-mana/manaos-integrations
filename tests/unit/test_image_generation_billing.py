"""
Unit Tests — image_generation_service.billing
===============================================
SQLite billing の CRUD テスト。ファイル IO だけで完結。
"""

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# テスト用 DB パスを先に設定
_tmp_dir = tempfile.mkdtemp()
os.environ["BILLING_DB_PATH"] = os.path.join(_tmp_dir, "test_billing.db")

from image_generation_service.billing import (
    BillingManager,
    Plan,
    PlanLimits,
    PLAN_LIMITS,
)


def _run(coro):
    """ヘルパー: 非同期関数を同期で実行"""
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """各テストで新しい DB を使用"""
    import image_generation_service.billing as billing_mod

    db_path = tmp_path / "billing.db"
    billing_mod._DB_PATH = db_path
    return db_path


class TestPlanLimits:

    def test_free_plan(self):
        limits = PLAN_LIMITS[Plan.free]
        assert limits.daily_quota == 10
        assert limits.max_resolution == 512
        assert limits.priority == 1
        assert limits.auto_improve is False
        assert limits.price_yen_monthly == 0

    def test_pro_plan(self):
        limits = PLAN_LIMITS[Plan.pro]
        assert limits.daily_quota == 100
        assert limits.max_resolution == 1024
        assert limits.auto_improve is True
        assert limits.price_yen_monthly == 2980

    def test_enterprise_plan(self):
        limits = PLAN_LIMITS[Plan.enterprise]
        assert limits.daily_quota == 999999
        assert limits.max_resolution == 2048
        assert limits.priority == 3
        assert limits.price_yen_monthly == 9800


class TestBillingManager:

    def test_init(self, fresh_db):
        """初期化でデフォルト API Key が作成される"""
        mgr = BillingManager()
        assert _run(mgr.validate_api_key("default")) is True

    def test_default_plan_is_enterprise(self, fresh_db):
        mgr = BillingManager()
        plan = _run(mgr.get_plan("default"))
        assert plan == Plan.enterprise

    def test_create_api_key(self, fresh_db):
        mgr = BillingManager()
        ok = _run(mgr.create_api_key("test-key-1", Plan.pro, "Test"))
        assert ok is True
        assert _run(mgr.validate_api_key("test-key-1")) is True
        plan = _run(mgr.get_plan("test-key-1"))
        assert plan == Plan.pro

    def test_duplicate_api_key(self, fresh_db):
        mgr = BillingManager()
        _run(mgr.create_api_key("dup-key", Plan.free))
        ok2 = _run(mgr.create_api_key("dup-key", Plan.pro))
        assert ok2 is False  # 重複は False

    def test_deactivate_api_key(self, fresh_db):
        mgr = BillingManager()
        _run(mgr.create_api_key("deact-key", Plan.pro))
        assert _run(mgr.validate_api_key("deact-key")) is True
        _run(mgr.deactivate_api_key("deact-key"))
        assert _run(mgr.validate_api_key("deact-key")) is False

    def test_unknown_key_is_free(self, fresh_db):
        mgr = BillingManager()
        plan = _run(mgr.get_plan("nonexistent-key"))
        assert plan == Plan.free

    def test_check_quota_enterprise_unlimited(self, fresh_db):
        """Enterprise は実質無制限"""
        mgr = BillingManager()
        for _ in range(20):
            assert _run(mgr.check_quota("default")) is True
            _run(mgr.record_usage("default", 0.01))

    def test_check_quota_free_limited(self, fresh_db):
        """Free プランは 10 枚/日で上限"""
        mgr = BillingManager()
        _run(mgr.create_api_key("free-key", Plan.free))
        for i in range(10):
            assert _run(mgr.check_quota("free-key")) is True
            _run(mgr.record_usage("free-key", 0.01))
        # 11 枚目は拒否
        assert _run(mgr.check_quota("free-key")) is False

    def test_remaining_quota(self, fresh_db):
        mgr = BillingManager()
        _run(mgr.create_api_key("quota-key", Plan.free))
        assert _run(mgr.get_remaining_quota("quota-key")) == 10
        _run(mgr.record_usage("quota-key", 0.01))
        assert _run(mgr.get_remaining_quota("quota-key")) == 9

    def test_check_resolution(self, fresh_db):
        mgr = BillingManager()
        _run(mgr.create_api_key("res-key", Plan.free))
        # Free: max 512
        assert _run(mgr.check_resolution("res-key", 512, 512)) is True
        assert _run(mgr.check_resolution("res-key", 1024, 512)) is False

    def test_estimate_cost(self, fresh_db):
        mgr = BillingManager()
        cost = _run(mgr.estimate_cost(512, 512, 20, 1))
        assert cost == 0.012
        # 1024x1024 = 4x pixels
        cost_big = _run(mgr.estimate_cost(1024, 1024, 20, 1))
        assert cost_big == pytest.approx(0.048, abs=0.001)

    def test_record_usage(self, fresh_db):
        mgr = BillingManager()
        _run(mgr.record_usage("default", 0.05, job_id="job-1", width=1024, height=1024, steps=30))
        remaining = _run(mgr.get_remaining_quota("default"))
        assert remaining == 999998  # enterprise: 999999 - 1

    def test_billing_dashboard(self, fresh_db):
        mgr = BillingManager()
        _run(mgr.record_usage("default", 0.1))
        _run(mgr.record_usage("default", 0.2))
        dash = _run(mgr.get_billing_dashboard("default"))
        assert dash["plan"] == "enterprise"
        assert dash["today"]["used"] == 2
        assert dash["today"]["cost_yen"] == pytest.approx(0.3, abs=0.01)
        assert dash["active_keys"] >= 1

    def test_register_user_creates_api_key(self, fresh_db):
        mgr = BillingManager()
        result = _run(
            mgr.register_user(
                email="user@example.com",
                plan=Plan.pro,
                label="test-user",
            )
        )
        assert result["email"] == "user@example.com"
        assert result["plan"] == "pro"
        assert result["newly_created"] is True
        assert result["api_key"].startswith("img_")
        assert _run(mgr.validate_api_key(result["api_key"])) is True

    def test_register_user_returns_existing_user(self, fresh_db):
        mgr = BillingManager()
        first = _run(mgr.register_user("existing@example.com", Plan.free))
        second = _run(mgr.register_user("existing@example.com", Plan.enterprise))
        assert second["email"] == "existing@example.com"
        assert second["api_key"] == first["api_key"]
        assert second["newly_created"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
