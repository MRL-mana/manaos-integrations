"""
Unit tests for scripts/misc/auth_system.py
"""
import sys
from unittest.mock import MagicMock

# ── module-level mocks (must be before any module import) ──────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh.ManaOSErrorHandler = MagicMock(return_value=MagicMock())
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={"api_call": 30.0})
sys.modules.setdefault("manaos_timeout_config", _tc)

# manaos_jwt: provide real-ish signing key (≥ 32 bytes for HS256)
_SIGNING_KEY = "test-signing-key-for-auth-system-testing-extended-32bytes"
_mj = MagicMock()
_mj.JWT_ALGORITHM = "HS256"
_mj.accept_legacy_short_key = MagicMock(return_value=False)
_mj.derive_hs256_signing_key = MagicMock(return_value=_SIGNING_KEY)
_mj.get_or_create_jwt_secret = MagicMock(return_value="test-jwt-secret")
sys.modules.setdefault("manaos_jwt", _mj)

import pytest  # noqa: E402
from scripts.misc.auth_system import AuthSystem, Role, User, APIKey  # noqa: E402


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def auth(tmp_path):
    return AuthSystem(db_path=tmp_path / "test_auth.db")


# ── TestRole ───────────────────────────────────────────────────────────────
class TestRole:
    def test_values(self):
        assert Role.GUEST == "guest"
        assert Role.USER == "user"
        assert Role.ADMIN == "admin"
        assert Role.SUPER_ADMIN == "super_admin"


# ── TestCreateUser ─────────────────────────────────────────────────────────
class TestCreateUser:
    def test_returns_user_object(self, auth):
        user = auth.create_user("alice", "alice@example.com")
        assert isinstance(user, User)

    def test_user_attributes(self, auth):
        user = auth.create_user("bob", "bob@example.com", Role.ADMIN)
        assert user.username == "bob"
        assert user.email == "bob@example.com"
        assert user.role == Role.ADMIN

    def test_default_role_is_user(self, auth):
        user = auth.create_user("carol", "carol@example.com")
        assert user.role == Role.USER

    def test_is_active_by_default(self, auth):
        user = auth.create_user("dave", "dave@example.com")
        assert user.is_active is True

    def test_user_id_generated(self, auth):
        user = auth.create_user("eve", "eve@example.com")
        assert user.user_id != ""
        assert len(user.user_id) > 0


# ── TestGetUser ────────────────────────────────────────────────────────────
class TestGetUser:
    def test_get_existing_user(self, auth):
        created = auth.create_user("frank", "frank@example.com")
        fetched = auth.get_user(created.user_id)
        assert fetched is not None
        assert fetched.username == "frank"

    def test_get_nonexistent_user_returns_none(self, auth):
        result = auth.get_user("nobody")
        assert result is None


# ── TestCreateAndVerifyAPIKey ──────────────────────────────────────────────
class TestCreateAndVerifyAPIKey:
    def test_create_api_key_returns_string(self, auth):
        user = auth.create_user("g", "g@example.com")
        key = auth.create_api_key(user.user_id)
        assert isinstance(key, str)
        assert key.startswith("mana_")

    def test_verify_valid_api_key(self, auth):
        user = auth.create_user("h", "h@example.com")
        key = auth.create_api_key(user.user_id)
        result = auth.verify_api_key(key)
        assert result is not None
        assert isinstance(result, APIKey)
        assert result.user_id == user.user_id

    def test_verify_invalid_api_key_returns_none(self, auth):
        result = auth.verify_api_key("mana_totally_wrong_key")
        assert result is None

    def test_create_api_key_invalid_user_raises(self, auth):
        with pytest.raises(ValueError):
            auth.create_api_key("nonexistent_user")

    def test_api_key_role_inherits_user_role(self, auth):
        user = auth.create_user("i", "i@example.com", Role.ADMIN)
        key = auth.create_api_key(user.user_id)
        verified = auth.verify_api_key(key)
        assert verified.role == Role.ADMIN


# ── TestCheckPermission ────────────────────────────────────────────────────
class TestCheckPermission:
    def test_guest_cannot_access_user_resource(self, auth):
        assert auth.check_permission(Role.GUEST, Role.USER) is False

    def test_user_can_access_user_resource(self, auth):
        assert auth.check_permission(Role.USER, Role.USER) is True

    def test_admin_can_access_user_resource(self, auth):
        assert auth.check_permission(Role.ADMIN, Role.USER) is True

    def test_admin_cannot_access_super_admin(self, auth):
        assert auth.check_permission(Role.ADMIN, Role.SUPER_ADMIN) is False

    def test_super_admin_can_access_everything(self, auth):
        for role in Role:
            assert auth.check_permission(Role.SUPER_ADMIN, role) is True

    def test_user_cannot_access_admin(self, auth):
        assert auth.check_permission(Role.USER, Role.ADMIN) is False


# ── TestCreateAndVerifyToken ───────────────────────────────────────────────
class TestCreateAndVerifyToken:
    def test_create_token_returns_string(self, auth):
        user = auth.create_user("j", "j@example.com")
        token = auth.create_token(user.user_id)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_verify_valid_token(self, auth):
        user = auth.create_user("k", "k@example.com")
        token = auth.create_token(user.user_id)
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == user.user_id

    def test_verify_invalid_token_returns_none(self, auth):
        result = auth.verify_token("not.a.valid.jwt.token")
        assert result is None

    def test_create_token_invalid_user_raises(self, auth):
        with pytest.raises(ValueError):
            auth.create_token("nobody")

    def test_token_contains_role(self, auth):
        user = auth.create_user("l", "l@example.com", Role.ADMIN)
        token = auth.create_token(user.user_id)
        payload = auth.verify_token(token)
        assert payload["role"] == Role.ADMIN.value
