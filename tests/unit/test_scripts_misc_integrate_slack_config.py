"""
Unit tests for scripts/misc/integrate_slack_config.py
"""
import json
import os
import sys
import types

import pytest

# Stub _paths if not available
if "_paths" not in sys.modules:
    _paths_mod = types.ModuleType("_paths")
    _paths_mod.FILE_SECRETARY_PORT = 5120
    _paths_mod.ORCHESTRATOR_PORT = 5106
    sys.modules.setdefault("_paths", _paths_mod)

from scripts.misc.integrate_slack_config import (
    mask_secret,
    get_webhook_from_md,
    get_config_from_json,
    get_env_vars,
)


class TestMaskSecret:
    def test_empty_string_returns_empty(self):
        assert mask_secret("") == ""

    def test_short_value_returns_asterisks(self):
        assert mask_secret("abc") == "***"

    def test_long_value_is_partially_masked(self):
        value = "A" * 6 + "MIDDLE" + "Z" * 4  # 16 chars
        result = mask_secret(value)
        assert result.startswith("AAAAAA")
        assert result.endswith("ZZZZ")
        assert "..." in result

    def test_respects_keep_start(self):
        value = "ABCDEFGHIJ"
        result = mask_secret(value, keep_start=3, keep_end=2)
        assert result.startswith("ABC")

    def test_respects_keep_end(self):
        value = "ABCDEFGHIJKLMN"
        result = mask_secret(value, keep_start=2, keep_end=3)
        assert result.endswith("LMN")


class TestGetWebhookFromMd:
    def test_returns_webhook_url_from_md(self, tmp_path, monkeypatch):
        md = tmp_path / "SLACK_WEBHOOK_URL.md"
        md.write_text("URL: https://hooks.slack.com/services/T000/B000/XXXX\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = get_webhook_from_md()
        assert result == "https://hooks.slack.com/services/T000/B000/XXXX"

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = get_webhook_from_md()
        assert result is None

    def test_returns_none_when_no_url_in_md(self, tmp_path, monkeypatch):
        md = tmp_path / "SLACK_WEBHOOK_URL.md"
        md.write_text("# no url here\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = get_webhook_from_md()
        assert result is None


class TestGetConfigFromJson:
    def test_returns_webhook_from_json(self, tmp_path, monkeypatch):
        d = {"slack_webhook_url": "https://hooks.slack.com/services/A", "slack_verification_token": "tok123"}
        (tmp_path / "notification_system_state.json").write_text(json.dumps(d), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = get_config_from_json()
        assert result["webhook_url"] == "https://hooks.slack.com/services/A"
        assert result["verification_token"] == "tok123"

    def test_returns_empty_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert get_config_from_json() == {}

    def test_returns_empty_on_invalid_json(self, tmp_path, monkeypatch):
        (tmp_path / "notification_system_state.json").write_text("not json", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert get_config_from_json() == {}


class TestGetEnvVars:
    def test_reads_slack_webhook_url(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/X")
        result = get_env_vars()
        assert result["webhook_url"] == "https://hooks.slack.com/services/X"

    def test_empty_string_when_not_set(self, monkeypatch):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("SLACK_VERIFICATION_TOKEN", raising=False)
        result = get_env_vars()
        assert result["webhook_url"] == ""
        assert result["verification_token"] == ""

    def test_returns_dict_with_required_keys(self, monkeypatch):
        result = get_env_vars()
        assert "webhook_url" in result and "verification_token" in result
