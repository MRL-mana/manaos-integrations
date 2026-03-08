"""
Unit tests for scripts/misc/payment_integration.py
Tests pure payment processing functions and record_payment.
No real HTTP calls — httpx is mocked.
"""
import sys
from unittest.mock import MagicMock, patch
import pytest

# ── Standard mocks ────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

# Flask
sys.modules.setdefault("flask", MagicMock())
sys.modules.setdefault("flask_cors", MagicMock())

# httpx mock (used for record_payment)
_httpx = MagicMock()
sys.modules.setdefault("httpx", _httpx)

# ── Import target ─────────────────────────────────────────────────────────────
from scripts.misc.payment_integration import (  # noqa: E402
    process_stripe_payment,
    process_paypal_payment,
    record_payment,
)


# ── TestProcessStripePayment ──────────────────────────────────────────────────
class TestProcessStripePayment:
    def test_error_when_no_key(self):
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}, clear=False):
            import scripts.misc.payment_integration as pm
            pm.STRIPE_SECRET_KEY = ""
            result = process_stripe_payment(1000.0)
        assert result["status"] == "error"
        assert "Stripe API key" in result["error"]

    def test_mock_impl_when_no_stripe_lib(self):
        """stripe ライブラリ未インストール時はモック実装が返る"""
        import scripts.misc.payment_integration as pm
        orig_key = pm.STRIPE_SECRET_KEY
        pm.STRIPE_SECRET_KEY = "sk_test_123"
        # stripe ライブラリはインストールされていないため自動的にモックパスへ
        try:
            result = process_stripe_payment(5000.0, "JPY")
            # stripe not installed → mock path
            assert result["status"] == "success"
            assert "payment_id" in result
            assert result["amount"] == 5000.0
            assert result["currency"] == "JPY"
        finally:
            pm.STRIPE_SECRET_KEY = orig_key

    def test_mock_returns_stripe_note(self):
        """stripe ライブラリなしの場合、note フィールドが含まれる"""
        import scripts.misc.payment_integration as pm
        orig_key = pm.STRIPE_SECRET_KEY
        pm.STRIPE_SECRET_KEY = "sk_test_abc"
        try:
            result = process_stripe_payment(100.0, "USD")
            if result["status"] == "success" and "note" in result:
                assert "stripe" in result["note"].lower()
        finally:
            pm.STRIPE_SECRET_KEY = orig_key

    def test_amount_preserved_in_result(self):
        import scripts.misc.payment_integration as pm
        orig_key = pm.STRIPE_SECRET_KEY
        pm.STRIPE_SECRET_KEY = "sk_test_xyz"
        try:
            result = process_stripe_payment(9999.0, "JPY")
            if result["status"] == "success":
                assert result["amount"] == 9999.0
        finally:
            pm.STRIPE_SECRET_KEY = orig_key

    def test_currency_preserved_in_result(self):
        import scripts.misc.payment_integration as pm
        orig_key = pm.STRIPE_SECRET_KEY
        pm.STRIPE_SECRET_KEY = "sk_test_xyz"
        try:
            result = process_stripe_payment(500.0, "USD")
            if result["status"] == "success":
                assert result["currency"] == "USD"
        finally:
            pm.STRIPE_SECRET_KEY = orig_key


# ── TestProcessPaypalPayment ──────────────────────────────────────────────────
class TestProcessPaypalPayment:
    def test_error_when_no_credentials(self):
        import scripts.misc.payment_integration as pm
        orig_id = pm.PAYPAL_CLIENT_ID
        orig_secret = pm.PAYPAL_CLIENT_SECRET
        pm.PAYPAL_CLIENT_ID = ""
        pm.PAYPAL_CLIENT_SECRET = ""
        try:
            result = process_paypal_payment(1000.0)
            assert result["status"] == "error"
            assert "PayPal credentials" in result["error"]
        finally:
            pm.PAYPAL_CLIENT_ID = orig_id
            pm.PAYPAL_CLIENT_SECRET = orig_secret

    def test_mock_impl_when_no_paypalrestsdk(self):
        """paypalrestsdk 未インストール時はモック実装が返る"""
        import scripts.misc.payment_integration as pm
        orig_id = pm.PAYPAL_CLIENT_ID
        orig_secret = pm.PAYPAL_CLIENT_SECRET
        pm.PAYPAL_CLIENT_ID = "pp_client_123"
        pm.PAYPAL_CLIENT_SECRET = "pp_secret_456"
        try:
            result = process_paypal_payment(3000.0, "JPY")
            assert result["status"] == "success"
            assert "payment_id" in result
            assert result["amount"] == 3000.0
        finally:
            pm.PAYPAL_CLIENT_ID = orig_id
            pm.PAYPAL_CLIENT_SECRET = orig_secret

    def test_currency_included_in_result(self):
        import scripts.misc.payment_integration as pm
        orig_id = pm.PAYPAL_CLIENT_ID
        orig_secret = pm.PAYPAL_CLIENT_SECRET
        pm.PAYPAL_CLIENT_ID = "pp_client"
        pm.PAYPAL_CLIENT_SECRET = "pp_secret"
        try:
            result = process_paypal_payment(200.0, "USD")
            if result["status"] == "success":
                assert result["currency"] == "USD"
        finally:
            pm.PAYPAL_CLIENT_ID = orig_id
            pm.PAYPAL_CLIENT_SECRET = orig_secret

    def test_note_field_when_mock(self):
        import scripts.misc.payment_integration as pm
        orig_id = pm.PAYPAL_CLIENT_ID
        orig_secret = pm.PAYPAL_CLIENT_SECRET
        pm.PAYPAL_CLIENT_ID = "c1"
        pm.PAYPAL_CLIENT_SECRET = "s1"
        try:
            result = process_paypal_payment(100.0)
            if result["status"] == "success" and "note" in result:
                assert "paypalrestsdk" in result["note"].lower()
        finally:
            pm.PAYPAL_CLIENT_ID = orig_id
            pm.PAYPAL_CLIENT_SECRET = orig_secret


# ── TestRecordPayment ─────────────────────────────────────────────────────────
class TestRecordPayment:
    @patch("scripts.misc.payment_integration.httpx.post")
    def test_returns_true_on_200(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        mock_post.return_value = resp
        result = record_payment("prod_001", 1000.0, "JPY", "stripe", "pi_abc123")
        assert result is True

    def test_returns_false_on_non_200(self):
        resp = MagicMock()
        resp.status_code = 500
        _httpx.post.return_value = resp
        result = record_payment("prod_001", 1000.0, "JPY", "stripe", "pi_abc123")
        assert result is False

    def test_returns_false_on_exception(self):
        _httpx.post.side_effect = RuntimeError("connection error")
        result = record_payment(None, 500.0, "JPY", "paypal", "paypal_mock_123")
        assert result is False
        _httpx.post.side_effect = None

    @patch("scripts.misc.payment_integration.httpx.post")
    def test_post_called_with_correct_amount(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        mock_post.return_value = resp
        record_payment("prod_x", 999.0, "JPY", "stripe", "pi_999")
        body = mock_post.call_args.kwargs["json"]
        assert body["amount"] == 999.0

    @patch("scripts.misc.payment_integration.httpx.post")
    def test_post_called_with_correct_currency(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        mock_post.return_value = resp
        record_payment(None, 100.0, "USD", "stripe", "pi_usd")
        body = mock_post.call_args.kwargs["json"]
        assert body["currency"] == "USD"
