"""
tests/unit/test_scripts_misc_api_documentation.py
API Documentation (FastAPI) のユニットテスト
"""

import sys
import json
from unittest.mock import MagicMock, patch
from datetime import datetime
import pytest

# ── _paths のモック ────────────────────────────────────────────────
sys.modules.setdefault("_paths", MagicMock(
    UNIFIED_API_URL="http://127.0.0.1:9502",
))

# ── モジュールをインポート ──────────────────────────────────────────────
import scripts.misc.api_documentation as _sut
from scripts.misc.api_documentation import (
    HealthResponse,
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemoryRetrieveResponse,
    LearningEventRequest,
    LearningEventResponse,
    LLMRoutingRequest,
    LLMRoutingResponse,
    ErrorResponse,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fixture: FastAPI test client
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(_sut.app)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestPydanticModels
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHealthResponse:
    def test_valid_instance(self):
        h = HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="2.6.0",
            services={"api": "healthy"},
        )
        assert h.status == "healthy"
        assert h.version == "2.6.0"


class TestMemoryStoreRequest:
    def test_basic_fields(self):
        r = MemoryStoreRequest(key="mykey", value={"x": 1})
        assert r.key == "mykey"
        assert r.value == {"x": 1}
        assert r.ttl is None
        assert r.tags is None

    def test_with_ttl_and_tags(self):
        r = MemoryStoreRequest(key="k", value="v", ttl=3600, tags=["a", "b"])
        assert r.ttl == 3600
        assert r.tags == ["a", "b"]


class TestLearningEventRequest:
    def test_valid_event_type(self):
        r = LearningEventRequest(
            event_type="success",
            context={"task": "test"},
        )
        assert r.event_type == "success"

    def test_metadata_optional(self):
        r = LearningEventRequest(event_type="failure", context={})
        assert r.metadata is None


class TestLLMRoutingRequest:
    def test_required_fields(self):
        r = LLMRoutingRequest(prompt="Hello")
        assert r.prompt == "Hello"
        assert r.temperature == 0.7

    def test_with_all_fields(self):
        r = LLMRoutingRequest(
            prompt="Test",
            max_tokens=512,
            temperature=0.5,
            preferred_model="gpt-4",
        )
        assert r.max_tokens == 512
        assert r.preferred_model == "gpt-4"


class TestErrorResponse:
    def test_required_fields(self):
        e = ErrorResponse(
            error="NotFound",
            message="Resource not found",
            timestamp=datetime.utcnow(),
        )
        assert e.error == "NotFound"
        assert e.request_id is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestModuleLevel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestModuleLevel:
    def test_app_created(self):
        assert hasattr(_sut, "app")
        assert _sut.app.title == "ManaOS Unified API"

    def test_app_version(self):
        assert _sut.app.version == "2.6.0"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestEndpoints (FastAPI TestClient)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRootEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_api_name(self, client):
        resp = client.get("/")
        data = resp.json()
        assert "ManaOS" in data.get("name", "")

    def test_returns_docs_link(self, client):
        resp = client.get("/")
        data = resp.json()
        assert "docs" in data


class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_healthy(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"

    def test_returns_version(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["version"] == "2.6.0"

    def test_returns_services(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "services" in data
        assert isinstance(data["services"], dict)

    def test_returns_timestamp(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "timestamp" in data


class TestMemoryStoreEndpoint:
    def test_returns_201(self, client):
        resp = client.post("/memory/store", json={"key": "test_key", "value": {"x": 1}})
        assert resp.status_code == 201

    def test_returns_success_true(self, client):
        resp = client.post("/memory/store", json={"key": "k", "value": "v"})
        data = resp.json()
        assert data["success"] is True
        assert data["key"] == "k"

    def test_with_ttl(self, client):
        resp = client.post("/memory/store", json={"key": "k2", "value": 42, "ttl": 3600})
        assert resp.status_code == 201


class TestMemoryRetrieveEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/memory/retrieve/testkey")
        assert resp.status_code == 200

    def test_returns_key_and_found(self, client):
        resp = client.get("/memory/retrieve/mykey")
        data = resp.json()
        assert data["key"] == "mykey"
        assert data["found"] is True


class TestLearningEventEndpoint:
    def test_returns_201(self, client):
        resp = client.post("/learning/event", json={
            "event_type": "success",
            "context": {"task": "test"},
        })
        assert resp.status_code == 201

    def test_returns_success_and_event_id(self, client):
        resp = client.post("/learning/event", json={
            "event_type": "failure",
            "context": {},
        })
        data = resp.json()
        assert data["success"] is True
        assert "event_id" in data
