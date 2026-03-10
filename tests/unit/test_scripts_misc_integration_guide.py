"""Tests for scripts/misc/integration_guide.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_logging_stub():
    mod = types.ModuleType("unified_logging")
    log = MagicMock()
    mod.get_service_logger = MagicMock(return_value=log)  # type: ignore
    return mod, log


def _prep(monkeypatch):
    sys.modules.pop("integration_guide", None)
    log_mod, log = _make_logging_stub()
    monkeypatch.setitem(sys.modules, "unified_logging", log_mod)
    monkeypatch.syspath_prepend(str(_MISC))
    import integration_guide as m
    return m, log


class TestIntegrationGuideImport:
    def test_imports(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "integration_guide" in sys.modules

    def test_has_all_functions(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        for fn in ("integrate_security_to_flask_app", "integrate_gpu_manager",
                   "integrate_cache", "integrate_backup_system", "integrate_metrics_collector"):
            assert callable(getattr(m, fn))


class TestIntegrateSecurityToFlaskApp:
    def test_success(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        mock_app = MagicMock()
        mock_security = MagicMock()
        sec_config = MagicMock()
        mock_security.SecurityConfig = MagicMock(return_value=sec_config)
        with patch.dict(sys.modules, {"manaos_security": mock_security}):
            m.integrate_security_to_flask_app(mock_app)
        sec_config.apply_security.assert_called_once_with(mock_app)

    def test_import_error_handled(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        with patch.dict(sys.modules, {"manaos_security": None}):
            m.integrate_security_to_flask_app(MagicMock())  # should not raise


class TestIntegrateGpuManager:
    def test_returns_manager_on_success(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        mock_manager = MagicMock()
        mock_gpu = types.ModuleType("gpu_resource_manager")
        mock_gpu.get_gpu_manager = MagicMock(return_value=mock_manager)  # type: ignore
        with patch.dict(sys.modules, {"gpu_resource_manager": mock_gpu}):
            result = m.integrate_gpu_manager()
        assert result is mock_manager

    def test_returns_none_on_error(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        with patch.dict(sys.modules, {"gpu_resource_manager": None}):
            result = m.integrate_gpu_manager()
        assert result is None


class TestIntegrateCache:
    def test_returns_cache_on_success(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        mock_cache = MagicMock()
        mock_mod = types.ModuleType("intelligent_cache")
        mock_mod.get_cache = MagicMock(return_value=mock_cache)  # type: ignore
        with patch.dict(sys.modules, {"intelligent_cache": mock_mod}):
            result = m.integrate_cache()
        assert result is mock_cache

    def test_returns_none_on_error(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        with patch.dict(sys.modules, {"intelligent_cache": None}):
            result = m.integrate_cache()
        assert result is None


class TestIntegrateBackupSystem:
    def test_returns_backup_on_success(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        mock_backup = MagicMock()
        mock_mod = types.ModuleType("auto_backup_system")
        mock_mod.get_backup_system = MagicMock(return_value=mock_backup)  # type: ignore
        with patch.dict(sys.modules, {"auto_backup_system": mock_mod}):
            result = m.integrate_backup_system()
        assert result is mock_backup

    def test_returns_none_on_error(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        with patch.dict(sys.modules, {"auto_backup_system": None}):
            result = m.integrate_backup_system()
        assert result is None


class TestIntegrateMetricsCollector:
    def test_returns_collector_on_success(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        mock_col = MagicMock()
        mock_mod = types.ModuleType("metrics_collector")
        mock_mod.get_metrics_collector = MagicMock(return_value=mock_col)  # type: ignore
        with patch.dict(sys.modules, {"metrics_collector": mock_mod}):
            result = m.integrate_metrics_collector()
        assert result is mock_col

    def test_returns_none_on_error(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        with patch.dict(sys.modules, {"metrics_collector": None}):
            result = m.integrate_metrics_collector()
        assert result is None
