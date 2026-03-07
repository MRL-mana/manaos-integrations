"""
Unit tests for scripts/misc/civitai_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

# ── module-level mocks ─────────────────────────────────────────────────────
# unified_logging (transitive via base_integration → config_validator_enhanced)
_ul = MagicMock()
_ul.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("unified_logging", _ul)

# config_validator_enhanced
_cve = MagicMock()
_cve.ConfigValidatorEnhanced = MagicMock(return_value=MagicMock(
    validate_config_file=MagicMock(return_value=(True, [], {}))
))
sys.modules.setdefault("config_validator_enhanced", _cve)

# manaos_logger
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# manaos_error_handler
_err_ret = MagicMock()
_err_ret.message = "err"
_err_ret.user_message = "err"
_eh = MagicMock()
_eh.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=_err_ret)
))
sys.modules.setdefault("manaos_error_handler", _eh)

# manaos_timeout_config (api_call, file_download)
sys.modules.setdefault(
    "manaos_timeout_config",
    MagicMock(get_timeout_config=MagicMock(return_value={"api_call": 10, "file_download": 60}))
)

# manaos_config_validator
sys.modules.setdefault(
    "manaos_config_validator",
    MagicMock(ConfigValidator=MagicMock(return_value=MagicMock(
        validate_config=MagicMock(return_value=(True, []))
    )))
)

import pytest
from scripts.misc.civitai_integration import CivitAIIntegration


def _make_response(json_data, status_code=200):
    m = MagicMock(status_code=status_code)
    m.json.return_value = json_data
    m.raise_for_status.return_value = None
    return m


@pytest.fixture
def ci():
    return CivitAIIntegration(api_key="test_api_key_xyz")


@pytest.fixture
def ci_no_key(monkeypatch):
    monkeypatch.delenv("CIVITAI_API_KEY", raising=False)
    return CivitAIIntegration(api_key=None)


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_api_key_stored(self, ci):
        assert ci.api_key == "test_api_key_xyz"

    def test_name_set(self, ci):
        assert ci.name == "CivitAI"

    def test_session_created(self, ci):
        import requests
        assert ci.session is not None

    def test_no_api_key_stored(self, ci_no_key):
        assert ci_no_key.api_key is None


# ── TestIsAvailable ────────────────────────────────────────────────────────
class TestIsAvailable:
    def test_true_when_api_key_set(self, ci):
        assert ci.is_available() is True

    def test_false_when_no_api_key(self, ci_no_key):
        assert ci_no_key.is_available() is False


# ── TestSearchModels ───────────────────────────────────────────────────────
class TestSearchModels:
    def test_returns_items_list(self, ci):
        models = [{"id": 1, "name": "Model A"}, {"id": 2, "name": "Model B"}]
        resp = _make_response({"items": models})
        with patch.object(ci.session, "get", return_value=resp):
            result = ci.search_models(query="anime")
        assert result == models

    def test_returns_empty_when_no_api_key(self, ci_no_key):
        result = ci_no_key.search_models()
        assert result == []

    def test_returns_empty_on_exception(self, ci):
        with patch.object(ci.session, "get", side_effect=Exception("network err")):
            result = ci.search_models()
        assert result == []

    def test_model_type_lora_normalized(self, ci):
        resp = _make_response({"items": []})
        with patch.object(ci.session, "get", return_value=resp) as mock_get:
            ci.search_models(model_type="lora")
        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {})
        assert params.get("types") == "LORA"


# ── TestGetModelDetails ────────────────────────────────────────────────────
class TestGetModelDetails:
    def test_returns_model_data(self, ci):
        model_data = {"id": 42, "name": "Test Model"}
        resp = _make_response(model_data)
        with patch.object(ci.session, "get", return_value=resp):
            result = ci.get_model_details(42)
        assert result == model_data

    def test_returns_none_when_no_key(self, ci_no_key):
        assert ci_no_key.get_model_details(1) is None

    def test_returns_none_on_error(self, ci):
        with patch.object(ci.session, "get", side_effect=Exception("err")):
            result = ci.get_model_details(99)
        assert result is None


# ── TestGetFavoriteModels ──────────────────────────────────────────────────
class TestGetFavoriteModels:
    def test_returns_items(self, ci):
        favs = [{"id": 10}, {"id": 20}]
        resp = _make_response({"items": favs})
        with patch.object(ci.session, "get", return_value=resp):
            result = ci.get_favorite_models()
        assert result == favs

    def test_empty_when_no_api_key(self, ci_no_key):
        assert ci_no_key.get_favorite_models() == []

    def test_limit_capped_at_100(self, ci):
        resp = _make_response({"items": []})
        with patch.object(ci.session, "get", return_value=resp) as mock_get:
            ci.get_favorite_models(limit=200)
        params_arg = mock_get.call_args[1].get("params", {})
        assert params_arg.get("limit") == 100


# ── TestGetImages ──────────────────────────────────────────────────────────
class TestGetImages:
    def test_returns_items(self, ci):
        images = [{"id": 1, "url": "http://example.com/img.jpg"}]
        resp = _make_response({"items": images})
        with patch.object(ci.session, "get", return_value=resp):
            result = ci.get_images(limit=5)
        assert result == images

    def test_returns_empty_when_no_key(self, ci_no_key):
        assert ci_no_key.get_images() == []

    def test_returns_empty_on_error(self, ci):
        with patch.object(ci.session, "get", side_effect=Exception("err")):
            result = ci.get_images()
        assert result == []
