"""
Unit tests for scripts/misc/learning_system_api.py
"""
import sys
import json
import types
from unittest.mock import MagicMock

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────

# manaos_logger / unified_logging
sys.modules["manaos_logger"] = MagicMock(
    get_logger=MagicMock(return_value=MagicMock()),
    get_service_logger=MagicMock(return_value=MagicMock()),
)
_ul = types.ModuleType("unified_logging")
_ul.get_service_logger = MagicMock(return_value=MagicMock())  # type: ignore
sys.modules["unified_logging"] = _ul

sys.modules["manaos_error_handler"] = MagicMock(
    ManaOSErrorHandler=MagicMock(return_value=MagicMock(
        handle_exception=MagicMock(return_value=MagicMock(
            message="err",
            to_json_response=MagicMock(return_value={"error": "err"}),
        ))
    )),
    ErrorCategory=MagicMock(),
    ErrorSeverity=MagicMock(),
)
sys.modules["manaos_timeout_config"] = MagicMock(
    get_timeout_config=MagicMock(return_value={"api_call": 10}),
)

# api_auth — DummyAuthManager pass-through
# Save and restore the real api_auth so test_api_auth_rate_limit_state.py is not polluted
_real_api_auth = sys.modules.pop("api_auth", None)
_api_auth = types.ModuleType("api_auth")
class _DummyAuthManager:
    def require_api_key(self, func):
        return func
_api_auth.get_auth_manager = MagicMock(return_value=_DummyAuthManager())  # type: ignore

# learning_system
_ls_instance = MagicMock()
_ls_instance.record_usage = MagicMock()
_ls_instance.analyze_patterns = MagicMock(return_value={"patterns": []})
_ls_instance.learn_preferences = MagicMock(return_value={"model": "qwen2.5"})
_ls_instance.suggest_optimizations = MagicMock(return_value=["opt1", "opt2"])
_ls_instance.get_status = MagicMock(return_value={"status": "active"})
_ls_instance.apply_learned_preferences = MagicMock(return_value={"temperature": 0.7})

_ls_mod = types.ModuleType("learning_system")
_ls_mod.LearningSystem = MagicMock(return_value=_ls_instance)  # type: ignore
sys.modules["learning_system"] = _ls_mod

# Force fresh import of learning_system_api so Flask app uses our stubs
sys.modules.pop("scripts.misc.learning_system_api", None)
sys.modules["api_auth"] = _api_auth
import scripts.misc.learning_system_api as api
# Restore real api_auth immediately (the Flask app already captured our stub's references)
if _real_api_auth is not None:
    sys.modules["api_auth"] = _real_api_auth
else:
    sys.modules.pop("api_auth", None)

# Reset global state between tests
@pytest.fixture(autouse=True)
def reset_learning_system():
    api.learning_system = None
    yield
    api.learning_system = None


@pytest.fixture
def client():
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c


# ─────────────────────────────────────────────
# /health
# ─────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_healthy(self, client):
        data = client.get("/health").get_json()
        assert data["status"] == "healthy"


# ─────────────────────────────────────────────
# /api/record
# ─────────────────────────────────────────────

class TestRecordUsage:
    def test_records_action(self, client):
        resp = client.post("/api/record",
                           json={"action": "generate_image", "context": {}, "result": {}},
                           content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "recorded"
        assert data["action"] == "generate_image"

    def test_returns_400_when_no_action(self, client):
        resp = client.post("/api/record", json={}, content_type="application/json")
        assert resp.status_code == 400

    def test_calls_record_usage(self, client):
        _ls_instance.record_usage.reset_mock()
        client.post("/api/record",
                    json={"action": "test_action"},
                    content_type="application/json")
        _ls_instance.record_usage.assert_called_once()


# ─────────────────────────────────────────────
# /api/analyze
# ─────────────────────────────────────────────

class TestAnalyzePatterns:
    def test_returns_200(self, client):
        resp = client.get("/api/analyze")
        assert resp.status_code == 200

    def test_returns_analysis(self, client):
        data = client.get("/api/analyze").get_json()
        assert "patterns" in data


# ─────────────────────────────────────────────
# /api/preferences
# ─────────────────────────────────────────────

class TestGetPreferences:
    def test_returns_200(self, client):
        resp = client.get("/api/preferences")
        assert resp.status_code == 200

    def test_returns_preferences_dict(self, client):
        data = client.get("/api/preferences").get_json()
        assert isinstance(data, dict)


# ─────────────────────────────────────────────
# /api/optimizations
# ─────────────────────────────────────────────

class TestGetOptimizations:
    def test_returns_200(self, client):
        resp = client.get("/api/optimizations")
        assert resp.status_code == 200

    def test_includes_count(self, client):
        data = client.get("/api/optimizations").get_json()
        assert "count" in data
        assert data["count"] == 2


# ─────────────────────────────────────────────
# /api/status
# ─────────────────────────────────────────────

class TestGetStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_returns_status_field(self, client):
        data = client.get("/api/status").get_json()
        assert data["status"] == "active"


# ─────────────────────────────────────────────
# /api/apply-preferences
# ─────────────────────────────────────────────

class TestApplyPreferences:
    def test_returns_200_with_action(self, client):
        resp = client.post("/api/apply-preferences",
                           json={"action": "generate", "params": {}},
                           content_type="application/json")
        assert resp.status_code == 200

    def test_returns_optimized_params(self, client):
        data = client.post("/api/apply-preferences",
                           json={"action": "generate", "params": {}},
                           content_type="application/json").get_json()
        assert "optimized_params" in data

    def test_returns_400_without_action(self, client):
        resp = client.post("/api/apply-preferences",
                           json={"params": {}},
                           content_type="application/json")
        assert resp.status_code == 400


# ─────────────────────────────────────────────
# init_learning_system
# ─────────────────────────────────────────────

class TestInitLearningSystem:
    def test_creates_instance_on_first_call(self):
        assert api.learning_system is None
        result = api.init_learning_system()
        assert result is not None

    def test_returns_same_instance_on_second_call(self):
        s1 = api.init_learning_system()
        s2 = api.init_learning_system()
        assert s1 is s2
