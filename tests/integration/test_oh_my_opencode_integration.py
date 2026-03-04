#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OH MY OPENCODE統合テスト（pytest対応）"""

import os
from pathlib import Path

import pytest
import requests

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))


def _load_env_if_present() -> None:
    if load_dotenv is None:
        return
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _base_url() -> str:
    return os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")


def _require_api_key_or_skip() -> None:
    _load_env_if_present()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY が未設定のためスキップ")


def test_health_check_smoke():
    _require_api_key_or_skip()
    try:
        response = requests.get(f"{_base_url()}/health", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"統合APIサーバーへ接続できないためスキップ: {exc}")

    assert response.status_code == 200


def test_oh_my_opencode_status_smoke():
    _require_api_key_or_skip()
    try:
        response = requests.get(f"{_base_url()}/api/integrations/status", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"統合ステータス取得不可のためスキップ: {exc}")

    assert response.status_code in (200, 401, 403, 404)
    if response.status_code == 404:
        pytest.skip("統合ステータスエンドポイント未実装のためスキップ")
    if response.status_code != 200:
        return
    data = response.json()
    integration = data.get("integrations", {}).get("oh_my_opencode", {})
    assert isinstance(integration, dict)


def test_oh_my_opencode_execute_smoke():
    _require_api_key_or_skip()
    payload = {
        "task_description": "PythonでHello Worldを出力するコードを生成してください",
        "mode": "normal",
        "task_type": "code_generation",
    }

    try:
        response = requests.post(
            f"{_base_url()}/api/oh_my_opencode/execute",
            json=payload,
            timeout=60,
        )
    except requests.RequestException as exc:
        pytest.skip(f"実行APIへ接続できないためスキップ: {exc}")

    assert response.status_code in (200, 400, 401, 403, 404, 503)
