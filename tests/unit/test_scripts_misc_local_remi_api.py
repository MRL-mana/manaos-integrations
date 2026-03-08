"""Tests for scripts/misc/local_remi_api.py

Strategy:
  - Stub manaos_process_manager (only hard non-stdlib dep not in sys.modules)
  - _paths is real module — no stub needed
  - Use FastAPI TestClient for endpoint tests
  - Test pure helpers, system status (mocked subprocess), security, notifications, suggestions
"""
import sys
import types
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import os

import pytest

# ============================================================
# Stubs — must be registered before importing the module
# ============================================================
if "manaos_process_manager" not in sys.modules:
    _pm_mod = types.ModuleType("manaos_process_manager")
    _pm_instance = MagicMock()
    _pm_instance.list_top_processes.return_value = []
    _pm_instance.kill_processes_by_keywords.return_value = 0
    _pm_mod.get_process_manager = MagicMock(return_value=_pm_instance)
    sys.modules["manaos_process_manager"] = _pm_mod

import scripts.misc.local_remi_api as _sut
from fastapi.testclient import TestClient

TOKEN = _sut.API_TOKEN


@pytest.fixture()
def client():
    with TestClient(_sut.app, raise_server_exceptions=True) as c:
        yield c


def _auth():
    return {"Authorization": f"Bearer {TOKEN}"}


# ============================================================
# Helpers
# ============================================================

@pytest.fixture(autouse=True)
def clear_stores():
    """Reset notification/suggestion stores between tests."""
    _sut.notification_log.clear()
    _sut._last_notif_messages.clear()
    _sut.suggestion_log.clear()
    _sut._last_suggestion_keys.clear()
    yield
    _sut.notification_log.clear()
    _sut._last_notif_messages.clear()
    _sut.suggestion_log.clear()
    _sut._last_suggestion_keys.clear()


# ============================================================
# TestWorkspaceHelpers
# ============================================================

class TestWorkspaceHelpers:
    def test_unified_api_base_default(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in ("MANAOS_INTEGRATION_API_URL", "MANAOS_API_URL"):
                os.environ.pop(key, None)
            base = _sut._unified_api_base()
        assert base.startswith("http://")
        assert not base.endswith("/")

    def test_unified_api_base_env_override(self):
        with patch.dict(os.environ, {"MANAOS_INTEGRATION_API_URL": "http://custom:9999/"}):
            base = _sut._unified_api_base()
        assert base == "http://custom:9999"

    def test_workspace_python_returns_string(self):
        result = _sut._workspace_python()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_powershell_exe_nt(self):
        with patch("os.name", "nt"):
            result = _sut._powershell_exe()
        assert result == "powershell.exe"

    def test_powershell_exe_posix(self):
        with patch("os.name", "posix"):
            result = _sut._powershell_exe()
        assert result == "powershell"

    def test_safe_resolve_workspace_path_valid(self, tmp_path):
        old_root = _sut._WORKSPACE_ROOT
        try:
            _sut._WORKSPACE_ROOT = tmp_path
            result = _sut._safe_resolve_workspace_path("manaos_integrations/foo.py")
            assert result == (tmp_path / "manaos_integrations" / "foo.py").resolve()
        finally:
            _sut._WORKSPACE_ROOT = old_root

    def test_safe_resolve_workspace_path_leading_slash(self, tmp_path):
        old_root = _sut._WORKSPACE_ROOT
        try:
            _sut._WORKSPACE_ROOT = tmp_path
            result = _sut._safe_resolve_workspace_path("/manaos_integrations/bar.py")
            assert result == (tmp_path / "manaos_integrations" / "bar.py").resolve()
        finally:
            _sut._WORKSPACE_ROOT = old_root

    def test_safe_resolve_workspace_path_escape_raises(self, tmp_path):
        old_root = _sut._WORKSPACE_ROOT
        try:
            _sut._WORKSPACE_ROOT = tmp_path
            with pytest.raises(ValueError, match="escapes workspace"):
                _sut._safe_resolve_workspace_path("../../etc/passwd")
        finally:
            _sut._WORKSPACE_ROOT = old_root

    def test_safe_resolve_workspace_path_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _sut._safe_resolve_workspace_path("")


# ============================================================
# TestPatchHelpers
# ============================================================

class TestPatchHelpers:
    def test_extract_patch_paths_basic(self):
        diff = (
            "--- a/manaos_integrations/foo.py\n"
            "+++ b/manaos_integrations/foo.py\n"
            "@@ -1,3 +1,3 @@\n"
            "-old\n"
            "+new\n"
        )
        paths = _sut._extract_patch_paths(diff)
        assert "manaos_integrations/foo.py" in paths

    def test_extract_patch_paths_dedup(self):
        diff = (
            "--- a/manaos_integrations/foo.py\n"
            "+++ b/manaos_integrations/foo.py\n"
        )
        paths = _sut._extract_patch_paths(diff)
        assert paths.count("manaos_integrations/foo.py") == 1

    def test_extract_patch_paths_multiple(self):
        diff = (
            "--- a/manaos_integrations/a.py\n"
            "+++ b/manaos_integrations/a.py\n"
            "--- a/manaos_integrations/b.py\n"
            "+++ b/manaos_integrations/b.py\n"
        )
        paths = _sut._extract_patch_paths(diff)
        assert "manaos_integrations/a.py" in paths
        assert "manaos_integrations/b.py" in paths

    def test_extract_patch_paths_empty_string(self):
        assert _sut._extract_patch_paths("") == []

    def test_extract_patch_paths_none_safe(self):
        assert _sut._extract_patch_paths(None) == []  # type: ignore

    def test_is_patch_path_allowed_valid(self):
        assert _sut._is_patch_path_allowed("manaos_integrations/scripts/foo.py") is True

    def test_is_patch_path_allowed_dot_dot(self):
        assert _sut._is_patch_path_allowed("manaos_integrations/../etc/passwd") is False

    def test_is_patch_path_allowed_absolute(self):
        assert _sut._is_patch_path_allowed("/etc/passwd") is False

    def test_is_patch_path_allowed_outside_dir(self):
        assert _sut._is_patch_path_allowed("other_project/foo.py") is False

    def test_is_patch_path_allowed_empty(self):
        assert _sut._is_patch_path_allowed("") is False


# ============================================================
# TestRunCmdCapture
# ============================================================

class TestRunCmdCapture:
    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hello"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            r = _sut._run_cmd_capture(["echo", "hello"])
        assert r["ok"] is True
        assert r["exit_code"] == 0
        assert "hello" in r["stdout"]

    def test_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error msg"
        with patch("subprocess.run", return_value=mock_result):
            r = _sut._run_cmd_capture(["false"])
        assert r["ok"] is False
        assert r["exit_code"] == 1
        assert "error msg" in r["stderr"]

    def test_timeout_exception(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 1)):
            r = _sut._run_cmd_capture(["sleep", "100"], timeout=1)
        assert r["ok"] is False
        assert "error" in r

    def test_os_error_exception(self):
        with patch("subprocess.run", side_effect=OSError("no such file")):
            r = _sut._run_cmd_capture(["nonexistent_cmd"])
        assert r["ok"] is False
        assert "no such file" in r["error"]

    def test_large_stdout_truncated(self):
        big = "x" * 10000
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = big
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            r = _sut._run_cmd_capture(["cmd"])
        assert len(r["stdout"]) <= 4000


# ============================================================
# TestWriteReadHelpers
# ============================================================

class TestWriteReadHelpers:
    def test_write_json_file_creates_file(self, tmp_path):
        target = tmp_path / "sub" / "out.json"
        _sut._write_json_file(target, {"key": "value"})
        import json
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["key"] == "value"

    def test_write_json_file_atomic_no_tmp_left(self, tmp_path):
        target = tmp_path / "result.json"
        _sut._write_json_file(target, {"x": 1})
        tmp = target.with_suffix(".json.tmp")
        assert not tmp.exists()

    def test_read_text_tail_existing(self, tmp_path):
        f = tmp_path / "log.txt"
        content = "abc\ndef\nghi"
        f.write_text(content, encoding="utf-8")
        result = _sut._read_text_tail(f, max_chars=5)
        assert result == content[-5:]

    def test_read_text_tail_missing_file(self, tmp_path):
        missing = tmp_path / "nope.txt"
        result = _sut._read_text_tail(missing)
        assert result == ""

    def test_read_text_tail_full_if_small(self, tmp_path):
        f = tmp_path / "small.txt"
        f.write_text("hello", encoding="utf-8")
        result = _sut._read_text_tail(f, max_chars=4000)
        assert result == "hello"


# ============================================================
# TestSystemStatusFunctions
# ============================================================

class TestSystemStatusFunctions:
    def test_get_gpu_info_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "50, 4000, 8000, 65, RTX 3080"
        with patch("subprocess.run", return_value=mock_result):
            info = _sut.get_gpu_info()
        assert info["available"] is True
        assert info["usage_percent"] == 50.0
        assert info["memory_used_mb"] == 4000.0
        assert info["name"] == "RTX 3080"

    def test_get_gpu_info_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            info = _sut.get_gpu_info()
        assert info["available"] is False

    def test_get_gpu_info_exception(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            info = _sut.get_gpu_info()
        assert info["available"] is False

    def test_get_docker_containers_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "mycontainer\tUp 5 minutes\t0.0.0.0:80->80/tcp"
        with patch("subprocess.run", return_value=mock_result):
            containers = _sut.get_docker_containers()
        assert len(containers) == 1
        assert containers[0]["name"] == "mycontainer"

    def test_get_docker_containers_exception(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            containers = _sut.get_docker_containers()
        assert containers == []

    def test_check_comfyui_queue_offline(self):
        with patch("urllib.request.urlopen", side_effect=Exception("conn refused")):
            result = _sut.check_comfyui_queue()
        assert result["queue_remaining"] == 0

    def test_check_ollama_models_offline(self):
        with patch("urllib.request.urlopen", side_effect=Exception("conn refused")):
            result = _sut.check_ollama_models()
        assert result["status"] == "offline"
        assert result["models"] == []


# ============================================================
# TestHealthEndpoint
# ============================================================

class TestHealthEndpoint:
    def test_health_no_auth(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_returns_ok(self, client):
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "ok"

    def test_health_has_required_fields(self, client):
        r = client.get("/health")
        data = r.json()
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_version(self, client):
        r = client.get("/health")
        assert r.json()["version"] == "4.3.0"


# ============================================================
# TestStatusEndpoint
# ============================================================

class TestStatusEndpoint:
    def test_status_no_auth_returns_401(self, client):
        r = client.get("/status")
        assert r.status_code == 401

    def test_status_wrong_token_returns_401(self, client):
        r = client.get("/status", headers={"Authorization": "Bearer wrong-token"})
        assert r.status_code == 401

    def test_status_valid_token_returns_200(self, client):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            r = client.get("/status", headers=_auth())
        assert r.status_code == 200

    def test_status_has_required_keys(self, client):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            r = client.get("/status", headers=_auth())
        data = r.json()
        for key in ("gpu", "cpu", "memory", "disk", "timestamp"):
            assert key in data, f"missing key: {key}"

    def test_status_cpu_has_percent(self, client):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            r = client.get("/status", headers=_auth())
        assert "percent" in r.json()["cpu"]


# ============================================================
# TestTasksEndpoint
# ============================================================

class TestTasksEndpoint:
    def test_tasks_no_auth_returns_401(self, client):
        r = client.get("/tasks")
        assert r.status_code == 401

    def test_tasks_valid_token_returns_200(self, client):
        with patch("subprocess.run", side_effect=FileNotFoundError), \
             patch("urllib.request.urlopen", side_effect=Exception):
            r = client.get("/tasks", headers=_auth())
        assert r.status_code == 200

    def test_tasks_has_required_keys(self, client):
        with patch("subprocess.run", side_effect=FileNotFoundError), \
             patch("urllib.request.urlopen", side_effect=Exception):
            r = client.get("/tasks", headers=_auth())
        data = r.json()
        assert "docker_containers" in data
        assert "is_busy" in data


# ============================================================
# TestNotifications
# ============================================================

class TestNotifications:
    def test_add_notification_basic(self):
        _sut.add_notification("system", "test message")
        assert len(_sut.notification_log) == 1
        n = _sut.notification_log[0]
        assert n["category"] == "system"
        assert n["message"] == "test message"
        assert n["read"] is False

    def test_add_notification_dedup_within_5min(self):
        _sut.add_notification("system", "same msg")
        _sut.add_notification("system", "same msg")
        assert len(_sut.notification_log) == 1

    def test_add_notification_different_messages(self):
        _sut.add_notification("system", "msg A")
        _sut.add_notification("system", "msg B")
        assert len(_sut.notification_log) == 2

    def test_add_notification_max_50(self):
        for i in range(60):
            _sut._last_notif_messages.clear()
            _sut.add_notification("test", f"msg-{i}")
        assert len(_sut.notification_log) <= _sut.MAX_NOTIFICATIONS

    def test_get_notifications_no_auth_returns_401(self, client):
        r = client.get("/notifications")
        assert r.status_code == 401

    def test_get_notifications_returns_list(self, client):
        _sut.add_notification("test", "hello")
        r = client.get("/notifications", headers=_auth())
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_mark_notifications_read(self, client):
        _sut.add_notification("test", "unread notif")
        r = client.post("/notifications/read", headers=_auth())
        assert r.status_code == 200
        assert _sut.notification_log[0]["read"] is True


# ============================================================
# TestSuggestions
# ============================================================

class TestSuggestions:
    def test_add_suggestion_basic(self):
        _sut.add_suggestion("gpu_idle", "GPU空いてるよ", icon="🎨")
        assert len(_sut.suggestion_log) == 1
        s = _sut.suggestion_log[0]
        assert s["key"] == "gpu_idle"
        assert s["message"] == "GPU空いてるよ"
        assert s["dismissed"] is False

    def test_add_suggestion_dedup_within_15min(self):
        _sut.add_suggestion("same_key", "msg")
        _sut.add_suggestion("same_key", "msg again")
        assert len(_sut.suggestion_log) == 1

    def test_add_suggestion_different_keys(self):
        _sut.add_suggestion("key1", "msg1")
        _sut.add_suggestion("key2", "msg2")
        assert len(_sut.suggestion_log) == 2

    def test_get_suggestions_no_auth_returns_401(self, client):
        r = client.get("/suggestions")
        assert r.status_code == 401

    def test_get_suggestions_returns_non_dismissed(self, client):
        _sut.add_suggestion("test_sug", "test message", icon="💡")
        r = client.get("/suggestions", headers=_auth())
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert all(not s["dismissed"] for s in data)

    def test_dismiss_suggestion(self, client):
        _sut.add_suggestion("dismiss_me", "dismiss this")
        sug_id = _sut.suggestion_log[0]["id"]
        r = client.post(f"/suggestions/{sug_id}/dismiss", headers=_auth())
        assert r.status_code == 200
        assert _sut.suggestion_log[0]["dismissed"] is True

    def test_dismiss_nonexistent_suggestion_returns_404(self, client):
        r = client.post("/suggestions/99999/dismiss", headers=_auth())
        assert r.status_code == 404


# ============================================================
# TestActionsEndpoint
# ============================================================

class TestActionsEndpoint:
    def test_list_actions_no_auth_returns_401(self, client):
        r = client.get("/actions")
        assert r.status_code == 401

    def test_list_actions_returns_dict(self, client):
        r = client.get("/actions", headers=_auth())
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
        assert "comfyui_start" in data

    def test_run_unknown_action_returns_404(self, client):
        r = client.post("/action/unknown_action_xyz", headers=_auth())
        assert r.status_code == 404

    def test_run_action_no_auth_returns_401(self, client):
        r = client.post("/action/comfyui_start")
        assert r.status_code == 401


# ============================================================
# TestDashboardEndpoint
# ============================================================

class TestDashboardEndpoint:
    def test_dashboard_no_auth_needed(self, client):
        r = client.get("/dashboard")
        # May return 200 or 200 with placeholder HTML
        assert r.status_code == 200

    def test_widget_no_token_returns_401(self, client):
        r = client.get("/widget")
        assert r.status_code == 401

    def test_widget_valid_token(self, client):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            r = client.get(f"/widget?token={TOKEN}")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")


# ============================================================
# TestEmergencyStopEndpoint
# ============================================================

class TestEmergencyStopEndpoint:
    def test_emergency_stop_no_auth_returns_401(self, client):
        r = client.post("/emergency-stop")
        assert r.status_code == 401

    def test_emergency_stop_with_auth(self, client):
        pm_mod = sys.modules["manaos_process_manager"]
        pm_instance = pm_mod.get_process_manager.return_value
        pm_instance.kill_processes_by_keywords.return_value = 2
        r = client.post("/emergency-stop", headers=_auth())
        assert r.status_code == 200
        data = r.json()
        assert "stopped" in data
        assert "message" in data
