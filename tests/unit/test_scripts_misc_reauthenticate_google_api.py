"""Tests for scripts/misc/reauthenticate_google_api.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_gp_stub():
    stub = types.ModuleType("google_calendar_tasks_sheets_integration")
    gp_mock = MagicMock()
    gp_mock.is_available.return_value = True
    stub.GoogleProductivityIntegration = MagicMock(return_value=gp_mock)
    return stub


def _prep_mocks(monkeypatch):
    monkeypatch.syspath_prepend(str(_MISC))
    monkeypatch.setitem(
        sys.modules,
        "google_calendar_tasks_sheets_integration",
        _make_gp_stub(),
    )
    stat_mock = MagicMock()
    stat_mock.st_mtime = 1700000000.0
    return stat_mock


class TestReauthenticateGoogleApi:
    def test_imports(self, monkeypatch):
        sys.modules.pop("reauthenticate_google_api", None)
        stat_mock = _prep_mocks(monkeypatch)
        with patch("os.chdir"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink"), \
             patch("pathlib.Path.stat", return_value=stat_mock), \
             patch("sys.exit"), \
             patch("builtins.print"):
            import reauthenticate_google_api  # noqa
        assert "reauthenticate_google_api" in sys.modules

    def test_prints_authorization_info(self, monkeypatch):
        sys.modules.pop("reauthenticate_google_api", None)
        stat_mock = _prep_mocks(monkeypatch)
        printed = []
        with patch("os.chdir"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink"), \
             patch("pathlib.Path.stat", return_value=stat_mock), \
             patch("sys.exit"), \
             patch("builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))):
            import reauthenticate_google_api  # noqa
        assert any("Google" in p or "認証" in p or "Auth" in p for p in printed)

    def test_prints_scopes(self, monkeypatch):
        sys.modules.pop("reauthenticate_google_api", None)
        stat_mock = _prep_mocks(monkeypatch)
        printed = []
        with patch("os.chdir"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink"), \
             patch("pathlib.Path.stat", return_value=stat_mock), \
             patch("sys.exit"), \
             patch("builtins.print", side_effect=lambda *a, **kw: printed.append(str(a))):
            import reauthenticate_google_api  # noqa
        full_output = " ".join(printed)
        assert any(scope in full_output for scope in ("Calendar", "Tasks", "Sheets", "API"))
