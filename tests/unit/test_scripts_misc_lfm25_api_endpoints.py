"""
Tests for scripts/misc/lfm25_api_endpoints.py
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ── mock: manaos_logger ────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger = MagicMock(return_value=MagicMock())
_ml.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_logger", _ml)

# ── mock: always_ready_llm_client ─────────────────────────────────
_arc_mod = types.ModuleType("always_ready_llm_client")

class _FakeModelTypeItem:
    def __init__(self, value):
        self.value = value
    def __eq__(self, other):
        return self.value == (other.value if hasattr(other, 'value') else other)

class _FakeModelType:
    ULTRA_LIGHT = _FakeModelTypeItem("ultra_light")
    LIGHT = _FakeModelTypeItem("light")
    MEDIUM = _FakeModelTypeItem("medium")
    HEAVY = _FakeModelTypeItem("heavy")
    REASONING = _FakeModelTypeItem("reasoning")

class _FakeTaskType:
    CONVERSATION = "conversation"
    LIGHTWEIGHT_CONVERSATION = "lightweight_conversation"

_arc_mod.AlwaysReadyLLMClient = MagicMock()  # type: ignore
_arc_mod.ModelType = _FakeModelType  # type: ignore
_arc_mod.TaskType = _FakeTaskType  # type: ignore
_arc_mod.LLMResponse = MagicMock()  # type: ignore  # テストセッション汚染防止
sys.modules["always_ready_llm_client"] = _arc_mod

# ── load module under test ─────────────────────────────────────────
sys.path.insert(0, "scripts/misc")
import lfm25_api_endpoints as lfm  # noqa: E402

from flask import Flask
from flask.testing import FlaskClient


def _make_app() -> FlaskClient:
    """テスト用Flaskアプリを作成してエンドポイント登録"""
    app = Flask(__name__)
    app.testing = True
    lfm.register_lfm25_endpoints(app)
    return app.test_client()


def _make_response(response_text="Hello!", model="LFM2.5", latency_ms=50.0,
                   cached=False, source="local", tokens=None):
    """AlwaysReadyLLMClient().chat() が返す MagicMock"""
    r = MagicMock()
    r.response = response_text
    r.model = model
    r.latency_ms = latency_ms
    r.cached = cached
    r.source = source
    r.tokens = tokens or {}
    return r


# ─────────────────────────────────────────────────────────────────────
# Helper: LFM25_AVAILABLE = True / False
# ─────────────────────────────────────────────────────────────────────

class TestLFM25Available:
    """LFM25_AVAILABLE=True のケース"""

    def setup_method(self):
        lfm.LFM25_AVAILABLE = True

    def teardown_method(self):
        lfm.LFM25_AVAILABLE = True  # 元に戻す


class TestLFM25Unavailable:
    """LFM25_AVAILABLE=False のケース"""

    def setup_method(self):
        lfm.LFM25_AVAILABLE = False

    def teardown_method(self):
        lfm.LFM25_AVAILABLE = True


# ─────────────────────────────────────────────────────────────────────
# /api/lfm25/chat
# ─────────────────────────────────────────────────────────────────────

class TestLFM25Chat:

    def test_chat_success(self):
        lfm.LFM25_AVAILABLE = True
        fake_response = _make_response("こんにちは！", latency_ms=30.0, cached=False)
        mock_client = MagicMock()
        mock_client.chat.return_value = fake_response

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/chat",
                               json={"message": "Hello", "task_type": "conversation"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["response"] == "こんにちは！"
        assert data["model"] == "LFM2.5"

    def test_chat_missing_message(self):
        lfm.LFM25_AVAILABLE = True
        client = _make_app()
        resp = client.post("/api/lfm25/chat", json={})
        assert resp.status_code == 400
        assert "message" in resp.get_json()["error"]

    def test_chat_unavailable(self):
        lfm.LFM25_AVAILABLE = False
        client = _make_app()
        resp = client.post("/api/lfm25/chat", json={"message": "X"})
        assert resp.status_code == 503

    def test_chat_lightweight_task_type(self):
        lfm.LFM25_AVAILABLE = True
        fake_response = _make_response("OK")
        mock_client = MagicMock()
        mock_client.chat.return_value = fake_response

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/chat",
                               json={"message": "Hi", "task_type": "lightweight_conversation"})

        assert resp.status_code == 200
        # TaskType.LIGHTWEIGHT_CONVERSATION がセットされたかを確認
        call_kwargs = mock_client.chat.call_args[1]
        assert call_kwargs["task_type"] == _FakeTaskType.LIGHTWEIGHT_CONVERSATION

    def test_chat_unknown_task_type_defaults_conversation(self):
        lfm.LFM25_AVAILABLE = True
        fake_response = _make_response("OK")
        mock_client = MagicMock()
        mock_client.chat.return_value = fake_response

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/chat",
                               json={"message": "Hi", "task_type": "unknown_type"})

        assert resp.status_code == 200
        call_kwargs = mock_client.chat.call_args[1]
        assert call_kwargs["task_type"] == _FakeTaskType.CONVERSATION

    def test_chat_exception_returns_500(self):
        lfm.LFM25_AVAILABLE = True
        mock_client = MagicMock()
        mock_client.chat.side_effect = RuntimeError("boom")

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/chat", json={"message": "Hi"})

        assert resp.status_code == 500
        assert "boom" in resp.get_json()["error"]

    def test_chat_passes_temperature_and_max_tokens(self):
        lfm.LFM25_AVAILABLE = True
        fake_response = _make_response("OK")
        mock_client = MagicMock()
        mock_client.chat.return_value = fake_response

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/chat",
                               json={"message": "Hi", "temperature": 0.9, "max_tokens": 100})

        assert resp.status_code == 200
        call_kwargs = mock_client.chat.call_args[1]
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_tokens"] == 100


# ─────────────────────────────────────────────────────────────────────
# /api/lfm25/lightweight
# ─────────────────────────────────────────────────────────────────────

class TestLFM25Lightweight:

    def test_lightweight_success(self):
        lfm.LFM25_AVAILABLE = True
        fake_response = _make_response("軽量応答", latency_ms=10.0)
        mock_client = MagicMock()
        mock_client.chat.return_value = fake_response

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/lightweight", json={"message": "Test"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["task_type"] == "lightweight_conversation"

    def test_lightweight_missing_message(self):
        lfm.LFM25_AVAILABLE = True
        client = _make_app()
        resp = client.post("/api/lfm25/lightweight", json={})
        assert resp.status_code == 400

    def test_lightweight_unavailable(self):
        lfm.LFM25_AVAILABLE = False
        client = _make_app()
        resp = client.post("/api/lfm25/lightweight", json={"message": "Hi"})
        assert resp.status_code == 503

    def test_lightweight_exception_returns_500(self):
        lfm.LFM25_AVAILABLE = True
        mock_client = MagicMock()
        mock_client.chat.side_effect = RuntimeError("fail")

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/lightweight", json={"message": "Hi"})

        assert resp.status_code == 500


# ─────────────────────────────────────────────────────────────────────
# /api/lfm25/batch
# ─────────────────────────────────────────────────────────────────────

class TestLFM25Batch:

    def _batch_results(self, n=2):
        results = []
        for i in range(n):
            r = MagicMock()
            r.response = f"response{i}"
            r.model = "LFM2.5"
            r.latency_ms = 20.0
            r.cached = False
            r.source = "local"
            results.append(r)
        return results

    def test_batch_success(self):
        lfm.LFM25_AVAILABLE = True
        mock_client = MagicMock()
        mock_client.batch_chat.return_value = self._batch_results(2)

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/batch",
                               json={"messages": ["msg1", "msg2"]})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["count"] == 2
        assert data["results"][0]["index"] == 0
        assert data["results"][1]["index"] == 1

    def test_batch_missing_messages(self):
        lfm.LFM25_AVAILABLE = True
        client = _make_app()
        resp = client.post("/api/lfm25/batch", json={})
        assert resp.status_code == 400

    def test_batch_messages_not_list(self):
        lfm.LFM25_AVAILABLE = True
        client = _make_app()
        resp = client.post("/api/lfm25/batch", json={"messages": "not-a-list"})
        assert resp.status_code == 400

    def test_batch_unavailable(self):
        lfm.LFM25_AVAILABLE = False
        client = _make_app()
        resp = client.post("/api/lfm25/batch", json={"messages": ["x"]})
        assert resp.status_code == 503

    def test_batch_lightweight_task_type(self):
        lfm.LFM25_AVAILABLE = True
        mock_client = MagicMock()
        mock_client.batch_chat.return_value = self._batch_results(1)

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/batch",
                               json={"messages": ["hi"],
                                     "task_type": "lightweight_conversation"})

        assert resp.status_code == 200
        call_kwargs = mock_client.batch_chat.call_args[1]
        assert call_kwargs["task_type"] == _FakeTaskType.LIGHTWEIGHT_CONVERSATION

    def test_batch_exception_returns_500(self):
        lfm.LFM25_AVAILABLE = True
        mock_client = MagicMock()
        mock_client.batch_chat.side_effect = RuntimeError("batch fail")

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.post("/api/lfm25/batch", json={"messages": ["x"]})

        assert resp.status_code == 500


# ─────────────────────────────────────────────────────────────────────
# /api/lfm25/status
# ─────────────────────────────────────────────────────────────────────

class TestLFM25Status:

    def test_status_available(self):
        lfm.LFM25_AVAILABLE = True
        fake_response = _make_response("test ok", latency_ms=5.0, source="local")
        mock_client = MagicMock()
        mock_client.chat.return_value = fake_response

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.get("/api/lfm25/status")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is True
        assert data["status"] == "operational"
        assert data["test_latency_ms"] == 5.0

    def test_status_unavailable(self):
        lfm.LFM25_AVAILABLE = False
        client = _make_app()
        resp = client.get("/api/lfm25/status")
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["available"] is False

    def test_status_exception_returns_500(self):
        lfm.LFM25_AVAILABLE = True
        mock_client = MagicMock()
        mock_client.chat.side_effect = RuntimeError("client err")

        with patch.object(lfm, "AlwaysReadyLLMClient", return_value=mock_client):
            client = _make_app()
            resp = client.get("/api/lfm25/status")

        assert resp.status_code == 500
        data = resp.get_json()
        assert data["available"] is False
        assert "client err" in data["error"]
