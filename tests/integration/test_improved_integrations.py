#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改善版統合クラスのテスト。"""

import importlib
import os

import pytest


def test_base_integration_importable():
    module = importlib.import_module("base_integration")
    assert hasattr(module, "BaseIntegration")


@pytest.mark.parametrize(
    "module_name,class_name,ctor_kwargs",
    [
        ("comfyui_integration_improved", "ComfyUIIntegration", {}),
        (
            "google_drive_integration_improved",
            "GoogleDriveIntegration",
            {},
        ),
        (
            "obsidian_integration_improved",
            "ObsidianIntegration",
            {
                "vault_path": os.getenv(
                    "OBSIDIAN_VAULT_PATH",
                    "C:/Users/mana4/Documents/Obsidian Vault",
                )
            },
        ),
        ("mem0_integration_improved", "Mem0Integration", {}),
        ("civitai_integration_improved", "CivitAIIntegration", {}),
        ("github_integration_improved", "GitHubIntegration", {}),
    ],
)
def test_improved_integration_smoke(module_name, class_name, ctor_kwargs):
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        pytest.skip(f"{module_name} unavailable: {exc}")

    integration_class = getattr(module, class_name, None)
    if integration_class is None:
        pytest.skip(f"{class_name} not found in {module_name}")

    instance = integration_class(**ctor_kwargs)
    assert hasattr(instance, "is_available")
    assert hasattr(instance, "get_status")
    status = instance.get_status()
    assert isinstance(status, dict)






















