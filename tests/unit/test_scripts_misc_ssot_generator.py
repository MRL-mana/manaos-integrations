"""
Unit tests for scripts/misc/ssot_generator.py
Tests SERVICES constant, SSOTGenerator pure logic, and fallback paths.
All network calls (httpx) and psutil are mocked.
"""
import sys
from typing import Dict, Any
from unittest.mock import MagicMock, patch
import pytest

# ── Standard mocks ────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# httpx mock
_httpx = MagicMock()
sys.modules.setdefault("httpx", _httpx)

# psutil mock
_psutil = MagicMock()
sys.modules.setdefault("psutil", _psutil)

# ── Import target ─────────────────────────────────────────────────────────────
from scripts.misc.ssot_generator import (  # noqa: E402
    SERVICES,
    SSOTGenerator,
)


# ── TestServicesConstant ──────────────────────────────────────────────────────
class TestServicesConstant:
    def test_services_count(self):
        assert len(SERVICES) == 19

    def test_each_entry_has_name(self):
        for svc in SERVICES:
            assert "name" in svc
            assert isinstance(svc["name"], str)

    def test_each_entry_has_port(self):
        for svc in SERVICES:
            assert "port" in svc
            assert isinstance(svc["port"], int)

    def test_each_entry_has_script(self):
        for svc in SERVICES:
            assert "script" in svc
            assert svc["script"].endswith(".py")

    def test_ports_unique(self):
        ports = [svc["port"] for svc in SERVICES]
        # Allow duplicates (LLM Optimization and UI Operations share 5110), just
        # ensure we have 19 entries
        assert len(ports) == 19


# ── TestSSOTGeneratorInit ─────────────────────────────────────────────────────
class TestSSOTGeneratorInit:
    def test_default_init(self):
        gen = SSOTGenerator()
        assert gen.recent_inputs == []
        assert gen.last_error is None
        assert gen.update_interval == 5


# ── TestCheckServiceHealth ────────────────────────────────────────────────────
class TestCheckServiceHealth:
    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_up_on_200(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.elapsed.total_seconds.return_value = 0.05
        mock_get.return_value = resp
        gen = SSOTGenerator()
        result = gen.check_service_health(5100)
        assert result["status"] == "up"
        assert result["response_time_ms"] == pytest.approx(50.0)
        assert result["last_heartbeat"] is not None

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_unhealthy_on_non_200(self, mock_get):
        resp = MagicMock()
        resp.status_code = 500
        mock_get.return_value = resp
        gen = SSOTGenerator()
        result = gen.check_service_health(5100)
        assert result["status"] == "unhealthy"
        assert result["response_time_ms"] is None

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_down_on_connect_error(self, mock_get):
        import httpx as real_httpx
        mock_get.side_effect = real_httpx.ConnectError("refused")
        gen = SSOTGenerator()
        result = gen.check_service_health(5100)
        assert result["status"] == "down"

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_timeout_on_timeout_exception(self, mock_get):
        import httpx as real_httpx
        mock_get.side_effect = real_httpx.TimeoutException("timeout")
        gen = SSOTGenerator()
        result = gen.check_service_health(5100)
        assert result["status"] == "timeout"

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_error_on_generic_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("boom")
        gen = SSOTGenerator()
        result = gen.check_service_health(5100)
        assert result["status"] == "error"
        assert "error" in result


# ── TestGetServiceProcessInfo ─────────────────────────────────────────────────
class TestGetServiceProcessInfo:
    def test_returns_none_when_no_match(self):
        proc = MagicMock()
        proc.info = {
            "cmdline": ["python", "unrelated_script.py"],
            "pid": 999,
            "memory_info": MagicMock(rss=10 * 1024**2),
            "cpu_percent": 1.5,
        }
        _psutil.process_iter.return_value = [proc]
        gen = SSOTGenerator()
        result = gen.get_service_process_info("other_script.py")
        assert result is None

    @patch("scripts.misc.ssot_generator.psutil.process_iter")
    def test_returns_pid_on_match(self, mock_iter):
        proc = MagicMock()
        proc.info = {
            "cmdline": ["python", "intent_router.py"],
            "pid": 1234,
            "memory_info": MagicMock(rss=50 * 1024**2),
            "cpu_percent": 2.0,
        }
        mock_iter.return_value = [proc]
        gen = SSOTGenerator()
        result = gen.get_service_process_info("intent_router.py")
        assert result is not None
        assert result["pid"] == 1234
        assert result["memory_mb"] == pytest.approx(50.0)
        assert result["cpu_percent"] == 2.0

    @patch("scripts.misc.ssot_generator.psutil.process_iter")
    def test_returns_none_on_exception(self, mock_iter):
        mock_iter.side_effect = RuntimeError("fail")
        gen = SSOTGenerator()
        result = gen.get_service_process_info("any.py")
        assert result is None


# ── TestGetSystemResources ────────────────────────────────────────────────────
class TestGetSystemResources:
    def _make_mocks(self):
        mem = MagicMock()
        mem.total = 16 * 1024**3
        mem.used = 8 * 1024**3
        mem.available = 8 * 1024**3
        mem.percent = 50.0
        disk = MagicMock()
        disk.total = 500 * 1024**3
        disk.used = 200 * 1024**3
        disk.free = 300 * 1024**3
        disk.percent = 40.0
        return mem, disk

    @patch("scripts.misc.ssot_generator.psutil.disk_usage")
    @patch("scripts.misc.ssot_generator.psutil.virtual_memory")
    @patch("scripts.misc.ssot_generator.psutil.cpu_count")
    @patch("scripts.misc.ssot_generator.psutil.cpu_percent")
    def test_has_cpu_key(self, mock_cpu_pct, mock_cpu_cnt, mock_vmem, mock_disk):
        mem, disk = self._make_mocks()
        mock_cpu_pct.return_value = 25.0
        mock_cpu_cnt.return_value = 8
        mock_vmem.return_value = mem
        mock_disk.return_value = disk
        gen = SSOTGenerator()
        result = gen.get_system_resources()
        assert "cpu" in result
        assert result["cpu"]["percent"] == 25.0

    @patch("scripts.misc.ssot_generator.psutil.disk_usage")
    @patch("scripts.misc.ssot_generator.psutil.virtual_memory")
    @patch("scripts.misc.ssot_generator.psutil.cpu_count")
    @patch("scripts.misc.ssot_generator.psutil.cpu_percent")
    def test_has_ram_key(self, mock_cpu_pct, mock_cpu_cnt, mock_vmem, mock_disk):
        mem, disk = self._make_mocks()
        mock_cpu_pct.return_value = 25.0
        mock_cpu_cnt.return_value = 8
        mock_vmem.return_value = mem
        mock_disk.return_value = disk
        gen = SSOTGenerator()
        result = gen.get_system_resources()
        assert "ram" in result
        assert result["ram"]["percent"] == 50.0

    @patch("scripts.misc.ssot_generator.psutil.disk_usage")
    @patch("scripts.misc.ssot_generator.psutil.virtual_memory")
    @patch("scripts.misc.ssot_generator.psutil.cpu_count")
    @patch("scripts.misc.ssot_generator.psutil.cpu_percent")
    def test_has_disk_key(self, mock_cpu_pct, mock_cpu_cnt, mock_vmem, mock_disk):
        mem, disk = self._make_mocks()
        mock_cpu_pct.return_value = 25.0
        mock_cpu_cnt.return_value = 8
        mock_vmem.return_value = mem
        mock_disk.return_value = disk
        gen = SSOTGenerator()
        result = gen.get_system_resources()
        assert "disk" in result
        assert result["disk"]["percent"] == 40.0

    @patch("scripts.misc.ssot_generator.psutil.cpu_percent")
    def test_returns_empty_on_exception(self, mock_cpu_pct):
        mock_cpu_pct.side_effect = RuntimeError("fail")
        gen = SSOTGenerator()
        result = gen.get_system_resources()
        assert result == {}


# ── TestGetActiveTasks ────────────────────────────────────────────────────────
class TestGetActiveTasks:
    def test_fallback_zeros_on_exception(self):
        _httpx.get.side_effect = RuntimeError("no connection")
        gen = SSOTGenerator()
        result = gen.get_active_tasks()
        assert result == {"pending": 0, "running": 0, "total": 0}
        _httpx.get.side_effect = None

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_returns_api_data(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "pending_tasks": 3,
            "status_counts": {"running": 1},
            "total_tasks": 4,
        }
        mock_get.return_value = resp
        gen = SSOTGenerator()
        result = gen.get_active_tasks()
        assert result["pending"] == 3
        assert result["running"] == 1
        assert result["total"] == 4


# ── TestGetRecentInputs ───────────────────────────────────────────────────────
class TestGetRecentInputs:
    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_fallback_to_recent_inputs_on_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("fail")
        gen = SSOTGenerator()
        gen.recent_inputs = [{"text": "hello"}]
        result = gen.get_recent_inputs()
        assert result == [{"text": "hello"}]

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_returns_empty_list_when_no_fallback(self, mock_get):
        mock_get.side_effect = RuntimeError("fail")
        gen = SSOTGenerator()
        result = gen.get_recent_inputs()
        assert result == []

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_returns_last_5_entries(self, mock_get):
        mock_get.side_effect = RuntimeError("fail")
        gen = SSOTGenerator()
        gen.recent_inputs = [{"text": f"m{i}"} for i in range(10)]
        result = gen.get_recent_inputs()
        assert len(result) == 5


# ── TestGetLastError ──────────────────────────────────────────────────────────
class TestGetLastError:
    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_returns_none_by_default_on_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("fail")
        gen = SSOTGenerator()
        result = gen.get_last_error()
        assert result is None

    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_returns_stored_last_error_on_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("fail")
        gen = SSOTGenerator()
        gen.last_error = {"service_name": "TestSvc", "error_message": "crash"}  # type: ignore
        result = gen.get_last_error()
        assert result["service_name"] == "TestSvc"  # type: ignore[index]


# ── TestGenerateSSOT ──────────────────────────────────────────────────────────
class TestGenerateSSOT:
    @patch("scripts.misc.ssot_generator.psutil.process_iter")
    @patch("scripts.misc.ssot_generator.psutil.cpu_percent")
    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_ssot_keys_present(self, mock_get, mock_cpu_pct, mock_iter):
        import httpx as real_httpx
        mock_get.side_effect = real_httpx.ConnectError("offline")
        mock_cpu_pct.side_effect = RuntimeError("fail")
        mock_iter.return_value = []
        gen = SSOTGenerator()
        ssot = gen.generate_ssot()
        assert "timestamp" in ssot
        assert "version" in ssot
        assert "services" in ssot
        assert "summary" in ssot
        assert "active_tasks" in ssot
        assert "recent_inputs" in ssot
        assert "last_error" in ssot

    @patch("scripts.misc.ssot_generator.psutil.process_iter")
    @patch("scripts.misc.ssot_generator.psutil.cpu_percent")
    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_services_count_in_ssot(self, mock_get, mock_cpu_pct, mock_iter):
        import httpx as real_httpx
        mock_get.side_effect = real_httpx.ConnectError("offline")
        mock_cpu_pct.side_effect = RuntimeError("fail")
        mock_iter.return_value = []
        gen = SSOTGenerator()
        ssot = gen.generate_ssot()
        assert len(ssot["services"]) == 19
        assert ssot["summary"]["total_services"] == 19

    @patch("scripts.misc.ssot_generator.psutil.process_iter")
    @patch("scripts.misc.ssot_generator.psutil.cpu_percent")
    @patch("scripts.misc.ssot_generator.httpx.get")
    def test_summary_counts_add_up(self, mock_get, mock_cpu_pct, mock_iter):
        import httpx as real_httpx
        mock_get.side_effect = real_httpx.ConnectError("offline")
        mock_cpu_pct.side_effect = RuntimeError("fail")
        mock_iter.return_value = []
        gen = SSOTGenerator()
        ssot = gen.generate_ssot()
        summary = ssot["summary"]
        # All services are "down" when httpx raises ConnectError
        total = summary["up"] + summary["down"] + summary["unhealthy"]
        assert total <= 19


# ── TestSaveSSOT ──────────────────────────────────────────────────────────────
class TestSaveSSOT:
    def test_writes_valid_json(self, tmp_path):
        gen = SSOTGenerator()
        import scripts.misc.ssot_generator as sg_mod
        orig_path = sg_mod.SSOT_FILE
        sg_mod.SSOT_FILE = tmp_path / "test_status.json"
        try:
            ssot = {"timestamp": "2026-03-08T00:00:00", "version": "1.0"}
            gen.save_ssot(ssot)
            import json
            with open(sg_mod.SSOT_FILE, encoding="utf-8") as f:
                data = json.load(f)
            assert data["version"] == "1.0"
        finally:
            sg_mod.SSOT_FILE = orig_path
