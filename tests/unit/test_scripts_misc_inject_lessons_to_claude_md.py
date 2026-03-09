"""
Unit tests for scripts/misc/inject_lessons_to_claude_md.py
"""
import sys
from datetime import datetime
from unittest.mock import MagicMock

# ── external module mocks ──────────────────────────────────────────────────
_mock_recorder = MagicMock()
_mock_recorder.get_context_text.return_value = "## 教訓1\ntest lesson"
_mock_recorder.stats.return_value = {"total": 5, "by_category": {"A": 3, "B": 2}}
_lr_mod = MagicMock()
_lr_mod.get_lessons_recorder.return_value = _mock_recorder
sys.modules.setdefault("lessons_recorder", _lr_mod)

import pytest  # noqa: E402
from scripts.misc.inject_lessons_to_claude_md import (  # noqa: E402
    build_lessons_section,
    inject,
    MARKER_START,
    MARKER_END,
)


# ── TestBuildLessonsSection ────────────────────────────────────────────────
class TestBuildLessonsSection:
    def test_starts_with_marker_start(self):
        result = build_lessons_section("some text", 5, {})
        assert result.startswith(MARKER_START)

    def test_ends_with_marker_end(self):
        result = build_lessons_section("some text", 5, {})
        assert result.endswith(MARKER_END)

    def test_contains_total_count(self):
        result = build_lessons_section("", 42, {})
        assert "42" in result

    def test_contains_lessons_text(self):
        result = build_lessons_section("my lesson content", 1, {})
        assert "my lesson content" in result

    def test_empty_lessons_shows_placeholder(self):
        result = build_lessons_section("", 0, {})
        assert "教訓はまだ記録されていません" in result

    def test_categories_included(self):
        result = build_lessons_section("x", 2, {"bugfix": 1, "refactor": 1})
        assert "bugfix" in result
        assert "refactor" in result

    def test_empty_categories_label(self):
        result = build_lessons_section("x", 1, {})
        assert "なし" in result

    def test_contains_auto_update_note(self):
        result = build_lessons_section("x", 1, {})
        assert "inject_lessons_to_claude_md.py" in result

    def test_date_stamp_in_output(self):
        result = build_lessons_section("x", 1, {})
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in result


# ── TestInject ─────────────────────────────────────────────────────────────
class TestInject:
    def test_dry_run_returns_section(self, tmp_path):
        md_file = tmp_path / "CLAUDE.md"
        md_file.write_text("# Title\n\nSome content.\n", encoding="utf-8")
        result = inject(md_file, limit=5, dry_run=True)
        assert MARKER_START in result
        assert MARKER_END in result

    def test_dry_run_does_not_modify_file(self, tmp_path):
        md_file = tmp_path / "CLAUDE.md"
        original = "# Title\n\nOriginal content.\n"
        md_file.write_text(original, encoding="utf-8")
        inject(md_file, limit=5, dry_run=True)
        assert md_file.read_text(encoding="utf-8") == original

    def test_inject_appends_when_no_markers(self, tmp_path):
        md_file = tmp_path / "CLAUDE.md"
        md_file.write_text("# Title\n\n", encoding="utf-8")
        inject(md_file, limit=5, dry_run=False)
        content = md_file.read_text(encoding="utf-8")
        assert MARKER_START in content
        assert MARKER_END in content

    def test_inject_replaces_existing_markers(self, tmp_path):
        md_file = tmp_path / "CLAUDE.md"
        initial = f"# Title\n\n{MARKER_START}\nOLD CONTENT\n{MARKER_END}\n\n# Other\n"
        md_file.write_text(initial, encoding="utf-8")
        inject(md_file, limit=5, dry_run=False)
        content = md_file.read_text(encoding="utf-8")
        assert "OLD CONTENT" not in content
        assert "# Other" in content

    def test_file_not_found_raises(self, tmp_path):
        missing = tmp_path / "NONEXISTENT.md"
        with pytest.raises(FileNotFoundError):
            inject(missing)
