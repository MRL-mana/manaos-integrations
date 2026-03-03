"""
Unit Tests — Stripe/KOMOJU payment flow & revenue KPI
=======================================================
決済フロー (スタブ/実装) とサブスクリプションアクティベーション、
収益KPI統合エンドポイントのテスト。
"""

import asyncio
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_tmp_dir = tempfile.mkdtemp()
os.environ["BILLING_DB_PATH"] = os.path.join(_tmp_dir, "test_billing_pay.db")


from image_generation_service.billing import BillingManager, Plan


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    import image_generation_service.billing as billing_mod
    db_path = tmp_path / "billing_pay.db"
    billing_mod._DB_PATH = db_path
    return db_path


class TestStripePayment:

    def test_stub_when_no_key(self, fresh_db):
        """STRIPE_SECRET_KEY 未設定ならスタブ応答"""
        os.environ.pop("STRIPE_SECRET_KEY", None)
        mgr = BillingManager()
        result = mgr.create_stripe_payment("user@test.com", "pro")
        assert result["status"] == "stub"
        assert result["provider"] == "stripe"
        assert "test_pro_user@test.com" in result["payment_url"]
        assert "hint" in result

    def test_stub_with_placeholder_key(self, fresh_db):
        """プレースホルダキーでもスタブ"""
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_placeholder_xxx"
        mgr = BillingManager()
        result = mgr.create_stripe_payment("u1", "enterprise")
        assert result["status"] == "stub"
        os.environ.pop("STRIPE_SECRET_KEY", None)


class TestKomojuPayment:

    def test_stub_when_no_key(self, fresh_db):
        """KOMOJU_SECRET_KEY 未設定ならスタブ応答"""
        os.environ.pop("KOMOJU_SECRET_KEY", None)
        mgr = BillingManager()
        result = mgr.create_komoju_payment("user@test.com", "pro")
        assert result["status"] == "stub"
        assert result["provider"] == "komoju"
        assert "hint" in result

    def test_unknown_plan_returns_error(self, fresh_db):
        """不明プラン → error"""
        mgr = BillingManager()
        result = mgr.create_komoju_payment("u1", "mega_plan")
        assert result["status"] == "error"
        assert "Unknown plan" in result["detail"]


class TestSubscriptionActivation:

    def test_activate_by_email(self, fresh_db):
        mgr = BillingManager()
        reg = _run(mgr.register_user("pay@test.com", Plan.free))
        assert reg["plan"] == "free"
        # アクティベート
        result = _run(mgr.activate_subscription("pay@test.com", "pro", "sess_123"))
        assert result["ok"] is True
        assert result["plan"] == "pro"
        # プランが更新されたか確認
        plan = _run(mgr.get_plan(reg["api_key"]))
        assert plan == Plan.pro

    def test_activate_by_api_key(self, fresh_db):
        """email ではなく api_key でも検索可能"""
        mgr = BillingManager()
        _run(mgr.create_api_key("direct-key", Plan.free))
        result = _run(mgr.activate_subscription("direct-key", "enterprise"))
        assert result["ok"] is True
        plan = _run(mgr.get_plan("direct-key"))
        assert plan == Plan.enterprise

    def test_activate_unknown_user_fails(self, fresh_db):
        mgr = BillingManager()
        result = _run(mgr.activate_subscription("nobody@void.com", "pro"))
        assert result["ok"] is False
        assert "not found" in result["detail"]

    def test_activate_invalid_plan_fails(self, fresh_db):
        mgr = BillingManager()
        result = _run(mgr.activate_subscription("x@x.com", "mega"))
        assert result["ok"] is False
        assert "Invalid plan" in result["detail"]


class TestRevenueKpiEndpoint:
    """router の /revenue/kpi の計算ロジックをテスト"""

    def test_compute_loop_health_zero(self):
        """全ゼロ → critical"""
        from image_generation_service.router import _compute_loop_health
        result = _compute_loop_health(
            bill={"mrr_yen": 0, "active_users_30d": 0},
            fb={"total_feedback": 0},
            rl={"success_rate": None, "total_cycles": 0},
        )
        assert result["level"] == "critical"
        assert result["score"] == 0

    def test_compute_loop_health_growing(self):
        """中程度の値 → growing"""
        from image_generation_service.router import _compute_loop_health
        result = _compute_loop_health(
            bill={"mrr_yen": 8000, "active_users_30d": 4},
            fb={"total_feedback": 8},
            rl={"success_rate": 0.8, "total_cycles": 50},
        )
        assert result["level"] in ("growing", "thriving")
        assert result["score"] >= 50

    def test_compute_loop_health_thriving(self):
        """最大値 → thriving"""
        from image_generation_service.router import _compute_loop_health
        result = _compute_loop_health(
            bill={"mrr_yen": 20000, "active_users_30d": 10},
            fb={"total_feedback": 100},
            rl={"success_rate": 1.0, "total_cycles": 200},
        )
        assert result["level"] == "thriving"
        assert result["score"] >= 80


class TestRlBridgeRevenue:
    """rl_bridge に revenue_yen が正しく伝搬されることをテスト"""

    def test_end_image_task_with_revenue_graceful_degrade(self):
        """orchestrator が無い環境では None が返る (crash しない)"""
        from image_generation_service import rl_bridge
        # _init_attempted=True にして再import を防ぎ、orchestrator=None を強制
        saved_attempted = rl_bridge._init_attempted
        saved_orch = rl_bridge._orchestrator
        try:
            rl_bridge._init_attempted = True
            rl_bridge._orchestrator = None
            result = rl_bridge.end_image_task(
                job_id="test-job-1",
                outcome="success",
                quality_overall=8.0,
                cost_yen=0.05,
                revenue_yen=0.50,
            )
            assert result is None  # graceful degrade
        finally:
            rl_bridge._init_attempted = saved_attempted
            rl_bridge._orchestrator = saved_orch

    def test_end_image_task_with_revenue_roi_metadata(self):
        """revenue_yen / cost_yen から ROI が計算されることを確認"""
        from image_generation_service import rl_bridge
        from unittest.mock import MagicMock
        saved_attempted = rl_bridge._init_attempted
        saved_orch = rl_bridge._orchestrator
        try:
            mock_rl = MagicMock()
            mock_rl.end_task.return_value = {"cycle": 1, "ok": True}
            rl_bridge._init_attempted = True
            rl_bridge._orchestrator = mock_rl
            result = rl_bridge.end_image_task(
                job_id="test-roi",
                outcome="success",
                quality_overall=8.0,
                cost_yen=0.05,
                revenue_yen=0.50,
            )
            assert result == {"cycle": 1, "ok": True}
            call_kwargs = mock_rl.end_task.call_args[1]
            assert call_kwargs["metadata"]["revenue_yen"] == 0.50
            assert call_kwargs["metadata"]["cost_yen"] == 0.05
            # ROI = (0.50 - 0.05) / 0.05 = 9.0
            assert call_kwargs["metadata"]["roi"] == 9.0
        finally:
            rl_bridge._init_attempted = saved_attempted
            rl_bridge._orchestrator = saved_orch


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
