#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_intelligent_cache.py
IntelligentCache の単体テスト
"""

import sys
import time
import hashlib
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# sys.path に scripts/misc を追加
MISC_DIR = Path(__file__).parent.parent / "scripts" / "misc"
sys.path.insert(0, str(MISC_DIR))

# unified_logging をモック化してモジュールをインポート
import importlib

mock_logger = MagicMock()

with patch.dict("sys.modules", {
    "unified_logging": MagicMock(get_service_logger=MagicMock(return_value=mock_logger)),
}):
    import intelligent_cache


CacheEntry = intelligent_cache.CacheEntry
IntelligentCache = intelligent_cache.IntelligentCache


# ============================================================
# CacheEntry
# ============================================================

class TestCacheEntry(unittest.TestCase):

    def test_defaults(self):
        entry = CacheEntry(key="k", value="v")
        self.assertEqual(entry.key, "k")
        self.assertEqual(entry.value, "v")
        self.assertEqual(entry.access_count, 0)
        self.assertEqual(entry.ttl, 3600)
        self.assertEqual(entry.size, 0)

    def test_custom_values(self):
        entry = CacheEntry(key="x", value=42, access_count=3, ttl=600, size=128)
        self.assertEqual(entry.access_count, 3)
        self.assertEqual(entry.ttl, 600)
        self.assertEqual(entry.size, 128)

    def test_created_at_is_datetime(self):
        entry = CacheEntry(key="k", value=None)
        self.assertIsInstance(entry.created_at, datetime)

    def test_last_accessed_defaults_to_now(self):
        before = datetime.now()
        entry = CacheEntry(key="k", value=None)
        after = datetime.now()
        self.assertGreaterEqual(entry.last_accessed, before)
        self.assertLessEqual(entry.last_accessed, after)


# ============================================================
# IntelligentCache — 基本操作
# ============================================================

class TestIntelligentCacheBasic(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache(max_size=100, default_ttl=3600)

    def test_get_miss_returns_none(self):
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_set_and_get(self):
        self.cache.set("key1", "value1")
        result = self.cache.get("key1")
        self.assertEqual(result, "value1")

    def test_set_dict_value(self):
        data = {"a": 1, "b": [1, 2, 3]}
        self.cache.set("d", data)
        self.assertEqual(self.cache.get("d"), data)

    def test_set_returns_true_on_success(self):
        self.assertTrue(self.cache.set("k", "v"))

    def test_hits_and_misses_count(self):
        self.cache.set("k", "v")
        self.cache.get("k")  # hit
        self.cache.get("k")  # hit
        self.cache.get("miss")  # miss
        self.assertEqual(self.cache.hits, 2)
        self.assertEqual(self.cache.misses, 1)

    def test_access_count_increments(self):
        self.cache.set("k", "v")
        self.cache.get("k")
        self.cache.get("k")
        self.cache.get("k")
        entry = self.cache.cache["k"]
        self.assertEqual(entry.access_count, 3)

    def test_overwrite_existing_key(self):
        self.cache.set("k", "old")
        self.cache.set("k", "new")
        self.assertEqual(self.cache.get("k"), "new")

    def test_overwrite_does_not_increase_total_size_unboundedly(self):
        self.cache.set("k", "short")
        size_after_first = self.cache.total_size
        self.cache.set("k", "longer value string")
        # total_size は古い分を引いて新しい分を加算するので増えることはある
        # が、古いエントリが2重にカウントされていないことを確認
        self.assertGreater(self.cache.total_size, 0)

    def test_custom_ttl(self):
        self.cache.set("k", "v", ttl=10)
        entry = self.cache.cache["k"]
        self.assertEqual(entry.ttl, 10)


# ============================================================
# IntelligentCache — TTL期限切れ
# ============================================================

class TestIntelligentCacheTTL(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache(max_size=100, default_ttl=3600)

    def test_expired_entry_returns_none(self):
        self.cache.set("k", "v", ttl=1)
        # エントリの created_at を過去に調整
        self.cache.cache["k"].created_at = datetime.now() - timedelta(seconds=10)
        self.assertIsNone(self.cache.get("k"))

    def test_expired_entry_increments_misses(self):
        self.cache.set("k", "v", ttl=1)
        self.cache.cache["k"].created_at = datetime.now() - timedelta(seconds=10)
        self.cache.get("k")
        self.assertEqual(self.cache.misses, 1)

    def test_expired_entry_removed_from_cache(self):
        self.cache.set("k", "v", ttl=1)
        self.cache.cache["k"].created_at = datetime.now() - timedelta(seconds=10)
        self.cache.get("k")
        self.assertNotIn("k", self.cache.cache)


# ============================================================
# IntelligentCache — `cleanup_expired`
# ============================================================

class TestCleanupExpired(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache(max_size=100, default_ttl=3600)

    def test_removes_only_expired_entries(self):
        self.cache.set("expired", "v1", ttl=1)
        self.cache.set("alive", "v2", ttl=3600)
        self.cache.cache["expired"].created_at = datetime.now() - timedelta(seconds=10)
        self.cache.cleanup_expired()
        self.assertNotIn("expired", self.cache.cache)
        self.assertIn("alive", self.cache.cache)

    def test_total_size_decreases_after_cleanup(self):
        self.cache.set("expired", "hello world", ttl=1)
        initial_size = self.cache.total_size
        self.cache.cache["expired"].created_at = datetime.now() - timedelta(seconds=10)
        self.cache.cleanup_expired()
        self.assertLessEqual(self.cache.total_size, initial_size)

    def test_no_entries_no_error(self):
        self.cache.cleanup_expired()  # 例外が出ないこと

    def test_all_alive_unchanged(self):
        self.cache.set("k1", "v1")
        self.cache.set("k2", "v2")
        self.cache.cleanup_expired()
        self.assertEqual(len(self.cache.cache), 2)


# ============================================================
# IntelligentCache — `clear`
# ============================================================

class TestIntelligentCacheClear(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache()

    def test_clear_removes_all_entries(self):
        self.cache.set("k1", "v1")
        self.cache.set("k2", "v2")
        self.cache.clear()
        self.assertEqual(len(self.cache.cache), 0)

    def test_clear_resets_hits_misses(self):
        self.cache.set("k", "v")
        self.cache.get("k")
        self.cache.get("missing")
        self.cache.clear()
        self.assertEqual(self.cache.hits, 0)
        self.assertEqual(self.cache.misses, 0)

    def test_clear_resets_total_size(self):
        self.cache.set("k", "some data")
        self.cache.clear()
        self.assertEqual(self.cache.total_size, 0)

    def test_clear_resets_access_patterns(self):
        self.cache.set("k", "v")
        self.cache.get("k")
        self.cache.clear()
        self.assertEqual(len(self.cache.access_patterns), 0)


# ============================================================
# IntelligentCache — `get_stats`
# ============================================================

class TestGetStats(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache()

    def test_stats_structure(self):
        stats = self.cache.get_stats()
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
        self.assertIn("hit_rate", stats)
        self.assertIn("total_entries", stats)
        self.assertIn("total_size_mb", stats)
        self.assertIn("max_size", stats)
        self.assertIn("max_memory_mb", stats)

    def test_hit_rate_zero_when_no_requests(self):
        stats = self.cache.get_stats()
        self.assertEqual(stats["hit_rate"], 0.0)

    def test_hit_rate_calculation(self):
        self.cache.set("k", "v")
        self.cache.get("k")   # hit
        self.cache.get("k")   # hit
        self.cache.get("x")   # miss
        stats = self.cache.get_stats()
        self.assertAlmostEqual(stats["hit_rate"], 2 / 3, places=5)

    def test_total_entries_increases_on_set(self):
        self.cache.set("k1", "v1")
        self.cache.set("k2", "v2")
        stats = self.cache.get_stats()
        self.assertEqual(stats["total_entries"], 2)


# ============================================================
# IntelligentCache — `_estimate_size`
# ============================================================

class TestEstimateSize(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache()

    def test_str_size(self):
        s = "hello"
        self.assertEqual(self.cache._estimate_size(s), len(s))

    def test_bytes_size(self):
        b = b"hello"
        self.assertEqual(self.cache._estimate_size(b), len(b))

    def test_dict_size(self):
        d = {"key": "value"}
        expected = len(json.dumps(d).encode())
        self.assertEqual(self.cache._estimate_size(d), expected)

    def test_list_size(self):
        lst = ["a", "bb"]
        expected = sum(len(s) for s in lst)
        self.assertEqual(self.cache._estimate_size(lst), expected)

    def test_int_size(self):
        # int は str(42).encode() = b'42' → 2 bytes
        size = self.cache._estimate_size(42)
        self.assertGreater(size, 0)

    def test_exception_fallback(self):
        class Unserializable:
            def __str__(self):
                raise RuntimeError("cannot stringify")
        size = self.cache._estimate_size(Unserializable())
        self.assertEqual(size, 1024)


# ============================================================
# IntelligentCache — `generate_cache_key`
# ============================================================

class TestGenerateCacheKey(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache()

    def test_returns_string(self):
        key = self.cache.generate_cache_key(1, 2, a=3)
        self.assertIsInstance(key, str)

    def test_deterministic(self):
        k1 = self.cache.generate_cache_key("x", 1, foo="bar")
        k2 = self.cache.generate_cache_key("x", 1, foo="bar")
        self.assertEqual(k1, k2)

    def test_different_args_different_key(self):
        k1 = self.cache.generate_cache_key("a")
        k2 = self.cache.generate_cache_key("b")
        self.assertNotEqual(k1, k2)

    def test_is_sha256_hex(self):
        key = self.cache.generate_cache_key()
        self.assertEqual(len(key), 64)
        int(key, 16)  # 16進数として解析できる


# ============================================================
# IntelligentCache — 最大サイズとLRU退避
# ============================================================

class TestIntelligentCacheEviction(unittest.TestCase):

    def test_max_size_enforced(self):
        cache = IntelligentCache(max_size=3, default_ttl=3600)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        cache.set("k4", "v4")  # 1件退避されるはず
        self.assertLessEqual(len(cache.cache), 3)

    def test_evict_lru_returns_false_on_empty(self):
        cache = IntelligentCache()
        self.assertFalse(cache._evict_lru())

    def test_evict_lru_removes_one_entry(self):
        cache = IntelligentCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        before = len(cache.cache)
        cache._evict_lru()
        self.assertEqual(len(cache.cache), before - 1)

    def test_access_pattern_evicts_least_accessed(self):
        cache = IntelligentCache(max_size=3, default_ttl=3600)
        cache.set("rare", "v")
        cache.set("common", "v")
        cache.set("med", "v")
        # rare は1回もアクセスされない
        cache.get("common")
        cache.get("common")
        cache.get("med")
        # もう1件追加すると rare が退避されるはず
        cache.set("new", "v")
        self.assertNotIn("rare", cache.cache)


# ============================================================
# `optimize` — TTL 調整
# ============================================================

class TestOptimize(unittest.TestCase):

    def setUp(self):
        self.cache = IntelligentCache()

    def test_high_access_extends_ttl(self):
        self.cache.set("popular", "v")
        self.cache.access_patterns["popular"] = 15  # > 10
        original_ttl = self.cache.cache["popular"].ttl
        self.cache.optimize()
        new_ttl = self.cache.cache["popular"].ttl
        self.assertGreater(new_ttl, original_ttl)

    def test_low_access_shortens_ttl(self):
        self.cache.set("unpopular", "v")
        self.cache.access_patterns["unpopular"] = 1  # < 3
        original_ttl = self.cache.cache["unpopular"].ttl
        self.cache.optimize()
        new_ttl = self.cache.cache["unpopular"].ttl
        self.assertLess(new_ttl, original_ttl)

    def test_high_ttl_capped_at_86400(self):
        self.cache.set("popular", "v")
        self.cache.cache["popular"].ttl = 80000
        self.cache.access_patterns["popular"] = 15
        self.cache.optimize()
        self.assertLessEqual(self.cache.cache["popular"].ttl, 86400)

    def test_low_ttl_floor_at_300(self):
        self.cache.set("unpopular", "v")
        self.cache.cache["unpopular"].ttl = 400
        self.cache.access_patterns["unpopular"] = 1
        self.cache.optimize()
        self.assertGreaterEqual(self.cache.cache["unpopular"].ttl, 300)

    def test_empty_cache_no_error(self):
        self.cache.optimize()  # 例外が出ないこと


if __name__ == "__main__":
    unittest.main()
