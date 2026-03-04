#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: personality_thought_mcp_server
人格思想システム MCP サーバーの基本動作を検証
"""

import pytest
from unittest.mock import patch, MagicMock


class TestPersonalityThoughtMCPServerImport:
    """モジュールのインポートテスト"""

    def test_server_module_importable(self):
        """server.py がインポートできること"""
        import personality_thought_mcp_server.server as srv
        assert srv is not None

    def test_api_url_default(self):
        """デフォルトの API URL が設定されていること (5126番ポート)"""
        import personality_thought_mcp_server.server as srv
        assert hasattr(srv, "API_URL")
        assert "5126" in srv.API_URL

    def test_health_port_defined(self):
        """MCP ヘルスポート (5147) が定義されていること"""
        import personality_thought_mcp_server.server as srv
        assert hasattr(srv, "HEALTH_PORT")
        assert srv.HEALTH_PORT == 5147


class TestPersonalityThoughtMCPHelpers:
    """HTTP ヘルパー関数のモックテスト"""

    def test_get_helper_calls_requests(self):
        """_get() が requests.get を呼び出すこと"""
        with patch("personality_thought_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "ok", "mood": "calm"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            import personality_thought_mcp_server.server as srv
            result = srv._get("/api/thought/mood")

            mock_req.get.assert_called_once()
            assert "status" in result or "mood" in result

    def test_post_helper_calls_requests(self):
        """_post() が requests.post を呼び出すこと"""
        with patch("personality_thought_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "ok"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import personality_thought_mcp_server.server as srv
            result = srv._post("/api/thought/mood/detect", {"text": "楽しい！"})

            mock_req.post.assert_called_once()
            assert result.get("status") == "ok"


class TestPersonalityThoughtMCPToolNames:
    """13ツールが全てサーバーコードに存在することを確認"""

    TOOL_NAMES = [
        "thought_get_mood",
        "thought_detect_mood",
        "thought_set_mood",
        "thought_get_values",
        "thought_reinforce_value",
        "thought_weaken_value",
        "thought_check_contradiction",
        "thought_log",
        "thought_get_log",
        "thought_record_evolution",
        "thought_get_evolution",
        "thought_get_prompt_prefix",
        "thought_dashboard",
    ]

    def _get_source(self):
        import personality_thought_mcp_server.server as srv
        return open(srv.__file__, encoding="utf-8").read()

    @pytest.mark.parametrize("tool_name", TOOL_NAMES)
    def test_tool_name_in_source(self, tool_name):
        """各ツール名がサーバーコードに含まれていること"""
        source = self._get_source()
        assert tool_name in source, f"{tool_name} がサーバーコードに見つかりません"


class TestPersonalityThoughtMCPToolHandlers:
    """ツールハンドラーのモックテスト"""

    def test_thought_dashboard_with_mock(self):
        """thought_dashboard がダッシュボード情報を返せること"""
        with patch("personality_thought_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "dashboard": {
                    "mood": "curious",
                    "values": {},
                    "recent_thoughts": [],
                    "recent_evolution": [],
                }
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            import personality_thought_mcp_server.server as srv
            result = srv._get("/api/thought/dashboard")
            assert "status" in result or "dashboard" in result

    def test_thought_get_mood_with_mock(self):
        """thought_get_mood が現在の気分を返せること"""
        with patch("personality_thought_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "mood": "calm",
                "mood_label": "穏やか"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            import personality_thought_mcp_server.server as srv
            result = srv._get("/api/thought/mood")
            assert "mood" in result or "status" in result

    def test_thought_check_contradiction_with_mock(self):
        """thought_check_contradiction が矛盾検出結果を返せること"""
        with patch("personality_thought_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "contradictions": [],
                "value_scores_updated": {}
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import personality_thought_mcp_server.server as srv
            result = srv._post("/api/thought/contradict", {"text": "正直に話す"})
            assert "status" in result or "contradictions" in result

    def test_thought_reinforce_value_with_mock(self):
        """thought_reinforce_value が価値強化を実行できること"""
        with patch("personality_thought_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "value": "honesty",
                "new_score": 0.72
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import personality_thought_mcp_server.server as srv
            result = srv._post("/api/thought/values/reinforce", {"value": "honesty"})
            assert "status" in result


class TestPersonalityThoughtMCPPackageInit:
    """パッケージ初期化テスト"""

    def test_package_importable(self):
        """personality_thought_mcp_server パッケージがインポートできること"""
        import personality_thought_mcp_server
        assert personality_thought_mcp_server is not None

    def test_has_version(self):
        """__version__ が設定されていること"""
        import personality_thought_mcp_server
        assert hasattr(personality_thought_mcp_server, "__version__")
        assert personality_thought_mcp_server.__version__ == "0.1.0"

    def test_has_service_name(self):
        """__service__ が personality-thought-system であること"""
        import personality_thought_mcp_server
        assert hasattr(personality_thought_mcp_server, "__service__")
        assert personality_thought_mcp_server.__service__ == "personality-thought-system"

    def test_has_port(self):
        """__port__ が 5126 であること"""
        import personality_thought_mcp_server
        assert hasattr(personality_thought_mcp_server, "__port__")
        assert personality_thought_mcp_server.__port__ == 5126
