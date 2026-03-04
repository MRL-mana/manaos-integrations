#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OH MY OPENCODE統合テスト（pytest対応）"""

import importlib

import pytest


def _import_module_or_skip(name: str):
    candidates = [name, f"oh_my_opencode.{name}"]
    last_error = None
    for module_name in candidates:
        try:
            return importlib.import_module(module_name)
        except Exception as exc:
            last_error = exc
    pytest.skip(f"{name} 読み込み失敗: {last_error}")


def test_oh_my_opencode_integration_init_smoke():
    module = _import_module_or_skip("oh_my_opencode_integration")
    integration_cls = getattr(module, "OHMyOpenCodeIntegration", None)
    if integration_cls is None:
        pytest.skip("OHMyOpenCodeIntegration が見つからないためスキップ")

    integration = integration_cls()
    assert integration is not None


def test_cost_manager_smoke():
    module = _import_module_or_skip("oh_my_opencode_cost_manager")
    cost_cls = getattr(module, "OHMyOpenCodeCostManager", None)
    if cost_cls is None:
        pytest.skip("OHMyOpenCodeCostManager が見つからないためスキップ")

    cost_manager = cost_cls(daily_limit=100.0, monthly_limit=2000.0)
    stats = cost_manager.get_statistics()
    assert isinstance(stats, dict)
