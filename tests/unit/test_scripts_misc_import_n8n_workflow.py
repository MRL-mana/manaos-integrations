"""
Unit tests for scripts/misc/import_n8n_workflow.py
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# manaos_integrations._paths is optional
sys.modules.setdefault("manaos_integrations._paths", MagicMock(N8N_PORT=5678))
sys.modules.setdefault("_paths", MagicMock(N8N_PORT=5678))

from scripts.misc.import_n8n_workflow import import_workflow


class TestImportWorkflow:
    def _make_workflow_file(self, tmp_path: Path) -> Path:
        data = {"name": "Test Workflow", "nodes": [{"id": 1}, {"id": 2}]}
        p = tmp_path / "workflow.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_returns_false_when_file_not_found(self, tmp_path: Path):
        """存在しないファイルを指定した場合は False を返す"""
        result = import_workflow(str(tmp_path / "no_file.json"))
        assert result is False

    def test_returns_true_on_success_201(self, tmp_path: Path):
        """201 ステータスのとき True を返す"""
        wf = self._make_workflow_file(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": "abc", "name": "Test Workflow"}
        with patch("scripts.misc.import_n8n_workflow.requests.post", return_value=mock_resp):
            result = import_workflow(str(wf))
        assert result is True

    def test_returns_true_on_success_200(self, tmp_path: Path):
        """200 ステータスのとき True を返す"""
        wf = self._make_workflow_file(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "xyz", "name": "Test Workflow"}
        with patch("scripts.misc.import_n8n_workflow.requests.post", return_value=mock_resp):
            result = import_workflow(str(wf))
        assert result is True

    def test_returns_false_on_401(self, tmp_path: Path):
        """401 認証エラーのとき False を返す"""
        wf = self._make_workflow_file(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        with patch("scripts.misc.import_n8n_workflow.requests.post", return_value=mock_resp):
            result = import_workflow(str(wf))
        assert result is False

    def test_returns_false_on_server_error(self, tmp_path: Path):
        """500 サーバエラーのとき False を返す"""
        wf = self._make_workflow_file(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.headers = {}
        with patch("scripts.misc.import_n8n_workflow.requests.post", return_value=mock_resp):
            result = import_workflow(str(wf))
        assert result is False

    def test_returns_false_on_connection_error(self, tmp_path: Path):
        """接続エラーのとき False を返す"""
        import requests as _requests
        wf = self._make_workflow_file(tmp_path)
        with patch(
            "scripts.misc.import_n8n_workflow.requests.post",
            side_effect=_requests.exceptions.ConnectionError("refused"),
        ):
            result = import_workflow(str(wf))
        assert result is False

    def test_bearer_auth_used_for_jwt_key(self, tmp_path: Path):
        """JWT トークン (eyJ...) は Bearer ヘッダとして送信される"""
        wf = self._make_workflow_file(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "tok", "name": "T"}
        header_used = {}
        def _fake_post(url, json=None, headers=None, timeout=None):
            header_used.update(headers or {})
            return mock_resp
        with patch("scripts.misc.import_n8n_workflow.requests.post", side_effect=_fake_post):
            import_workflow(str(wf), api_key="eyJfake.jwt.token")
        assert "Authorization" in header_used
        assert header_used["Authorization"].startswith("Bearer ")

    def test_api_key_header_used_for_non_jwt_key(self, tmp_path: Path):
        """非 JWT キーは X-N8N-API-KEY ヘッダとして送信される"""
        wf = self._make_workflow_file(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "k", "name": "T"}
        header_used = {}
        def _fake_post(url, json=None, headers=None, timeout=None):
            header_used.update(headers or {})
            return mock_resp
        with patch("scripts.misc.import_n8n_workflow.requests.post", side_effect=_fake_post):
            import_workflow(str(wf), api_key="plain-api-key-12345678901234567890")
        assert "X-N8N-API-KEY" in header_used
