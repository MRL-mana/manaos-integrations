"""
Unit tests for scripts/misc/manaos_integration_monitor.py
（Flask app + check_all_integrations / analyze_performance）
"""
import sys
from unittest.mock import MagicMock

import pytest

# ─── Module-level mocking (before import) ─────────────────────────────────────
# Flask / CORS
_flask_mod = MagicMock()
_flask_app_inst = MagicMock()
_flask_mod.Flask.return_value = _flask_app_inst
_flask_mod.jsonify.side_effect = lambda x: x  # jsonify returns the dict itself
sys.modules.setdefault("flask", _flask_mod)
sys.modules.setdefault("flask_cors", MagicMock())

# manaos_logger
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# manaos_error_handler
_meh_mod = MagicMock()
_error_obj = MagicMock()
_error_obj.message = "test error"
_error_obj.user_message = "テストエラー"
_meh_mod.ManaOSErrorHandler.return_value.handle_exception.return_value = _error_obj
sys.modules.setdefault("manaos_error_handler", _meh_mod)

# manaos_unified_client
_client_inst = MagicMock()
_muc_mod = MagicMock()
_muc_mod.get_unified_client.return_value = _client_inst
sys.modules["manaos_unified_client"] = _muc_mod

# manaos_service_bridge
_bridge_inst = MagicMock()
_msb_mod = MagicMock()
_msb_mod.ManaOSServiceBridge.return_value = _bridge_inst
sys.modules["manaos_service_bridge"] = _msb_mod

# Remove cached module if present
sys.modules.pop("scripts.misc.manaos_integration_monitor", None)

from scripts.misc.manaos_integration_monitor import (  # noqa: E402
    check_all_integrations,
    analyze_performance,
)


# ─── check_all_integrations ───────────────────────────────────────────────────
class TestCheckAllIntegrations:
    def setup_method(self):
        _client_inst.reset_mock()
        _bridge_inst.reset_mock()

    def test_returns_dict_with_expected_keys(self):
        _client_inst.check_all_services.return_value = {"ollama": "ok"}
        _bridge_inst.get_integration_status.return_value = {"n8n": "connected"}
        _client_inst.get_stats.return_value = {"total_requests": 10}

        result = check_all_integrations()

        assert "services" in result
        assert "integrations" in result
        assert "client_stats" in result
        assert "timestamp" in result

    def test_services_value_matches_client(self):
        _client_inst.check_all_services.return_value = {"svc": "up"}
        _bridge_inst.get_integration_status.return_value = {}
        _client_inst.get_stats.return_value = {}

        result = check_all_integrations()
        assert result["services"] == {"svc": "up"}

    def test_integrations_value_matches_bridge(self):
        _client_inst.check_all_services.return_value = {}
        _bridge_inst.get_integration_status.return_value = {"n8n": "ok"}
        _client_inst.get_stats.return_value = {}

        result = check_all_integrations()
        assert result["integrations"] == {"n8n": "ok"}

    def test_returns_error_key_when_exception(self):
        _client_inst.check_all_services.side_effect = RuntimeError("network down")

        result = check_all_integrations()

        assert "error" in result
        assert "timestamp" in result
        # error should be non-empty string
        assert result["error"]

        # Cleanup side_effect for subsequent tests
        _client_inst.check_all_services.side_effect = None


# ─── analyze_performance ──────────────────────────────────────────────────────
class TestAnalyzePerformance:
    def setup_method(self):
        _client_inst.reset_mock()

    def test_returns_performance_keys(self):
        _client_inst.get_stats.return_value = {
            "success_rate": 95.0,
            "cache_hits": 80,
            "cache_misses": 20,
            "total_requests": 100,
            "retry_count": 2,
        }
        result = analyze_performance()
        assert "success_rate" in result
        assert "cache_hit_rate" in result
        assert "total_requests" in result
        assert "suggestions" in result

    def test_cache_hit_rate_calculated_correctly(self):
        _client_inst.get_stats.return_value = {
            "success_rate": 100.0,
            "cache_hits": 60,
            "cache_misses": 40,
            "total_requests": 100,
            "retry_count": 0,
        }
        result = analyze_performance()
        assert abs(result["cache_hit_rate"] - 60.0) < 0.01

    def test_zero_cache_ops_no_division_error(self):
        _client_inst.get_stats.return_value = {
            "success_rate": 100.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_requests": 0,
            "retry_count": 0,
        }
        result = analyze_performance()
        assert result["cache_hit_rate"] == 0

    def test_low_success_rate_generates_warning(self):
        _client_inst.get_stats.return_value = {
            "success_rate": 80.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_requests": 10,
            "retry_count": 0,
        }
        result = analyze_performance()
        types = [s["type"] for s in result["suggestions"]]
        assert "warning" in types

    def test_high_retry_rate_generates_warning(self):
        _client_inst.get_stats.return_value = {
            "success_rate": 95.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_requests": 100,
            "retry_count": 20,  # 20% > 10% threshold
        }
        result = analyze_performance()
        types = [s["type"] for s in result["suggestions"]]
        assert "warning" in types

    def test_returns_error_key_when_exception(self):
        _client_inst.get_stats.side_effect = RuntimeError("stats failure")
        result = analyze_performance()
        assert "error" in result
        assert "timestamp" in result
        _client_inst.get_stats.side_effect = None
