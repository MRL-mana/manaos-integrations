"""
Unit tests for scripts/misc/brave_search_integration.py
"""
import sys
import json
from unittest.mock import MagicMock, patch

import pytest
from scripts.misc.brave_search_integration import BraveSearchIntegration, BraveSearchResult


# ── helpers ────────────────────────────────────────────────────────────────
def make_integration(key: str = "test_key_abc") -> BraveSearchIntegration:
    return BraveSearchIntegration(api_key=key)


def make_search_response(n: int = 2) -> dict:
    return {
        "web": {
            "results": [
                {
                    "title": f"Result {i}",
                    "url": f"https://example.com/{i}",
                    "description": f"Description {i}",
                    "age": "2 hours ago",
                }
                for i in range(n)
            ]
        }
    }


def mock_requests_get(n: int = 2):
    resp = MagicMock()
    resp.json.return_value = make_search_response(n)
    resp.raise_for_status.return_value = None
    return resp


# ── TestBraveSearchResult ──────────────────────────────────────────────────
class TestBraveSearchResult:
    def test_fields(self):
        r = BraveSearchResult(title="T", url="U", description="D")
        assert r.title == "T"
        assert r.url == "U"
        assert r.description == "D"
        assert r.age is None


# ── TestIsAvailable ────────────────────────────────────────────────────────
class TestIsAvailable:
    def test_with_key_is_available(self):
        b = make_integration("key123")
        assert b.is_available() is True

    def test_without_key_not_available(self, monkeypatch):
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        b = BraveSearchIntegration()
        assert b.is_available() is False

    def test_empty_string_key_not_available(self):
        b = BraveSearchIntegration(api_key="")
        assert b.is_available() is False


# ── TestSearch ─────────────────────────────────────────────────────────────
class TestSearch:
    def test_returns_list_of_results(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(2)):
            results = b.search("test query")
        assert len(results) == 2
        assert all(isinstance(r, BraveSearchResult) for r in results)

    def test_no_api_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        b = BraveSearchIntegration()
        results = b.search("anything")
        assert results == []

    def test_count_capped_at_20(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(0)) as mock_get:
            b.search("q", count=50)
        params = mock_get.call_args[1]["params"]
        assert params["count"] == 20

    def test_count_respected_when_small(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(0)) as mock_get:
            b.search("q", count=5)
        params = mock_get.call_args[1]["params"]
        assert params["count"] == 5

    def test_freshness_param_included(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(0)) as mock_get:
            b.search("q", freshness="pw")
        params = mock_get.call_args[1]["params"]
        assert params["freshness"] == "pw"

    def test_http_error_returns_empty(self):
        import requests as req
        b = make_integration()
        err_resp = MagicMock()
        err_resp.status_code = 429
        err_resp.json.return_value = {"error": "rate limited"}
        err_resp.text = "rate limited"
        exc = req.exceptions.HTTPError(response=err_resp)
        with patch("requests.get", side_effect=exc):
            results = b.search("q")
        assert results == []

    def test_request_exception_returns_empty(self):
        import requests as req
        b = make_integration()
        with patch("requests.get", side_effect=req.exceptions.ConnectionError("timeout")):
            results = b.search("q")
        assert results == []

    def test_result_fields_populated(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(1)):
            results = b.search("q")
        assert results[0].title == "Result 0"
        assert "example.com" in results[0].url


# ── TestSearchSimple ───────────────────────────────────────────────────────
class TestSearchSimple:
    def test_returns_list_of_dicts(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(3)):
            results = b.search_simple("q", count=3)
        assert len(results) == 3
        assert all("title" in r and "url" in r for r in results)

    def test_no_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        b = BraveSearchIntegration()
        assert b.search_simple("q") == []


# ── TestSearchWithSummary ──────────────────────────────────────────────────
class TestSearchWithSummary:
    def test_returns_summary_dict(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(2)):
            summary = b.search_with_summary("test")
        assert "query" in summary
        assert "total_results" in summary
        assert summary["total_results"] == 2

    def test_summary_query_matches_input(self):
        b = make_integration()
        with patch("requests.get", return_value=mock_requests_get(0)):
            summary = b.search_with_summary("python unittest")
        assert summary["query"] == "python unittest"
