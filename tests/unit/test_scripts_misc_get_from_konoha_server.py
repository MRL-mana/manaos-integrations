"""tests/unit/test_scripts_misc_get_from_konoha_server.py

get_from_konoha_server.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.get_from_konoha_server as _mod


class TestRunSshCommand:
    def test_returns_stdout_on_success(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output text\n"
        monkeypatch.setattr(_mod.subprocess, "run", lambda *a, **kw: mock_result)

        result = _mod.run_ssh_command("echo hello")
        assert result == "output text"  # stripped

    def test_returns_none_on_nonzero_returncode(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Permission denied"
        monkeypatch.setattr(_mod.subprocess, "run", lambda *a, **kw: mock_result)

        result = _mod.run_ssh_command("ls /root")
        assert result is None

    def test_returns_none_on_timeout(self, monkeypatch):
        import subprocess
        def _raise(*a, **kw): raise subprocess.TimeoutExpired(cmd="ssh", timeout=10)
        monkeypatch.setattr(_mod.subprocess, "run", _raise)

        result = _mod.run_ssh_command("slow_command")
        assert result is None


class TestScpFile:
    def test_returns_true_on_success(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 0
        monkeypatch.setattr(_mod.subprocess, "run", lambda *a, **kw: mock_result)

        result = _mod.scp_file("/remote/path.conf", "/local/path.conf")
        assert result is True

    def test_returns_false_on_error(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "No such file"
        monkeypatch.setattr(_mod.subprocess, "run", lambda *a, **kw: mock_result)

        result = _mod.scp_file("/remote/missing.conf", "/local/path.conf")
        assert result is False

    def test_returns_false_on_timeout(self, monkeypatch):
        import subprocess
        def _raise(*a, **kw): raise subprocess.TimeoutExpired(cmd="scp", timeout=30)
        monkeypatch.setattr(_mod.subprocess, "run", _raise)

        result = _mod.scp_file("/remote/large.bin", "/local/large.bin")
        assert result is False
