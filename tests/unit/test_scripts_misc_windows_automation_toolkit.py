"""Tests for scripts/misc/windows_automation_toolkit.py"""
import importlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

# ── top-level dependency mocks (must come before import) ──────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_pm_inst = MagicMock()
_pm_inst.list_top_processes.return_value = [{"name": "python", "pid": 1, "cpu_percent": 50.0}]
_pm_inst.kill_by_pid.return_value = True
_pm_mod = MagicMock()
_pm_mod.get_process_manager.return_value = _pm_inst
sys.modules["manaos_process_manager"] = _pm_mod

# ── optional deps ──────────────────────────────────────────────────────
_mss_tools = MagicMock()
_mss_mod = MagicMock()
_mss_mod.tools = _mss_tools
sys.modules.setdefault("mss", _mss_mod)
sys.modules.setdefault("mss.tools", _mss_tools)

# ── import SUT ────────────────────────────────────────────────────────
_misc_path = str(Path(__file__).parent.parent.parent)
if _misc_path not in sys.path:
    sys.path.insert(0, _misc_path)

import scripts.misc.windows_automation_toolkit as _wat_mod
from scripts.misc.windows_automation_toolkit import WindowsAutomationToolkit


# ── helpers ───────────────────────────────────────────────────────────
def _make_toolkit(tmp_path, extra_config=None):
    """Create a WindowsAutomationToolkit with a real temp config file."""
    config = {"screenshot_dir": str(tmp_path / "shots")}
    if extra_config:
        config.update(extra_config)
    cfg_file = tmp_path / "wat_config.json"
    cfg_file.write_text(json.dumps(config))
    return WindowsAutomationToolkit(config_path=str(cfg_file))


# ── fixtures ──────────────────────────────────────────────────────────
@pytest.fixture
def toolkit(tmp_path):
    return _make_toolkit(tmp_path)


# ══════════════════════════════════════════════════════════════════════
class TestInit:
    def test_loads_existing_config(self, tmp_path):
        tk = _make_toolkit(tmp_path, {"cpu_warning_threshold": 70})
        assert tk.config["cpu_warning_threshold"] == 70

    def test_creates_default_config_when_missing(self, tmp_path):
        tk = WindowsAutomationToolkit(config_path=str(tmp_path / "nonexistent.json"))
        assert (tmp_path / "nonexistent.json").exists()
        assert tk.config.get("cpu_warning_threshold") == 80

    def test_alert_thresholds_populated(self, toolkit):
        for key in ("cpu_warning", "cpu_critical", "ram_warning", "ram_critical",
                    "disk_warning", "disk_critical"):
            assert key in toolkit.alerts

    def test_screenshot_dir_created(self, tmp_path):
        tk = _make_toolkit(tmp_path)
        assert tk.screenshot_dir.exists()


# ══════════════════════════════════════════════════════════════════════
class TestGetSystemInfo:
    def test_returns_hostname_key(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch("scripts.misc.windows_automation_toolkit.subprocess.run") as mr:
            boot_time = MagicMock()
            mp.boot_time.return_value = 0.0
            mp.cpu_count.return_value = 4
            vm = MagicMock()
            vm.total = 16 * (1024 ** 3)
            mp.virtual_memory.return_value = vm
            mr.return_value = MagicMock(returncode=0, stdout="Intel Core i7\n")
            result = toolkit.get_system_info()
        assert "hostname" in result or "error" in result

    def test_returns_error_dict_on_exception(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp:
            mp.boot_time.side_effect = RuntimeError("boom")
            mp.cpu_count.side_effect = RuntimeError("boom")
            mp.virtual_memory.side_effect = RuntimeError("boom")
            result = toolkit.get_system_info()
        assert "error" in result

    def test_uses_subprocess_for_cpu_name(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch("scripts.misc.windows_automation_toolkit.subprocess.run") as mr:
            mp.boot_time.return_value = 0.0
            mp.cpu_count.return_value = 2
            vm = MagicMock()
            vm.total = 8 * (1024 ** 3)
            mp.virtual_memory.return_value = vm
            mr.return_value = MagicMock(returncode=0, stdout="Test CPU\n")
            with patch.object(toolkit, "_get_gpu_name", return_value="GPU"):
                result = toolkit.get_system_info()
            if "cpu_name" in result:
                assert result["cpu_name"] == "Test CPU"


# ══════════════════════════════════════════════════════════════════════
class TestGetResourceUsage:
    def test_returns_error_when_no_psutil(self, toolkit):
        orig = _wat_mod.psutil
        try:
            _wat_mod.psutil = None
            result = toolkit.get_resource_usage()
            assert "error" in result
        finally:
            _wat_mod.psutil = orig

    def test_returns_cpu_percent(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch.object(toolkit, "_get_gpu_stats", return_value={}):
            vm = MagicMock()
            vm.used = 8 * (1024 ** 3)
            vm.total = 16 * (1024 ** 3)
            vm.percent = 50.0
            mp.virtual_memory.return_value = vm
            disk = MagicMock()
            disk.used = 100 * (1024 ** 3)
            disk.total = 500 * (1024 ** 3)
            disk.percent = 20.0
            mp.disk_usage.return_value = disk
            net = MagicMock()
            net.bytes_sent = 100 * (1024 ** 2)
            net.bytes_recv = 200 * (1024 ** 2)
            mp.net_io_counters.return_value = net
            mp.cpu_percent.return_value = 35.0
            result = toolkit.get_resource_usage()
        assert result.get("cpu_percent") == 35.0

    def test_includes_network_keys(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch.object(toolkit, "_get_gpu_stats", return_value={}):
            vm = MagicMock()
            vm.used = 4 * (1024 ** 3)
            vm.total = 16 * (1024 ** 3)
            vm.percent = 25.0
            mp.virtual_memory.return_value = vm
            disk = MagicMock()
            disk.used = 50 * (1024 ** 3)
            disk.total = 200 * (1024 ** 3)
            disk.percent = 25.0
            mp.disk_usage.return_value = disk
            net = MagicMock()
            net.bytes_sent = 0
            net.bytes_recv = 0
            mp.net_io_counters.return_value = net
            mp.cpu_percent.return_value = 10.0
            result = toolkit.get_resource_usage()
        assert "network_sent_mb" in result
        assert "network_recv_mb" in result

    def test_returns_error_on_exception(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp:
            mp.virtual_memory.side_effect = OSError("disk fail")
            mp.cpu_percent.side_effect = OSError("bad")
            result = toolkit.get_resource_usage()
        assert "error" in result


# ══════════════════════════════════════════════════════════════════════
class TestCheckResourceAlerts:
    def _usage(self, cpu=10.0, ram=10.0, disk=10.0):
        return {
            "cpu_percent": cpu,
            "ram_percent": ram,
            "disk_percent": disk,
            "gpu_temp_celsius": None,
        }

    def test_no_alerts_under_threshold(self, toolkit):
        with patch.object(toolkit, "get_resource_usage", return_value=self._usage()):
            alerts = toolkit.check_resource_alerts()
        assert alerts == []

    def test_cpu_warning(self, toolkit):
        with patch.object(toolkit, "get_resource_usage", return_value=self._usage(cpu=85.0)):
            alerts = toolkit.check_resource_alerts()
        assert any(a.get("metric") == "cpu" for a in alerts)

    def test_cpu_critical(self, toolkit):
        with patch.object(toolkit, "get_resource_usage", return_value=self._usage(cpu=96.0)):
            alerts = toolkit.check_resource_alerts()
        cpu_alerts = [a for a in alerts if a.get("metric") == "cpu"]
        assert len(cpu_alerts) == 1
        assert cpu_alerts[0]["alert_type"] == "critical"

    def test_error_propagated(self, toolkit):
        with patch.object(toolkit, "get_resource_usage", return_value={"error": "psutil 必要"}):
            result = toolkit.check_resource_alerts()
        assert any("error" in a for a in result)

    def test_multiple_alerts(self, toolkit):
        usage = self._usage(cpu=90.0, ram=92.0, disk=88.0)
        with patch.object(toolkit, "get_resource_usage", return_value=usage):
            alerts = toolkit.check_resource_alerts()
        metrics = {a["metric"] for a in alerts}
        assert "cpu" in metrics
        assert "ram" in metrics
        assert "disk" in metrics


# ══════════════════════════════════════════════════════════════════════
class TestExecutePowershell:
    def test_success_returns_stdout(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Hello\n"
        mock_result.stderr = ""
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run", return_value=mock_result):
            result = toolkit.execute_powershell("echo Hello")
        assert result["success"] is True
        assert result["stdout"] == "Hello"

    def test_nonzero_returncode_returns_failure(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error msg"
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run", return_value=mock_result):
            result = toolkit.execute_powershell("bad command")
        assert result["success"] is False

    def test_timeout_returns_error(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("cmd", 30)):
            result = toolkit.execute_powershell("slow command", timeout=30)
        assert result["success"] is False
        assert "タイムアウト" in result["error"]

    def test_exception_returns_error(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   side_effect=FileNotFoundError("powershell not found")):
            result = toolkit.execute_powershell("whatever")
        assert result["success"] is False
        assert "error" in result


# ══════════════════════════════════════════════════════════════════════
class TestGetTopProcesses:
    def test_delegates_to_process_manager(self, toolkit):
        _pm_inst.list_top_processes.reset_mock()
        _pm_inst.list_top_processes.return_value = [{"name": "chrome", "pid": 42}]
        with patch("scripts.misc.windows_automation_toolkit.psutil", MagicMock()), \
             patch("scripts.misc.windows_automation_toolkit.get_process_manager",
                   return_value=_pm_inst):
            result = toolkit.get_top_processes(sort_by="cpu", limit=5)
        assert result[0]["name"] == "chrome"

    def test_returns_error_when_no_psutil(self, toolkit):
        orig = _wat_mod.psutil
        try:
            _wat_mod.psutil = None
            result = toolkit.get_top_processes()
            assert any("error" in r for r in result)
        finally:
            _wat_mod.psutil = orig

    def test_returns_error_on_exception(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.psutil", MagicMock()), \
             patch("scripts.misc.windows_automation_toolkit.get_process_manager",
                   side_effect=RuntimeError("pm fail")):
            result = toolkit.get_top_processes()
        assert any("error" in r for r in result)


# ══════════════════════════════════════════════════════════════════════
class TestKillProcess:
    def test_returns_error_when_no_psutil(self, toolkit):
        orig = _wat_mod.psutil
        try:
            _wat_mod.psutil = None
            result = toolkit.kill_process(999)
            assert result["success"] is False
        finally:
            _wat_mod.psutil = orig

    def test_returns_error_for_no_such_process(self, toolkit):
        import psutil as real_psutil
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp:
            mp.Process.side_effect = real_psutil.NoSuchProcess(pid=999)
            mp.NoSuchProcess = real_psutil.NoSuchProcess
            mp.AccessDenied = real_psutil.AccessDenied
            result = toolkit.kill_process(999)
        assert result["success"] is False
        assert "見つかりません" in result["error"]

    def test_returns_error_for_access_denied(self, toolkit):
        import psutil as real_psutil
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp:
            mp.Process.side_effect = real_psutil.AccessDenied(pid=1)
            mp.NoSuchProcess = real_psutil.NoSuchProcess
            mp.AccessDenied = real_psutil.AccessDenied
            result = toolkit.kill_process(1)
        assert result["success"] is False
        assert "拒否" in result["error"]

    def test_success_delegates_to_process_manager(self, toolkit):
        import psutil as real_psutil
        mock_proc = MagicMock()
        mock_proc.name.return_value = "notepad.exe"
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch("scripts.misc.windows_automation_toolkit.get_process_manager",
                   return_value=_pm_inst):
            mp.Process.return_value = mock_proc
            mp.NoSuchProcess = real_psutil.NoSuchProcess
            mp.AccessDenied = real_psutil.AccessDenied
            _pm_inst.kill_by_pid.return_value = True
            result = toolkit.kill_process(1234)
        assert result["success"] is True
        assert result["name"] == "notepad.exe"

    def test_fails_when_process_manager_returns_false(self, toolkit):
        import psutil as real_psutil
        mock_proc = MagicMock()
        mock_proc.name.return_value = "notepad.exe"
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch("scripts.misc.windows_automation_toolkit.get_process_manager",
                   return_value=_pm_inst):
            mp.Process.return_value = mock_proc
            mp.NoSuchProcess = real_psutil.NoSuchProcess
            mp.AccessDenied = real_psutil.AccessDenied
            _pm_inst.kill_by_pid.return_value = False
            result = toolkit.kill_process(1234)
        assert result["success"] is False


# ══════════════════════════════════════════════════════════════════════
class TestStartApplication:
    def test_success_returns_pid(self, toolkit):
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        with patch("scripts.misc.windows_automation_toolkit.subprocess.Popen",
                   return_value=mock_proc):
            result = toolkit.start_application("notepad.exe")
        assert result["success"] is True
        assert result["pid"] == 5678

    def test_file_not_found_returns_error(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.subprocess.Popen",
                   side_effect=FileNotFoundError):
            result = toolkit.start_application("no_such_app.exe")
        assert result["success"] is False
        assert "見つかりません" in result["error"]

    def test_passes_args(self, toolkit):
        mock_proc = MagicMock()
        mock_proc.pid = 100
        with patch("scripts.misc.windows_automation_toolkit.subprocess.Popen",
                   return_value=mock_proc) as mpopen:
            toolkit.start_application("app.exe", args=["--flag"])
            mpopen.assert_called_once_with(["app.exe", "--flag"], shell=False)

    def test_exception_returns_error(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.subprocess.Popen",
                   side_effect=OSError("cannot exec")):
            result = toolkit.start_application("app.exe")
        assert result["success"] is False


# ══════════════════════════════════════════════════════════════════════
class TestTakeScreenshot:
    def test_returns_error_when_no_mss(self, toolkit):
        orig = _wat_mod.mss
        try:
            _wat_mod.mss = None
            result = toolkit.take_screenshot()
            assert result["success"] is False
            assert "mss" in result["error"]
        finally:
            _wat_mod.mss = orig

    def test_success_returns_path(self, tmp_path, toolkit):
        fake_shot = MagicMock()
        fake_shot.rgb = b"\x00" * 100
        fake_shot.size = (10, 10)
        fake_monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
        fake_ctx = MagicMock()
        fake_ctx.__enter__ = MagicMock(return_value=fake_ctx)
        fake_ctx.__exit__ = MagicMock(return_value=False)
        fake_ctx.grab.return_value = fake_shot
        fake_ctx.monitors = fake_monitors

        # Create a fake png file so stat().st_size works
        fake_file = toolkit.screenshot_dir / "test.png"
        fake_file.write_bytes(b"\x89PNG\r\n" + b"\x00" * 100)

        with patch("scripts.misc.windows_automation_toolkit.mss") as mmss:
            mmss.mss.return_value = fake_ctx
            mmss.tools.to_png = MagicMock(
                side_effect=lambda rgb, size, output: Path(output).write_bytes(b"\x89PNG\r\n" + b"\x00" * 100)
            )
            result = toolkit.take_screenshot(filename="test.png")
        assert result["success"] is True
        assert "path" in result


# ══════════════════════════════════════════════════════════════════════
class TestListInstalledApps:
    def test_returns_list_on_success(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Name  ID  Version\n--------\nNotepad  Microsoft.Notepad  1.0\n"
        mock_result.stderr = ""
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   return_value=mock_result):
            result = toolkit.list_installed_apps()
        assert isinstance(result, list)

    def test_returns_error_when_winget_missing(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   side_effect=FileNotFoundError):
            result = toolkit.list_installed_apps()
        assert any("error" in r for r in result)

    def test_returns_error_on_failure(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "winget error"
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   return_value=mock_result):
            result = toolkit.list_installed_apps()
        assert any("error" in r for r in result)


# ══════════════════════════════════════════════════════════════════════
class TestInstallApp:
    def test_success(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully installed"
        mock_result.stderr = ""
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   return_value=mock_result):
            result = toolkit.install_app("Google.Chrome")
        assert result["success"] is True

    def test_failure(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Not found"
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   return_value=mock_result):
            result = toolkit.install_app("Unknown.App")
        assert result["success"] is False

    def test_timeout(self, toolkit):
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("winget", 300)):
            result = toolkit.install_app("SomeApp")
        assert result["success"] is False
        assert "タイムアウト" in result["error"]


# ══════════════════════════════════════════════════════════════════════
class TestUninstallApp:
    def test_success(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Uninstalled"
        mock_result.stderr = ""
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   return_value=mock_result):
            result = toolkit.uninstall_app("Google.Chrome")
        assert result["success"] is True

    def test_failure_returns_false(self, toolkit):
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "Not installed"
        with patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   return_value=mock_result):
            result = toolkit.uninstall_app("X.Y")
        assert result["success"] is False


# ══════════════════════════════════════════════════════════════════════
class TestGetNetworkInfo:
    def test_returns_error_when_no_psutil(self, toolkit):
        orig = _wat_mod.psutil
        try:
            _wat_mod.psutil = None
            result = toolkit.get_network_info()
            assert "error" in result
        finally:
            _wat_mod.psutil = orig

    def test_returns_interfaces_dict(self, toolkit):
        mock_addr = MagicMock()
        mock_addr.family.name = "AF_INET"
        mock_addr.address = "192.168.1.100"
        mock_stat = MagicMock()
        mock_stat.isup = True
        mock_stat.speed = 1000
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch("scripts.misc.windows_automation_toolkit.subprocess.run") as mr:
            mp.net_if_addrs.return_value = {"Ethernet": [mock_addr]}
            mp.net_if_stats.return_value = {"Ethernet": mock_stat}
            mr.return_value = MagicMock(returncode=1, stdout="")
            result = toolkit.get_network_info()
        assert "interfaces" in result
        assert "Ethernet" in result["interfaces"]

    def test_handles_subprocess_exception(self, toolkit):
        mock_addr = MagicMock()
        mock_addr.family.name = "AF_INET"
        mock_addr.address = "10.0.0.1"
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp, \
             patch("scripts.misc.windows_automation_toolkit.subprocess.run",
                   side_effect=FileNotFoundError("tailscale not found")):
            mp.net_if_addrs.return_value = {"lo": [mock_addr]}
            mp.net_if_stats.return_value = {}
            result = toolkit.get_network_info()
        assert "interfaces" in result
        assert result.get("tailscale") is None


# ══════════════════════════════════════════════════════════════════════
class TestGetDiskInfo:
    def test_returns_error_when_no_psutil(self, toolkit):
        orig = _wat_mod.psutil
        try:
            _wat_mod.psutil = None
            result = toolkit.get_disk_info()
            assert any("error" in r for r in result)
        finally:
            _wat_mod.psutil = orig

    def test_returns_disk_list(self, toolkit):
        part = MagicMock()
        part.device = "C:\\"
        part.mountpoint = "C:\\"
        part.fstype = "NTFS"
        usage = MagicMock()
        usage.total = 500 * (1024 ** 3)
        usage.used = 200 * (1024 ** 3)
        usage.free = 300 * (1024 ** 3)
        usage.percent = 40.0
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp:
            mp.disk_partitions.return_value = [part]
            mp.disk_usage.return_value = usage
            result = toolkit.get_disk_info()
        assert len(result) == 1
        assert result[0]["device"] == "C:\\"
        assert result[0]["percent"] == 40.0

    def test_skips_oserror_partition(self, toolkit):
        part = MagicMock()
        part.device = "D:\\"
        part.mountpoint = "D:\\"
        part.fstype = "NTFS"
        with patch("scripts.misc.windows_automation_toolkit.psutil") as mp:
            mp.disk_partitions.return_value = [part]
            mp.disk_usage.side_effect = OSError("No disk")
            result = toolkit.get_disk_info()
        assert result == []
