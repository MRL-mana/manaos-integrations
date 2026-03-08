"""tests/unit/test_scripts_misc_manaos_obsidian_integration.py

manaos_obsidian_integration.py の単体テスト
"""
from pathlib import Path
from unittest.mock import MagicMock
import pytest

import scripts.misc.manaos_obsidian_integration as _mod


class TestGetRecentDailyNotes:
    def test_returns_empty_when_obsidian_unavailable(self, tmp_path):
        obj = _mod.ObsidianNotebookLMAntigravityIntegration.__new__(
            _mod.ObsidianNotebookLMAntigravityIntegration
        )
        obj.obsidian = None
        obj.memory = None
        obj.vault_path = tmp_path

        result = obj.get_recent_daily_notes()
        assert result == []

    def test_returns_empty_when_daily_dir_missing(self, tmp_path):
        mock_obsidian = MagicMock()
        mock_obsidian.is_available.return_value = True
        obj = _mod.ObsidianNotebookLMAntigravityIntegration.__new__(
            _mod.ObsidianNotebookLMAntigravityIntegration
        )
        obj.obsidian = mock_obsidian
        obj.memory = None
        obj.vault_path = tmp_path  # no "Daily" subdir

        result = obj.get_recent_daily_notes()
        assert result == []


class TestSaveNotebooklmResult:
    def test_creates_result_file(self, tmp_path):
        obj = _mod.ObsidianNotebookLMAntigravityIntegration.__new__(
            _mod.ObsidianNotebookLMAntigravityIntegration
        )
        obj.obsidian = None
        obj.memory = None
        obj.vault_path = tmp_path

        result_path = obj.save_notebooklm_result("# テスト分析結果", date_str="2026-01-01")
        assert result_path is not None
        assert result_path.exists()
        content = result_path.read_text(encoding="utf-8")
        assert "2026-01-01" in content

    def test_creates_review_directory_if_missing(self, tmp_path):
        obj = _mod.ObsidianNotebookLMAntigravityIntegration.__new__(
            _mod.ObsidianNotebookLMAntigravityIntegration
        )
        obj.obsidian = None
        obj.memory = None
        obj.vault_path = tmp_path

        review_dir = tmp_path / "Review"
        assert not review_dir.exists()

        obj.save_notebooklm_result("analysis content", date_str="2026-02-01")
        assert review_dir.exists()

    def test_filename_contains_date(self, tmp_path):
        obj = _mod.ObsidianNotebookLMAntigravityIntegration.__new__(
            _mod.ObsidianNotebookLMAntigravityIntegration
        )
        obj.vault_path = tmp_path
        obj.obsidian = None
        obj.memory = None

        path = obj.save_notebooklm_result("content", date_str="2026-03-15")
        assert "2026-03-15" in path.name


class TestPrepareNotebooklmInput:
    def test_returns_none_when_no_notes(self, tmp_path):
        obj = _mod.ObsidianNotebookLMAntigravityIntegration.__new__(
            _mod.ObsidianNotebookLMAntigravityIntegration
        )
        obj.obsidian = None
        obj.memory = None
        obj.vault_path = tmp_path  # no Daily dir → get_recent_daily_notes → []

        result = obj.prepare_notebooklm_input()
        assert result is None
