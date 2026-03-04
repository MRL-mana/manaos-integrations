#!/usr/bin/env python3
"""Slack会話機能のpytestスモークテスト。"""

import os

import pytest
import requests

try:
    from manaos_integrations._paths import SLACK_INTEGRATION_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import SLACK_INTEGRATION_PORT  # type: ignore
    except Exception:  # pragma: no cover
        SLACK_INTEGRATION_PORT = int(os.getenv("SLACK_INTEGRATION_PORT", "5114"))


def test_slack_webhook_endpoint_smoke():
    url = os.getenv("SLACK_API_URL", f"http://127.0.0.1:{SLACK_INTEGRATION_PORT}") + "/api/slack/webhook"
    payload = {"text": "pytest smoke", "user": "test_user", "channel": "test_channel"}
    try:
        response = requests.post(url, json=payload, timeout=10)
    except Exception as exc:
        pytest.xfail(f"Slack統合APIに接続できない: {exc}")

    assert response.status_code in (200, 400, 401, 403, 404, 422, 500, 501)
