"""
Unit tests for scripts/misc/emergency_stop.py
"""
import json
import sys
from unittest.mock import MagicMock, patch

# ── module-level mocks ─────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.MRL_MEMORY_PORT = 5100
_paths_mod.LEARNING_SYSTEM_PORT = 5101
_paths_mod.LLM_ROUTING_PORT = 5117
_paths_mod.VIDEO_PIPELINE_PORT = 5102
_paths_mod.WINDOWS_AUTOMATION_PORT = 5103
_paths_mod.PICO_HID_PORT = 5104
_paths_mod.UNIFIED_API_PORT = 9999
_paths_mod.GALLERY_PORT = 5559
_paths_mod.COMFYUI_PORT = 8188
_paths_mod.MOLTBOT_GATEWAY_PORT = 5105
sys.modules["_paths"] = _paths_mod

import pytest
from scripts.misc.emergency_stop import EmergencyStop


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def es():
    return EmergencyStop()


def _mock_run(returncode=0, stdout="", stderr=""):
    m = MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)
    return m


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_stopped_processes_empty(self, es):
        assert es.stopped_processes == []

    def test_keywords_list_nonempty(self, es):
        assert len(es.MANAOS_PROCESS_KEYWORDS) > 0

    def test_service_ports_nonempty(self, es):
        assert len(es.SERVICE_PORTS) > 0


# ── TestFindManaosProcesses ────────────────────────────────────────────────
class TestFindManaosProcesses:
    def test_empty_when_no_processes(self, es):
        mock_result = _mock_run(returncode=0, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            procs = es.find_manaos_processes()
        assert procs == []

    def test_returns_list_when_found(self, es):
        proc_json = json.dumps([{"Id": 1234, "ProcessName": "python", "CommandLine": "manaos llm_routing"}])
        mock_result = _mock_run(returncode=0, stdout=proc_json)
        with patch("subprocess.run", return_value=mock_result):
            procs = es.find_manaos_processes()
        assert isinstance(procs, list)
        assert len(procs) == 1
        assert procs[0]["Id"] == 1234

    def test_single_object_wrapped_in_list(self, es):
        proc_json = json.dumps({"Id": 5678, "ProcessName": "python", "CommandLine": "manaos"})
        mock_result = _mock_run(returncode=0, stdout=proc_json)
        with patch("subprocess.run", return_value=mock_result):
            procs = es.find_manaos_processes()
        assert len(procs) == 1

    def test_returns_empty_on_error(self, es):
        with patch("subprocess.run", side_effect=Exception("fail")):
            procs = es.find_manaos_processes()
        assert procs == []

    def test_null_output_returns_empty(self, es):
        mock_result = _mock_run(returncode=0, stdout="null")
        with patch("subprocess.run", return_value=mock_result):
            procs = es.find_manaos_processes()
        assert procs == []


# ── TestStopProcess ────────────────────────────────────────────────────────
class TestStopProcess:
    def test_success_when_process_gone_after_stop(self, es):
        # first call: stop → success; second call: check → not found (returncode 1)
        side_effects = [
            _mock_run(returncode=0),  # Stop-Process
            _mock_run(returncode=1),  # Get-Process → not found = stopped
        ]
        with patch("subprocess.run", side_effect=side_effects), \
             patch("time.sleep"):
            result = es.stop_process(1234, "test_proc")
        assert result is True

    def test_returns_false_on_timeout(self, es):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="cmd", timeout=5)), \
             patch("time.sleep"):
            result = es.stop_process(9999, "timeout_proc")
        assert result is False


# ── TestExecute ────────────────────────────────────────────────────────────
class TestExecute:
    def test_no_processes_returns_true(self, es):
        with patch.object(es, "find_manaos_processes", return_value=[]), \
             patch.object(es, "find_processes_by_port", return_value=[]):
            result = es.execute(confirm=False)
        assert result is True

    def test_all_stopped_returns_true(self, es):
        processes = [{"Id": 111, "ProcessName": "python", "CommandLine": "manaos"}]
        with patch.object(es, "find_manaos_processes", return_value=processes), \
             patch.object(es, "find_processes_by_port", return_value=[]), \
             patch.object(es, "stop_process", return_value=True):
            result = es.execute(confirm=False)
        assert result is True
        assert es.get_stopped_count() == 1

    def test_partial_stop_returns_false(self, es):
        processes = [
            {"Id": 111, "ProcessName": "python", "CommandLine": "manaos"},
            {"Id": 222, "ProcessName": "python", "CommandLine": "manaos2"},
        ]
        with patch.object(es, "find_manaos_processes", return_value=processes), \
             patch.object(es, "find_processes_by_port", return_value=[]), \
             patch.object(es, "stop_process", side_effect=[True, False]):
            result = es.execute(confirm=False)
        assert result is False

    def test_deduplicates_port_processes(self, es):
        kw_procs = [{"Id": 100, "ProcessName": "python", "CommandLine": "manaos"}]
        port_procs = [{"Id": 100, "ProcessName": "port-5100", "CommandLine": "Listening on :5100"}]
        with patch.object(es, "find_manaos_processes", return_value=kw_procs), \
             patch.object(es, "find_processes_by_port", return_value=port_procs), \
             patch.object(es, "stop_process", return_value=True):
            result = es.execute(confirm=False)
        # only 1 unique PID → stopped once
        assert es.get_stopped_count() == 1


# ── TestGetStoppedCount ────────────────────────────────────────────────────
class TestGetStoppedCount:
    def test_initially_zero(self, es):
        assert es.get_stopped_count() == 0
