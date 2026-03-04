"""
Unit Tests — image_generation_service.api_auth
================================================
API Key 認証 & レートリミッターの単体テスト。
"""

import asyncio
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# テスト用 DB パスを先に設定 (billing が import される前に)
_tmp_dir = tempfile.mkdtemp()
os.environ["BILLING_DB_PATH"] = os.path.join(_tmp_dir, "test_auth_billing.db")

from image_generation_service.api_auth import (
    AuthContext,
    _RateLimiter,
)
from image_generation_service.billing import (
    BillingManager,
    Plan,
    PLAN_LIMITS,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """各テストで新しい DB を使用"""
    import image_generation_service.billing as billing_mod
    import image_generation_service.api_auth as auth_mod

    db_path = tmp_path / "auth_billing.db"
    billing_mod._DB_PATH = db_path
    # auth のシングルトンをリセット
    auth_mod._billing = None
    return db_path


# ─── AuthContext ─────────────────────────────────────

class TestAuthContext:

    def test_free_context(self):
        limits = PLAN_LIMITS[Plan.free]
        ctx = AuthContext(
            api_key="free-key",
            plan=Plan.free,
            limits=limits,
            remaining_quota=10,
        )
        assert ctx.priority == 1
        assert ctx.can_auto_improve is False
        assert ctx.remaining_quota == 10

    def test_enterprise_context(self):
        limits = PLAN_LIMITS[Plan.enterprise]
        ctx = AuthContext(
            api_key="ent-key",
            plan=Plan.enterprise,
            limits=limits,
            remaining_quota=999999,
        )
        assert ctx.priority == 3
        assert ctx.can_auto_improve is True

    def test_pro_context(self):
        limits = PLAN_LIMITS[Plan.pro]
        ctx = AuthContext(
            api_key="pro-key",
            plan=Plan.pro,
            limits=limits,
            remaining_quota=100,
        )
        assert ctx.priority == 2
        assert ctx.can_auto_improve is True


# ─── Rate Limiter ────────────────────────────────────

class TestRateLimiter:

    def test_allows_within_limit(self):
        rl = _RateLimiter(window_seconds=60)
        for i in range(5):
            allowed, remaining = rl.check("key-1", limit=5)
            assert allowed is True
            assert remaining >= 0

    def test_blocks_over_limit(self):
        rl = _RateLimiter(window_seconds=60)
        for _ in range(5):
            rl.check("key-2", limit=5)
        allowed, remaining = rl.check("key-2", limit=5)
        assert allowed is False
        assert remaining == 0

    def test_separate_keys(self):
        rl = _RateLimiter(window_seconds=60)
        for _ in range(5):
            rl.check("key-a", limit=5)
        # key-b はまだ使っていない
        allowed, _ = rl.check("key-b", limit=5)
        assert allowed is True

    def test_window_expiration(self):
        """超短いウィンドウで期限切れテスト"""
        rl = _RateLimiter(window_seconds=0)  # 即期限切れ
        rl.check("key-3", limit=1)
        time.sleep(0.01)
        allowed, _ = rl.check("key-3", limit=1)
        assert allowed is True


# ─── Integration: Auth + Billing ─────────────────────

class TestAuthIntegration:

    def test_default_key_validates(self, fresh_db):
        """デフォルト key は有効"""
        mgr = BillingManager()
        assert _run(mgr.validate_api_key("default")) is True
        plan = _run(mgr.get_plan("default"))
        assert plan == Plan.enterprise

    def test_invalid_key(self, fresh_db):
        mgr = BillingManager()
        assert _run(mgr.validate_api_key("does-not-exist")) is False

    def test_deactivated_key(self, fresh_db):
        mgr = BillingManager()
        _run(mgr.create_api_key("temp-key", Plan.pro))
        assert _run(mgr.validate_api_key("temp-key")) is True
        _run(mgr.deactivate_api_key("temp-key"))
        assert _run(mgr.validate_api_key("temp-key")) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
