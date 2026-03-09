"""
Unit tests for scripts/misc/redis_cache.py
REDIS_AVAILABLE=False パスでテスト（redis不要）
"""
import json
import sys
from unittest.mock import MagicMock

# ── external module mocks (before import) ─────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh_mod = MagicMock()
_mock_error = MagicMock()
_mock_error.message = "mock error"
_eh_mod.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=_mock_error)
))
_eh_mod.ErrorCategory = MagicMock()
_eh_mod.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh_mod)

import pytest  # noqa: E402
from scripts.misc.redis_cache import RedisCache, redis_cache  # noqa: E402


# ── helpers ────────────────────────────────────────────────────────────────
def make_cache():
    """redis_client=None の RedisCache（REDIS_AVAILABLE=False 相当）"""
    rc = RedisCache.__new__(RedisCache)
    rc.default_ttl_seconds = 3600
    rc.redis_client = None
    return rc


def make_cache_with_client():
    """redis_client をモックで差し込んだ RedisCache"""
    rc = RedisCache.__new__(RedisCache)
    rc.default_ttl_seconds = 3600
    rc.redis_client = MagicMock()
    return rc


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def cache():
    return make_cache()


@pytest.fixture
def mock_cache():
    return make_cache_with_client()


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_no_redis_client_when_unavailable(self):
        import scripts.misc.redis_cache as rc_mod
        if rc_mod.REDIS_AVAILABLE:
            pytest.skip("Redis is available in this environment")
        rc = RedisCache()
        assert rc.redis_client is None

    def test_default_ttl_stored(self):
        rc = RedisCache(default_ttl_seconds=120)
        assert rc.default_ttl_seconds == 120

    def test_default_ttl_default_value(self):
        rc = RedisCache()
        assert rc.default_ttl_seconds == 3600


# ── TestGenerateKey ────────────────────────────────────────────────────────
class TestGenerateKey:
    def test_starts_with_prefix(self, cache):
        key = cache._generate_key("mytype")
        assert key.startswith("manaos:cache:")

    def test_same_args_same_key(self, cache):
        k1 = cache._generate_key("mytype", "arg1")
        k2 = cache._generate_key("mytype", "arg1")
        assert k1 == k2

    def test_different_type_different_key(self, cache):
        k1 = cache._generate_key("type_a", "foo")
        k2 = cache._generate_key("type_b", "foo")
        assert k1 != k2

    def test_different_args_different_key(self, cache):
        k1 = cache._generate_key("mytype", "arg1")
        k2 = cache._generate_key("mytype", "arg2")
        assert k1 != k2

    def test_kwargs_affect_key(self, cache):
        k1 = cache._generate_key("mytype")
        k2 = cache._generate_key("mytype", user_id=42)
        assert k1 != k2


# ── TestGet ────────────────────────────────────────────────────────────────
class TestGet:
    def test_returns_none_when_no_client(self, cache):
        assert cache.get("mytype", "arg") is None

    def test_returns_value_from_redis(self, mock_cache):
        mock_cache.redis_client.get.return_value = json.dumps({"answer": 42})
        result = mock_cache.get("mytype", "arg")
        assert result == {"answer": 42}

    def test_returns_none_on_cache_miss(self, mock_cache):
        mock_cache.redis_client.get.return_value = None
        result = mock_cache.get("mytype", "arg")
        assert result is None

    def test_returns_none_on_exception(self, mock_cache):
        mock_cache.redis_client.get.side_effect = Exception("Redis error")
        result = mock_cache.get("mytype", "arg")
        assert result is None

    def test_calls_redis_get_with_correct_key(self, mock_cache):
        mock_cache.redis_client.get.return_value = None
        expected_key = mock_cache._generate_key("t1", "a")
        mock_cache.get("t1", "a")
        mock_cache.redis_client.get.assert_called_once_with(expected_key)


# ── TestSet ────────────────────────────────────────────────────────────────
class TestSet:
    def test_no_op_when_no_client(self, cache):
        # Should not raise
        cache.set("mytype", {"data": 1}, "arg")

    def test_calls_setex(self, mock_cache):
        mock_cache.set("mytype", "value", "arg")
        mock_cache.redis_client.setex.assert_called_once()

    def test_uses_default_ttl(self, mock_cache):
        mock_cache.set("t", "v", "arg")
        _, call_args, _ = mock_cache.redis_client.setex.mock_calls[0]
        assert call_args[1] == mock_cache.default_ttl_seconds

    def test_uses_custom_ttl(self, mock_cache):
        mock_cache.set("t", "v", "arg", ttl_seconds=60)
        _, call_args, _ = mock_cache.redis_client.setex.mock_calls[0]
        assert call_args[1] == 60

    def test_silently_handles_exception(self, mock_cache):
        mock_cache.redis_client.setex.side_effect = Exception("write error")
        mock_cache.set("t", "v", "arg")  # Should not raise


# ── TestInvalidate ─────────────────────────────────────────────────────────
class TestInvalidate:
    def test_no_op_when_no_client(self, cache):
        cache.invalidate("mytype", "arg")  # Should not raise

    def test_calls_delete(self, mock_cache):
        mock_cache.invalidate("mytype", "arg")
        mock_cache.redis_client.delete.assert_called_once()

    def test_silently_handles_exception(self, mock_cache):
        mock_cache.redis_client.delete.side_effect = Exception("del error")
        mock_cache.invalidate("mytype", "arg")  # Should not raise


# ── TestInvalidatePattern ──────────────────────────────────────────────────
class TestInvalidatePattern:
    def test_no_op_when_no_client(self, cache):
        cache.invalidate_pattern("manaos:cache:*")  # Should not raise

    def test_calls_keys_then_delete(self, mock_cache):
        mock_cache.redis_client.keys.return_value = ["k1", "k2"]
        mock_cache.invalidate_pattern("manaos:cache:*")
        mock_cache.redis_client.delete.assert_called_once_with("k1", "k2")

    def test_no_delete_when_no_keys(self, mock_cache):
        mock_cache.redis_client.keys.return_value = []
        mock_cache.invalidate_pattern("manaos:cache:*")
        mock_cache.redis_client.delete.assert_not_called()

    def test_silently_handles_exception(self, mock_cache):
        mock_cache.redis_client.keys.side_effect = Exception("keys error")
        mock_cache.invalidate_pattern("manaos:cache:*")  # Should not raise


# ── TestCacheDecorator (sync) ──────────────────────────────────────────────
class TestCacheDecoratorSync:
    def test_cache_miss_calls_function(self, mock_cache):
        mock_cache.redis_client.get.return_value = None
        calls = []

        @mock_cache.cache_decorator("t")
        def fn(x):
            calls.append(x)
            return x * 2

        result = fn(5)
        assert result == 10
        assert calls == [5]

    def test_cache_hit_skips_function(self, mock_cache):
        mock_cache.redis_client.get.return_value = json.dumps(99)
        calls = []

        @mock_cache.cache_decorator("t")
        def fn(x):
            calls.append(x)
            return x * 2

        result = fn(5)
        assert result == 99
        assert calls == []

    def test_cache_miss_saves_result(self, mock_cache):
        mock_cache.redis_client.get.return_value = None

        @mock_cache.cache_decorator("t")
        def fn(x):
            return x * 3

        fn(4)
        mock_cache.redis_client.setex.assert_called_once()


# ── TestGlobalInstance ─────────────────────────────────────────────────────
class TestGlobalInstance:
    def test_global_instance_exists(self):
        assert redis_cache is not None

    def test_global_instance_is_redis_cache(self):
        assert isinstance(redis_cache, RedisCache)

    def test_global_instance_has_default_ttl(self):
        assert redis_cache.default_ttl_seconds == 3600
