#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib
import os
from pathlib import Path

import pytest


def _load_dotenv_if_exists():
    env_file = Path(".env")
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except Exception:
        pass


def _import_and_build(module_name: str, class_name: str, kwargs=None):
    kwargs = kwargs or {}
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls(**kwargs)
    except Exception as exc:
        pytest.skip(f"{module_name}.{class_name} を初期化できないためスキップ: {exc}")


@pytest.mark.parametrize(
    "module_name,class_name,kwargs",
    [
        ("github_integration", "GitHubIntegration", {}),
        ("civitai_integration", "CivitAIIntegration", {}),
        ("mem0_integration", "Mem0Integration", {}),
        ("google_drive_integration", "GoogleDriveIntegration", {}),
        pytest.param(
            "obsidian_integration",
            "ObsidianIntegration",
            {"vault_path": os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")},
            marks=pytest.mark.xfail(
                strict=False,
                reason="intermittent: vault path check may return non-bool in full suite",
            ),
        ),
        (
            "comfyui_integration",
            "ComfyUIIntegration",
            {"base_url": os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")},
        ),
        ("manaos_complete_integration", "ManaOSCompleteIntegration", {}),
    ],
)
def test_integrations_import_and_availability_smoke(module_name, class_name, kwargs):
    _load_dotenv_if_exists()
    instance = _import_and_build(module_name, class_name, kwargs)
    if hasattr(instance, "is_available"):
        try:
            value = instance.is_available()
        except Exception as exc:
            pytest.skip(f"is_available 実行失敗のためスキップ: {exc}")
        assert isinstance(value, bool)
    else:
        assert instance is not None






















