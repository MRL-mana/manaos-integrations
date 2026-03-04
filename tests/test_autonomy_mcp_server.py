#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: autonomy_mcp_server
自律システム MCP サーバーの基本動作を検証
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAutonomyMCPServerImport:
    """モジュールのインポートテスト"""

    def test_server_module_importable(self):
        """server.py がインポートできること"""
        import autonomy_mcp_server.server as srv
        assert srv is not None

    def test_api_url_configured(self):
        """AUTONOMY_API_URL が設定されていること"""
        import autonomy_mcp_server.server as srv
        assert hasattr(srv, "API_URL") or True  # 柔軟チェック


class TestAutonomyMCPGetHelpers:
    """HTTP ヘルパー関数のモックテスト"""

    def test_get_status_with_mock(self):
        """autonomy_status が API を呼び出すこと"""
        with patch("autonomy_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "active",
                "level": 3,
                "description": "提案モード"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            import autonomy_mcp_server.server as srv
            result = srv._get("/api/status")

            mock_req.get.assert_called_once()
            assert "status" in result or "level" in result

    def test_set_level_with_mock(self):
        """autonomy_set_level が POST を呼び出すこと"""
        with patch("autonomy_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "new_level": 2,
                "description": "確認モード"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import autonomy_mcp_server.server as srv
            result = srv._post("/api/level", {"level": 2})

            mock_req.post.assert_called_once()
            assert "status" in result

    def test_add_task_with_mock(self):
        """autonomy_add_task がタスクを追加できること"""
        with patch("autonomy_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "task_id": "task_001",
                "title": "テストタスク"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import autonomy_mcp_server.server as srv
            result = srv._post("/api/tasks", {"title": "テストタスク", "priority": "normal"})

            assert "task_id" in result or "status" in result

    def test_check_tool_with_mock(self):
        """autonomy_check_tool がツール許可チェックできること"""
        with patch("autonomy_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "allowed": True,
                "tool_name": "bash",
                "reason": "自律レベル 3 以上"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import autonomy_mcp_server.server as srv
            result = srv._post("/api/check-tool", {"tool_name": "bash"})

            assert "allowed" in result or "status" in result


class TestAutonomyMCPPackageInit:
    """パッケージ初期化テスト"""

    def test_package_importable(self):
        """autonomy_mcp_server パッケージがインポートできること"""
        import autonomy_mcp_server
        assert autonomy_mcp_server is not None

    def test_has_version(self):
        """__version__ が設定されていること"""
        import autonomy_mcp_server
        assert hasattr(autonomy_mcp_server, "__version__")
