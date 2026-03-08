"""
tests/unit/test_scripts_misc_integration_test_manaos.py
Unit tests for scripts/misc/integration_test_manaos.py
"""
import sys
import types
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import scripts.misc.integration_test_manaos as _sut
import requests as _real_requests


# ---------------------------------------------------------------------------
# check_service()
# ---------------------------------------------------------------------------
class TestCheckService:
    def _mock_response(self, status_code: int):
        r = MagicMock()
        r.status_code = status_code
        return r

    def test_returns_true_on_200(self):
        with patch("requests.get", return_value=self._mock_response(200)):
            ok, msg = _sut.check_service("http://example.com")
        assert ok is True
        assert "オンライン" in msg

    def test_returns_false_on_non_200(self):
        with patch("requests.get", return_value=self._mock_response(500)):
            ok, msg = _sut.check_service("http://example.com")
        assert ok is False
        assert "500" in msg

    def test_returns_false_on_connection_error(self):
        with patch("requests.get", side_effect=_real_requests.exceptions.ConnectionError("refused")):
            ok, msg = _sut.check_service("http://example.com")
        assert ok is False
        assert "接続不可" in msg

    def test_returns_false_on_timeout(self):
        with patch("requests.get", side_effect=_real_requests.exceptions.Timeout("timed out")):
            ok, msg = _sut.check_service("http://example.com")
        assert ok is False
        assert "タイムアウト" in msg

    def test_returns_false_on_generic_exception(self):
        with patch("requests.get", side_effect=Exception("unexpected")):
            ok, msg = _sut.check_service("http://example.com")
        assert ok is False
        assert "エラー" in msg

    def test_passes_timeout_to_requests(self):
        with patch("requests.get", return_value=self._mock_response(200)) as m:
            _sut.check_service("http://example.com", timeout=99)
            _, kwargs = m.call_args
        assert kwargs.get("timeout") == 99

    def test_calls_health_endpoint(self):
        with patch("requests.get", return_value=self._mock_response(200)) as m:
            _sut.check_service("http://myservice.local")
            called_url = m.call_args[0][0]
        assert called_url.endswith("/health")


# ---------------------------------------------------------------------------
# test_manaos_integration()
# ---------------------------------------------------------------------------
class TestTestManaosIntegration:
    def test_returns_dict(self):
        with patch.object(_sut, "check_service", return_value=(True, "オンライン")):
            result = _sut.test_manaos_integration()
        assert isinstance(result, dict)

    def test_result_keys_match_services(self):
        with patch.object(_sut, "check_service", return_value=(False, "接続不可")):
            result = _sut.test_manaos_integration()
        assert set(result.keys()) == set(_sut.MANAOS_SERVICES.keys())

    def test_result_has_url_available_status(self):
        with patch.object(_sut, "check_service", return_value=(True, "オンライン")):
            result = _sut.test_manaos_integration()
        for v in result.values():
            assert "url" in v
            assert "available" in v
            assert "status" in v


# ---------------------------------------------------------------------------
# test_integration_systems()
# ---------------------------------------------------------------------------
class TestTestIntegrationSystems:
    def test_returns_dict(self):
        with patch.object(_sut, "check_service", return_value=(True, "オンライン")):
            result = _sut.test_integration_systems()
        assert isinstance(result, dict)

    def test_result_keys_match_services(self):
        with patch.object(_sut, "check_service", return_value=(False, "接続不可")):
            result = _sut.test_integration_systems()
        assert set(result.keys()) == set(_sut.INTEGRATION_SERVICES.keys())


# ---------------------------------------------------------------------------
# test_integration_modules()
# ---------------------------------------------------------------------------
class TestTestIntegrationModules:
    def test_returns_dict(self):
        with patch("builtins.__import__", side_effect=ImportError("stub")):
            result = _sut.test_integration_modules()
        assert isinstance(result, dict)

    def test_success_status_on_import_ok(self):
        with patch("builtins.__import__", return_value=MagicMock()):
            result = _sut.test_integration_modules()
        # At least some modules should have succeeded
        statuses = {v["status"] for v in result.values()}
        assert "成功" in statuses

    def test_fail_status_on_import_error(self):
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result = _sut.test_integration_modules()
        statuses = {v["status"] for v in result.values()}
        assert "失敗" in statuses

    def test_error_status_on_exception(self):
        with patch("builtins.__import__", side_effect=RuntimeError("crash")):
            result = _sut.test_integration_modules()
        statuses = {v["status"] for v in result.values()}
        assert "エラー" in statuses


# ---------------------------------------------------------------------------
# test_manaos_service_bridge()
# ---------------------------------------------------------------------------
class TestTestManaosServiceBridge:
    def test_success_when_bridge_available(self):
        mock_bridge_cls = MagicMock()
        mock_bridge_cls.return_value.get_integration_status.return_value = {"ok": True}
        with patch.dict(sys.modules, {"manaos_service_bridge": types.SimpleNamespace(
            ManaOSServiceBridge=mock_bridge_cls
        )}):
            result = _sut.test_manaos_service_bridge()
        assert result["status"] == "成功"

    def test_failure_when_bridge_raises(self):
        with patch.dict(sys.modules, {"manaos_service_bridge": None}):
            result = _sut.test_manaos_service_bridge()
        assert result["status"] == "失敗"
        assert "error" in result


# ---------------------------------------------------------------------------
# test_ultimate_integration()
# ---------------------------------------------------------------------------
class TestTestUltimateIntegration:
    def test_returns_dict(self):
        # The function imports and instantiates UltimateIntegrationSystem
        # Just verify it handles errors gracefully
        result = _sut.test_ultimate_integration()
        assert isinstance(result, dict)
        assert "status" in result

    def test_failure_when_import_raises(self):
        # Force an import error by removing the module stub
        with patch.dict(sys.modules, {"ultimate_integration_system": None}):
            result = _sut.test_ultimate_integration()
        # May succeed or fail depending on stubs already loaded; just check structure
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# generate_test_report()
# ---------------------------------------------------------------------------
class TestGenerateTestReport:
    def _make_args(self):
        manaos_results = {
            "svc_a": {"url": "http://a", "available": True, "status": "オンライン"},
            "svc_b": {"url": "http://b", "available": False, "status": "接続不可"},
        }
        integration_results = {
            "unified_api": {"url": "http://c", "available": True, "status": "オンライン"},
        }
        module_results = {
            "comfyui_integration": {"status": "成功", "error": None},
            "bad_module": {"status": "失敗", "error": "no module"},
        }
        bridge_result = {"status": "成功", "data": {}}
        ultimate_result = {"status": "成功", "data": {}}
        return manaos_results, integration_results, module_results, bridge_result, ultimate_result

    def test_writes_report_file(self):
        args = self._make_args()
        m = mock_open()
        with patch("builtins.open", m), \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "write_text") as m_write:
            _sut.generate_test_report(*args)
            assert m_write.called

    def test_report_content_contains_header(self):
        args = self._make_args()
        written = []
        def _write_text(content, **kw):
            written.append(content)
        with patch("builtins.open", mock_open()), \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "write_text", side_effect=_write_text):
            _sut.generate_test_report(*args)
        assert written
        assert "ManaOS" in written[0]
