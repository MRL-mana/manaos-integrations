"""
Unit tests for scripts/misc/hf_api_endpoint.py
"""
import sys
import types
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────

# unified_logging
_ul = types.ModuleType("unified_logging")
_ul.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules["unified_logging"] = _ul

# manaos_core_api
_core_api_instance = MagicMock()
_core_api_instance.act = MagicMock(return_value={"image_path": "/tmp/img.png"})
_core_api_mod = types.ModuleType("manaos_core_api")
_core_api_mod.get_manaos_api = MagicMock(return_value=_core_api_instance)
sys.modules["manaos_core_api"] = _core_api_mod

# huggingface_integration
_hf_instance = MagicMock()
_hf_instance.list_popular_models = MagicMock(return_value=[{"id": "model1"}])
_hf_instance.get_recommended_models = MagicMock(return_value={"text-to-image": ["sdd"]})
_hf_mod = types.ModuleType("huggingface_integration")
_hf_mod.HuggingFaceManaOSIntegration = MagicMock(return_value=_hf_instance)
sys.modules["huggingface_integration"] = _hf_mod

import scripts.misc.hf_api_endpoint as hfapi
from fastapi.testclient import TestClient

client = TestClient(hfapi.app, raise_server_exceptions=False)


# ─────────────────────────────────────────────
# GET /
# ─────────────────────────────────────────────

class TestRoot:
    def test_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_contains_service_name(self):
        data = client.get("/").json()
        assert "Hugging Face" in data["service"]


# ─────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────

class TestHealthCheck:
    def test_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_status_ok(self):
        assert client.get("/health").json()["status"] == "ok"


# ─────────────────────────────────────────────
# POST /api/hf/generate
# ─────────────────────────────────────────────

class TestGenerateImage:
    def test_returns_200_on_success(self):
        _core_api_instance.act.return_value = {"image_path": "/tmp/img.png"}
        resp = client.post("/api/hf/generate",
                           json={"prompt": "cat in forest"})
        assert resp.status_code == 200

    def test_returns_500_on_act_exception(self):
        _core_api_instance.act.side_effect = RuntimeError("crash")
        resp = client.post("/api/hf/generate",
                           json={"prompt": "test"})
        assert resp.status_code == 500
        _core_api_instance.act.side_effect = None


# ─────────────────────────────────────────────
# POST /api/hf/search
# ─────────────────────────────────────────────

class TestSearchModels:
    def test_returns_200_on_success(self):
        _core_api_instance.act.return_value = {"models": []}
        resp = client.post("/api/hf/search",
                           json={"query": "stable diffusion"})
        assert resp.status_code == 200

    def test_returns_500_on_exception(self):
        _core_api_instance.act.side_effect = ValueError("bad")
        resp = client.post("/api/hf/search",
                           json={"query": "xyz"})
        assert resp.status_code == 500
        _core_api_instance.act.side_effect = None


# ─────────────────────────────────────────────
# GET /api/hf/model/{model_id}
# ─────────────────────────────────────────────

class TestGetModelInfo:
    def test_returns_200_when_found(self):
        _core_api_instance.act.return_value = {"name": "SD"}
        resp = client.get("/api/hf/model/stable-diffusion")
        assert resp.status_code == 200

    def test_returns_500_on_exception(self):
        _core_api_instance.act.side_effect = RuntimeError("not found")
        resp = client.get("/api/hf/model/unknown-model")
        assert resp.status_code == 500
        _core_api_instance.act.side_effect = None


# ─────────────────────────────────────────────
# GET /api/hf/popular
# ─────────────────────────────────────────────

class TestGetPopularModels:
    def test_returns_200(self):
        _core_api_instance.act.return_value = {}  # reset
        resp = client.get("/api/hf/popular")
        assert resp.status_code == 200

    def test_includes_count(self):
        resp = client.get("/api/hf/popular")
        data = resp.json()
        assert "count" in data
        assert data["count"] == 1  # _hf_instance returns 1 model


# ─────────────────────────────────────────────
# GET /api/hf/recommended
# ─────────────────────────────────────────────

class TestGetRecommendedModels:
    def test_returns_200(self):
        resp = client.get("/api/hf/recommended")
        assert resp.status_code == 200

    def test_returns_recommendations(self):
        data = client.get("/api/hf/recommended").json()
        assert "text-to-image" in data
