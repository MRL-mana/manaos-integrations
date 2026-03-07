"""
Unit tests for scripts/misc/degraded_mode_system.py
"""
import sys
from unittest.mock import MagicMock

# ── module-level mocks ─────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh.ManaOSErrorHandler = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv.ConfigValidator = MagicMock(return_value=MagicMock(
    validate_config=MagicMock(return_value=(True, []))
))
sys.modules.setdefault("manaos_config_validator", _cv)

import pytest
from scripts.misc.degraded_mode_system import (
    DegradedModeSystem,
    DegradedModeLevel,
    ServiceStatus,
)


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def system(tmp_path):
    dms = DegradedModeSystem(config_path=tmp_path / "no_config.json")
    # isolate history file to tmp_path
    from pathlib import Path
    dms.mode_history_storage = tmp_path / "history.json"
    return dms


# ── TestDegradedModeLevel ──────────────────────────────────────────────────
class TestDegradedModeLevel:
    def test_values(self):
        assert DegradedModeLevel.NORMAL == "normal"
        assert DegradedModeLevel.DEGRADED == "degraded"
        assert DegradedModeLevel.MINIMAL == "minimal"
        assert DegradedModeLevel.EMERGENCY == "emergency"


# ── TestServiceStatus ──────────────────────────────────────────────────────
class TestServiceStatus:
    def test_fields(self):
        s = ServiceStatus(
            service_name="svc",
            available=True,
            degraded=False,
            fallback_available=True,
            last_check="2026-01-01T00:00:00",
        )
        assert s.service_name == "svc"
        assert s.available is True
        assert s.fallback_available is True


# ── TestLoadConfig ─────────────────────────────────────────────────────────
class TestLoadConfig:
    def test_default_config_has_required_keys(self, system):
        cfg = system.config
        assert "enable_degraded_mode" in cfg
        assert "degraded_threshold_cpu" in cfg
        assert "minimal_threshold_cpu" in cfg


# ── TestGetAvailableFeatures ───────────────────────────────────────────────
class TestGetAvailableFeatures:
    def test_normal_mode_all_true(self, system):
        system.current_mode = DegradedModeLevel.NORMAL
        features = system.get_available_features()
        assert features["llm_chat"] is True
        assert features["llm_reasoning"] is True
        assert features["cache_responses"] is True

    def test_degraded_mode_limits_features(self, system):
        system.current_mode = DegradedModeLevel.DEGRADED
        features = system.get_available_features()
        assert features["llm_chat"] is True
        assert features["llm_reasoning"] is False

    def test_minimal_mode_no_llm_chat(self, system):
        system.current_mode = DegradedModeLevel.MINIMAL
        features = system.get_available_features()
        assert features["llm_chat"] is False
        assert features["cache_responses"] is True

    def test_emergency_mode_most_disabled(self, system):
        system.current_mode = DegradedModeLevel.EMERGENCY
        features = system.get_available_features()
        assert features["llm_chat"] is False
        assert features["cache_responses"] is True
        assert features["memory_search"] is False


# ── TestCheckServiceAvailability ───────────────────────────────────────────
class TestCheckServiceAvailability:
    def test_returns_service_status(self, system):
        result = system.check_service_availability("test-service")
        assert isinstance(result, ServiceStatus)
        assert result.service_name == "test-service"

    def test_available_by_default(self, system):
        result = system.check_service_availability("svc-x")
        assert result.available is True

    def test_stored_in_service_statuses(self, system):
        system.check_service_availability("my-svc")
        assert "my-svc" in system.service_statuses


# ── TestGetStatus ──────────────────────────────────────────────────────────
class TestGetStatus:
    def test_returns_dict(self, system):
        status = system.get_status()
        assert isinstance(status, dict)

    def test_has_current_mode(self, system):
        status = system.get_status()
        assert "current_mode" in status
        assert status["current_mode"] == DegradedModeLevel.NORMAL.value

    def test_has_available_features(self, system):
        status = system.get_status()
        assert "available_features" in status

    def test_has_timestamp(self, system):
        status = system.get_status()
        assert "timestamp" in status
