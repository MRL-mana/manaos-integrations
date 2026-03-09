"""
Unit tests for scripts/misc/service_monitor.py
"""
import sys
from datetime import datetime
from dataclasses import asdict
from unittest.mock import MagicMock, patch

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_flask = MagicMock()
_flask.Flask.return_value = MagicMock()
_flask.jsonify = MagicMock(side_effect=lambda x: x)
sys.modules.setdefault("flask", _flask)

_flask_cors = MagicMock()
sys.modules.setdefault("flask_cors", _flask_cors)

import pytest  # noqa: E402
from scripts.misc.service_monitor import ServiceStatus, ServiceMonitor  # noqa: E402


# ── helpers ────────────────────────────────────────────────────────────────
_MINIMAL_CONFIG = {
    "services": [
        {"name": "ServiceA", "port": 5100, "script": "a.py"},
        {"name": "ServiceB", "port": 5101, "script": "b.py"},
    ],
    "check_interval": 30,
    "max_restarts": 3,
    "restart_delay": 1,
}


def make_monitor(tmp_path=None):
    """ディスクI/O・スレッドをバイパスした ServiceMonitor"""
    sm = ServiceMonitor.__new__(ServiceMonitor)
    sm.config = _MINIMAL_CONFIG.copy()
    sm.check_interval = 30
    sm.max_restarts = 3
    sm.services = {}
    sm.monitoring = False
    sm.monitor_thread = None
    from pathlib import Path
    sm.config_path = (tmp_path or Path("/tmp")) / "service_monitor_config.json"
    return sm


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def monitor(tmp_path):
    return make_monitor(tmp_path)


# ── TestServiceStatus ──────────────────────────────────────────────────────
class TestServiceStatus:
    def test_required_fields(self):
        ss = ServiceStatus(
            name="TestSvc",
            port=5100,
            status="running",
            last_check=datetime.now().isoformat(),
            restart_count=0,
        )
        assert ss.name == "TestSvc"
        assert ss.port == 5100
        assert ss.status == "running"
        assert ss.restart_count == 0
        assert ss.error_message is None

    def test_error_message_field(self):
        ss = ServiceStatus(
            name="X",
            port=1,
            status="error",
            last_check="",
            restart_count=1,
            error_message="oops",
        )
        assert ss.error_message == "oops"

    def test_asdict_works(self):
        ss = ServiceStatus(name="X", port=1, status="running",
                           last_check="", restart_count=0)
        d = asdict(ss)
        assert "name" in d
        assert "port" in d


# ── TestGetDefaultConfig ───────────────────────────────────────────────────
class TestGetDefaultConfig:
    def test_has_services_key(self, monitor):
        cfg = monitor._get_default_config()
        assert "services" in cfg

    def test_services_is_list(self, monitor):
        cfg = monitor._get_default_config()
        assert isinstance(cfg["services"], list)

    def test_has_required_fields(self, monitor):
        cfg = monitor._get_default_config()
        for key in ("check_interval", "max_restarts", "restart_delay"):
            assert key in cfg

    def test_service_entries_have_name_and_port(self, monitor):
        cfg = monitor._get_default_config()
        for svc in cfg["services"]:
            assert "name" in svc
            assert "port" in svc


# ── TestInitServices ───────────────────────────────────────────────────────
class TestInitServices:
    def test_creates_service_entries(self, monitor):
        monitor._init_services()
        assert "ServiceA" in monitor.services
        assert "ServiceB" in monitor.services

    def test_initial_status_unknown(self, monitor):
        monitor._init_services()
        assert monitor.services["ServiceA"].status == "unknown"

    def test_initial_restart_count_zero(self, monitor):
        monitor._init_services()
        assert monitor.services["ServiceA"].restart_count == 0

    def test_port_correct(self, monitor):
        monitor._init_services()
        assert monitor.services["ServiceA"].port == 5100


# ── TestCheckService ───────────────────────────────────────────────────────
class TestCheckService:
    def test_connect_error_returns_stopped(self, monitor):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = monitor._check_service(5100)
        assert status == "stopped"

    def test_200_response_returns_running(self, monitor):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.get", return_value=mock_resp):
            status = monitor._check_service(5100)
        assert status == "running"

    def test_non_200_returns_stopped(self, monitor):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.get", return_value=mock_resp):
            status = monitor._check_service(5100)
        assert status == "stopped"

    def test_exception_returns_stopped(self, monitor):
        with patch("httpx.get", side_effect=Exception("timeout")):
            status = monitor._check_service(5100)
        assert status == "stopped"


# ── TestGetStatusReport ────────────────────────────────────────────────────
class TestGetStatusReport:
    def _setup_services(self, monitor, statuses):
        for name, st in statuses.items():
            monitor.services[name] = ServiceStatus(
                name=name,
                port=5100,
                status=st,
                last_check=datetime.now().isoformat(),
                restart_count=0,
            )

    def test_returns_dict(self, monitor):
        self._setup_services(monitor, {"A": "running"})
        assert isinstance(monitor.get_status_report(), dict)

    def test_required_keys(self, monitor):
        self._setup_services(monitor, {"A": "running"})
        report = monitor.get_status_report()
        for key in ("timestamp", "total_services", "running", "stopped", "error", "services"):
            assert key in report

    def test_running_count_correct(self, monitor):
        self._setup_services(monitor, {
            "A": "running",
            "B": "running",
            "C": "stopped",
        })
        report = monitor.get_status_report()
        assert report["running"] == 2
        assert report["stopped"] == 1

    def test_error_count(self, monitor):
        self._setup_services(monitor, {"A": "error"})
        assert monitor.get_status_report()["error"] == 1

    def test_total_services(self, monitor):
        self._setup_services(monitor, {"A": "running", "B": "stopped"})
        assert monitor.get_status_report()["total_services"] == 2

    def test_timestamp_is_string(self, monitor):
        self._setup_services(monitor, {"A": "running"})
        ts = monitor.get_status_report()["timestamp"]
        datetime.fromisoformat(ts)  # raises if invalid

    def test_services_detail_included(self, monitor):
        self._setup_services(monitor, {"A": "running"})
        report = monitor.get_status_report()
        assert "A" in report["services"]

    def test_empty_services(self, monitor):
        report = monitor.get_status_report()
        assert report["total_services"] == 0
        assert report["running"] == 0


# ── TestStartStopMonitoring ────────────────────────────────────────────────
class TestStartStopMonitoring:
    def test_start_sets_monitoring_true(self, monitor):
        monitor._monitor_loop = lambda: None  # prevent actual loop
        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            monitor.start_monitoring()
        assert monitor.monitoring is True

    def test_start_twice_no_duplicate(self, monitor):
        monitor.monitoring = True
        original_thread = monitor.monitor_thread
        monitor.start_monitoring()
        assert monitor.monitor_thread is original_thread

    def test_stop_sets_monitoring_false(self, monitor):
        monitor.monitoring = True
        monitor.monitor_thread = MagicMock()
        monitor.stop_monitoring()
        assert monitor.monitoring is False
