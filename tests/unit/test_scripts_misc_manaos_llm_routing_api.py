"""
Unit tests for scripts/misc/manaos_llm_routing_api.py
Flask routes and pure helper functions.
"""
import sys
import json
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# EnhancedLLMRouter mock – must be in place BEFORE module import
# (because router = EnhancedLLMRouter() executes at module level)
_router_inst = MagicMock()
_router_inst.get_available_models.return_value = ["modelA", "modelB"]
_router_inst.route.return_value = {
    "success": True,
    "response": "mocked answer",
    "model": "modelA",
    "difficulty_score": 3.0,
    "difficulty_level": "low",
    "reasoning": "simple",
    "response_time_ms": 100,
}
_router_inst.llm_server = "lm_studio"
_analyzer = MagicMock()
_analyzer.calculate_difficulty.return_value = 4.0
_analyzer.get_difficulty_level.return_value = "medium"
_analyzer.get_recommended_model.return_value = "modelB"
_router_inst.analyzer = _analyzer

_lre = MagicMock()
_lre.EnhancedLLMRouter = MagicMock(return_value=_router_inst)
sys.modules["llm_router_enhanced"] = _lre
sys.modules["llm.llm_router_enhanced"] = _lre

import pytest
from scripts.misc.manaos_llm_routing_api import (
    app,
    _build_openai_model_list,
    _extract_text_from_content,
    _build_prompt_from_messages,
    _make_openai_chat_response,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── TestBuildOpenAIModelList ───────────────────────────────────────────────
class TestBuildOpenAIModelList:
    def test_always_has_auto_entries(self):
        result = _build_openai_model_list([])
        ids = [m["id"] for m in result]
        assert "auto" in ids
        assert "auto-local" in ids

    def test_includes_provided_models(self):
        result = _build_openai_model_list(["gpt-4", "llama3"])
        ids = [m["id"] for m in result]
        assert "gpt-4" in ids
        assert "llama3" in ids

    def test_auto_comes_first(self):
        result = _build_openai_model_list(["X"])
        assert result[0]["id"] == "auto"
        assert result[1]["id"] == "auto-local"

    def test_deduplicates(self):
        result = _build_openai_model_list(["X", "X"])
        ids = [m["id"] for m in result]
        assert ids.count("X") == 1

    def test_filters_invalid_model_ids(self):
        result = _build_openai_model_list(["valid-model", "invalid id with space"])
        ids = [m["id"] for m in result]
        assert "valid-model" in ids
        assert "invalid id with space" not in ids

    def test_result_items_have_required_fields(self):
        result = _build_openai_model_list(["m1"])
        for item in result:
            assert "id" in item
            assert "object" in item
            assert item["object"] == "model"
            assert "created" in item
            assert item["owned_by"] == "manaos"

    def test_empty_string_skipped(self):
        result = _build_openai_model_list(["", None])
        ids = [m["id"] for m in result]
        assert "" not in ids


# ── TestExtractTextFromContent ─────────────────────────────────────────────
class TestExtractTextFromContent:
    def test_string_returned_as_is(self):
        assert _extract_text_from_content("hello") == "hello"

    def test_list_of_text_items(self):
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"},
        ]
        result = _extract_text_from_content(content)
        assert "Hello" in result
        assert "World" in result

    def test_skips_non_text_items(self):
        content = [
            {"type": "image", "data": "..."},
            {"type": "text", "text": "hi"},
        ]
        assert _extract_text_from_content(content) == "hi"

    def test_empty_list(self):
        assert _extract_text_from_content([]) == ""

    def test_other_types_return_empty(self):
        assert _extract_text_from_content(42) == ""
        assert _extract_text_from_content(None) == ""


# ── TestBuildPromptFromMessages ────────────────────────────────────────────
class TestBuildPromptFromMessages:
    def test_basic_user_message(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = _build_prompt_from_messages(messages)
        assert "Hello" in result
        assert "user" in result

    def test_multiple_roles(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Question"},
        ]
        result = _build_prompt_from_messages(messages)
        assert "system" in result
        assert "user" in result
        assert "You are helpful" in result

    def test_empty_list(self):
        assert _build_prompt_from_messages([]) == ""

    def test_non_list_returns_empty(self):
        assert _build_prompt_from_messages("not a list") == ""

    def test_skips_empty_content(self):
        messages = [{"role": "user", "content": ""}]
        result = _build_prompt_from_messages(messages)
        assert result == ""

    def test_list_content(self):
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "nested"}]}
        ]
        result = _build_prompt_from_messages(messages)
        assert "nested" in result


# ── TestMakeOpenAIChatResponse ─────────────────────────────────────────────
class TestMakeOpenAIChatResponse:
    def test_has_required_keys(self):
        r = _make_openai_chat_response("hi", "gpt-4", "cmpl-001")
        assert "id" in r
        assert "object" in r
        assert "choices" in r
        assert "usage" in r

    def test_id_and_model(self):
        r = _make_openai_chat_response("response", "my-model", "id-xyz")
        assert r["id"] == "id-xyz"
        assert r["model"] == "my-model"

    def test_choices_content(self):
        r = _make_openai_chat_response("hello world", "m", "id1")
        assert r["choices"][0]["message"]["content"] == "hello world"
        assert r["choices"][0]["message"]["role"] == "assistant"
        assert r["choices"][0]["finish_reason"] == "stop"

    def test_usage_tokens_positive(self):
        r = _make_openai_chat_response("a" * 40, "m", "id1")
        assert r["usage"]["completion_tokens"] >= 1
        assert r["usage"]["total_tokens"] >= 1


# ── TestHealthCheck ────────────────────────────────────────────────────────
class TestHealthCheck:
    def test_returns_200(self, client):
        r = client.get("/api/llm/health")
        assert r.status_code == 200

    def test_status_ok(self, client):
        data = json.loads(r.data) if hasattr((r := client.get("/api/llm/health")), "data") else {}
        data = json.loads(client.get("/api/llm/health").data)
        assert data["status"] == "ok"

    def test_has_available_models_count(self, client):
        data = json.loads(client.get("/api/llm/health").data)
        assert "available_models" in data
        assert data["available_models"] == 2  # modelA, modelB


# ── TestGetAvailableModels ─────────────────────────────────────────────────
class TestGetAvailableModels:
    def test_returns_200(self, client):
        r = client.get("/api/llm/models")
        assert r.status_code == 200

    def test_models_key_present(self, client):
        data = json.loads(client.get("/api/llm/models").data)
        assert "models" in data

    def test_models_is_list(self, client):
        data = json.loads(client.get("/api/llm/models").data)
        assert isinstance(data["models"], list)


# ── TestRouteLLMRequest ────────────────────────────────────────────────────
class TestRouteLLMRequest:
    def test_valid_request(self, client):
        r = client.post("/api/llm/route",
                        json={"prompt": "Write a hello world function"})
        assert r.status_code == 200

    def test_empty_body_returns_400(self, client):
        # {} is falsy so the route returns 400 for empty request
        r = client.post("/api/llm/route", json={})
        assert r.status_code == 400

    def test_missing_prompt_returns_400(self, client):
        r = client.post("/api/llm/route", json={"context": {}})
        assert r.status_code == 400

    def test_error_message_on_missing_prompt(self, client):
        data = json.loads(client.post("/api/llm/route", json={}).data)
        assert "error" in data


# ── TestAnalyzeDifficulty ──────────────────────────────────────────────────
class TestAnalyzeDifficulty:
    def test_valid_request(self, client):
        r = client.post("/api/llm/analyze",
                        json={"prompt": "Simple task"})
        assert r.status_code == 200

    def test_response_has_difficulty_keys(self, client):
        data = json.loads(
            client.post("/api/llm/analyze", json={"prompt": "task"}).data
        )
        assert "difficulty_score" in data
        assert "difficulty_level" in data
        assert "recommended_model" in data

    def test_empty_body_returns_400(self, client):
        # {} is falsy so the route returns 400 for empty request
        r = client.post("/api/llm/analyze", json={})
        assert r.status_code == 400


# ── TestOpenAIModels ───────────────────────────────────────────────────────
class TestOpenAIModels:
    def test_returns_200(self, client):
        assert client.get("/v1/models").status_code == 200

    def test_object_is_list(self, client):
        data = json.loads(client.get("/v1/models").data)
        assert data["object"] == "list"
        assert isinstance(data["data"], list)

    def test_auto_in_data(self, client):
        data = json.loads(client.get("/v1/models").data)
        ids = [m["id"] for m in data["data"]]
        assert "auto" in ids


# ── TestOpenAPISchema ──────────────────────────────────────────────────────
class TestOpenAPISchema:
    def test_returns_200(self, client):
        assert client.get("/openapi.json").status_code == 200

    def test_has_openapi_key(self, client):
        data = json.loads(client.get("/openapi.json").data)
        assert "openapi" in data
        assert "paths" in data


# ── TestOpenAIChatCompletions ──────────────────────────────────────────────
class TestOpenAIChatCompletions:
    def _valid_payload(self):
        return {
            "model": "auto",
            "messages": [{"role": "user", "content": "Hello"}],
        }

    def test_valid_request_200(self, client):
        r = client.post("/v1/chat/completions", json=self._valid_payload())
        assert r.status_code == 200

    def test_response_has_id(self, client):
        data = json.loads(
            client.post("/v1/chat/completions", json=self._valid_payload()).data
        )
        assert "id" in data

    def test_choices_present(self, client):
        data = json.loads(
            client.post("/v1/chat/completions", json=self._valid_payload()).data
        )
        assert "choices" in data
        assert len(data["choices"]) > 0

    def test_missing_messages_400(self, client):
        r = client.post("/v1/chat/completions", json={"model": "auto"})
        assert r.status_code == 400

    def test_empty_messages_400(self, client):
        r = client.post("/v1/chat/completions",
                        json={"model": "auto", "messages": []})
        assert r.status_code == 400

    def test_stream_returns_event_stream(self, client):
        payload = dict(self._valid_payload(), stream=True)
        r = client.post("/v1/chat/completions", json=payload)
        assert r.status_code == 200
        assert "text/event-stream" in r.content_type

    def test_auto_model_alias_routes_to_default(self, client):
        import os
        os.environ["MANAOS_AUTO_MODEL_DEFAULT"] = "llama3:latest"
        payload = {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}
        r = client.post("/v1/chat/completions", json=payload)
        assert r.status_code == 200

    def test_max_tokens_truncates_response(self, client):
        long_response = "x" * 1000
        _router_inst.route.return_value = {
            "success": True,
            "response": long_response,
            "model": "modelA",
        }
        payload = dict(self._valid_payload(), max_tokens=1)
        r = client.post("/v1/chat/completions", json=payload)
        assert r.status_code == 200
        data = json.loads(r.data)
        content = data["choices"][0]["message"]["content"]
        assert len(content) < len(long_response)
