"""
tests/unit/test_scripts_misc_health_check_optimizer.py

scripts/misc/health_check_optimizer.py の単体テスト
- HealthCheckCache: get/set/clear/TTL
- HealthCheckOptimizer: cached_health_check デコレーター / lightweight_check
- get_health_check_optimizer / init_health_check_optimizer
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))

from health_check_optimizer import (
    HealthCheckCache,
    HealthCheckOptimizer,
    get_health_check_optimizer,
    init_health_check_optimizer,
)


# ===========================
# HealthCheckCache
# ===========================

class TestHealthCheckCache:
    def test_miss_returns_none(self):
        cache = HealthCheckCache(ttl_seconds=5)
        assert cache.get("missing") is None

    def test_set_and_get(self):
        cache = HealthCheckCache(ttl_seconds=5)
        cache.set("k", {"status": "ok"})
        assert cache.get("k") == {"status": "ok"}

    def test_ttl_expire(self):
        cache = HealthCheckCache(ttl_seconds=0)
        cache.set("k", {"status": "ok"})
        # 0秒 TTL → 即期限切れ
        time.sleep(0.01)
        assert cache.get("k") is None

    def test_clear_specific_key(self):
        cache = HealthCheckCache(ttl_seconds=30)
        cache.set("a", {"v": 1})
        cache.set("b", {"v": 2})
        cache.clear("a")
        assert cache.get("a") is None
        assert cache.get("b") == {"v": 2}

    def test_clear_all(self):
        cache = HealthCheckCache(ttl_seconds=30)
        cache.set("a", {"v": 1})
        cache.set("b", {"v": 2})
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite_value(self):
        cache = HealthCheckCache(ttl_seconds=30)
        cache.set("k", {"status": "old"})
        cache.set("k", {"status": "new"})
        assert cache.get("k") == {"status": "new"}

    def test_multiple_keys_independent(self):
        cache = HealthCheckCache(ttl_seconds=30)
        cache.set("x", {"v": 10})
        cache.set("y", {"v": 20})
        assert cache.get("x") == {"v": 10}
        assert cache.get("y") == {"v": 20}

    def test_default_ttl_5(self):
        cache = HealthCheckCache()
        assert cache.ttl_seconds == 5

    def test_custom_ttl_stored(self):
        cache = HealthCheckCache(ttl_seconds=60)
        assert cache.ttl_seconds == 60

    def test_clear_nonexistent_key_no_error(self):
        cache = HealthCheckCache()
        # should not raise
        cache.clear("nonexistent")


# ===========================
# HealthCheckOptimizer
# ===========================

class TestHealthCheckOptimizer:
    def test_default_timeout_ms(self):
        opt = HealthCheckOptimizer()
        assert opt.timeout_ms == 100

    def test_custom_timeout_ms(self):
        opt = HealthCheckOptimizer(timeout_ms=500)
        assert opt.timeout_ms == 500

    def test_has_cache(self):
        opt = HealthCheckOptimizer()
        assert isinstance(opt.cache, HealthCheckCache)

    # --- cached_health_check デコレーター ---

    def test_cached_check_returns_result(self):
        opt = HealthCheckOptimizer()
        call_count = [0]

        @opt.cached_health_check("test_key", ttl_seconds=30)
        def check():
            call_count[0] += 1
            return {"status": "healthy"}

        result = check()
        assert result == {"status": "healthy"}
        assert call_count[0] == 1

    def test_cached_check_uses_cache_on_second_call(self):
        opt = HealthCheckOptimizer()
        call_count = [0]

        @opt.cached_health_check("test_key2", ttl_seconds=30)
        def check():
            call_count[0] += 1
            return {"status": "healthy", "count": call_count[0]}

        check()
        check()
        # 2回目はキャッシュから → 実際の関数は1回しか呼ばれない
        assert call_count[0] == 1

    def test_cached_check_exception_returns_unhealthy(self):
        opt = HealthCheckOptimizer()

        @opt.cached_health_check("err_key", ttl_seconds=30)
        def check():
            raise RuntimeError("boom")

        result = check()
        assert result["status"] == "unhealthy"
        assert "error" in result

    def test_cached_check_error_message_truncated(self):
        opt = HealthCheckOptimizer()

        @opt.cached_health_check("err_key2", ttl_seconds=30)
        def check():
            raise ValueError("x" * 300)

        result = check()
        assert len(result["error"]) <= 100

    # --- lightweight_check デコレーター ---

    def test_lightweight_check_returns_result(self):
        opt = HealthCheckOptimizer(timeout_ms=500)

        @opt.lightweight_check()
        def check():
            return {"status": "ok"}

        assert check() == {"status": "ok"}

    def test_lightweight_check_exception_returns_unavailable(self):
        opt = HealthCheckOptimizer()

        @opt.lightweight_check()
        def check():
            raise ConnectionError("unreachable")

        result = check()
        assert result["status"] == "unavailable"
        assert "error" in result

    def test_lightweight_check_error_truncated(self):
        opt = HealthCheckOptimizer()

        @opt.lightweight_check(timeout_ms=200)
        def check():
            raise RuntimeError("y" * 300)

        result = check()
        assert len(result["error"]) <= 100

    def test_lightweight_check_custom_timeout_ms(self):
        opt = HealthCheckOptimizer(timeout_ms=100)
        # Just ensure decorator accepts timeout_ms kwarg
        @opt.lightweight_check(timeout_ms=500)
        def check():
            return {"status": "ok"}

        assert check()["status"] == "ok"


# ===========================
# グローバルファクトリ
# ===========================

class TestGlobalOptimizer:
    def test_get_returns_optimizer(self):
        opt = get_health_check_optimizer()
        assert isinstance(opt, HealthCheckOptimizer)

    def test_get_returns_same_instance(self):
        a = get_health_check_optimizer()
        b = get_health_check_optimizer()
        assert a is b

    def test_init_replaces_global(self):
        init_health_check_optimizer(timeout_ms=250)
        opt = get_health_check_optimizer()
        assert opt.timeout_ms == 250

    def test_init_default_timeout(self):
        init_health_check_optimizer()
        opt = get_health_check_optimizer()
        assert opt.timeout_ms == 100
