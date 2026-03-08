"""
Unit tests for scripts/misc/obsidian_integration.py
Tests _sanitize_filename, create_note, read_note, search_notes.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# ── Standard mocks ────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv_inst = MagicMock()
_cv_inst.validate_config = MagicMock(return_value=(True, []))
_cv.ConfigValidator = MagicMock(return_value=_cv_inst)
sys.modules.setdefault("manaos_config_validator", _cv)

_cve = MagicMock()
_cve_inst = MagicMock()
_cve_inst.validate_config_file = MagicMock(return_value=(True, [], {}))
_cve.ConfigValidatorEnhanced = MagicMock(return_value=_cve_inst)
sys.modules.setdefault("config_validator_enhanced", _cve)

# ── Import target ─────────────────────────────────────────────────────────────
from scripts.misc.obsidian_integration import ObsidianIntegration  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def vault(tmp_path):
    """Return an ObsidianIntegration with _available=True pointing at tmp_path."""
    oi = ObsidianIntegration(str(tmp_path))
    oi._available = True
    return oi


# ── TestSanitizeFilename ──────────────────────────────────────────────────────
class TestSanitizeFilename:
    def test_removes_forward_slash(self, vault):
        result = vault._sanitize_filename("test/file")
        assert "/" not in result

    def test_removes_backslash(self, vault):
        result = vault._sanitize_filename("test\\file")
        assert "\\" not in result

    def test_removes_colon(self, vault):
        result = vault._sanitize_filename("test:file")
        assert ":" not in result

    def test_removes_angle_brackets(self, vault):
        result = vault._sanitize_filename("<test>")
        assert "<" not in result
        assert ">" not in result

    def test_removes_question_mark(self, vault):
        result = vault._sanitize_filename("test?file")
        assert "?" not in result

    def test_removes_asterisk(self, vault):
        result = vault._sanitize_filename("test*file")
        assert "*" not in result

    def test_strips_leading_trailing_spaces(self, vault):
        result = vault._sanitize_filename("  test  ")
        assert result == "test"

    def test_strips_leading_trailing_dots(self, vault):
        result = vault._sanitize_filename(".test.")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_normal_name_unchanged(self, vault):
        result = vault._sanitize_filename("my_note_2024")
        assert result == "my_note_2024"

    def test_replaces_with_underscore(self, vault):
        result = vault._sanitize_filename("hello/world")
        assert "_" in result


# ── TestCreateNote ────────────────────────────────────────────────────────────
class TestCreateNote:
    def test_not_available_returns_none(self, tmp_path):
        # Non-existent vault → _initialize_internal returns False → not available
        oi = ObsidianIntegration(str(tmp_path / "no_such_vault"))
        assert oi.create_note("Test", "Content") is None

    def test_creates_md_file(self, vault):
        path = vault.create_note("Test Note", "body content")
        assert path is not None
        assert path.exists()
        assert path.suffix == ".md"

    def test_frontmatter_written(self, vault):
        path = vault.create_note("Test", "body")
        content = path.read_text(encoding="utf-8")
        assert "---" in content
        assert "title" in content

    def test_content_included_in_file(self, vault):
        path = vault.create_note("Test", "unique_body_content_xyz")
        content = path.read_text(encoding="utf-8")
        assert "unique_body_content_xyz" in content

    def test_tags_written(self, vault):
        path = vault.create_note("Test", "body", tags=["ai", "notes"])
        content = path.read_text(encoding="utf-8")
        assert "#ai" in content

    def test_with_folder_creates_subdir(self, vault):
        path = vault.create_note("Test", "body", folder="subfolder")
        assert path is not None
        assert "subfolder" in str(path)
        assert path.exists()

    def test_title_in_frontmatter(self, vault):
        path = vault.create_note("MyTitle", "body")
        content = path.read_text(encoding="utf-8")
        assert "MyTitle" in content


# ── TestReadNote ──────────────────────────────────────────────────────────────
class TestReadNote:
    def test_not_available_returns_none(self, tmp_path):
        oi = ObsidianIntegration(str(tmp_path / "no_such_vault"))
        assert oi.read_note("anything.md") is None

    def test_reads_existing_note(self, vault):
        # Create a note and read it back
        created_path = vault.create_note("Readable", "readable_content")
        assert created_path is not None
        rel = created_path.relative_to(vault.vault_path)
        content = vault.read_note(str(rel))
        assert content is not None
        assert "readable_content" in content

    def test_missing_file_returns_none(self, vault):
        assert vault.read_note("nonexistent_file.md") is None

    def test_read_returns_full_content(self, vault):
        created_path = vault.create_note("Full", "line1\nline2\nline3")
        rel = created_path.relative_to(vault.vault_path)
        content = vault.read_note(str(rel))
        assert "line1" in content
        assert "line3" in content


# ── TestSearchNotes ───────────────────────────────────────────────────────────
class TestSearchNotes:
    def test_not_available_returns_empty(self, tmp_path):
        oi = ObsidianIntegration(str(tmp_path / "no_such_vault"))
        assert oi.search_notes("query") == []

    def test_finds_note_by_content(self, vault):
        vault.create_note("some_note", "unique_search_content_abc")
        results = vault.search_notes("unique_search_content_abc")
        assert len(results) >= 1

    def test_finds_note_by_stem(self, vault):
        vault.create_note("findable_stem_unique", "some content")
        results = vault.search_notes("findable_stem_unique")
        assert len(results) >= 1

    def test_no_match_returns_empty(self, vault):
        vault.create_note("note1", "hello world")
        results = vault.search_notes("zzz_nothing_here_xyz_123")
        assert results == []

    def test_returns_paths(self, vault):
        vault.create_note("result_note", "searchable content here")
        results = vault.search_notes("searchable content")
        assert all(isinstance(r, Path) for r in results)

    def test_finds_multiple_notes(self, vault):
        vault.create_note("note_a", "keyword_xyz match")
        vault.create_note("note_b", "keyword_xyz match too")
        results = vault.search_notes("keyword_xyz")
        assert len(results) >= 2
