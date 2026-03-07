"""Unit tests for tools/personality_self_check.py — pure helper functions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import personality_self_check as psc


# ─────────────────────────────────────────────────────────────────────────────
# _get_nested
# ─────────────────────────────────────────────────────────────────────────────

class TestGetNested:
    def test_single_key(self):
        assert psc._get_nested({"a": 1}, "a") == 1

    def test_nested_key(self):
        obj = {"a": {"b": {"c": 42}}}
        assert psc._get_nested(obj, "a.b.c") == 42

    def test_missing_key_raises_key_error(self):
        with pytest.raises(KeyError):
            psc._get_nested({"a": 1}, "b")

    def test_missing_intermediate_key_raises(self):
        with pytest.raises(KeyError):
            psc._get_nested({"a": {}}, "a.b.c")

    def test_non_dict_raises_when_traversing(self):
        with pytest.raises(KeyError):
            psc._get_nested({"a": "string"}, "a.inner")

    def test_value_is_none_returned(self):
        assert psc._get_nested({"key": None}, "key") is None

    def test_value_is_list(self):
        assert psc._get_nested({"items": [1, 2, 3]}, "items") == [1, 2, 3]

    def test_value_is_false(self):
        result = psc._get_nested({"flag": False}, "flag")
        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# _check_file_exists
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckFileExists:
    def test_existing_file_returns_true(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("key: value", encoding="utf-8")
        ok, detail = psc._check_file_exists({"path": "config.yaml"}, tmp_path)
        assert ok is True
        assert "config.yaml" in detail

    def test_missing_file_returns_false(self, tmp_path):
        ok, detail = psc._check_file_exists({"path": "missing.yaml"}, tmp_path)
        assert ok is False

    def test_nested_path(self, tmp_path):
        (tmp_path / "sub").mkdir()
        f = tmp_path / "sub" / "file.py"
        f.write_text("x = 1", encoding="utf-8")
        ok, detail = psc._check_file_exists({"path": "sub/file.py"}, tmp_path)
        assert ok is True

    def test_missing_path_key_treats_as_root(self, tmp_path):
        # check without 'path' key → path becomes "." → tmp_path itself exists
        ok, detail = psc._check_file_exists({}, tmp_path)
        # tmp_path / "" is tmp_path itself, which exists
        assert ok is True

    def test_detail_contains_exists_field(self, tmp_path):
        ok, detail = psc._check_file_exists({"path": "x.yaml"}, tmp_path)
        assert "exists=" in detail


# ─────────────────────────────────────────────────────────────────────────────
# _fetch_json  (caching + HTTP mock)
# ─────────────────────────────────────────────────────────────────────────────

class TestFetchJson:
    def _make_mock_response(self, status: int, json_data=None, text: str = ""):
        resp = MagicMock()
        resp.status_code = status
        resp.text = text
        if json_data is not None:
            resp.json.return_value = json_data
        else:
            resp.json.side_effect = Exception("no json")
        return resp

    def test_cache_returns_cached_value(self):
        cache: dict = {}
        cached_tuple = (200, {"from": "cache"})
        cache["http://example.com/|"] = cached_tuple
        result = psc._fetch_json("http://example.com/", 1.0, cache, {})
        assert result == cached_tuple

    def test_successful_request_stored_in_cache(self):
        cache: dict = {}
        mock_resp = self._make_mock_response(200, json_data={"status": "ok"})
        with patch.object(psc.requests, "get", return_value=mock_resp):
            status, body = psc._fetch_json("http://example.com/", 1.0, cache, {})
        assert status == 200
        assert body == {"status": "ok"}
        assert "http://example.com/|" in cache

    def test_cache_key_includes_api_key(self):
        cache: dict = {}
        mock_resp = self._make_mock_response(200, json_data={})
        headers = {"X-API-Key": "secret"}
        with patch.object(psc.requests, "get", return_value=mock_resp):
            psc._fetch_json("http://example.com/", 1.0, cache, headers)
        assert "http://example.com/|secret" in cache

    def test_non_json_response_falls_back_to_raw_text(self):
        cache: dict = {}
        mock_resp = self._make_mock_response(200, text="not-json")
        with patch.object(psc.requests, "get", return_value=mock_resp):
            status, body = psc._fetch_json("http://example.com/", 1.0, cache, {})
        assert "_raw_text" in body
        assert body["_raw_text"] == "not-json"

    def test_second_call_uses_cache_not_http(self):
        cache: dict = {}
        mock_resp = self._make_mock_response(200, json_data={"val": 1})
        with patch.object(psc.requests, "get", return_value=mock_resp) as mock_get:
            psc._fetch_json("http://example.com/", 1.0, cache, {})
            psc._fetch_json("http://example.com/", 1.0, cache, {})
        # requests.get called only once
        assert mock_get.call_count == 1
