#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ManaOS 統合機能の pytest スモークテスト。"""

import os
import asyncio

import httpx
import pytest

try:
    from manaos_integrations._paths import LEARNING_SYSTEM_PORT, METRICS_COLLECTOR_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import LEARNING_SYSTEM_PORT, METRICS_COLLECTOR_PORT  # type: ignore
    except Exception:  # pragma: no cover
        METRICS_COLLECTOR_PORT = int(os.getenv("METRICS_COLLECTOR_PORT", "5127"))
        LEARNING_SYSTEM_PORT = int(os.getenv("LEARNING_SYSTEM_PORT", "5126"))


def _require_or_skip(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as error:
        pytest.skip(f"optional module unavailable: {module_name} ({error})")


def test_unified_orchestrator_init():
    module = _require_or_skip("unified_orchestrator")
    orchestrator = module.UnifiedOrchestrator()
    assert orchestrator is not None


def test_metrics_collector():
    module = _require_or_skip("metrics_collector")
    collector = module.MetricsCollector()
    collector.record(name="test.response_time", value=1.23, tags={"service": "TestService"})
    metrics = collector.get_metrics(name="test.response_time")
    assert isinstance(metrics, list)


def test_intelligent_retry():
    module = _require_or_skip("intelligent_retry")
    retry_system = module.IntelligentRetry()

    call_count = 0

    async def success_func():
        nonlocal call_count
        call_count += 1
        return {"status": "success"}

    result = asyncio.run(retry_system.execute_with_retry(success_func))
    assert getattr(result, "success", False) is True
    assert call_count == 1


def test_response_cache():
    module = _require_or_skip("response_cache")
    cache = module.ResponseCache()
    cache.set(
        cache_type="test",
        value={"result": "test_value"},
        test_key="test_value",
        ttl_seconds=60,
    )
    cached_value = cache.get(cache_type="test", test_key="test_value")
    assert isinstance(cached_value, dict)
    assert cached_value.get("result") == "test_value"


def test_service_health_if_reachable():
    services = {
        "Metrics Collector": os.getenv(
            "METRICS_COLLECTOR_URL",
            f"http://127.0.0.1:{METRICS_COLLECTOR_PORT}",
        )
        + "/health",
        "Learning System API": os.getenv(
            "LEARNING_SYSTEM_URL",
            f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}",
        )
        + "/health",
    }

    reachable = False
    for url in services.values():
        try:
            response = httpx.get(url, timeout=5.0)
        except Exception:
            continue
        reachable = True
        assert response.status_code < 500

    if not reachable:
        return

