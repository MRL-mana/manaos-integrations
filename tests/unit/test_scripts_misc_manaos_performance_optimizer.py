"""Tests for scripts/misc/manaos_performance_optimizer.py"""
import sys
import types
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from pathlib import Path
from datetime import datetime

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_stubs(monkeypatch):
    for name in ("flask", "flask_cors", "manaos_logger", "manaos_error_handler",
                 "manaos_async_client", "unified_cache_system",
                 "database_connection_pool", "http_session_pool", "config_cache"):
        if name not in sys.modules:
            mod = types.ModuleType(name)
            monkeypatch.setitem(sys.modules, name, mod)

    # flask
    flask_mod = types.ModuleType("flask")
    flask_mod.Flask = MagicMock(return_value=MagicMock())
    flask_mod.jsonify = MagicMock(side_effect=lambda x: x)
    flask_mod.request = MagicMock()
    monkeypatch.setitem(sys.modules, "flask", flask_mod)
    monkeypatch.setitem(sys.modules, "flask_cors", types.ModuleType("flask_cors"))
    sys.modules["flask_cors"].CORS = MagicMock()

    # logger
    log_mod = types.ModuleType("manaos_logger")
    log_mod.get_logger = MagicMock(return_value=MagicMock())
    log_mod.get_service_logger = MagicMock(return_value=MagicMock())
    monkeypatch.setitem(sys.modules, "manaos_logger", log_mod)

    # error_handler
    eh_mod = types.ModuleType("manaos_error_handler")
    eh = MagicMock()
    eh.handle_exception = MagicMock(return_value=MagicMock(user_message="err", message="err"))
    eh_mod.ManaOSErrorHandler = MagicMock(return_value=eh)
    eh_mod.ErrorCategory = MagicMock()
    eh_mod.ErrorSeverity = MagicMock()
    monkeypatch.setitem(sys.modules, "manaos_error_handler", eh_mod)

    # async client
    async_client = AsyncMock()
    async_client.check_all_services = AsyncMock(return_value={"all_healthy": True})
    async_client.get_stats = MagicMock(return_value={})
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=False)
    async_mod = types.ModuleType("manaos_async_client")
    async_mod.AsyncUnifiedAPIClient = MagicMock(return_value=async_client)
    monkeypatch.setitem(sys.modules, "manaos_async_client", async_mod)

    # cache / pool / config
    cache = MagicMock()
    cache.get_stats.return_value = {"hits": 10, "misses": 1}
    cache_mod = types.ModuleType("unified_cache_system")
    cache_mod.get_unified_cache = MagicMock(return_value=cache)
    monkeypatch.setitem(sys.modules, "unified_cache_system", cache_mod)

    pool = MagicMock()
    pool.get_stats.return_value = {"connections": 3}
    db_mod = types.ModuleType("database_connection_pool")
    db_mod.get_pool = MagicMock(return_value=pool)
    monkeypatch.setitem(sys.modules, "database_connection_pool", db_mod)

    http_pool = MagicMock()
    http_pool.get_stats.return_value = {"active": 2}
    http_mod = types.ModuleType("http_session_pool")
    http_mod.get_http_session_pool = MagicMock(return_value=http_pool)
    monkeypatch.setitem(sys.modules, "http_session_pool", http_mod)

    cfg_cache = MagicMock()
    cfg_cache.get_stats.return_value = {"entries": 5}
    cfg_mod = types.ModuleType("config_cache")
    cfg_mod.get_config_cache = MagicMock(return_value=cfg_cache)
    monkeypatch.setitem(sys.modules, "config_cache", cfg_mod)

    return cache, http_pool, cfg_cache, async_client


def _prep(monkeypatch):
    sys.modules.pop("manaos_performance_optimizer", None)
    cache, http_pool, cfg_cache, async_client = _make_stubs(monkeypatch)
    monkeypatch.syspath_prepend(str(_MISC))
    import manaos_performance_optimizer as m
    return m, cache, http_pool, cfg_cache, async_client


class TestManaosPerformanceOptimizerImport:
    def test_imports(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        assert hasattr(m, "PerformanceOptimizer")

    def test_flask_app_created(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        assert m.app is not None

    def test_instantiation(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        assert obj.optimization_history == []
        assert obj.optimization_rules == []


class TestGetCacheStats:
    def test_returns_stats(self, monkeypatch):
        m, cache, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        stats = obj.get_cache_stats()
        assert isinstance(stats, dict)


class TestGetHttpPoolStats:
    def test_returns_stats(self, monkeypatch):
        m, _, http_pool, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        stats = obj.get_http_pool_stats()
        assert isinstance(stats, dict)


class TestGetAllStats:
    def test_has_all_keys(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        stats = obj.get_all_stats()
        assert "cache" in stats
        assert "http_pool" in stats
        assert "config_cache" in stats
        assert "timestamp" in stats


class TestOptimizeCache:
    def test_returns_success(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        result = obj.optimize_cache()
        assert result["status"] == "success"

    def test_has_stats_before_and_after(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        result = obj.optimize_cache()
        assert "stats_before" in result
        assert "stats_after" in result


class TestOptimizeAll:
    def test_returns_dict_with_timestamp(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        result = obj.optimize_all()
        assert isinstance(result, dict)
        assert "timestamp" in result


class TestOptimizeAllServicesHealthCheck:
    def test_returns_dict(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        result = asyncio.run(obj.optimize_all_services_health_check())
        assert isinstance(result, dict)

    def test_status_success(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        result = asyncio.run(obj.optimize_all_services_health_check())
        assert result.get("status") == "success"


class TestGetDatabasePoolStats:
    def test_returns_stats_on_success(self, monkeypatch):
        m, *_ = _prep(monkeypatch)
        obj = m.PerformanceOptimizer()
        stats = obj.get_database_pool_stats("/test.db")
        assert isinstance(stats, dict)
