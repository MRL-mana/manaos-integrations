"""tests/unit/test_scripts_misc_production_setup.py

production_setup.py の単体テスト
"""
import pytest

import scripts.misc.production_setup as _mod


class TestCheckSecurity:
    def test_returns_dict_with_expected_keys(self):
        setup = _mod.ProductionSetup()
        result = setup.check_security()
        assert "api_auth" in result
        assert "input_validation" in result
        assert "secrets_management" in result
        assert "https" in result
        assert "rate_limiting" in result

    def test_warns_when_api_auth_disabled(self):
        setup = _mod.ProductionSetup()
        setup.check_security()
        warning_text = " ".join(setup.warnings)
        assert "API" in warning_text

    def test_known_defaults(self):
        setup = _mod.ProductionSetup()
        result = setup.check_security()
        assert result["input_validation"] is True
        assert result["secrets_management"] is True


class TestCheckEnvironmentVariables:
    def test_returns_dict_with_expected_keys(self, monkeypatch):
        setup = _mod.ProductionSetup()
        result = setup.check_environment_variables()
        assert "required" in result
        assert "optional" in result
        assert "missing_required" in result

    def test_detects_set_env_var(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        setup = _mod.ProductionSetup()
        result = setup.check_environment_variables()
        assert result["required"]["SLACK_WEBHOOK_URL"] is True
        assert "SLACK_WEBHOOK_URL" not in result["missing_required"]

    def test_detects_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        setup = _mod.ProductionSetup()
        result = setup.check_environment_variables()
        assert result["required"]["SLACK_WEBHOOK_URL"] is False
        assert "SLACK_WEBHOOK_URL" in result["missing_required"]


class TestCheckServices:
    def test_returns_dict(self, monkeypatch):
        import httpx
        mock_resp = type("R", (), {"status_code": 200})()
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        setup = _mod.ProductionSetup()
        result = setup.check_services()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_down_when_exception(self, monkeypatch):
        import httpx
        def _raise(*a, **kw): raise Exception("refused")
        monkeypatch.setattr(httpx, "get", _raise)
        setup = _mod.ProductionSetup()
        result = setup.check_services()
        for status in result.values():
            assert status is False

    def test_appends_errors_when_services_down(self, monkeypatch):
        import httpx
        def _raise(*a, **kw): raise Exception("refused")
        monkeypatch.setattr(httpx, "get", _raise)
        setup = _mod.ProductionSetup()
        setup.check_services()
        assert len(setup.errors) > 0

    def test_no_errors_when_all_healthy(self, monkeypatch):
        import httpx
        mock_resp = type("R", (), {"status_code": 200})()
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: mock_resp)
        setup = _mod.ProductionSetup()
        result = setup.check_services()
        for status in result.values():
            assert status is True
        assert len(setup.errors) == 0
