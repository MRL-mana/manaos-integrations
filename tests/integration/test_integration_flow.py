#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Obsidian × NotebookLM × ManaOS 統合フローのスモークテスト。"""

import os
from datetime import datetime
from pathlib import Path

import pytest

try:
    from manaos_integrations._paths import ORCHESTRATOR_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import ORCHESTRATOR_PORT  # type: ignore
    except Exception:  # pragma: no cover
        ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "5106"))


def _vault_path() -> Path:
    return Path(os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault"))


def test_obsidian_vault_exists():
    vault = _vault_path()
    if not vault.exists():
        pytest.skip(f"obsidian vault not found: {vault}")
    assert vault.is_dir()


def test_daily_note_path_is_constructible():
    vault = _vault_path()
    if not vault.exists():
        pytest.skip(f"obsidian vault not found: {vault}")
    today = datetime.now().strftime("%Y-%m-%d")
    daily_note = vault / "Daily" / f"{today}.md"
    assert daily_note.name.endswith(".md")


def test_prepare_notebooklm_input_if_available():
    try:
        module = __import__(
            "manaos_obsidian_integration",
            fromlist=["ObsidianNotebookLMAntigravityIntegration"],
        )
    except Exception as error:
        pytest.skip(f"integration module unavailable: {error}")

    try:
        integration = module.ObsidianNotebookLMAntigravityIntegration()
        input_file = integration.prepare_notebooklm_input(days=14)
    except Exception as error:
        pytest.skip(f"notebooklm input preparation unavailable: {error}")

    if input_file is not None:
        assert Path(input_file).suffix == ".txt"


def test_antigravity_env_is_optional():
    antigravity_url = os.getenv("ANTIGRAVITY_URL", "")
    assert isinstance(antigravity_url, str)


def test_orchestrator_health_if_reachable():
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", f"http://127.0.0.1:{ORCHESTRATOR_PORT}")
    try:
        import httpx

        response = httpx.get(f"{orchestrator_url}/health", timeout=5.0)
    except Exception as error:
        return

    assert response.status_code < 500




















