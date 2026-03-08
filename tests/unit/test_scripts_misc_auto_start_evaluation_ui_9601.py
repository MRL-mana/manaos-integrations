"""tests/unit/test_scripts_misc_auto_start_evaluation_ui_9601.py

auto_start_evaluation_ui_9601.py の単体テスト
"""
import sys
import socket
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

import scripts.misc.auto_start_evaluation_ui_9601 as _mod


class TestIsPortInUse:
    def test_returns_false_for_unused_port(self):
        # 65530 はほぼ確実に使われていない
        result = _mod.is_port_in_use(65530)
        assert result is False

    def test_returns_true_when_connect_succeeds(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect = MagicMock(return_value=None)  # 成功

        monkeypatch.setattr("socket.socket", lambda *a, **kw: mock_sock)

        result = _mod.is_port_in_use(9999)
        assert result is True

    def test_returns_false_when_connect_raises(self, monkeypatch):
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.connect = MagicMock(side_effect=OSError("refused"))

        monkeypatch.setattr("socket.socket", lambda *a, **kw: mock_sock)

        result = _mod.is_port_in_use(9999)
        assert result is False


class TestMain:
    def test_returns_1_when_script_missing(self, tmp_path, monkeypatch):
        # __file__ を tmp_path 配下に向ける（script が存在しない）
        fake_file = str(tmp_path / "auto_start_evaluation_ui_9601.py")
        monkeypatch.setattr(_mod, "__file__", fake_file)

        result = _mod.main()
        assert result == 1

    def test_returns_0_when_port_already_in_use(self, tmp_path, monkeypatch):
        # script ファイルを作成してport使用中にする
        script = tmp_path / "start_evaluation_ui_port9601.py"
        script.write_text("# stub")
        fake_file = str(tmp_path / "auto_start_evaluation_ui_9601.py")
        monkeypatch.setattr(_mod, "__file__", fake_file)
        monkeypatch.setattr(_mod, "is_port_in_use", lambda port: True)

        result = _mod.main()
        assert result == 0

    def test_spawns_process_when_port_free(self, tmp_path, monkeypatch):
        script = tmp_path / "start_evaluation_ui_port9601.py"
        script.write_text("# stub")
        fake_file = str(tmp_path / "auto_start_evaluation_ui_9601.py")
        monkeypatch.setattr(_mod, "__file__", fake_file)
        monkeypatch.setattr(_mod, "is_port_in_use", lambda port: False)

        popen_calls = []
        monkeypatch.setattr(_mod.subprocess, "Popen", lambda *a, **kw: popen_calls.append((a, kw)) or MagicMock())

        result = _mod.main()
        assert result == 0
        assert len(popen_calls) == 1
