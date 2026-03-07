"""Unit tests for tools/trinity_service_manager.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_service_manager import TrinityServiceManager


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sp(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


# ─────────────────────────────────────────────────────────────────────────────
# __init__  —  サービス辞書の検証
# ─────────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_on_demand_services_is_dict(self):
        sm = TrinityServiceManager()
        assert isinstance(sm.on_demand_services, dict)

    def test_known_aliases_present(self):
        sm = TrinityServiceManager()
        assert "image-generator" in sm.on_demand_services
        assert "auto-backup" in sm.on_demand_services

    def test_values_are_service_unit_strings(self):
        sm = TrinityServiceManager()
        for alias, unit in sm.on_demand_services.items():
            assert unit.endswith(".service"), f"'{alias}' → '{unit}' should end with .service"


# ─────────────────────────────────────────────────────────────────────────────
# start_service
# ─────────────────────────────────────────────────────────────────────────────

class TestStartService:
    def setup_method(self):
        self.sm = TrinityServiceManager()

    def test_success_returns_true(self):
        with patch("subprocess.run", return_value=_sp(returncode=0)):
            assert self.sm.start_service("image-generator") is True

    def test_failure_returns_false(self):
        with patch("subprocess.run", return_value=_sp(returncode=1, stderr="fail")):
            assert self.sm.start_service("image-generator") is False

    def test_exception_returns_false(self):
        with patch("subprocess.run", side_effect=OSError("perm denied")):
            assert self.sm.start_service("image-generator") is False

    def test_unknown_service_passed_directly(self):
        """エイリアス未登録の名前はそのまま systemctl に渡される。"""
        captured = []

        def fake_run(args, **kwargs):
            captured.append(args)
            return _sp(0)

        with patch("subprocess.run", side_effect=fake_run):
            self.sm.start_service("custom.service")

        assert "custom.service" in captured[0]

    def test_alias_resolved_before_run(self):
        """エイリアス名は実際のユニット名に解決される。"""
        captured = []

        def fake_run(args, **kwargs):
            captured.append(args)
            return _sp(0)

        with patch("subprocess.run", side_effect=fake_run):
            self.sm.start_service("image-generator")

        assert "trinity-image-generator.service" in captured[0]


# ─────────────────────────────────────────────────────────────────────────────
# stop_service
# ─────────────────────────────────────────────────────────────────────────────

class TestStopService:
    def setup_method(self):
        self.sm = TrinityServiceManager()

    def test_success_returns_true(self):
        with patch("subprocess.run", return_value=_sp(0)):
            assert self.sm.stop_service("auto-backup") is True

    def test_failure_returns_false(self):
        with patch("subprocess.run", return_value=_sp(1)):
            assert self.sm.stop_service("auto-backup") is False

    def test_exception_returns_false(self):
        with patch("subprocess.run", side_effect=Exception("broken")):
            assert self.sm.stop_service("auto-backup") is False


# ─────────────────────────────────────────────────────────────────────────────
# status_service
# ─────────────────────────────────────────────────────────────────────────────

class TestStatusService:
    def setup_method(self):
        self.sm = TrinityServiceManager()

    def test_active_service_status_true(self):
        with patch("subprocess.run", return_value=_sp(0, stdout="active")):
            result = self.sm.status_service("image-generator")
        assert result["status"] is True
        assert result["name"] == "image-generator"

    def test_inactive_service_status_false(self):
        with patch("subprocess.run", return_value=_sp(3, stdout="inactive")):
            result = self.sm.status_service("image-generator")
        assert result["status"] is False

    def test_alias_resolved_in_actual_name(self):
        with patch("subprocess.run", return_value=_sp(0)):
            result = self.sm.status_service("image-generator")
        assert result["actual_name"] == "trinity-image-generator.service"

    def test_exception_returns_error_dict(self):
        with patch("subprocess.run", side_effect=OSError("broken")):
            result = self.sm.status_service("fail-service")
        assert "error" in result
        assert result["name"] == "fail-service"

    def test_output_field_present(self):
        with patch("subprocess.run", return_value=_sp(0, stdout="service output")):
            result = self.sm.status_service("calendar-reminder")
        assert "output" in result
