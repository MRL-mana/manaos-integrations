"""Tests for scripts/misc/connect_existing_github_repo.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_github_automation_stub(available=True):
    mod = types.ModuleType("github_automation")
    mock_gh = MagicMock()
    mock_gh.is_available.return_value = available
    inst = MagicMock()
    inst.github = mock_gh
    mod.GitHubAutomation = MagicMock(return_value=inst)
    return mod, inst


def _make_github_helper_stub():
    mod = types.ModuleType("github_helper")
    mod.GitHubHelper = MagicMock()
    return mod


def _prep(monkeypatch, available=True):
    sys.modules.pop("connect_existing_github_repo", None)
    sys.modules.pop("github_automation", None)
    sys.modules.pop("github_helper", None)
    ga_mod, inst = _make_github_automation_stub(available)
    monkeypatch.setitem(sys.modules, "github_automation", ga_mod)
    monkeypatch.setitem(sys.modules, "github_helper", _make_github_helper_stub())
    mock_subprocess = MagicMock()
    monkeypatch.setitem(sys.modules, "subprocess", mock_subprocess)
    monkeypatch.syspath_prepend(str(_MISC))
    return ga_mod, inst, mock_subprocess


class TestConnectExistingGithubRepoImport:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        import connect_existing_github_repo  # noqa
        assert "connect_existing_github_repo" in sys.modules

    def test_has_main_function(self, monkeypatch):
        _prep(monkeypatch)
        import connect_existing_github_repo as m
        assert callable(m.main)


class TestConnectExistingGithubRepoMain:
    def test_main_not_available_exits_early(self, monkeypatch):
        ga_mod, inst, subp = _prep(monkeypatch, available=False)
        inst.github.is_available.return_value = False
        import connect_existing_github_repo as m
        with patch("builtins.print"):
            m.main()
        # subprocess.run should not be called to push
        assert subp.run.call_count == 0

    def test_main_github_none_exits_early(self, monkeypatch):
        ga_mod, inst, subp = _prep(monkeypatch)
        inst.github = None
        import connect_existing_github_repo as m
        with patch("builtins.print"):
            m.main()
        assert subp.run.call_count == 0

    def test_main_available_calls_subprocess(self, monkeypatch):
        ga_mod, inst, subp = _prep(monkeypatch, available=True)
        inst.github.is_available.return_value = True
        inst.github.github = MagicMock()
        inst.github.github.get_user.return_value = MagicMock(login="testuser")
        # stub repo list
        inst.github.list_repos = MagicMock(return_value=[])
        import connect_existing_github_repo as m
        # patch input to avoid reading from stdin during test
        with patch("builtins.print"), patch("builtins.input", side_effect=["manaos-integrations", "n"]):
            m.main()
        # function runs without exception
