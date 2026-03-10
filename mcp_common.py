"""MCP サーバー共通基盤モジュール.

各MCPサーバーで重複するヘルスチェックHTTPサーバー、MCP SDK 可用性チェック、
ロガー初期化などを共通化する。

使い方::

    from mcp_common import (
        MCPHealthServer,
        check_mcp_available,
        get_mcp_logger,
        start_health_thread,
    )
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

# ── ロガー ──────────────────────────────────
try:
    from manaos_logger import get_logger as _get_logger
except ImportError:
    import logging

    def _get_logger(name: str, **kw) -> logging.Logger:  # type: ignore[misc]
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)8s] [%(name)s] %(message)s",
        )
        return logging.getLogger(name)


def get_mcp_logger(name: str):
    """MCP サーバー用ロガーを取得"""
    return _get_logger(name)


# ── MCP SDK チェック ────────────────────────
def check_mcp_available() -> bool:
    """mcp パッケージが利用可能か確認"""
    try:
        from mcp.server import Server  # noqa: F401
        from mcp.server.stdio import stdio_server  # noqa: F401
        from mcp.types import Tool, TextContent  # noqa: F401

        return True
    except ImportError:
        return False


# ── ヘルスチェック HTTP サーバー ──────────────
class MCPHealthServer:
    """各 MCP サーバーに HTTP /health エンドポイントを提供する軽量サーバー.

    Parameters
    ----------
    service_name:
        ヘルスレスポンスに含める識別名 (例: ``"mrl-memory-mcp"``).
    port:
        リッスンポート (環境変数 ``{SERVICE}_MCP_HEALTH_PORT`` で上書き可能).
    host:
        バインドアドレス.
    """

    def __init__(
        self,
        service_name: str,
        port: int,
        host: str = "127.0.0.1",
        extra_health_data: Optional[dict] = None,
    ):
        self.service_name = service_name
        self.port = port
        self.host = host
        self.extra_health_data = extra_health_data or {}
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def _make_handler(self):
        svc = self.service_name
        extra = self.extra_health_data

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    body = {"status": "healthy", "service": svc, **extra}
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(body).encode())
                else:
                    self.send_error(404)

            def log_message(self, fmt, *args):  # type: ignore
                pass  # suppress access log

        return _Handler

    def start(self, daemon: bool = True) -> threading.Thread:
        """ヘルスチェックサーバーをバックグラウンドスレッドで開始"""
        handler = self._make_handler()

        def _run():
            try:
                self._server = HTTPServer((self.host, self.port), handler)
                self._server.serve_forever()
            except OSError as e:
                logger = get_mcp_logger("mcp_common.health")
                logger.warning(f"ヘルスサーバー起動失敗 (port={self.port}): {e}")

        self._thread = threading.Thread(target=_run, daemon=daemon)
        self._thread.start()
        return self._thread

    def stop(self):
        if self._server:
            self._server.shutdown()


def start_health_thread(
    service_name: str,
    port: int,
    host: str = "127.0.0.1",
) -> MCPHealthServer:
    """ヘルスチェックサーバーを起動してインスタンスを返すショートカット"""
    srv = MCPHealthServer(service_name, port, host)
    srv.start()
    return srv
