"""
Unit tests for scripts/misc/mcp_common.py
"""
import json
import sys
import time
import threading
import urllib.request
from unittest.mock import MagicMock

# manaos_logger mock (optional import inside module)
sys.modules.setdefault("manaos_logger", MagicMock(
    get_logger=MagicMock(return_value=MagicMock()),
    get_service_logger=MagicMock(return_value=MagicMock()),
))

import pytest
from scripts.misc.mcp_common import (
    MCPHealthServer,
    check_mcp_available,
    get_mcp_logger,
    start_health_thread,
)


# ── TestGetMcpLogger ────────────────────────────────────────────────────────
class TestGetMcpLogger:
    def test_returns_logger(self):
        logger = get_mcp_logger("test-service")
        assert logger is not None

    def test_different_names_allowed(self):
        l1 = get_mcp_logger("svc1")
        l2 = get_mcp_logger("svc2")
        assert l1 is not None and l2 is not None


# ── TestCheckMcpAvailable ──────────────────────────────────────────────────
class TestCheckMcpAvailable:
    def test_returns_bool(self):
        result = check_mcp_available()
        assert isinstance(result, bool)


# ── TestMCPHealthServerInit ───────────────────────────────────────────────
class TestMCPHealthServerInit:
    def test_service_name_stored(self):
        srv = MCPHealthServer("my-svc", 9999)
        assert srv.service_name == "my-svc"

    def test_port_stored(self):
        srv = MCPHealthServer("my-svc", 9999)
        assert srv.port == 9999

    def test_default_host(self):
        srv = MCPHealthServer("my-svc", 9999)
        assert srv.host == "127.0.0.1"

    def test_custom_host(self):
        srv = MCPHealthServer("my-svc", 9999, host="0.0.0.0")
        assert srv.host == "0.0.0.0"

    def test_extra_health_data_default_empty(self):
        srv = MCPHealthServer("my-svc", 9999)
        assert srv.extra_health_data == {}

    def test_extra_health_data_stored(self):
        srv = MCPHealthServer("my-svc", 9999, extra_health_data={"version": "1.0"})
        assert srv.extra_health_data == {"version": "1.0"}

    def test_server_none_before_start(self):
        srv = MCPHealthServer("my-svc", 9999)
        assert srv._server is None

    def test_thread_none_before_start(self):
        srv = MCPHealthServer("my-svc", 9999)
        assert srv._thread is None


# ── TestMakeHandler ──────────────────────────────────────────────────────
class TestMakeHandler:
    def test_returns_class(self):
        srv = MCPHealthServer("svc", 9998)
        handler_cls = srv._make_handler()
        assert handler_cls is not None
        assert isinstance(handler_cls, type)

    def test_handler_has_do_get(self):
        srv = MCPHealthServer("svc", 9998)
        handler_cls = srv._make_handler()
        assert hasattr(handler_cls, "do_GET")


# ── TestStartStop ─────────────────────────────────────────────────────────
class TestStartStop:
    def test_start_returns_thread(self):
        import socket
        # Find a free port
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        srv = MCPHealthServer("test-svc", port)
        thread = srv.start(daemon=True)
        assert isinstance(thread, threading.Thread)
        time.sleep(0.1)
        srv.stop()

    def test_health_endpoint_returns_200(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        srv = MCPHealthServer("test-svc", port)
        srv.start(daemon=True)
        time.sleep(0.2)

        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=2
            ) as resp:
                assert resp.status == 200
                body = json.loads(resp.read())
                assert body["status"] == "healthy"
                assert body["service"] == "test-svc"
        finally:
            srv.stop()

    def test_health_endpoint_includes_extra_data(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        srv = MCPHealthServer("test-svc", port, extra_health_data={"version": "2.0"})
        srv.start(daemon=True)
        time.sleep(0.2)

        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=2
            ) as resp:
                body = json.loads(resp.read())
                assert body["version"] == "2.0"
        finally:
            srv.stop()

    def test_unknown_path_returns_404(self):
        import socket
        from urllib.error import HTTPError
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        srv = MCPHealthServer("test-svc", port)
        srv.start(daemon=True)
        time.sleep(0.2)

        try:
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/unknown", timeout=2
                )
                assert False, "Should have raised HTTPError"
            except HTTPError as e:
                assert e.code == 404
        finally:
            srv.stop()


# ── TestStartHealthThread ─────────────────────────────────────────────────
class TestStartHealthThread:
    def test_returns_mcp_health_server(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        srv = start_health_thread("quick-svc", port)
        assert isinstance(srv, MCPHealthServer)
        time.sleep(0.1)
        srv.stop()

    def test_service_name_set(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        srv = start_health_thread("named-svc", port)
        assert srv.service_name == "named-svc"
        time.sleep(0.1)
        srv.stop()
