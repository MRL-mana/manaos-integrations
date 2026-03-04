#!/usr/bin/env python3
"""Slack Webhook直接送信テスト（pytest対応）"""

import json
from pathlib import Path

import pytest
import requests


def _load_webhook_url() -> str:
    config_path = Path("notification_hub_enhanced_config.json")
    if not config_path.exists():
        pytest.skip("notification_hub_enhanced_config.json が見つからないためスキップ")

    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    webhook_url = str(config.get("slack_webhook_url", "")).strip()
    if not webhook_url:
        pytest.skip("Slack Webhook URLが未設定のためスキップ")

    return webhook_url


def test_slack_webhook_direct_send_smoke():
    webhook_url = _load_webhook_url()
    payload = {"text": "🤖 Slack Integrationテスト: pytest smoke"}

    response = requests.post(webhook_url, json=payload, timeout=10)

    assert response.status_code in (200, 204)
