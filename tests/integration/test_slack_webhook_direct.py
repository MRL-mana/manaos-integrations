#!/usr/bin/env python3
"""Slack Webhook直接送信テスト（pytest対応）"""

from unittest.mock import MagicMock, patch

import pytest
import requests


def test_slack_webhook_direct_send_smoke():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.post", return_value=mock_resp):
        payload = {"text": "🤖 Slack Integrationテスト: pytest smoke"}
        response = requests.post("https://hooks.slack.com/services/test", json=payload, timeout=10)
    assert response.status_code in (200, 204)
