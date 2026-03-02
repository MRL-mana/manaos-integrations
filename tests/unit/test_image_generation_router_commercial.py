"""
Unit Tests — image_generation_service.router (commercial endpoints)
===================================================================
/signup, /payment/*, /dashboard の回帰テスト。
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """各テストで新しい billing DB を使用"""
    import image_generation_service.billing as billing_mod
    import image_generation_service.router as router_mod

    db_path = tmp_path / "router_commercial_billing.db"
    billing_mod._DB_PATH = db_path
    os.environ["BILLING_DB_PATH"] = str(db_path)

    # シングルトンをリセット
    router_mod._billing = None

    yield db_path


@pytest.fixture
def client():
    from image_generation_service.router import create_app

    app = create_app()
    return TestClient(app)


class TestCommercialRouter:

    def test_signup_success(self, client):
        response = client.post(
            "/api/v1/images/signup",
            json={
                "email": "user@example.com",
                "plan": "pro",
                "label": "test-user",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["email"] == "user@example.com"
        assert data["plan"] == "pro"
        assert data["api_key"].startswith("img_")

    def test_signup_invalid_email(self, client):
        response = client.post(
            "/api/v1/images/signup",
            json={
                "email": "invalid-email",
                "plan": "free",
            },
        )
        assert response.status_code == 400
        assert "Invalid email" in response.json()["detail"]

    def test_signup_invalid_plan(self, client):
        response = client.post(
            "/api/v1/images/signup",
            json={
                "email": "user@example.com",
                "plan": "gold",
            },
        )
        assert response.status_code == 400
        assert "Invalid plan" in response.json()["detail"]

    def test_payment_stripe_stub(self, client):
        response = client.post(
            "/api/v1/images/payment/stripe",
            params={"plan": "pro", "user_id": "u123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "stripe"
        assert data["status"] == "stub"
        assert "checkout.stripe.com" in data["payment_url"]

    def test_payment_komoju_stub(self, client):
        response = client.post(
            "/api/v1/images/payment/komoju",
            params={"plan": "enterprise", "user_id": "u456"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "komoju"
        assert data["status"] == "stub"
        assert "checkout.komoju.com" in data["payment_url"]

    def test_dashboard_includes_commercial_metrics(self, client):
        response = client.get(
            "/api/v1/images/dashboard",
            headers={"X-API-Key": "default"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "mrr_yen" in data
        assert "daily_sales_yen" in data
        assert "active_users_30d" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
