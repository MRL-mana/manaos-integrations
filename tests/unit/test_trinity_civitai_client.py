"""Unit tests for tools/trinity_civitai_client.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_civitai_client import CivitAIClient


def _mock_response(status_code: int = 200, json_data: dict | None = None):
    """requests.Response の最小モック。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# __init__
# ─────────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_explicit_api_key(self):
        client = CivitAIClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert "Bearer test_key" in client.headers["Authorization"]

    def test_no_env_file_api_key_is_none(self):
        # /root/.mana_vault/civitai_api.env は Windows 環境に存在しない想定
        with patch("pathlib.Path.exists", return_value=False):
            client = CivitAIClient()
        assert client.api_key is None

    def test_base_url_set(self):
        client = CivitAIClient(api_key="x")
        assert client.base_url == "https://civitai.com/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# get_favorites
# ─────────────────────────────────────────────────────────────────────────────

class TestGetFavorites:
    def test_returns_json_on_200(self):
        client = CivitAIClient(api_key="test")
        data = {"items": [{"id": 1}, {"id": 2}], "totalItems": 2}
        with patch("requests.get", return_value=_mock_response(200, data)):
            result = client.get_favorites()
        assert result["totalItems"] == 2
        assert len(result["items"]) == 2

    def test_request_exception_returns_none(self):
        client = CivitAIClient(api_key="test")
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("fail")):
            result = client.get_favorites()
        assert result is None

    def test_sends_favorites_param(self):
        client = CivitAIClient(api_key="test")
        with patch("requests.get", return_value=_mock_response(200, {})) as mock_get:
            client.get_favorites()
        call_params = mock_get.call_args[1]["params"]
        assert call_params.get("favorites") == "true"


# ─────────────────────────────────────────────────────────────────────────────
# get_model_details
# ─────────────────────────────────────────────────────────────────────────────

class TestGetModelDetails:
    def test_returns_model_dict(self):
        client = CivitAIClient(api_key="test")
        model_data = {"id": 42, "name": "DreamShaper", "type": "Checkpoint"}
        with patch("requests.get", return_value=_mock_response(200, model_data)):
            result = client.get_model_details(42)
        assert result["id"] == 42
        assert result["name"] == "DreamShaper"

    def test_url_contains_model_id(self):
        client = CivitAIClient(api_key="test")
        with patch("requests.get", return_value=_mock_response(200, {})) as mock_get:
            client.get_model_details(99)
        called_url = mock_get.call_args[0][0]
        assert "99" in called_url

    def test_http_error_returns_none(self):
        client = CivitAIClient(api_key="test")
        with patch("requests.get", return_value=_mock_response(404)):
            result = client.get_model_details(99)
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# search_models
# ─────────────────────────────────────────────────────────────────────────────

class TestSearchModels:
    def test_returns_json_on_200(self):
        client = CivitAIClient(api_key="test")
        data = {"items": [{"id": 10}], "totalItems": 1}
        with patch("requests.get", return_value=_mock_response(200, data)):
            result = client.search_models("anime")
        assert result["totalItems"] == 1

    def test_query_in_request_params(self):
        client = CivitAIClient(api_key="test")
        with patch("requests.get", return_value=_mock_response(200, {})) as mock_get:
            client.search_models("portrait")
        call_params = mock_get.call_args[1]["params"]
        assert call_params.get("query") == "portrait"

    def test_request_exception_returns_none(self):
        client = CivitAIClient(api_key="test")
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            result = client.search_models("test")
        assert result is None
