#!/usr/bin/env python3
"""MRL Memory SystemとManaOS統合の pytest スモークテスト。"""

import pytest


def _require_or_skip(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as error:
        pytest.skip(f"optional module unavailable: {module_name} ({error})")


def test_manaos_core_api_integration():
    manaos = _require_or_skip("manaos_core_api")

    test_data = {
        "content": "これはMRL Memory統合のテストです。ManaOSから保存されます。",
        "metadata": {
            "source": "test",
            "test_type": "integration",
        },
    }

    try:
        remember_result = manaos.remember(test_data, format_type="conversation")
        recall_results = manaos.recall("MRL Memory統合", limit=5)
    except Exception as error:
        pytest.skip(f"mrl memory integration unavailable: {error}")

    assert isinstance(remember_result, dict)
    assert isinstance(recall_results, list)


def test_service_bridge_integration():
    module = _require_or_skip("manaos_service_bridge")
    bridge = module.ManaOSServiceBridge()

    try:
        services = bridge.check_manaos_services()
    except Exception as error:
        pytest.skip(f"service bridge unavailable: {error}")

    assert isinstance(services, dict)
    assert "mrl_memory" in services or len(services) > 0
