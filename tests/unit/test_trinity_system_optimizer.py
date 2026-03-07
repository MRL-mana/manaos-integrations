"""Unit tests for tools/trinity_system_optimizer.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import trinity_system_optimizer
from trinity_system_optimizer import TrinitySystemOptimizer


@pytest.fixture(autouse=True)
def _patch_systemctl(monkeypatch):
    """Windows 環境でも _SYSTEMCTL が非山 None となるようにパッチ。"""
    monkeypatch.setattr(trinity_system_optimizer, "_SYSTEMCTL", "/usr/bin/systemctl")


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sp_result(stdout: str, returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


# ─────────────────────────────────────────────────────────────────────────────
# __init__  —  services リストのデータ構造
# ─────────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_core_services_is_nonempty_list(self):
        opt = TrinitySystemOptimizer()
        assert isinstance(opt.core_services, list)
        assert len(opt.core_services) > 0

    def test_on_demand_services_is_nonempty_list(self):
        opt = TrinitySystemOptimizer()
        assert isinstance(opt.on_demand_services, list)
        assert len(opt.on_demand_services) > 0

    def test_core_services_are_strings(self):
        opt = TrinitySystemOptimizer()
        assert all(isinstance(s, str) for s in opt.core_services)


# ─────────────────────────────────────────────────────────────────────────────
# get_service_status  —  subprocess.run をモック
# ─────────────────────────────────────────────────────────────────────────────

class TestGetServiceStatus:
    def setup_method(self):
        self.opt = TrinitySystemOptimizer()

    def test_active_enabled_service(self):
        with patch("subprocess.run",
                   side_effect=[_sp_result("active"), _sp_result("enabled")]):
            result = self.opt.get_service_status("test.service")
        assert result["active"] is True
        assert result["enabled"] is True
        assert result["name"] == "test.service"

    def test_inactive_disabled_service(self):
        with patch("subprocess.run",
                   side_effect=[_sp_result("inactive"), _sp_result("disabled")]):
            result = self.opt.get_service_status("test.service")
        assert result["active"] is False
        assert result["enabled"] is False

    def test_active_but_not_enabled(self):
        with patch("subprocess.run",
                   side_effect=[_sp_result("active"), _sp_result("static")]):
            result = self.opt.get_service_status("hybrid.service")
        assert result["active"] is True
        assert result["enabled"] is False

    def test_subprocess_error_returns_safe_dict(self):
        with patch("subprocess.run", side_effect=OSError("not found")):
            result = self.opt.get_service_status("broken.service")
        assert result["active"] is False
        assert result["enabled"] is False
        assert "error" in result

    def test_name_preserved_on_success(self):
        with patch("subprocess.run",
                   side_effect=[_sp_result("inactive"), _sp_result("disabled")]):
            result = self.opt.get_service_status("my.service")
        assert result["name"] == "my.service"

    def test_name_preserved_on_error(self):
        with patch("subprocess.run", side_effect=OSError("x")):
            result = self.opt.get_service_status("err.service")
        assert result["name"] == "err.service"

    def test_status_field_set_from_stdout(self):
        with patch("subprocess.run",
                   side_effect=[_sp_result("failed"), _sp_result("enabled")]):
            result = self.opt.get_service_status("failed.service")
        assert result["status"] == "failed"


# ─────────────────────────────────────────────────────────────────────────────
# create_optimization_report  —  get_service_status を patch して JSON 検証
# ─────────────────────────────────────────────────────────────────────────────

def _mock_status(name: str) -> dict:
    return {"name": name, "active": False, "enabled": False, "status": "inactive"}


class TestCreateOptimizationReport:
    def setup_method(self):
        self.opt = TrinitySystemOptimizer()

    def test_returns_valid_json_string(self):
        with patch.object(self.opt, "get_service_status", side_effect=_mock_status):
            report_str = self.opt.create_optimization_report()
        parsed = json.loads(report_str)
        assert isinstance(parsed, dict)

    def test_report_contains_timestamp(self):
        with patch.object(self.opt, "get_service_status", side_effect=_mock_status):
            report_str = self.opt.create_optimization_report()
        parsed = json.loads(report_str)
        assert "timestamp" in parsed

    def test_report_optimization_status_completed(self):
        with patch.object(self.opt, "get_service_status", side_effect=_mock_status):
            report_str = self.opt.create_optimization_report()
        parsed = json.loads(report_str)
        assert parsed["optimization_status"] == "completed"

    def test_all_core_services_in_report(self):
        with patch.object(self.opt, "get_service_status", side_effect=_mock_status):
            report_str = self.opt.create_optimization_report()
        parsed = json.loads(report_str)
        for svc in self.opt.core_services:
            assert svc in parsed["core_services"]

    def test_all_on_demand_services_in_report(self):
        with patch.object(self.opt, "get_service_status", side_effect=_mock_status):
            report_str = self.opt.create_optimization_report()
        parsed = json.loads(report_str)
        for svc in self.opt.on_demand_services:
            assert svc in parsed["on_demand_services"]

    def test_core_services_dict_in_report(self):
        with patch.object(self.opt, "get_service_status", side_effect=_mock_status):
            report_str = self.opt.create_optimization_report()
        parsed = json.loads(report_str)
        assert isinstance(parsed["core_services"], dict)
