"""
Unit tests for scripts/misc/git_hook_inject_lessons.py
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.misc.git_hook_inject_lessons import main


class TestMain:
    def test_returns_zero_when_inject_missing(self, tmp_path: Path, monkeypatch):
        """inject スクリプトが存在しない場合は 0 を返す（コミットはブロックしない）"""
        # _INJECT が存在しないパスを指定
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._INJECT",
            tmp_path / "nonexistent.py",
        )
        assert main() == 0

    def test_returns_zero_when_inject_fails(self, tmp_path: Path, monkeypatch):
        """inject 実行が失敗しても 0 を返す"""
        inject_path = tmp_path / "inject.py"
        inject_path.write_text("pass", encoding="utf-8")
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._INJECT", inject_path
        )
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._CLAUDE_MD",
            tmp_path / "CLAUDE.md",
        )
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._REPO", tmp_path
        )
        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stderr = "error"
        with patch("scripts.misc.git_hook_inject_lessons.subprocess.run", return_value=fake_result):
            result = main()
        assert result == 0

    def test_returns_zero_on_success_no_changes(self, tmp_path: Path, monkeypatch):
        """inject が成功しても CLAUDE.md に変更なければ 0 を返す"""
        inject_path = tmp_path / "inject.py"
        inject_path.write_text("pass", encoding="utf-8")
        claude_md = tmp_path / "CLAUDE.md"
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._INJECT", inject_path
        )
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._CLAUDE_MD", claude_md
        )
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._REPO", tmp_path
        )
        run_results = iter([
            MagicMock(returncode=0, stderr=""),   # inject run
            MagicMock(returncode=0, stdout=""),    # git diff (no changes)
        ])
        with patch(
            "scripts.misc.git_hook_inject_lessons.subprocess.run",
            side_effect=run_results,
        ):
            result = main()
        assert result == 0

    def test_git_add_called_when_claude_md_changed(self, tmp_path: Path, monkeypatch):
        """CLAUDE.md が変更された場合 git add が呼ばれる"""
        inject_path = tmp_path / "inject.py"
        inject_path.write_text("pass", encoding="utf-8")
        claude_md = tmp_path / "CLAUDE.md"
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._INJECT", inject_path
        )
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._CLAUDE_MD", claude_md
        )
        monkeypatch.setattr(
            "scripts.misc.git_hook_inject_lessons._REPO", tmp_path
        )
        calls = []
        def _fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stderr = ""
            # git diff returns CLAUDE.md name
            r.stdout = "CLAUDE.md" if "diff" in (cmd[1] if len(cmd) > 1 else "") else ""
            return r
        with patch(
            "scripts.misc.git_hook_inject_lessons.subprocess.run",
            side_effect=_fake_run,
        ):
            result = main()
        assert result == 0
        # git add should have been called
        add_calls = [c for c in calls if "add" in c]
        assert len(add_calls) >= 1
