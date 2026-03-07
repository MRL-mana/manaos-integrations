"""
Unit tests for scripts/misc/base_ai_integration.py
"""
import sys
import json
from unittest.mock import MagicMock, patch

# manaos_logger mock (module level import)
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

import pytest
from scripts.misc.base_ai_integration import BaseAIIntegration, BaseAIResponse


# ── helpers ────────────────────────────────────────────────────────────────
def make_mock_response(content: str = "hello", model: str = "base-ai",
                        usage: dict = None) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "model": model,
        "usage": usage or {"prompt_tokens": 5, "completion_tokens": 5},
    }
    resp.raise_for_status.return_value = None
    return resp


# ── TestBaseAIResponse ─────────────────────────────────────────────────────
class TestBaseAIResponse:
    def test_fields_accessible(self):
        r = BaseAIResponse(content="hi", model="base-ai", usage={"tokens": 1})
        assert r.content == "hi"
        assert r.model == "base-ai"

    def test_optional_fields_default_none(self):
        r = BaseAIResponse(content="hi")
        assert r.model is None
        assert r.usage is None


# ── TestIsAvailable ────────────────────────────────────────────────────────
class TestIsAvailable:
    def test_with_api_key_is_available(self):
        integration = BaseAIIntegration(api_key="test_key_123")
        assert integration.is_available() is True

    def test_without_api_key_not_available(self, monkeypatch):
        monkeypatch.delenv("BASE_AI_API_KEY", raising=False)
        monkeypatch.delenv("BASE_AI_FREE_API_KEY", raising=False)
        integration = BaseAIIntegration()
        assert integration.is_available() is False

    def test_with_free_key_is_available(self, monkeypatch):
        monkeypatch.setenv("BASE_AI_FREE_API_KEY", "free_key_xyz")
        integration = BaseAIIntegration(use_free=True)
        assert integration.is_available() is True


# ── TestChat ───────────────────────────────────────────────────────────────
class TestChat:
    def test_chat_returns_base_ai_response(self):
        integration = BaseAIIntegration(api_key="test_key")
        mock_resp = make_mock_response("the answer")
        with patch("requests.post", return_value=mock_resp):
            result = integration.chat([{"role": "user", "content": "hi"}])
        assert isinstance(result, BaseAIResponse)
        assert result.content == "the answer"

    def test_chat_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("BASE_AI_API_KEY", raising=False)
        monkeypatch.delenv("BASE_AI_FREE_API_KEY", raising=False)
        integration = BaseAIIntegration()
        with pytest.raises(ValueError):
            integration.chat([{"role": "user", "content": "hi"}])

    def test_chat_passes_model_in_payload(self):
        integration = BaseAIIntegration(api_key="test_key")
        mock_resp = make_mock_response()
        with patch("requests.post", return_value=mock_resp) as mock_post:
            integration.chat([{"role": "user", "content": "hi"}], model="custom-model")
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "custom-model"

    def test_chat_passes_temperature(self):
        integration = BaseAIIntegration(api_key="key")
        mock_resp = make_mock_response()
        with patch("requests.post", return_value=mock_resp) as mock_post:
            integration.chat([{"role": "user", "content": "hi"}], temperature=0.1)
        payload = mock_post.call_args[1]["json"]
        assert payload["temperature"] == 0.1

    def test_chat_includes_max_tokens_when_set(self):
        integration = BaseAIIntegration(api_key="key")
        mock_resp = make_mock_response()
        with patch("requests.post", return_value=mock_resp) as mock_post:
            integration.chat([{"role": "user", "content": "hi"}], max_tokens=100)
        payload = mock_post.call_args[1]["json"]
        assert payload["max_tokens"] == 100

    def test_chat_model_from_response(self):
        integration = BaseAIIntegration(api_key="key")
        mock_resp = make_mock_response(model="returned-model")
        with patch("requests.post", return_value=mock_resp):
            result = integration.chat([{"role": "user", "content": "q"}])
        assert result.model == "returned-model"


# ── TestChatSimple ─────────────────────────────────────────────────────────
class TestChatSimple:
    def test_returns_string(self):
        integration = BaseAIIntegration(api_key="key")
        mock_resp = make_mock_response("simple answer")
        with patch("requests.post", return_value=mock_resp):
            result = integration.chat_simple("what is 1+1?")
        assert result == "simple answer"

    def test_with_system_prompt(self):
        integration = BaseAIIntegration(api_key="key")
        mock_resp = make_mock_response("I am a bot")
        with patch("requests.post", return_value=mock_resp) as mock_post:
            integration.chat_simple("hello", system_prompt="You are a bot")
        messages = mock_post.call_args[1]["json"]["messages"]
        assert messages[0]["role"] == "system"

    def test_without_system_prompt_single_message(self):
        integration = BaseAIIntegration(api_key="key")
        mock_resp = make_mock_response("ok")
        with patch("requests.post", return_value=mock_resp) as mock_post:
            integration.chat_simple("hello")
        messages = mock_post.call_args[1]["json"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
