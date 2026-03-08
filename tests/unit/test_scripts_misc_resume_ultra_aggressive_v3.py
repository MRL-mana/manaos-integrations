"""Tests for scripts/misc/resume_ultra_aggressive_v3.py"""
import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def _mod():
    sys.path.insert(0, "scripts/misc")
    if "resume_ultra_aggressive_v3" in sys.modules:
        return sys.modules["resume_ultra_aggressive_v3"]
    return importlib.import_module("resume_ultra_aggressive_v3")


class TestResumeFromPass3:
    def test_returns_false_when_pass3_file_missing(self, _mod, monkeypatch, tmp_path):
        """pass3 ファイルが存在しない場合 False を返す"""
        monkeypatch.setattr(_mod, "REPO_ROOT", tmp_path)
        result = _mod.resume_from_pass3()
        assert result is False

    def test_uses_repo_root_for_pass3_path(self, _mod, monkeypatch, tmp_path):
        """REPO_ROOT を基準にパスが構築されること"""
        # REPO_ROOT を存在しないディレクトリに設定 → ファイルなし → False
        nonexistent = tmp_path / "doesnotexist"
        monkeypatch.setattr(_mod, "REPO_ROOT", nonexistent)
        result = _mod.resume_from_pass3()
        assert result is False
