"""Unit tests for tools/validate_contract.py — pure functions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import validate_contract as vc


# ─────────────────────────────────────────────────────────────────────────────
# has_keys
# ─────────────────────────────────────────────────────────────────────────────

class TestHasKeys:
    def test_all_keys_present_no_warning(self):
        warnings: list[str] = []
        vc.has_keys({"a": 1, "b": 2}, ["a", "b"], "MyCheck", warnings)
        assert warnings == []

    def test_missing_single_key_adds_warning(self):
        warnings: list[str] = []
        vc.has_keys({"a": 1}, ["a", "b"], "MyCheck", warnings)
        assert len(warnings) == 1
        assert "b" in warnings[0]
        assert "MyCheck" in warnings[0]

    def test_missing_multiple_keys_adds_multiple_warnings(self):
        warnings: list[str] = []
        vc.has_keys({}, ["x", "y", "z"], "ChkName", warnings)
        assert len(warnings) == 3

    def test_non_dict_obj_adds_one_warning_with_type_name(self):
        warnings: list[str] = []
        vc.has_keys(["list", "not", "dict"], ["key"], "MyCheck", warnings)
        assert len(warnings) == 1
        assert "list" in warnings[0]  # type name mentioned

    def test_non_dict_none_adds_warning(self):
        warnings: list[str] = []
        vc.has_keys(None, ["key"], "NullCheck", warnings)
        assert len(warnings) == 1
        assert "NoneType" in warnings[0]

    def test_empty_keys_list_no_warning(self):
        warnings: list[str] = []
        vc.has_keys({"a": 1}, [], "Empty", warnings)
        assert warnings == []

    def test_extra_keys_not_required_no_warning(self):
        warnings: list[str] = []
        vc.has_keys({"a": 1, "b": 2, "c": 3}, ["a"], "Extra", warnings)
        assert warnings == []

    def test_warning_contains_name_prefix(self):
        warnings: list[str] = []
        vc.has_keys({}, ["status"], "HealthEndpoint", warnings)
        assert warnings[0].startswith("HealthEndpoint")


# ─────────────────────────────────────────────────────────────────────────────
# get_json
# ─────────────────────────────────────────────────────────────────────────────

def _mock_response(status: int, content_type: str, json_data=None, text: str = "") -> MagicMock:
    """requests.Response モック生成ヘルパー。"""
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"content-type": content_type}
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("no json")
    return resp


class TestGetJson:
    def test_json_response_returns_parsed_dict(self):
        mock_resp = _mock_response(200, "application/json", json_data={"status": "ok"})
        with patch("requests.get", return_value=mock_resp):
            status, body = vc.get_json("http://example.com/health", {}, timeout=1.0)
        assert status == 200
        assert body == {"status": "ok"}

    def test_non_json_content_type_returns_raw_text(self):
        mock_resp = _mock_response(200, "text/plain", text="healthy")
        with patch("requests.get", return_value=mock_resp):
            status, body = vc.get_json("http://example.com/health", {}, timeout=1.0)
        assert status == 200
        assert body.get("_raw_text") == "healthy"
        assert "_content_type" in body

    def test_json_decode_error_falls_back_to_raw_text(self):
        mock_resp = _mock_response(200, "application/json", text="not-json")
        # json() raises ValueError
        mock_resp.json.side_effect = ValueError("invalid json")
        with patch("requests.get", return_value=mock_resp):
            status, body = vc.get_json("http://example.com/health", {}, timeout=1.0)
        assert status == 200
        assert "_raw_text" in body

    def test_non_200_status_returned_correctly(self):
        mock_resp = _mock_response(503, "application/json", json_data={"error": "down"})
        with patch("requests.get", return_value=mock_resp):
            status, body = vc.get_json("http://example.com/health", {}, timeout=1.0)
        assert status == 503
        assert body == {"error": "down"}

    def test_headers_passed_to_request(self):
        mock_resp = _mock_response(200, "application/json", json_data={})
        with patch("requests.get", return_value=mock_resp) as mock_get:
            vc.get_json("http://example.com/health", {"X-API-Key": "secret"}, timeout=2.0)
        _, kwargs = mock_get.call_args
        assert kwargs.get("headers", mock_get.call_args[0][1] if len(mock_get.call_args[0]) > 1 else {}) is not None

    def test_timeout_passed_to_request(self):
        mock_resp = _mock_response(200, "application/json", json_data={})
        with patch("requests.get", return_value=mock_resp) as mock_get:
            vc.get_json("http://example.com/health", {}, timeout=5.5)
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("timeout") == 5.5

    def test_raw_text_truncated_to_2000(self):
        long_text = "x" * 5000
        mock_resp = _mock_response(200, "text/html", text=long_text)
        with patch("requests.get", return_value=mock_resp):
            _, body = vc.get_json("http://example.com/", {}, timeout=1.0)
        assert len(body["_raw_text"]) == 2000
