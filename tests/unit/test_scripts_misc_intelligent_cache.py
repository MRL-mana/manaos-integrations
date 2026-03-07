"""
Unit tests for scripts/misc/intelligent_cache.py
"""
import sys
import time
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from collections import OrderedDict
import pytest

# Mock unified_logging before import
sys.modules.setdefault("unified_logging", MagicMock(
    get_service_logger=MagicMock(return_value=MagicMock())
))

sys.path.insert(0, "scripts/misc")
from intelligent_cache import (
    CacheEntry,
    IntelligentCache,
    get_cache,
    cached,
)


# ── CacheEntry ──────────────────────────────────────────────────────────────

class TestCacheEntry:
    def test_default_fields(self):
        entry = CacheEntry(key="k", value=42)
        assert entry.key == "k"
        assert entry.value == 42
        assert entry.access_count == 0
        assert entry.ttl == 3600
        assert entry.size == 0

    def test_custom_ttl(self):
        entry = CacheEntry(key="k", value="v", ttl=60)
        assert entry.ttl == 60

    def test_timestamps_set(self):
        before = datetime.now()
        entry = CacheEntry(key="k", value=1)
        after = datetime.now()
        assert before <= entry.created_at <= after
        assert before <= entry.last_accessed <= after


# ── IntelligentCache.get / set ───────────────────────────────────────────────

class TestIntelligentCacheGetSet:
    def setup_method(self):
        self.cache = IntelligentCache(max_size=10, default_ttl=3600)

    def test_miss_returns_none(self):
        assert self.cache.get("missing") is None

    def test_set_and_get(self):
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

    def test_set_returns_true(self):
        result = self.cache.set("k", 123)
        assert result is True

    def test_hit_increments_access_count(self):
        self.cache.set("k", "v")
        self.cache.get("k")
        self.cache.get("k")
        entry = self.cache.cache["k"]
        assert entry.access_count == 2

    def test_miss_increments_misses(self):
        self.cache.get("nope")
        assert self.cache.misses == 1

    def test_hit_increments_hits(self):
        self.cache.set("k", "v")
        self.cache.get("k")
        assert self.cache.hits == 1

    def test_overwrite_key(self):
        self.cache.set("k", "old")
        self.cache.set("k", "new")
        assert self.cache.get("k") == "new"

    def test_custom_ttl_on_set(self):
        self.cache.set("k", "v", ttl=999)
        entry = self.cache.cache["k"]
        assert entry.ttl == 999

    def test_expired_entry_returns_none(self):
        entry = CacheEntry(key="k", value="v", ttl=0)
        entry.created_at = datetime.now() - timedelta(seconds=1)
        self.cache.cache["k"] = entry
        result = self.cache.get("k")
        assert result is None

    def test_expired_entry_removed_from_cache(self):
        entry = CacheEntry(key="k", value="v", ttl=0)
        entry.created_at = datetime.now() - timedelta(seconds=1)
        self.cache.cache["k"] = entry
        self.cache.get("k")
        assert "k" not in self.cache.cache

    def test_multiple_keys(self):
        for i in range(5):
            self.cache.set(f"k{i}", i * 10)
        for i in range(5):
            assert self.cache.get(f"k{i}") == i * 10

    def test_access_patterns_updated(self):
        self.cache.set("k", "v")
        self.cache.get("k")
        assert self.cache.access_patterns.get("k", 0) >= 1


# ── IntelligentCache.clear / cleanup_expired ────────────────────────────────

class TestIntelligentCacheClear:
    def setup_method(self):
        self.cache = IntelligentCache()

    def test_clear_removes_all_entries(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.clear()
        assert len(self.cache.cache) == 0

    def test_clear_resets_stats(self):
        self.cache.set("a", 1)
        self.cache.get("a")
        self.cache.clear()
        assert self.cache.hits == 0
        assert self.cache.misses == 0

    def test_clear_resets_total_size(self):
        self.cache.set("a", "data")
        self.cache.clear()
        assert self.cache.total_size == 0

    def test_cleanup_expired_removes_old_entries(self):
        # Insert an already-expired entry
        entry = CacheEntry(key="old", value="v", ttl=1)
        entry.created_at = datetime.now() - timedelta(seconds=10)
        self.cache.cache["old"] = entry
        self.cache.cleanup_expired()
        assert "old" not in self.cache.cache

    def test_cleanup_expired_keeps_valid_entries(self):
        self.cache.set("fresh", "v", ttl=3600)
        self.cache.cleanup_expired()
        assert "fresh" in self.cache.cache


# ── IntelligentCache.get_stats ───────────────────────────────────────────────

class TestIntelligentCacheStats:
    def setup_method(self):
        self.cache = IntelligentCache()

    def test_stats_returns_dict(self):
        stats = self.cache.get_stats()
        assert isinstance(stats, dict)

    def test_zero_hit_rate_on_fresh_cache(self):
        stats = self.cache.get_stats()
        assert stats["hit_rate"] == 0.0

    def test_hit_rate_calculation(self):
        self.cache.set("k", "v")
        self.cache.get("k")   # hit
        self.cache.get("nope")  # miss
        stats = self.cache.get_stats()
        assert stats["hit_rate"] == pytest.approx(0.5)

    def test_stats_contains_expected_keys(self):
        stats = self.cache.get_stats()
        for k in ("hits", "misses", "hit_rate", "total_entries", "total_size_mb"):
            assert k in stats

    def test_total_entries_count(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        assert self.cache.get_stats()["total_entries"] == 2


# ── IntelligentCache.generate_cache_key ─────────────────────────────────────

class TestGenerateCacheKey:
    def setup_method(self):
        self.cache = IntelligentCache()

    def test_returns_string(self):
        key = self.cache.generate_cache_key("a", 1)
        assert isinstance(key, str)

    def test_same_args_same_key(self):
        k1 = self.cache.generate_cache_key("a", b=2)
        k2 = self.cache.generate_cache_key("a", b=2)
        assert k1 == k2

    def test_different_args_different_key(self):
        k1 = self.cache.generate_cache_key("a")
        k2 = self.cache.generate_cache_key("b")
        assert k1 != k2

    def test_key_is_sha256_hex(self):
        key = self.cache.generate_cache_key()
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


# ── IntelligentCache._evict_lru / max_size ──────────────────────────────────

class TestIntelligentCacheEviction:
    def test_evict_when_over_max_size(self):
        cache = IntelligentCache(max_size=3, default_ttl=3600)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")
        cache.set("d", "4")  # should evict one
        assert len(cache.cache) <= 3

    def test_evict_lru_returns_false_on_empty(self):
        cache = IntelligentCache()
        result = cache._evict_lru()
        assert result is False

    def test_evict_lru_reduces_total_size(self):
        cache = IntelligentCache()
        cache.set("k", "hello")
        size_before = cache.total_size
        cache._evict_lru()
        assert cache.total_size < size_before


# ── IntelligentCache._estimate_size ─────────────────────────────────────────

class TestEstimateSize:
    def setup_method(self):
        self.cache = IntelligentCache()

    def test_string_size(self):
        size = self.cache._estimate_size("hello")
        assert size == 5

    def test_bytes_size(self):
        size = self.cache._estimate_size(b"abc")
        assert size == 3

    def test_dict_size(self):
        size = self.cache._estimate_size({"a": 1})
        assert size > 0

    def test_list_size(self):
        size = self.cache._estimate_size(["x", "y"])
        assert size > 0

    def test_unknown_type_fallback(self):
        size = self.cache._estimate_size(12345)
        assert size > 0


# ── cached decorator ─────────────────────────────────────────────────────────

class TestCachedDecorator:
    def test_decorator_caches_result(self):
        call_count = [0]

        @cached(ttl=60)
        def expensive():
            call_count[0] += 1
            return 42

        r1 = expensive()
        r2 = expensive()
        assert r1 == 42
        assert r2 == 42
        assert call_count[0] == 1  # called only once

    def test_decorator_exposes_cache(self):
        @cached(ttl=60)
        def fn():
            return 1

        assert hasattr(fn, "cache")
        assert isinstance(fn.cache, IntelligentCache)

    def test_decorator_different_args_different_cache_keys(self):
        call_count = [0]

        @cached(ttl=60)
        def multiply(x):
            call_count[0] += 1
            return x * 2

        multiply(3)
        multiply(5)
        assert call_count[0] == 2

    def test_custom_key_func(self):
        call_count = [0]

        @cached(ttl=60, key_func=lambda x: "fixed_key")
        def fn(x):
            call_count[0] += 1
            return x

        fn(1)
        fn(2)  # same key → cached
        assert call_count[0] == 1


# ── get_cache singleton ──────────────────────────────────────────────────────

class TestGetCache:
    def test_returns_intelligent_cache(self):
        import intelligent_cache as ic_mod
        ic_mod._cache = None  # reset singleton
        c = get_cache()
        assert isinstance(c, IntelligentCache)

    def test_same_instance_on_second_call(self):
        import intelligent_cache as ic_mod
        ic_mod._cache = None
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_reset_allows_new_instance(self):
        import intelligent_cache as ic_mod
        ic_mod._cache = None
        c1 = get_cache()
        ic_mod._cache = None
        c2 = get_cache()
        assert c1 is not c2
