"""
Unit tests for scripts/misc/system_status_api.py
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────
_ml = MagicMock()
_ml.get_logger = MagicMock(return_value=MagicMock())
_ml.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_logger", _ml)

_error_obj = MagicMock()
_error_obj.message = "mocked error"
_error_obj.user_message = "mocked user error"
_meh = MagicMock()
_meh.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=_error_obj)
))
_meh.ErrorCategory = MagicMock()
_meh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _meh)

_mtc = MagicMock()
_mtc.get_timeout_config = MagicMock(return_value={"health_check": 5.0, "api_call": 10})
sys.modules.setdefault("manaos_timeout_config", _mtc)

# httpx mock
_httpx_mod = MagicMock()
sys.modules.setdefault("httpx", _httpx_mod)

# psutil mock
_psutil_mod = MagicMock()
_psutil_mod.cpu_percent.return_value = 25.0
_psutil_mod.cpu_count.return_value = 8
_mem_mock = MagicMock(total=8 * 1024**3, used=4 * 1024**3, available=4 * 1024**3, percent=50.0)
_psutil_mod.virtual_memory.return_value = _mem_mock
_disk_mock = MagicMock(total=100 * 1024**3, used=40 * 1024**3, free=60 * 1024**3, percent=40.0)
_psutil_mod.disk_usage.return_value = _disk_mock
sys.modules.setdefault("psutil", _psutil_mod)

# flask / flask_cors
_flask_mod = MagicMock()
_flask_app_instance = MagicMock()
_flask_mod.Flask.return_value = _flask_app_instance
_flask_mod.jsonify = MagicMock(side_effect=lambda d: d)
sys.modules.setdefault("flask", _flask_mod)
sys.modules.setdefault("flask_cors", MagicMock())

from scripts.misc.system_status_api import (
    check_service_health,
    get_system_resources,
    get_service_process_info,
)


# ─── check_service_health ─────────────────────────────────────────────────────
class TestCheckServiceHealth:
    def test_healthy_response(self):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {"status": "healthy"}
        fake_response.elapsed.total_seconds.return_value = 0.042
        with patch("scripts.misc.system_status_api.httpx.get", return_value=fake_response):
            result = check_service_health(5100)
        assert result["status"] == "healthy"
        assert "response_time_ms" in result

    def test_non_200_response(self):
        import httpx as _real_httpx
        fake_response = MagicMock()
        fake_response.status_code = 503
        with patch("scripts.misc.system_status_api.httpx.get", return_value=fake_response):
            result = check_service_health(5100)
        assert result["status"] == "unhealthy"
        assert "HTTP 503" in result["error"]

    def test_connect_error_returns_down(self):
        import httpx as _real_httpx
        with patch("scripts.misc.system_status_api.httpx.get", side_effect=_real_httpx.ConnectError("refused")):
            result = check_service_health(5100)
        assert result["status"] == "down"

    def test_timeout_returns_timeout(self):
        import httpx as _real_httpx
        with patch("scripts.misc.system_status_api.httpx.get", side_effect=_real_httpx.TimeoutException("timed out")):
            result = check_service_health(5100)
        assert result["status"] == "timeout"

    def test_generic_exception_returns_error(self):
        with patch("scripts.misc.system_status_api.httpx.get", side_effect=ValueError("unexpected error")):
            result = check_service_health(5100)
        assert result["status"] == "error"
        assert "unexpected error" in result["error"]


# ─── get_system_resources ─────────────────────────────────────────────────────
class TestGetSystemResources:
    def test_returns_cpu_memory_disk(self):
        fake_mem = MagicMock(total=8 * 1024**3, used=3 * 1024**3, available=5 * 1024**3, percent=37.5)
        fake_disk = MagicMock(total=200 * 1024**3, used=80 * 1024**3, free=120 * 1024**3, percent=40.0)
        with patch("scripts.misc.system_status_api.psutil.cpu_percent", return_value=30.0):
            with patch("scripts.misc.system_status_api.psutil.cpu_count", return_value=4):
                with patch("scripts.misc.system_status_api.psutil.virtual_memory", return_value=fake_mem):
                    with patch("scripts.misc.system_status_api.psutil.disk_usage", return_value=fake_disk):
                        result = get_system_resources()
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert result["cpu"]["percent"] == 30.0
        assert result["cpu"]["count"] == 4

    def test_returns_empty_dict_on_exception(self):
        with patch("scripts.misc.system_status_api.psutil.cpu_percent", side_effect=RuntimeError("psutil error")):
            result = get_system_resources()
        assert result == {}


# ─── get_service_process_info ─────────────────────────────────────────────────
class TestGetServiceProcessInfo:
    def test_process_found_on_windows(self):
        fake_result = MagicMock()
        fake_result.stdout = "python.exe intent_router.py something"
        with patch("subprocess.run", return_value=fake_result):
            with patch("platform.system", return_value="Windows"):
                result = get_service_process_info("intent_router.py")
        assert result is not None

    def test_process_not_found_on_windows(self):
        fake_result = MagicMock()
        fake_result.stdout = "python.exe some_other_script.py"
        with patch("subprocess.run", return_value=fake_result):
            with patch("platform.system", return_value="Windows"):
                result = get_service_process_info("intent_router.py")
        # Returns {"running": False}
        assert result == {"running": False}

    def test_process_found_on_linux(self):
        fake_result = MagicMock()
        fake_result.stdout = "1234 pts/0 python3 task_planner.py"
        with patch("subprocess.run", return_value=fake_result):
            with patch("platform.system", return_value="Linux"):
                result = get_service_process_info("task_planner.py")
        assert result is not None
        assert result.get("running") is True

    def test_exception_returns_none(self):
        with patch("subprocess.run", side_effect=Exception("fail")):
            with patch("platform.system", return_value="Linux"):
                result = get_service_process_info("broken.py")
        assert result is None
