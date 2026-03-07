"""Unit tests for tools/lm_studio_model_selector.py — pure/cache functions."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import lm_studio_model_selector as lms


# ─────────────────────────────────────────────────────────────────────────────
# _env_int
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvInt:
    def test_env_set_returns_int(self, monkeypatch):
        monkeypatch.setenv("TEST_PORT", "8080")
        assert lms._env_int("TEST_PORT", 1234) == 8080

    def test_env_unset_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_PORT", raising=False)
        assert lms._env_int("TEST_PORT", 9999) == 9999

    def test_env_non_numeric_returns_default(self, monkeypatch):
        monkeypatch.setenv("TEST_PORT", "notanumber")
        assert lms._env_int("TEST_PORT", 42) == 42


# ─────────────────────────────────────────────────────────────────────────────
# _safe_lower
# ─────────────────────────────────────────────────────────────────────────────

class TestSafeLower:
    def test_uppercase_to_lower(self):
        assert lms._safe_lower("LLAMA") == "llama"

    def test_strips_whitespace(self):
        assert lms._safe_lower("  GPT-4  ") == "gpt-4"

    def test_already_lower_unchanged(self):
        assert lms._safe_lower("mistral") == "mistral"


# ─────────────────────────────────────────────────────────────────────────────
# _should_skip
# ─────────────────────────────────────────────────────────────────────────────

class TestShouldSkip:
    def test_skip_substring_present_returns_true(self):
        assert lms._should_skip("llama-vision-instruct", ["vision"]) is True

    def test_no_match_returns_false(self):
        assert lms._should_skip("mistral-7b-instruct", ["vision"]) is False

    def test_empty_skip_list_never_skips(self):
        assert lms._should_skip("any-model", []) is False

    def test_case_insensitive_skip(self):
        assert lms._should_skip("LLAMA-VISION", ["vision"]) is True

    def test_multiple_substrings_any_match_skips(self):
        assert lms._should_skip("model-draft-q8", ["draft", "embed"]) is True

    def test_empty_substring_ignored(self):
        # empty string substring should not skip everything
        assert lms._should_skip("good-model", [""]) is False


# ─────────────────────────────────────────────────────────────────────────────
# _load_cache / _save_cache
# ─────────────────────────────────────────────────────────────────────────────

class TestCacheRoundtrip:
    def test_save_then_load(self, tmp_path):
        cache_path = str(tmp_path / "cache.json")
        data = {"timestamp": 1234567890.0, "models": ["modelA", "modelB"]}
        lms._save_cache(cache_path, data)
        loaded = lms._load_cache(cache_path)
        assert loaded == data

    def test_load_missing_file_returns_none(self, tmp_path):
        result = lms._load_cache(str(tmp_path / "nonexistent.json"))
        assert result is None

    def test_load_invalid_json_returns_none(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not-json{{{", encoding="utf-8")
        assert lms._load_cache(str(p)) is None

    def test_save_creates_parent_dirs(self, tmp_path):
        cache_path = str(tmp_path / "sub" / "dir" / "cache.json")
        lms._save_cache(cache_path, {"key": "val"})
        assert Path(cache_path).exists()


# ─────────────────────────────────────────────────────────────────────────────
# list_lm_studio_models
# ─────────────────────────────────────────────────────────────────────────────

def _mock_models_response(model_ids: list[str]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": [{"id": mid} for mid in model_ids]}
    return resp


class TestListLmStudioModels:
    def test_returns_model_ids(self):
        mock_resp = _mock_models_response(["llama-3-8b", "mistral-7b"])
        with patch("requests.get", return_value=mock_resp):
            result = lms.list_lm_studio_models(timeout_sec=1)
        assert result == ["llama-3-8b", "mistral-7b"]

    def test_empty_data_returns_empty_list(self):
        mock_resp = _mock_models_response([])
        with patch("requests.get", return_value=mock_resp):
            result = lms.list_lm_studio_models(timeout_sec=1)
        assert result == []

    def test_non_dict_response_returns_empty(self):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = ["not", "a", "dict"]
        with patch("requests.get", return_value=resp):
            result = lms.list_lm_studio_models(timeout_sec=1)
        assert result == []

    def test_items_without_id_skipped(self):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"data": [{"id": "model-a"}, {"no_id": True}, {"id": ""}]}
        with patch("requests.get", return_value=resp):
            result = lms.list_lm_studio_models(timeout_sec=1)
        assert result == ["model-a"]
