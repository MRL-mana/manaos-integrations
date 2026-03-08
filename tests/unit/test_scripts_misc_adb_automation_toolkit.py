"""
tests/unit/test_scripts_misc_adb_automation_toolkit.py
ADBAutomationToolkit のユニットテスト
"""

import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest

# ── hard import のモック（manaos_logger のみ） ──────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# ── モジュールをインポート ──────────────────────────────────────────────
import importlib
import scripts.misc.adb_automation_toolkit as _sut
from scripts.misc.adb_automation_toolkit import (
    DeviceInfo,
    BatteryAlert,
    ADBAutomationToolkit,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Fixture
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture
def toolkit(tmp_path):
    cfg_file = tmp_path / "adb_config.json"
    mock_sub = MagicMock()
    mock_sub.returncode = 1
    mock_sub.stdout = b""
    with patch("subprocess.run", return_value=mock_sub):
        t = ADBAutomationToolkit(config_path=str(cfg_file))
    t.adb_path = "/fake/adb"
    return t


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestDeviceInfo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDeviceInfo:
    def test_init_fields(self):
        d = DeviceInfo(
            device_id="192.168.1.1:5555",
            model="Pixel 7",
            android_version="13",
            battery_level=80,
            battery_status="3",
            screen_on=True,
            connected=True,
        )
        assert d.device_id == "192.168.1.1:5555"
        assert d.model == "Pixel 7"
        assert d.android_version == "13"
        assert d.battery_level == 80
        assert d.screen_on is True
        assert d.connected is True

    def test_asdict_works(self):
        from dataclasses import asdict
        d = DeviceInfo(
            device_id="x", model="x", android_version="x",
            battery_level=50, battery_status="3", screen_on=False, connected=False,
        )
        result = asdict(d)
        assert isinstance(result, dict)
        assert "device_id" in result
        assert result["battery_level"] == 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestBatteryAlert
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBatteryAlert:
    def test_init_fields(self):
        a = BatteryAlert(level=15, status="3", timestamp="2024-01-01T00:00:00", alert_type="low")
        assert a.level == 15
        assert a.status == "3"
        assert a.alert_type == "low"

    def test_alert_types(self):
        for alert_type in ("low", "critical", "charging", "full"):
            a = BatteryAlert(level=10, status="3", timestamp="t", alert_type=alert_type)
            assert a.alert_type == alert_type


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestLoadConfig
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLoadConfig:
    def test_creates_default_config_when_missing(self, tmp_path):
        cfg_file = tmp_path / "missing.json"
        mock_sub = MagicMock(); mock_sub.returncode = 1; mock_sub.stdout = b""
        with patch("subprocess.run", return_value=mock_sub):
            t = ADBAutomationToolkit(config_path=str(cfg_file))
        assert cfg_file.exists()

    def test_loads_existing_config(self, tmp_path):
        cfg_file = tmp_path / "existing.json"
        cfg_data = {
            "device_ip": "10.0.0.5",
            "device_port": 5556,
            "screenshot_dir": str(tmp_path / "shots"),
            "adb_path": "",
            "battery_alerts": {
                "low_threshold": 25,
                "critical_threshold": 8,
                "full_threshold": 95,
                "monitor_interval": 300,
            },
        }
        cfg_file.write_text(json.dumps(cfg_data))
        mock_sub = MagicMock(); mock_sub.returncode = 1; mock_sub.stdout = b""
        with patch("subprocess.run", return_value=mock_sub):
            t = ADBAutomationToolkit(config_path=str(cfg_file))
        assert t.device_ip == "10.0.0.5"
        assert t.device_port == 5556

    def test_default_config_has_required_keys(self, tmp_path):
        cfg_file = tmp_path / "new.json"
        mock_sub = MagicMock(); mock_sub.returncode = 1; mock_sub.stdout = b""
        with patch("subprocess.run", return_value=mock_sub):
            t = ADBAutomationToolkit(config_path=str(cfg_file))
        cfg = json.loads(cfg_file.read_text())
        for key in ("device_ip", "device_port", "screenshot_dir",
                    "battery_low_threshold", "battery_critical_threshold"):
            assert key in cfg


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestFindAdb
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFindAdb:
    def test_uses_config_adb_path_when_set(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        # adb_path に実在するファイルを指定
        fake_adb = tmp_path / "adb.exe"
        fake_adb.write_bytes(b"")
        cfg_data = {
            "device_ip": "127.0.0.1", "device_port": 5555,
            "screenshot_dir": str(tmp_path),
            "adb_path": str(fake_adb),
            "battery_low_threshold": 20, "battery_critical_threshold": 5,
            "battery_full_threshold": 90, "battery_monitor_interval": 60,
        }
        cfg_file.write_text(json.dumps(cfg_data))
        mock_sub = MagicMock(); mock_sub.returncode = 1; mock_sub.stdout = b""
        with patch("subprocess.run", return_value=mock_sub):
            t = ADBAutomationToolkit(config_path=str(cfg_file))
        assert t.adb_path == str(fake_adb)

    def test_finds_adb_via_subprocess(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        # subprocess.run で text=True なので stdout は str
        mock_sub_found = MagicMock()
        mock_sub_found.returncode = 0
        mock_sub_found.stdout = "C:\\adb\\adb.exe\n"
        with patch("subprocess.run", return_value=mock_sub_found):
            t = ADBAutomationToolkit(config_path=str(cfg_file))
        assert t.adb_path is not None

    def test_returns_none_when_not_found(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        mock_sub = MagicMock(); mock_sub.returncode = 1; mock_sub.stdout = b""
        with patch("subprocess.run", return_value=mock_sub):
            t = ADBAutomationToolkit(config_path=str(cfg_file))
        assert t.adb_path is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestRunAdbCommand
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRunAdbCommand:
    def test_returns_error_when_no_adb_path(self, toolkit):
        toolkit.adb_path = None
        result = toolkit._run_adb_command(["devices"])
        assert result["success"] is False
        assert "error" in result

    def test_success_result(self, toolkit):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "List of devices attached\n192.168.1.1:5555 device"
        mock_proc.stderr = ""
        with patch("subprocess.run", return_value=mock_proc):
            result = toolkit._run_adb_command(["devices"])
        assert result["success"] is True
        assert "stdout" in result

    def test_failure_result(self, toolkit):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "error: no devices found"
        with patch("subprocess.run", return_value=mock_proc):
            result = toolkit._run_adb_command(["devices"])
        assert result["success"] is False

    def test_timeout_result(self, toolkit):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["adb"], timeout=10)):
            result = toolkit._run_adb_command(["devices"])
        assert result["success"] is False
        assert "error" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestCheckConnection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCheckConnection:
    def test_returns_true_when_device_listed(self, toolkit):
        addr = f"{toolkit.device_ip}:{toolkit.device_port}"
        mock_result = {"success": True, "stdout": f"List of devices\n{addr} device", "stderr": "", "returncode": 0}
        with patch.object(toolkit, "_run_adb_command", return_value=mock_result):
            assert toolkit.check_connection() is True

    def test_returns_false_when_no_device(self, toolkit):
        mock_result = {"success": True, "stdout": "List of devices attached\n", "stderr": "", "returncode": 0}
        with patch.object(toolkit, "_run_adb_command", return_value=mock_result):
            assert toolkit.check_connection() is False

    def test_returns_false_on_command_failure(self, toolkit):
        mock_result = {"success": False, "error": "adb not found"}
        with patch.object(toolkit, "_run_adb_command", return_value=mock_result):
            assert toolkit.check_connection() is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestConnect
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConnect:
    def test_returns_true_when_already_connected(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=True):
            result = toolkit.connect()
        assert result is True

    def test_connects_successfully(self, toolkit):
        call_count = {"n": 0}
        def check_conn():
            call_count["n"] += 1
            # First call (already connected?) → False; second call (after connect) → True
            return call_count["n"] > 1

        with patch.object(toolkit, "check_connection", side_effect=check_conn), \
             patch.object(toolkit, "_run_adb_command", return_value={"success": True, "stdout": "connected", "stderr": "", "returncode": 0}), \
             patch("time.sleep"):
            result = toolkit.connect()
        assert result is True

    def test_force_disconnect_before_connect(self, toolkit):
        disconnected = {"called": False}
        def fake_disconnect():
            disconnected["called"] = True

        with patch.object(toolkit, "disconnect", side_effect=fake_disconnect), \
             patch.object(toolkit, "check_connection", return_value=True):
            toolkit.connect(force=True)
        assert disconnected["called"] is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestGetDeviceInfo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGetDeviceInfo:
    def _make_adb_call(self, cmd_map):
        """cmd_map: list[str] → result dict"""
        def fake_run(cmd, **kwargs):
            key = " ".join(cmd[1:]) if cmd else ""
            return cmd_map.get(key, {"success": False, "stdout": "", "stderr": "", "returncode": 1})
        return fake_run

    def test_returns_none_when_not_connected(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=False):
            assert toolkit.get_device_info() is None

    def test_returns_device_info(self, toolkit):
        battery_output = "Current Battery Service state:\nlevel: 78\nstatus: 3"
        power_output = "mWakefulness=Awake"

        def fake_run(cmd, **kwargs):
            joined = " ".join(cmd)
            if "ro.product.model" in joined:
                return {"success": True, "stdout": "Pixel 7", "stderr": "", "returncode": 0}
            if "ro.build.version.release" in joined:
                return {"success": True, "stdout": "13", "stderr": "", "returncode": 0}
            if "dumpsys battery" in joined:
                return {"success": True, "stdout": battery_output, "stderr": "", "returncode": 0}
            if "dumpsys power" in joined:
                return {"success": True, "stdout": power_output, "stderr": "", "returncode": 0}
            return {"success": False, "stdout": "", "stderr": "", "returncode": 1}

        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", side_effect=fake_run):
            info = toolkit.get_device_info()

        assert isinstance(info, DeviceInfo)
        assert info.model == "Pixel 7"
        assert info.android_version == "13"
        assert info.battery_level == 78
        assert info.screen_on is True
        assert info.connected is True

    def test_returns_none_on_exception(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", side_effect=Exception("fail")):
            assert toolkit.get_device_info() is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestGetBatteryInfo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGetBatteryInfo:
    def test_returns_none_when_not_connected(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=False):
            assert toolkit.get_battery_info() is None

    def test_returns_none_on_command_failure(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
            assert toolkit.get_battery_info() is None

    def test_parses_battery_output(self, toolkit):
        battery_output = "  level: 75\n  status: 3\n  temperature: 280"
        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", return_value={"success": True, "stdout": battery_output, "stderr": "", "returncode": 0}):
            info = toolkit.get_battery_info()
        assert isinstance(info, dict)
        assert "level" in info


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestCheckBatteryAlert
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCheckBatteryAlert:
    def test_returns_none_when_no_battery_info(self, toolkit):
        with patch.object(toolkit, "get_battery_info", return_value=None):
            assert toolkit.check_battery_alert() is None

    def test_returns_critical_alert(self, toolkit):
        # critical_threshold default is 5
        toolkit.battery_alerts["critical_threshold"] = 5
        with patch.object(toolkit, "get_battery_info", return_value={"level": 3, "status": "3"}):
            alert = toolkit.check_battery_alert()
        assert isinstance(alert, BatteryAlert)
        assert alert.alert_type == "critical"
        assert alert.level == 3

    def test_returns_low_alert(self, toolkit):
        toolkit.battery_alerts["low_threshold"] = 20
        toolkit.battery_alerts["critical_threshold"] = 5
        with patch.object(toolkit, "get_battery_info", return_value={"level": 15, "status": "3"}):
            alert = toolkit.check_battery_alert()
        assert isinstance(alert, BatteryAlert)
        assert alert.alert_type == "low"

    def test_returns_full_alert_when_charging(self, toolkit):
        toolkit.battery_alerts["full_threshold"] = 90
        with patch.object(toolkit, "get_battery_info", return_value={"level": 95, "status": "2"}):
            alert = toolkit.check_battery_alert()
        assert isinstance(alert, BatteryAlert)
        assert alert.alert_type == "full"

    def test_returns_none_when_ok(self, toolkit):
        toolkit.battery_alerts["low_threshold"] = 20
        toolkit.battery_alerts["critical_threshold"] = 5
        with patch.object(toolkit, "get_battery_info", return_value={"level": 60, "status": "3"}):
            assert toolkit.check_battery_alert() is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestExecuteShellCommand
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestExecuteShellCommand:
    def test_returns_error_when_not_connected(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=False):
            result = toolkit.execute_shell_command("ls /sdcard")
        assert result["success"] is False

    def test_passes_command_through_adb(self, toolkit):
        mock_result = {"success": True, "stdout": "file1\nfile2", "stderr": "", "returncode": 0}
        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", return_value=mock_result) as mock_adb:
            result = toolkit.execute_shell_command("ls /sdcard")
        assert result["success"] is True
        called_cmd = mock_adb.call_args[0][0]
        assert called_cmd[0] == "shell"
        assert "ls /sdcard" in called_cmd


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestInstallApp / TestUninstallApp
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInstallApp:
    def test_returns_false_when_not_connected(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=False):
            assert toolkit.install_app("/fake/app.apk") is False

    def test_returns_false_when_apk_not_found(self, toolkit, tmp_path):
        missing_apk = str(tmp_path / "notexist.apk")
        with patch.object(toolkit, "check_connection", return_value=True):
            assert toolkit.install_app(missing_apk) is False

    def test_returns_true_on_success(self, toolkit, tmp_path):
        apk = tmp_path / "app.apk"
        apk.write_bytes(b"fakeapk")
        mock_result = {"success": True, "stdout": "Success", "stderr": "", "returncode": 0}
        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", return_value=mock_result):
            assert toolkit.install_app(str(apk)) is True


class TestUninstallApp:
    def test_returns_false_when_not_connected(self, toolkit):
        with patch.object(toolkit, "check_connection", return_value=False):
            assert toolkit.uninstall_app("com.example.app") is False

    def test_returns_true_on_success(self, toolkit):
        mock_result = {"success": True, "stdout": "Success", "stderr": "", "returncode": 0}
        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", return_value=mock_result):
            assert toolkit.uninstall_app("com.example.app") is True

    def test_returns_false_on_failure(self, toolkit):
        mock_result = {"success": False, "stdout": "", "stderr": "failed", "returncode": 1}
        with patch.object(toolkit, "check_connection", return_value=True), \
             patch.object(toolkit, "_run_adb_command", return_value=mock_result):
            assert toolkit.uninstall_app("com.example.app") is False
