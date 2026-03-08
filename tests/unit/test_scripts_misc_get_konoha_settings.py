"""tests/unit/test_scripts_misc_get_konoha_settings.py

get_konoha_settings.py の単体テスト
"""
import pytest
import scripts.misc.get_konoha_settings as _mod


class TestGetKonohaEnvVars:
    def test_prints_header(self, capsys):
        _mod.get_konoha_env_vars()
        out = capsys.readouterr().out
        assert "このはサーバー" in out

    def test_prints_ssh_command(self, capsys):
        _mod.get_konoha_env_vars()
        out = capsys.readouterr().out
        assert "ssh konoha" in out

    def test_returns_none(self):
        assert _mod.get_konoha_env_vars() is None


class TestGetKonohaApiKey:
    def test_prints_header(self, capsys):
        _mod.get_konoha_n8n_api_key()
        out = capsys.readouterr().out
        assert "n8n" in out

    def test_prints_url(self, capsys):
        _mod.get_konoha_n8n_api_key()
        out = capsys.readouterr().out
        assert "5678" in out

    def test_returns_none(self):
        assert _mod.get_konoha_n8n_api_key() is None


class TestCheckLocalSettings:
    def test_prints_env_vars(self, capsys):
        _mod.check_local_settings()
        out = capsys.readouterr().out
        assert "GITHUB_TOKEN" in out
        assert "SLACK_WEBHOOK_URL" in out

    def test_set_env_var_shown_as_ok(self, monkeypatch, capsys):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_123")
        _mod.check_local_settings()
        out = capsys.readouterr().out
        assert "GITHUB_TOKEN" in out
        assert "OK" in out

    def test_unset_env_var_shown_as_warn(self, monkeypatch, capsys):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        _mod.check_local_settings()
        out = capsys.readouterr().out
        assert "GITHUB_TOKEN" in out
        assert "WARN" in out

    def test_returns_none(self):
        assert _mod.check_local_settings() is None
