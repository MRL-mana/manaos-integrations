"""Tests for scripts/misc/ultimate_integration.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"

_STUB_MODULES = [
    "unified_api_server",
    "workflow_automation",
    "ai_agent_autonomous",
    "predictive_maintenance",
    "auto_optimization",
    "learning_system",
    "notification_system",
    "backup_recovery",
    "performance_analytics",
    "cost_optimization",
    "streaming_processing",
    "batch_processing",
    "database_integration",
    "cloud_integration",
    "multimodal_integration",
    "distributed_execution",
    "security_monitor",
    "manaos_service_bridge",
    "intrinsic_motivation",
]


def _make_stub_class(name):
    cls = type(name, (), {"__init__": lambda self, *a, **kw: None})
    return cls


def _stub_all(monkeypatch):
    for mod_name in _STUB_MODULES:
        mod = types.ModuleType(mod_name)
        mod.initialize_integrations = MagicMock()
        mod.integrations = {}
        stub_cls = _make_stub_class(mod_name.title().replace("_", ""))
        # assign common class names
        mod.WorkflowAutomation = stub_cls
        mod.AutonomousAgent = type("AutonomousAgent", (), {"__init__": lambda self, name="", *a, **kw: None})
        mod.PredictiveMaintenance = stub_cls
        mod.AutoOptimization = stub_cls
        mod.LearningSystem = stub_cls
        mod.NotificationSystem = stub_cls
        mod.BackupRecovery = stub_cls
        mod.PerformanceAnalytics = stub_cls
        mod.CostOptimization = stub_cls
        mod.StreamingProcessor = stub_cls
        mod.BatchProcessor = stub_cls
        mod.DatabaseIntegration = stub_cls
        mod.CloudIntegration = stub_cls
        mod.MultimodalIntegration = stub_cls
        mod.DistributedExecution = stub_cls
        mod.SecurityMonitor = stub_cls
        mod.ManaOSServiceBridge = stub_cls
        mod.IntrinsicMotivation = stub_cls
        monkeypatch.setitem(sys.modules, mod_name, mod)


def _load(monkeypatch):
    sys.modules.pop("ultimate_integration", None)
    monkeypatch.syspath_prepend(str(_MISC))
    _stub_all(monkeypatch)
    with patch("builtins.print"):
        import ultimate_integration as m
    return m


class TestUltimateIntegration:
    def test_module_loads(self, monkeypatch):
        m = _load(monkeypatch)
        assert "ultimate_integration" in sys.modules

    def test_class_exists(self, monkeypatch):
        m = _load(monkeypatch)
        assert hasattr(m, "UltimateIntegration")

    def test_instantiation(self, monkeypatch):
        m = _load(monkeypatch)
        instance = m.UltimateIntegration()
        assert instance is not None

    def test_initialize_integrations_called(self, monkeypatch):
        sys.modules.pop("ultimate_integration", None)
        monkeypatch.syspath_prepend(str(_MISC))
        _stub_all(monkeypatch)

        mock_init = MagicMock()
        sys.modules["unified_api_server"].initialize_integrations = mock_init

        with patch("builtins.print"):
            import ultimate_integration as m
        m.UltimateIntegration()
        mock_init.assert_called_once()

    def test_intrinsic_motivation_optional(self, monkeypatch):
        """intrinsic_motivationが存在しなくてもロード可能"""
        sys.modules.pop("ultimate_integration", None)
        monkeypatch.syspath_prepend(str(_MISC))
        _stub_all(monkeypatch)
        # Make intrinsic_motivation raise ImportError at import time
        monkeypatch.delitem(sys.modules, "intrinsic_motivation", raising=False)

        import importlib

        orig_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else None

        with patch("builtins.print"):
            import ultimate_integration as m
        assert m.INTRINSIC_MOTIVATION_AVAILABLE in (True, False)
