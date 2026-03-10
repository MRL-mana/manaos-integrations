"""
Unit tests for scripts/misc/manaos_security.py
Tests APIKeyManager, RateLimiter, InputValidator, and JWTManager.__init__
"""
import sys
from unittest.mock import MagicMock, patch

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

# ── manaos_jwt mock ───────────────────────────────────────────────────────────
_mj = MagicMock()
_mj.accept_legacy_short_key.return_value = False
_mj.derive_hs256_signing_key.return_value = b"x" * 32
_mj.get_or_create_jwt_secret.return_value = "a" * 32
_orig_mj = sys.modules.pop("manaos_jwt", None)
sys.modules["manaos_jwt"] = _mj

# ── Flask mock ────────────────────────────────────────────────────────────────
sys.modules.setdefault("flask", MagicMock())
sys.modules.setdefault("flask_cors", MagicMock())

# ── Import target ─────────────────────────────────────────────────────────────
sys.modules.pop("scripts.misc.manaos_security", None)
from scripts.misc.manaos_security import (  # noqa: E402
    APIKeyManager,
    RateLimiter,
    InputValidator,
    JWTManager,
)
# Restore real manaos_jwt; security module already captured _mj's function references
if _orig_mj is not None:
    sys.modules["manaos_jwt"] = _orig_mj
else:
    sys.modules.pop("manaos_jwt", None)


# ── TestAPIKeyManager ─────────────────────────────────────────────────────────
class TestAPIKeyManager:
    def test_empty_env_gives_empty_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            mgr = APIKeyManager()
            assert mgr.api_keys == {}

    def test_key_loaded_from_env(self):
        with patch.dict("os.environ", {"MANAOS_API_KEY": "secret123"}):
            mgr = APIKeyManager()
            assert "default" in mgr.api_keys
            assert mgr.api_keys["default"]["key"] == "secret123"

    def test_validate_api_key_valid(self):
        with patch.dict("os.environ", {"MANAOS_API_KEY": "mykey"}):
            mgr = APIKeyManager()
            assert mgr.validate_api_key("mykey") is True

    def test_validate_api_key_invalid(self):
        with patch.dict("os.environ", {"MANAOS_API_KEY": "mykey"}):
            mgr = APIKeyManager()
            assert mgr.validate_api_key("wrong") is False

    def test_validate_api_key_empty_store(self):
        with patch.dict("os.environ", {}, clear=True):
            mgr = APIKeyManager()
            assert mgr.validate_api_key("anything") is False

    def test_get_permissions_valid_key(self):
        with patch.dict("os.environ", {"MANAOS_API_KEY": "mykey"}):
            mgr = APIKeyManager()
            perms = mgr.get_permissions("mykey")
            assert "read" in perms
            assert "write" in perms

    def test_get_permissions_invalid_key_returns_empty(self):
        with patch.dict("os.environ", {"MANAOS_API_KEY": "mykey"}):
            mgr = APIKeyManager()
            assert mgr.get_permissions("wrong") == []

    def test_key_has_created_at(self):
        with patch.dict("os.environ", {"MANAOS_API_KEY": "mykey"}):
            mgr = APIKeyManager()
            assert "created_at" in mgr.api_keys["default"]


# ── TestRateLimiter ───────────────────────────────────────────────────────────
class TestRateLimiter:
    def test_first_request_allowed(self):
        rl = RateLimiter()
        assert rl.is_allowed("user1") is True

    def test_multiple_requests_within_limit(self):
        rl = RateLimiter()
        for _ in range(10):
            assert rl.is_allowed("user2") is True

    def test_default_limit_enforcement(self):
        rl = RateLimiter()
        for _ in range(100):
            rl.is_allowed("user3")
        # 101st request should be denied
        assert rl.is_allowed("user3") is False

    def test_strict_limit(self):
        rl = RateLimiter()
        for _ in range(20):
            rl.is_allowed("user4", "strict")
        assert rl.is_allowed("user4", "strict") is False

    def test_independent_identifiers(self):
        rl = RateLimiter()
        for _ in range(100):
            rl.is_allowed("userA")
        # Different identifier should still be allowed
        assert rl.is_allowed("userB") is True

    def test_get_remaining_full(self):
        rl = RateLimiter()
        assert rl.get_remaining("fresh_user") == 100

    def test_get_remaining_after_some_requests(self):
        rl = RateLimiter()
        for _ in range(10):
            rl.is_allowed("partial_user")
        assert rl.get_remaining("partial_user") == 90

    def test_get_remaining_after_exhaustion(self):
        rl = RateLimiter()
        for _ in range(100):
            rl.is_allowed("full_user")
        assert rl.get_remaining("full_user") == 0

    def test_get_remaining_unknown_type_uses_default(self):
        rl = RateLimiter()
        # Unknown limit_type falls back to 'default' (100 requests)
        assert rl.get_remaining("someone", "nonexistent_type") == 100

    def test_strict_get_remaining_full(self):
        rl = RateLimiter()
        assert rl.get_remaining("user_strict", "strict") == 20


# ── TestInputValidator ────────────────────────────────────────────────────────
class TestInputValidator:
    def test_valid_text(self):
        ok, err = InputValidator.validate_text("Hello world")
        assert ok is True
        assert err is None

    def test_too_short(self):
        ok, err = InputValidator.validate_text("", min_length=1)
        assert ok is False
        assert err is not None

    def test_too_long(self):
        ok, err = InputValidator.validate_text("x" * 10001, max_length=10000)
        assert ok is False
        assert err is not None

    def test_non_string_rejected(self):
        ok, err = InputValidator.validate_text(123)  # type: ignore
        assert ok is False

    def test_dangerous_drop_table(self):
        ok, err = InputValidator.validate_text("DROP TABLE users")
        assert ok is False

    def test_dangerous_union_select(self):
        ok, err = InputValidator.validate_text("UNION SELECT * FROM foo")
        assert ok is False

    def test_dangerous_comment_injection(self):
        ok, err = InputValidator.validate_text("'; --")
        assert ok is False

    def test_dangerous_xp_prefix(self):
        ok, err = InputValidator.validate_text("exec xp_cmdshell")
        assert ok is False

    def test_safe_text_passes(self):
        ok, err = InputValidator.validate_text("This is a normal sentence.")
        assert ok is True
        assert err is None

    def test_validate_mode_auto(self):
        ok, err = InputValidator.validate_mode("auto")
        assert ok is True
        assert err is None

    def test_validate_mode_manual(self):
        ok, err = InputValidator.validate_mode("manual")
        assert ok is True

    def test_validate_mode_interactive(self):
        ok, err = InputValidator.validate_mode("interactive")
        assert ok is True

    def test_validate_mode_invalid(self):
        ok, err = InputValidator.validate_mode("robot")
        assert ok is False
        assert err is not None

    def test_validate_json_valid(self):
        data = {"name": "Alice", "age": 30}
        schema = {"name": str, "age": int}
        ok, err = InputValidator.validate_json(data, schema)
        assert ok is True
        assert err is None

    def test_validate_json_missing_field(self):
        ok, err = InputValidator.validate_json({"name": "Alice"}, {"name": str, "age": int})
        assert ok is False
        assert "age" in err  # type: ignore

    def test_validate_json_wrong_type(self):
        ok, err = InputValidator.validate_json({"name": 42}, {"name": str})
        assert ok is False
        assert err is not None

    def test_validate_json_empty_schema(self):
        ok, err = InputValidator.validate_json({"x": 1}, {})
        assert ok is True
        assert err is None


# ── TestJWTManager ────────────────────────────────────────────────────────────
class TestJWTManager:
    def test_init_with_explicit_key(self):
        mgr = JWTManager(secret_key="a" * 32)
        assert mgr.secret_key == "a" * 32
        assert mgr._algorithm == "HS256"

    def test_init_without_key_calls_mock(self):
        _mj.get_or_create_jwt_secret.reset_mock()
        JWTManager()
        _mj.get_or_create_jwt_secret.assert_called_once()

    def test_signing_key_set(self):
        mgr = JWTManager(secret_key="a" * 32)
        # derive_hs256_signing_key is called in __init__
        assert mgr._signing_key is not None
