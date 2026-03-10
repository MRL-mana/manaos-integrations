"""
Unit tests for scripts/misc/voice_secretary_remi.py
"""
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────

# _paths
_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.INTENT_ROUTER_PORT = 5100  # type: ignore
_paths_mod.LLM_ROUTING_PORT = 5117  # type: ignore
_paths_mod.UNIFIED_API_PORT = 9510  # type: ignore
sys.modules["_paths"] = _paths_mod

# httpx
_httpx_mod = MagicMock()
_httpx_mod.AsyncClient = MagicMock
sys.modules.setdefault("httpx", _httpx_mod)

# voice_integration
_voice_mod = MagicMock()
_voice_mod.create_stt_engine = MagicMock(return_value=MagicMock())
_voice_mod.create_tts_engine = MagicMock(return_value=MagicMock())
_voice_mod.VoiceConversationLoop = MagicMock(return_value=MagicMock())
sys.modules.setdefault("voice_integration", _voice_mod)

# unified_logging
_unified_log = MagicMock()
_unified_log.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("unified_logging", _unified_log)

from scripts.misc.voice_secretary_remi import (
    create_llm_callback,
    create_intent_router_callback,
    create_task_registration_callback,
    create_conversation_save_callback,
    INTENT_ROUTER_URL,
    UNIFIED_API_URL,
    LLM_ROUTING_URL,
)


# ─── create_llm_callback ──────────────────────────────────────────────────────
class TestCreateLLMCallback:
    def test_returns_callable(self):
        cb = create_llm_callback()
        assert callable(cb)

    def test_callback_returns_string_on_success(self):
        cb = create_llm_callback()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"response": "Hello!"}
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__.return_value = async_client_mock
        async_client_mock.post.return_value = fake_resp

        with patch("httpx.AsyncClient", return_value=async_client_mock):
            result = cb("Hello")
        assert result == "Hello!"

    def test_callback_fallback_on_exception(self):
        cb = create_llm_callback()
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__.return_value = async_client_mock
        async_client_mock.post.side_effect = Exception("network error")

        with patch("httpx.AsyncClient", return_value=async_client_mock):
            result = cb("Something")
        assert isinstance(result, str)


# ─── create_intent_router_callback ────────────────────────────────────────────
class TestCreateIntentRouterCallback:
    def test_returns_callable(self):
        cb = create_intent_router_callback()
        assert callable(cb)

    def test_callback_returns_dict_on_success(self):
        cb = create_intent_router_callback()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"intent_type": "question", "confidence": 0.9}
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__.return_value = async_client_mock
        async_client_mock.post.return_value = fake_resp

        with patch("httpx.AsyncClient", return_value=async_client_mock):
            result = cb("What time is it?")
        assert result.get("intent_type") == "question"

    def test_callback_fallback_dict_on_error(self):
        cb = create_intent_router_callback()
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__.return_value = async_client_mock
        async_client_mock.post.side_effect = Exception("connection error")

        with patch("httpx.AsyncClient", return_value=async_client_mock):
            result = cb("test")
        assert isinstance(result, dict)
        assert "intent_type" in result


# ─── create_task_registration_callback ────────────────────────────────────────
class TestCreateTaskRegistrationCallback:
    def test_returns_callable(self):
        cb = create_task_registration_callback()
        assert callable(cb)

    def test_returns_true_on_success(self):
        cb = create_task_registration_callback()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__.return_value = async_client_mock
        async_client_mock.post.return_value = fake_resp

        with patch("httpx.AsyncClient", return_value=async_client_mock):
            result = cb("buy groceries", {"intent_type": "task_execution"})
        assert result is True

    def test_returns_false_on_exception(self):
        cb = create_task_registration_callback()
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__.return_value = async_client_mock
        async_client_mock.post.side_effect = Exception("fail")

        with patch("httpx.AsyncClient", return_value=async_client_mock):
            result = cb("text", {})
        assert result is False


# ─── create_conversation_save_callback ────────────────────────────────────────
class TestCreateConversationSaveCallback:
    def test_returns_callable(self):
        cb = create_conversation_save_callback()
        assert callable(cb)

    def test_no_notion_no_slack_does_not_raise(self):
        cb = create_conversation_save_callback()
        with patch("scripts.misc.voice_secretary_remi.NOTION_AVAILABLE", False):
            with patch("scripts.misc.voice_secretary_remi.SLACK_AVAILABLE", False):
                # Should not raise even if both external services are off
                cb({"user": "hello", "assistant": "hi", "timestamp": "2024-01-01T00:00:00"})

    def test_notion_available_calls_post(self):
        cb = create_conversation_save_callback()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__.return_value = async_client_mock
        async_client_mock.post.return_value = fake_resp

        with patch("scripts.misc.voice_secretary_remi.NOTION_AVAILABLE", True):
            with patch("scripts.misc.voice_secretary_remi.SLACK_AVAILABLE", False):
                with patch("httpx.AsyncClient", return_value=async_client_mock):
                    cb({
                        "user": "hello",
                        "assistant": "hi",
                        "timestamp": "2024-01-01T00:00:00",
                        "intent": "greeting"
                    })
        async_client_mock.post.assert_called()


# ─── URL constants ─────────────────────────────────────────────────────────────
class TestURLConstants:
    def test_intent_router_url_is_string(self):
        assert isinstance(INTENT_ROUTER_URL, str)
        assert "http" in INTENT_ROUTER_URL

    def test_unified_api_url_is_string(self):
        assert isinstance(UNIFIED_API_URL, str)
        assert "http" in UNIFIED_API_URL

    def test_llm_routing_url_is_string(self):
        assert isinstance(LLM_ROUTING_URL, str)
        assert "http" in LLM_ROUTING_URL
