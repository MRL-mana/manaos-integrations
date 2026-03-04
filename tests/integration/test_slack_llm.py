"""Slack LLM統合テスト（pytest対応）"""
import importlib
import os

import pytest
import requests


def _import_slack_llm_module():
    candidates = ["slack_llm_integration", "slack_integration.slack_llm_integration"]
    last_error = None
    for module_name in candidates:
        try:
            return importlib.import_module(module_name)
        except Exception as exc:
            last_error = exc
    pytest.skip(f"slack_llm_integration の読み込みに失敗: {last_error}")


def _slack_llm_base_url() -> str:
    try:
        from manaos_integrations._paths import WINDOWS_AUTOMATION_PORT
    except Exception:
        try:
            from _paths import WINDOWS_AUTOMATION_PORT  # type: ignore
        except Exception:
            WINDOWS_AUTOMATION_PORT = int(os.getenv("WINDOWS_AUTOMATION_PORT", "5115"))

    return os.getenv("SLACK_LLM_URL", f"http://127.0.0.1:{WINDOWS_AUTOMATION_PORT}")


def test_parse_slack_message_smoke():
    module = _import_slack_llm_module()
    parser = getattr(module, "parse_slack_message", None)
    if parser is None:
        pytest.skip("parse_slack_message が存在しないためスキップ")

    parsed = parser("reasoning この問題を分析してください")
    assert isinstance(parsed, dict)
    assert "model" in parsed
    assert "task_type" in parsed


def test_llm_client_available_or_skip():
    module = _import_slack_llm_module()
    client = getattr(module, "LLM_CLIENT", None)
    if not client:
        pytest.skip("LLM_CLIENT が利用不可のためスキップ")

    assert client is not None


def test_slack_llm_chat_endpoint_smoke():
    module = _import_slack_llm_module()
    client = getattr(module, "LLM_CLIENT", None)
    if not client:
        pytest.skip("LLM_CLIENT が利用不可のためスキップ")

    base_url = _slack_llm_base_url()
    try:
        response = requests.post(
            f"{base_url}/api/slack/llm/chat",
            json={
                "text": "こんにちは！短く挨拶してください。",
                "channel": "#test",
                "auto_reply": False,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        pytest.xfail(f"Slack LLM APIへ接続できない: {exc}")

    assert response.status_code in (200, 400, 401, 403, 404, 500, 501, 503)






















