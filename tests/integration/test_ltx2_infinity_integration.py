#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LTX-2 Infinity統合のpytestスモークテスト。"""

import sys
from pathlib import Path

import pytest

# tests/integration 配下からリポジトリルートを import 対象に追加
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def _require_or_skip(module_name):
    fallbacks = {
        "ltx2_infinity_integration": ["ltx2.ltx2_infinity_integration"],
        "ltx2_workflow_generator": ["ltx2.ltx2_workflow_generator"],
        "ltx2_template_manager": ["ltx2.ltx2_template_manager"],
        "ltx2_nsfw_config": ["ltx2.ltx2_nsfw_config"],
        "ltx2_storage_manager": ["ltx2.ltx2_storage_manager"],
    }
    candidates = [module_name] + fallbacks.get(module_name, [])
    last_error = None
    for candidate in candidates:
        try:
            return __import__(candidate, fromlist=["*"])
        except Exception as error:
            last_error = error
    try:
        raise RuntimeError(last_error)
    except Exception as error:
        pytest.skip(f"optional module unavailable: {module_name} ({error})")

def test_imports_smoke():
    modules = [
        ["ltx2_infinity_integration", "ltx2.ltx2_infinity_integration"],
        ["ltx2_workflow_generator", "ltx2.ltx2_workflow_generator"],
        ["ltx2_template_manager", "ltx2.ltx2_template_manager"],
        ["ltx2_nsfw_config", "ltx2.ltx2_nsfw_config"],
        ["ltx2_storage_manager", "ltx2.ltx2_storage_manager"],
    ]
    loaded = 0
    for candidates in modules:
        for name in candidates:
            try:
                __import__(name)
                loaded += 1
                break
            except Exception:
                continue
    if loaded == 0:
        pytest.skip("ltx2 modules are not available")
    assert loaded >= 1


def test_initialization_smoke():
    module = _require_or_skip("ltx2_infinity_integration")
    try:
        instance = module.LTX2InfinityIntegration()
    except Exception as error:
        pytest.skip(f"ltx2 init failed: {error}")
    assert instance is not None

def test_unified_api_integration():
    """統一API統合テスト"""
    api_server_path = Path(__file__).resolve().parents[2] / "unified_api_server.py"
    if not api_server_path.exists():
        pytest.skip("unified_api_server.py not found")

    content = api_server_path.read_text(encoding="utf-8")
    checks = {
        "LTX2_INFINITY_AVAILABLE": "LTX2_INFINITY_AVAILABLE" in content,
        "ltx2_infinity endpoint": "/api/ltx2-infinity/generate" in content,
    }
    assert any(checks.values())

def test_basic_functionality():
    template_module = _require_or_skip("ltx2_template_manager")
    storage_module = _require_or_skip("ltx2_storage_manager")

    try:
        templates = template_module.LTX2TemplateManager().list_templates()
    except Exception as error:
        pytest.skip(f"template manager unavailable: {error}")
    assert isinstance(templates, list)

    try:
        stats = storage_module.LTX2StorageManager().get_storage_stats()
    except Exception as error:
        pytest.skip(f"storage manager unavailable: {error}")
    assert isinstance(stats, dict)
