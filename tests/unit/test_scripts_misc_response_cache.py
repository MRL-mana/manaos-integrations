"""
Unit tests for scripts/misc/response_cache.py
"""
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# ── external module mocks ──────────────────────────────────────────────────
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

import pytest  # noqa: E402, F401
from scripts.misc.response_cache import (  # noqa: E402
    CacheEntry,
    ResponseCache,
    response_cache,
    cache,
)


# ── Helpers ───────────────────────────────────────────────────────────────
def make_cache(tmp_path):
    return ResponseCache(db_path=tmp_path / "cache.db")


# ── CacheEntry ────────────────────────────────────────────────────────────
class TestCacheEntry:
    def test_create(self):
        entry = CacheEntry(
            cache_key="k1",
            cache_type="llm",
            value="hello",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=1)).isoformat(),
        )
        assert entry.cache_key == "k1"
        assert entry.hit_count == 0
        assert entry.metadata == {}

    def test_custom_metadata(self):
        entry = CacheEntry(
            cache_key="k2",
            cache_type="intent",
            value=42,
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=1)).isoformat(),
            metadata={"source": "test"},
        )
        assert entry.metadata["source"] == "test"


# ── ResponseCache._generate_key ───────────────────────────────────────────
class TestGenerateKey:
    def test_returns_hex_string(self, tmp_path):
        rc = make_cache(tmp_path)
        key = rc._generate_key("llm", "prompt1")
        assert isinstance(key, str)
        assert len(key) == 64  # sha256 hex

    def test_same_args_same_key(self, tmp_path):
        rc = make_cache(tmp_path)
        k1 = rc._generate_key("llm", "abc", x=1)
        k2 = rc._generate_key("llm", "abc", x=1)
        assert k1 == k2

    def test_different_type_different_key(self, tmp_path):
        rc = make_cache(tmp_path)
        k1 = rc._generate_key("llm", "abc")
        k2 = rc._generate_key("intent", "abc")
        assert k1 != k2

    def test_different_args_different_key(self, tmp_path):
        rc = make_cache(tmp_path)
        k1 = rc._generate_key("llm", "a")
        k2 = rc._generate_key("llm", "b")
        assert k1 != k2


# ── ResponseCache.set / get ───────────────────────────────────────────────
class TestSetGet:
    def test_set_and_get_returns_value(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "response1", "prompt1")
        result = rc.get("llm", "prompt1")
        assert result == "response1"

    def test_get_miss_returns_none(self, tmp_path):
        rc = make_cache(tmp_path)
        result = rc.get("llm", "nonexistent_prompt")
        assert result is None

    def test_set_complex_value(self, tmp_path):
        rc = make_cache(tmp_path)
        val = {"key": "val", "nested": [1, 2, 3]}
        rc.set("plan", val, "input1")
        result = rc.get("plan", "input1")
        assert result == val

    def test_expired_entry_returns_none(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "stale", "prompt_stale", ttl_seconds=-1)  # already expired
        # Memory cache: check expiry
        result = rc.get("llm", "prompt_stale")
        assert result is None

    def test_hit_count_increments(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "v", "p")
        rc.get("llm", "p")  # first access via memory → hit_count += 1
        key = rc._generate_key("llm", "p")
        assert rc.memory_cache[key].hit_count == 1

    def test_overwrite_with_new_set(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "first", "pk")
        rc.set("llm", "second", "pk")
        result = rc.get("llm", "pk")
        assert result == "second"

    def test_different_cache_types_independent(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "llm_val", "q")
        rc.set("intent", "intent_val", "q")
        assert rc.get("llm", "q") == "llm_val"
        assert rc.get("intent", "q") == "intent_val"

    def test_memory_cache_populated(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "x", "arg1")
        assert len(rc.memory_cache) == 1

    def test_set_with_ttl_seconds(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "ttl_val", "p_ttl", ttl_seconds=3600)
        assert rc.get("llm", "p_ttl") == "ttl_val"


# ── ResponseCache.invalidate ──────────────────────────────────────────────
class TestInvalidate:
    def test_invalidate_removes_from_memory(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "v", "p")
        rc.invalidate("llm", "p")
        key = rc._generate_key("llm", "p")
        assert key not in rc.memory_cache

    def test_invalidate_makes_get_return_none(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "v", "p")
        rc.invalidate("llm", "p")
        assert rc.get("llm", "p") is None

    def test_invalidate_nonexistent_noop(self, tmp_path):
        rc = make_cache(tmp_path)
        # Should not raise
        rc.invalidate("llm", "does_not_exist")

    def test_invalidate_only_removes_target(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "v1", "p1")
        rc.set("llm", "v2", "p2")
        rc.invalidate("llm", "p1")
        assert rc.get("llm", "p2") == "v2"


# ── ResponseCache.cleanup_expired ────────────────────────────────────────
class TestCleanupExpired:
    def test_removes_expired_entries(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "old", "p_old", ttl_seconds=-1)
        rc.cleanup_expired()
        # At least memory entries cleaned
        key = rc._generate_key("llm", "p_old")
        assert key not in rc.memory_cache

    def test_keeps_valid_entries(self, tmp_path):
        rc = make_cache(tmp_path)
        rc.set("llm", "new", "p_new", ttl_seconds=3600)
        rc.cleanup_expired()
        assert rc.get("llm", "p_new") == "new"

    def test_returns_int(self, tmp_path):
        rc = make_cache(tmp_path)
        result = rc.cleanup_expired()
        assert isinstance(result, int)


# ── ResponseCache.cache_decorator ────────────────────────────────────────
class TestCacheDecorator:
    def test_caches_result(self, tmp_path):
        rc = make_cache(tmp_path)
        call_count = [0]

        @rc.cache_decorator("llm_dec", ttl_seconds=3600)
        def expensive(arg):
            call_count[0] += 1
            return f"result:{arg}"

        r1 = expensive("x")
        r2 = expensive("x")
        assert r1 == r2 == "result:x"
        assert call_count[0] == 1  # called only once

    def test_different_args_different_cache(self, tmp_path):
        rc = make_cache(tmp_path)
        call_count = [0]

        @rc.cache_decorator("plan_dec", ttl_seconds=3600)
        def fn(arg):
            call_count[0] += 1
            return arg * 2

        fn("a")
        fn("b")
        assert call_count[0] == 2

    def test_async_caching(self, tmp_path):
        import asyncio
        rc = make_cache(tmp_path)
        call_count = [0]

        @rc.cache_decorator("async_dec", ttl_seconds=3600)
        async def async_fn(arg):
            call_count[0] += 1
            return f"async:{arg}"

        r1 = asyncio.run(async_fn("z"))
        r2 = asyncio.run(async_fn("z"))
        assert r1 == r2 == "async:z"
        assert call_count[0] == 1


# ── ResponseCache init ────────────────────────────────────────────────────
class TestResponseCacheInit:
    def test_default_ttl(self, tmp_path):
        rc = make_cache(tmp_path)
        assert rc.default_ttl_seconds == 3600

    def test_custom_ttl(self, tmp_path):
        rc = ResponseCache(db_path=tmp_path / "c.db", default_ttl_seconds=7200)
        assert rc.default_ttl_seconds == 7200

    def test_memory_cache_empty_on_init(self, tmp_path):
        rc = make_cache(tmp_path)
        assert rc.memory_cache == {}

    def test_db_file_created(self, tmp_path):
        db = tmp_path / "cache.db"
        ResponseCache(db_path=db)
        assert db.exists()


# ── Global instance ───────────────────────────────────────────────────────
class TestGlobalInstance:
    def test_response_cache_is_instance(self):
        assert isinstance(response_cache, ResponseCache)

    def test_cache_is_callable(self):
        assert callable(cache)
