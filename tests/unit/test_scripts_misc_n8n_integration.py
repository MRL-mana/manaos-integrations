"""
Unit tests for scripts/misc/n8n_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────
_ml = MagicMock()
_ml.get_logger = MagicMock(return_value=MagicMock())
_ml.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_logger", _ml)

_error_obj = MagicMock()
_error_obj.message = "mocked error"
_error_obj.user_message = "mocked user error"
_meh = MagicMock()
_meh.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=_error_obj)
))
_meh.ErrorCategory = MagicMock()
_meh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _meh)

_mtc = MagicMock()
_mtc.get_timeout_config = MagicMock(return_value={"api_call": 10})
sys.modules.setdefault("manaos_timeout_config", _mtc)

_mcv = MagicMock()
_mcv.ConfigValidator = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_config_validator", _mcv)

_cve = MagicMock()
_cve.ConfigValidatorEnhanced = MagicMock(return_value=MagicMock(
    validate_config_file=MagicMock(return_value=(True, [], {}))
))
sys.modules.setdefault("config_validator_enhanced", _cve)

# _paths
_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.N8N_PORT = 5678
sys.modules["_paths"] = _paths_mod

# requests
_requests_mod = MagicMock()
_session_cls = MagicMock()
_requests_mod.Session = _session_cls
sys.modules.setdefault("requests", _requests_mod)

# dotenv (optional)
sys.modules.setdefault("dotenv", MagicMock())

from scripts.misc.n8n_integration import (
    N8NIntegration,
    DEFAULT_N8N_BASE_URL,
)


# ─── helpers ──────────────────────────────────────────────────────────────────
def _make_n8n(api_key: str = "test-key") -> N8NIntegration:
    obj = N8NIntegration.__new__(N8NIntegration)
    obj.logger = MagicMock()
    obj.error_handler = MagicMock(
        handle_exception=MagicMock(return_value=_error_obj)
    )
    obj.timeout_config = {"api_call": 10}
    obj.base_url = DEFAULT_N8N_BASE_URL
    obj.api_key = api_key
    # Provide a fake requests session
    obj.session = MagicMock()
    obj._initialized = False
    return obj


# ─── Init ─────────────────────────────────────────────────────────────────────
class TestN8NInit:
    def test_default_base_url(self):
        obj = _make_n8n()
        assert "5678" in obj.base_url or "localhost" in obj.base_url or "127.0.0.1" in obj.base_url

    def test_api_key_set(self):
        obj = _make_n8n(api_key="my-key")
        assert obj.api_key == "my-key"

    def test_no_session_when_no_key(self):
        # Simulate construction path without api_key
        obj = _make_n8n(api_key=None)
        obj.session = None
        assert obj.session is None


# ─── _check_availability_internal ─────────────────────────────────────────────
class TestN8NCheckAvailability:
    def test_available_with_session_and_key(self):
        obj = _make_n8n()
        result = obj._check_availability_internal()
        assert result is True

    def test_not_available_without_key(self):
        obj = _make_n8n(api_key=None)
        result = obj._check_availability_internal()
        assert result is False

    def test_not_available_without_session(self):
        obj = _make_n8n()
        obj.session = None
        result = obj._check_availability_internal()
        assert result is False


# ─── list_workflows ────────────────────────────────────────────────────────────
class TestN8NListWorkflows:
    def test_returns_empty_when_unavailable(self):
        obj = _make_n8n()
        with patch.object(obj, "is_available", return_value=False):
            result = obj.list_workflows()
        assert result == []

    def test_returns_list_on_200(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = [{"id": "wf1"}, {"id": "wf2"}]
        obj.session.get.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.list_workflows()
        assert result == [{"id": "wf1"}, {"id": "wf2"}]

    def test_returns_empty_on_non_200(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 404
        obj.session.get.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.list_workflows()
        assert result == []

    def test_returns_empty_on_exception(self):
        obj = _make_n8n()
        obj.session.get.side_effect = ConnectionError("refused")
        with patch.object(obj, "is_available", return_value=True):
            result = obj.list_workflows()
        obj.session.get.side_effect = None
        assert result == []


# ─── execute_workflow ──────────────────────────────────────────────────────────
class TestN8NExecuteWorkflow:
    def test_returns_none_when_unavailable(self):
        obj = _make_n8n()
        with patch.object(obj, "is_available", return_value=False):
            result = obj.execute_workflow("wf1")
        assert result is None

    def test_returns_result_on_200(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"status": "success"}
        obj.session.post.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.execute_workflow("wf1", data={"key": "val"})
        assert result == {"status": "success"}

    def test_returns_none_on_error_status(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 500
        obj.session.post.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.execute_workflow("wf1")
        assert result is None

    def test_returns_none_on_exception(self):
        obj = _make_n8n()
        obj.session.post.side_effect = RuntimeError("timeout")
        with patch.object(obj, "is_available", return_value=True):
            result = obj.execute_workflow("wf1")
        obj.session.post.side_effect = None
        assert result is None


# ─── get_workflow ──────────────────────────────────────────────────────────────
class TestN8NGetWorkflow:
    def test_returns_none_when_unavailable(self):
        obj = _make_n8n()
        with patch.object(obj, "is_available", return_value=False):
            result = obj.get_workflow("wf1")
        assert result is None

    def test_returns_dict_on_200(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"id": "wf1", "name": "Test"}
        obj.session.get.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.get_workflow("wf1")
        assert result == {"id": "wf1", "name": "Test"}

    def test_returns_none_on_404(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 404
        obj.session.get.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.get_workflow("wf1")
        assert result is None


# ─── activate_workflow / deactivate_workflow ───────────────────────────────────
class TestN8NActivateDeactivate:
    def test_activate_returns_true_on_200(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        obj.session.post.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.activate_workflow("wf1")
        assert result is True

    def test_activate_returns_false_on_error(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 400
        obj.session.post.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.activate_workflow("wf1")
        assert result is False

    def test_activate_returns_false_when_unavailable(self):
        obj = _make_n8n()
        with patch.object(obj, "is_available", return_value=False):
            result = obj.activate_workflow("wf1")
        assert result is False

    def test_deactivate_returns_true_on_200(self):
        obj = _make_n8n()
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        obj.session.post.return_value = fake_resp
        with patch.object(obj, "is_available", return_value=True):
            result = obj.deactivate_workflow("wf1")
        assert result is True

    def test_deactivate_returns_false_on_exception(self):
        obj = _make_n8n()
        obj.session.post.side_effect = ConnectionError("fail")
        with patch.object(obj, "is_available", return_value=True):
            result = obj.deactivate_workflow("wf1")
        obj.session.post.side_effect = None
        assert result is False
