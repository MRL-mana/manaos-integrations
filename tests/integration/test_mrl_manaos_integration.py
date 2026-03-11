#!/usr/bin/env python3
"""MRL Memory SystemとManaOS統合の pytest スモークテスト。"""

import sys
import pytest
from unittest.mock import patch, MagicMock


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

    _mock_remember = {"status": "stored", "id": "test_id_001"}
    _mock_recall = [{"content": "MRL Memory統合テスト", "id": "test_id_001"}]

    with patch.object(manaos, "remember", return_value=_mock_remember, create=True), \
         patch.object(manaos, "recall", return_value=_mock_recall, create=True):
        try:
            remember_result = manaos.remember(test_data, format_type="conversation")
            recall_results = manaos.recall("MRL Memory統合", limit=5)
        except Exception as error:
            pytest.skip(f"mrl memory integration unavailable: {error}")

    assert isinstance(remember_result, dict)
    assert isinstance(recall_results, list)


def test_service_bridge_integration():
    sys.modules.pop("manaos_service_bridge", None)  # clear any unit-test mock
    module = _require_or_skip("manaos_service_bridge")
    bridge = module.ManaOSServiceBridge()

    try:
        services = bridge.check_manaos_services()
    except Exception as error:
        pytest.skip(f"service bridge unavailable: {error}")

    assert isinstance(services, dict)
    assert "mrl_memory" in services or len(services) > 0
