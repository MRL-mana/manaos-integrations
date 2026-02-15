#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: mcp_common モジュール
MCPヘルスサーバーの起動・応答と、ユーティリティ関数を検証
"""

import json
import time
import requests
import pytest

from mcp_common import (
    MCPHealthServer,
    check_mcp_available,
    get_mcp_logger,
    start_health_thread,
)


class TestCheckMCPAvailable:
    """MCP SDK 可用性チェック"""

    def test_returns_bool(self):
        result = check_mcp_available()
        assert isinstance(result, bool)

    def test_returns_true_when_installed(self):
        """mcp がインストールされている環境では True を返す"""
        try:
            import mcp  # noqa: F401
            assert check_mcp_available() is True
        except ImportError:
            pytest.skip("mcp not installed")


class TestGetMCPLogger:
    """ロガー取得"""

    def test_returns_logger(self):
        logger = get_mcp_logger("test.mcp")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")


class TestMCPHealthServer:
    """ヘルスチェック HTTP サーバー"""

    @pytest.fixture()
    def health_server(self):
        """テスト用ヘルスサーバーをポート 19876 で起動"""
        srv = MCPHealthServer("test-service", port=19876)
        srv.start(daemon=True)
        time.sleep(0.3)  # サーバー起動待ち
        yield srv
        srv.stop()

    def test_health_endpoint(self, health_server):
        resp = requests.get("http://127.0.0.1:19876/health", timeout=2)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "test-service"

    def test_404_on_other_paths(self, health_server):
        resp = requests.get("http://127.0.0.1:19876/unknown", timeout=2)
        assert resp.status_code == 404


class TestStartHealthThread:
    """ショートカット関数"""

    def test_start_and_stop(self):
        srv = start_health_thread("shortcut-test", port=19877)
        time.sleep(0.3)
        try:
            resp = requests.get("http://127.0.0.1:19877/health", timeout=2)
            assert resp.status_code == 200
            assert resp.json()["service"] == "shortcut-test"
        finally:
            srv.stop()
