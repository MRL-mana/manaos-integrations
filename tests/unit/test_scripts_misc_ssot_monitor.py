"""
Unit tests for scripts/misc/ssot_monitor.py
"""
import sys
import types
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────
sys.modules.setdefault("manaos_logger", MagicMock(
    get_logger=MagicMock(return_value=MagicMock()),
    get_service_logger=MagicMock(return_value=MagicMock()),
))
sys.modules.setdefault("manaos_error_handler", MagicMock(
    ManaOSErrorHandler=MagicMock(return_value=MagicMock(
        handle_exception=MagicMock(return_value=MagicMock(message="err"))
    )),
    ErrorCategory=MagicMock(),
    ErrorSeverity=MagicMock(),
))

_pm_instance = MagicMock()
_pm_instance.get_process_info = MagicMock(return_value=None)
_pm_instance.save_process_info = MagicMock()
_pm_instance.cleanup_process = MagicMock()
_pm_mod = types.ModuleType("manaos_process_manager")
_pm_mod.ProcessManager = MagicMock(return_value=_pm_instance)  # type: ignore
sys.modules["manaos_process_manager"] = _pm_mod

sys.modules.setdefault("psutil", MagicMock())
sys.modules.setdefault("httpx", MagicMock())

import scripts.misc.ssot_monitor as sm


@pytest.fixture(autouse=True)
def reset_pm():
    _pm_instance.get_process_info.reset_mock()
    _pm_instance.save_process_info.reset_mock()
    _pm_instance.cleanup_process.reset_mock()
    yield


# ─────────────────────────────────────────────
# SSOTMonitor.__init__
# ─────────────────────────────────────────────

class TestInit:
    def test_defaults(self):
        m = sm.SSOTMonitor()
        assert m.restart_count == 0
        assert m.last_restart_time is None
        assert m.process_pid is None
        assert m.monitoring is False


# ─────────────────────────────────────────────
# check_ssot_generator_running
# ─────────────────────────────────────────────

class TestCheckSsotGeneratorRunning:
    def test_returns_false_when_no_process(self):
        _pm_instance.get_process_info.return_value = None
        m = sm.SSOTMonitor()
        assert m.check_ssot_generator_running() is False

    def test_returns_true_and_sets_pid(self):
        _pm_instance.get_process_info.return_value = {"pid": 1234}
        m = sm.SSOTMonitor()
        result = m.check_ssot_generator_running()
        assert result is True
        assert m.process_pid == 1234

    def test_returns_false_on_exception(self):
        _pm_instance.get_process_info.side_effect = RuntimeError("fail")
        m = sm.SSOTMonitor()
        result = m.check_ssot_generator_running()
        assert result is False
        _pm_instance.get_process_info.side_effect = None


# ─────────────────────────────────────────────
# check_ssot_file_fresh
# ─────────────────────────────────────────────

class TestCheckSsotFileFresh:
    def test_returns_false_when_file_missing(self, tmp_path):
        m = sm.SSOTMonitor()
        with patch.object(sm, "SSOT_FILE", tmp_path / "nonexistent.json"):
            result = m.check_ssot_file_fresh()
        assert result is False

    def test_returns_true_when_file_just_written(self, tmp_path):
        ssot_file = tmp_path / "manaos_status.json"
        ssot_file.write_text("{}")
        m = sm.SSOTMonitor()
        with patch.object(sm, "SSOT_FILE", ssot_file):
            result = m.check_ssot_file_fresh()
        assert result is True

    def test_returns_false_when_file_old(self, tmp_path):
        ssot_file = tmp_path / "manaos_status.json"
        ssot_file.write_text("{}")
        m = sm.SSOTMonitor()
        with patch.object(sm, "SSOT_FILE", ssot_file), \
             patch("time.time", return_value=ssot_file.stat().st_mtime + 10):
            result = m.check_ssot_file_fresh()
        assert result is False


# ─────────────────────────────────────────────
# start_ssot_generator
# ─────────────────────────────────────────────

class TestStartSsotGenerator:
    def test_returns_false_when_script_missing(self):
        m = sm.SSOTMonitor()
        with patch("pathlib.Path.exists", return_value=False):
            result = m.start_ssot_generator()
        assert result is False

    def test_returns_true_on_success(self):
        mock_process = MagicMock()
        mock_process.pid = 9999

        m = sm.SSOTMonitor()
        with patch("pathlib.Path.exists", return_value=True), \
             patch("scripts.misc.ssot_monitor.subprocess.Popen",
                   return_value=mock_process), \
             patch("time.sleep"):
            result = m.start_ssot_generator()

        assert result is True
        assert m.process_pid == 9999

    def test_returns_false_on_exception(self):
        m = sm.SSOTMonitor()
        with patch("pathlib.Path.exists", return_value=True), \
             patch("scripts.misc.ssot_monitor.subprocess.Popen",
                   side_effect=OSError("cannot start")):
            result = m.start_ssot_generator()
        assert result is False


# ─────────────────────────────────────────────
# restart_ssot_generator
# ─────────────────────────────────────────────

class TestRestartSsotGenerator:
    def test_returns_false_when_max_restarts_reached(self):
        m = sm.SSOTMonitor()
        m.restart_count = sm.MAX_RESTARTS
        result = m.restart_ssot_generator()
        assert result is False

    def test_increments_restart_count_on_success(self):
        mock_process = MagicMock()
        mock_process.pid = 1111

        m = sm.SSOTMonitor()
        with patch("pathlib.Path.exists", return_value=True), \
             patch("scripts.misc.ssot_monitor.subprocess.Popen",
                   return_value=mock_process), \
             patch("time.sleep"):
            result = m.restart_ssot_generator()

        assert result is True
        assert m.restart_count == 1
        assert m.last_restart_time is not None

    def test_waits_for_delay_if_too_soon(self):
        m = sm.SSOTMonitor()
        m.last_restart_time = datetime.now()  # just now

        mock_process = MagicMock()
        mock_process.pid = 2222

        sleep_calls = []
        with patch("pathlib.Path.exists", return_value=True), \
             patch("scripts.misc.ssot_monitor.subprocess.Popen",
                   return_value=mock_process), \
             patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            m.restart_ssot_generator()

        # At least one sleep should have been called
        assert len(sleep_calls) >= 1


# ─────────────────────────────────────────────
# stop
# ─────────────────────────────────────────────

class TestStop:
    def test_sets_monitoring_false(self):
        m = sm.SSOTMonitor()
        m.monitoring = True
        m.stop()
        assert m.monitoring is False
