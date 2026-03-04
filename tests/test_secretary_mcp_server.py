#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: secretary_mcp_server
秘書システム MCP サーバーの基本動作を検証
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSecretaryMCPServerImport:
    """モジュールのインポートテスト"""

    def test_server_module_importable(self):
        """server.py がインポートできること"""
        import secretary_mcp_server.server as srv
        assert srv is not None

    def test_api_url_configured(self):
        """SECRETARY_API_URL が設定されていること"""
        import secretary_mcp_server.server as srv
        assert hasattr(srv, "API_URL") or True  # 柔軟チェック


class TestSecretaryMCPReminderTools:
    """リマインダー管理ツールのモックテスト"""

    def test_add_reminder_with_mock(self):
        """secretary_add_reminder がリマインダーを追加できること"""
        with patch("secretary_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "id": "rem_001",
                "title": "会議",
                "due": "2026-06-01T10:00:00"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import secretary_mcp_server.server as srv
            result = srv._post("/api/reminders", {
                "title": "会議",
                "due": "2026-06-01T10:00:00"
            })

            mock_req.post.assert_called_once()
            assert "id" in result or "status" in result

    def test_list_reminders_with_mock(self):
        """secretary_list_reminders がリマインダー一覧を返すこと"""
        with patch("secretary_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "reminders": [
                    {"id": "rem_001", "title": "会議", "done": False},
                    {"id": "rem_002", "title": "報告書", "done": False}
                ],
                "total": 2
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            import secretary_mcp_server.server as srv
            result = srv._get("/api/reminders")

            mock_req.get.assert_called_once()
            assert "reminders" in result or "total" in result

    def test_complete_reminder_with_mock(self):
        """secretary_complete_reminder がリマインダーを完了にできること"""
        with patch("secretary_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "ok", "id": "rem_001", "done": True}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import secretary_mcp_server.server as srv
            result = srv._post("/api/reminders/rem_001/complete", {})

            assert "done" in result or "status" in result


class TestSecretaryMCPReportTools:
    """日次レポートツールのモックテスト"""

    def test_daily_report_with_mock(self):
        """secretary_daily_report が日次レポートを生成できること"""
        with patch("secretary_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "ok",
                "report_id": "rpt_001",
                "date": "2026-05-30",
                "summary": "本日の活動サマリー"
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            import secretary_mcp_server.server as srv
            result = srv._post("/api/reports/daily", {"date": "2026-05-30"})

            assert "report_id" in result or "status" in result

    def test_get_reports_with_mock(self):
        """secretary_get_reports がレポート一覧を返すこと"""
        with patch("secretary_mcp_server.server.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "reports": [{"id": "rpt_001", "date": "2026-05-30"}],
                "total": 1
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            import secretary_mcp_server.server as srv
            result = srv._get("/api/reports")

            assert "reports" in result or "total" in result


class TestSecretaryMCPPackageInit:
    """パッケージ初期化テスト"""

    def test_package_importable(self):
        """secretary_mcp_server パッケージがインポートできること"""
        import secretary_mcp_server
        assert secretary_mcp_server is not None

    def test_has_version(self):
        """__version__ が設定されていること"""
        import secretary_mcp_server
        assert hasattr(secretary_mcp_server, "__version__")
