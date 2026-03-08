"""tests/unit/test_scripts_misc_download_civitai_favorites.py

download_civitai_favorites.py の単体テスト
"""
from pathlib import Path
import pytest

import scripts.misc.download_civitai_favorites as _mod


class TestSanitizeFilename:
    def test_removes_forbidden_characters(self):
        result = _mod.sanitize_filename("file<name>test")
        assert "<" not in result
        assert ">" not in result

    def test_replaces_with_underscore(self):
        result = _mod.sanitize_filename('bad:name/file')
        assert result == "bad_name_file"

    def test_empty_string_returns_download(self):
        result = _mod.sanitize_filename("")
        assert result == "download"

    def test_none_like_empty_returns_download(self):
        result = _mod.sanitize_filename(None)  # type: ignore[arg-type]
        assert result == "download"

    def test_clean_name_unchanged(self):
        result = _mod.sanitize_filename("normal_filename")
        assert result == "normal_filename"

    def test_all_bad_chars_replaced(self):
        bad = r'<>:"/\|?*[]'
        for ch in bad:
            if ch:
                result = _mod.sanitize_filename(f"test{ch}name")
                assert ch not in result


class TestIsSafetensorsCorrupted:
    def test_returns_false_for_nonexistent_path(self, tmp_path):
        result = _mod.is_safetensors_corrupted(tmp_path / "model.safetensors")
        assert result is False

    def test_returns_false_for_non_safetensors_extension(self, tmp_path):
        f = tmp_path / "model.bin"
        f.write_bytes(b"data")
        result = _mod.is_safetensors_corrupted(f)
        assert result is False

    def test_returns_false_for_pt_extension(self, tmp_path):
        f = tmp_path / "model.pt"
        f.write_bytes(b"data")
        result = _mod.is_safetensors_corrupted(f)
        assert result is False
