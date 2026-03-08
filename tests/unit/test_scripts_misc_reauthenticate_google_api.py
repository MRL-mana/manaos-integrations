"""Tests for scripts/misc/reauthenticate_google_api.py"""
import sys
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


class TestReauthenticateGoogleApi:
    def test_imports(self, monkeypatch):
        sys.modules.pop("reauthenticate_google_api", None)
        monkeypatch.syspath_prepend(str(_MISC))
        with patch("builtins.print"):
            import reauthenticate_google_api  # noqa
        assert "reauthenticate_google_api" in sys.modules

    def test_prints_authorization_info(self, monkeypatch):
        sys.modules.pop("reauthenticate_google_api", None)
        monkeypatch.syspath_prepend(str(_MISC))
        printed = []
        with patch("builtins.print", side_effect=lambda *a: printed.append(str(a))):
            import reauthenticate_google_api  # noqa
        assert any("Google" in p or "認証" in p or "Auth" in p for p in printed)

    def test_prints_scopes(self, monkeypatch):
        sys.modules.pop("reauthenticate_google_api", None)
        monkeypatch.syspath_prepend(str(_MISC))
        printed = []
        with patch("builtins.print", side_effect=lambda *a: printed.append(str(a))):
            import reauthenticate_google_api  # noqa
        full_output = " ".join(printed)
        assert any(scope in full_output for scope in ("Calendar", "Tasks", "Sheets", "API"))
