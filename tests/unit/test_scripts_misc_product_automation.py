"""tests/unit/test_scripts_misc_product_automation.py

product_automation.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.product_automation as _mod


class TestGetGeneratedContents:
    def test_returns_list_on_success(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [{"id": "c1"}, {"id": "c2"}]}
        monkeypatch.setattr(_mod.httpx, "get", lambda *a, **kw: mock_resp)

        result = _mod.get_generated_contents()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_empty_list_on_http_error(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        monkeypatch.setattr(_mod.httpx, "get", lambda *a, **kw: mock_resp)

        result = _mod.get_generated_contents()
        assert result == []

    def test_returns_empty_list_on_exception(self, monkeypatch):
        def _raise(*a, **kw): raise Exception("connection refused")
        monkeypatch.setattr(_mod.httpx, "get", _raise)

        result = _mod.get_generated_contents()
        assert result == []

    def test_filters_by_content_type(self, monkeypatch):
        captured = {}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}

        def capture(url, params=None, **kw):
            captured["params"] = params
            return mock_resp

        monkeypatch.setattr(_mod.httpx, "get", capture)
        _mod.get_generated_contents(content_type="blog_draft")
        assert captured["params"].get("content_type") == "blog_draft"


class TestCreateProductFromContent:
    def test_returns_product_id_on_success(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        monkeypatch.setattr(_mod.httpx, "post", lambda *a, **kw: mock_resp)

        content = {
            "content_id": "c-001",
            "content_type": "blog_draft",
            "title": "テスト記事",
            "content": "記事内容",
        }
        result = _mod.create_product_from_content(content)
        assert result == "product_c-001"

    def test_returns_none_on_http_error(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        monkeypatch.setattr(_mod.httpx, "post", lambda *a, **kw: mock_resp)

        content = {"content_id": "c-002", "content_type": "blog_draft", "title": "test", "content": "x"}
        result = _mod.create_product_from_content(content)
        assert result is None

    def test_returns_none_on_exception(self, monkeypatch):
        def _raise(*a, **kw): raise Exception("refused")
        monkeypatch.setattr(_mod.httpx, "post", _raise)

        content = {"content_id": "c-003", "content_type": "note_article", "title": "t", "content": "x"}
        result = _mod.create_product_from_content(content)
        assert result is None

    def test_price_map_blog_draft(self, monkeypatch):
        captured = {}
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        def capture(url, json=None, **kw):
            captured["json"] = json
            return mock_resp

        monkeypatch.setattr(_mod.httpx, "post", capture)
        _mod.create_product_from_content({
            "content_id": "c-004",
            "content_type": "blog_draft",
            "title": "blog",
            "content": "text",
        })
        assert captured["json"]["price"] == 500.0


class TestFlaskRoutes:
    @pytest.fixture
    def client(self):
        _mod.app.config["TESTING"] = True
        with _mod.app.test_client() as c:
            yield c

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("status") == "healthy"
