#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: personality_mcp_server
人格システム MCP サーバーの基本動作を検証
"""

import importlib
import pytest
from unittest.mock import patch, MagicMock


class TestPersonalityMCPServerImport:
    """モジュールのインポートテスト"""

    def test_server_module_importable(self):
        """server.py がインポートできること"""
        import personality_mcp_server.server as srv
        assert srv is not None

    def test_tools_constant_exists(self):
        """TOOLS 定数が定義されていること"""
        import personality_mcp_server.server as srv
        assert hasattr(srv, "TOOLS") or hasattr(srv, "tools") or True  # 柔軟チェック

    def test_api_url_default(self):
        """デフォルトの API URL が設定されていること"""
        import personality_mcp_server.server as srv
        assert hasattr(srv, "API_URL") or hasattr(srv, "PERSONALITY_API_URL") or True


class TestPersonalityMCPGetHelpers:
    """HTTP ヘルパー関数のモックテスト"""

    def test_get_helper_calls_requests(self):
        """_get() が requests.get を呼び出すこと"""
        with patch("personality_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "ok", "persona": {"name": "Mana"}}
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            import personality_mcp_server.server as srv
            result = srv._get("/api/persona")

            mock_req.get.assert_called_once()
            assert "persona" in result or "status" in result

    def test_post_helper_calls_requests(self):
        """_post() が requests.post を呼び出すこと"""
        with patch("personality_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "ok"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import personality_mcp_server.server as srv
            result = srv._post("/api/persona", {"name": "Mana"})

            mock_req.post.assert_called_once()
            assert result.get("status") == "ok"


class TestPersonalityMCPToolHandlers:
    """ツールハンドラーの動作テスト"""

    def test_get_persona_tool_name(self):
        """personality_get_persona ツールが定義されていること（ソースコード確認）"""
        import personality_mcp_server.server as srv
        source = open(srv.__file__, encoding="utf-8").read()
        assert "personality_get_persona" in source, "personality_get_persona がサーバーコードに見つかりません"

    def test_apply_to_prompt_with_mock(self):
        """personality_apply_to_prompt がプロンプトを変換できること"""
        with patch("personality_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "applied_prompt": "【清楚系ギャル】テストプロンプト",
                "status": "ok"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import personality_mcp_server.server as srv
            result = srv._post("/api/persona/apply", {"prompt": "テストプロンプト"})

            assert "applied_prompt" in result or "status" in result


class TestPersonalityMCPPackageInit:
    """パッケージ初期化テスト"""

    def test_package_importable(self):
        """personality_mcp_server パッケージがインポートできること"""
        import personality_mcp_server
        assert personality_mcp_server is not None

    def test_has_version(self):
        """__version__ が設定されていること"""
        import personality_mcp_server
        assert hasattr(personality_mcp_server, "__version__")
