"""
tests/unit/test_scripts_maintenance_duplicates.py
scripts/maintenance/find_duplicate_files.py の純粋関数テスト

対象関数:
  - should_exclude(path_str)
  - calculate_file_hash(file_path)
"""
import sys
import hashlib
from pathlib import Path
import pytest

sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent / "scripts" / "maintenance"),
)

from find_duplicate_files import should_exclude, calculate_file_hash  # type: ignore


# ─── should_exclude ───────────────────────────────────────────────────────────

class TestShouldExclude:
    """should_exclude は EXCLUDE_PATHS リスト中の文字列が含まれていれば True"""

    def test_windows_dir_excluded(self):
        assert should_exclude(r"C:\Windows\system32\ntdll.dll") is True

    def test_program_files_excluded(self):
        assert should_exclude(r"C:\Program Files\SomeApp\app.exe") is True

    def test_program_files_x86_excluded(self):
        assert should_exclude(r"C:\Program Files (x86)\App\app.exe") is True

    def test_programdata_excluded(self):
        assert should_exclude(r"C:\ProgramData\Microsoft\foo.dll") is True

    def test_recycle_bin_excluded(self):
        assert should_exclude(r"C:\$Recycle.Bin\whatever") is True

    def test_recovery_excluded(self):
        assert should_exclude(r"C:\Recovery\some.dat") is True

    def test_user_dir_not_excluded(self):
        assert should_exclude(r"C:\Users\mana4\Desktop\project.py") is False

    def test_temp_not_excluded(self):
        assert should_exclude(r"C:\Temp\file.txt") is False

    def test_case_insensitive_check(self):
        # EXCLUDE_PATHS は lowercase 比較なので大文字小文字問わず除外
        assert should_exclude(r"c:\windows\system32\foo.dll") is True

    def test_empty_string_not_excluded(self):
        assert should_exclude("") is False


# ─── calculate_file_hash ─────────────────────────────────────────────────────

class TestCalculateFileHash:
    def test_returns_hex_string(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"hello world")
        result = calculate_file_hash(str(f))
        assert isinstance(result, str)
        assert len(result) == 32  # MD5 hexdigest は 32 文字

    def test_nonexistent_file_returns_none(self, tmp_path):
        ghost = tmp_path / "ghost.bin"
        assert calculate_file_hash(str(ghost)) is None

    def test_same_content_same_hash(self, tmp_path):
        content = b"manaos test data"
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert calculate_file_hash(str(f1)) == calculate_file_hash(str(f2))

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "x.bin"
        f2 = tmp_path / "y.bin"
        f1.write_bytes(b"content_alpha")
        f2.write_bytes(b"content_beta_")
        assert calculate_file_hash(str(f1)) != calculate_file_hash(str(f2))

    def test_empty_file_hash(self, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = calculate_file_hash(str(f))
        expected = hashlib.md5(b"").hexdigest()
        assert result == expected

    def test_large_file_consistent_hash(self, tmp_path):
        """chunk_size 境界を跨ぐファイルでも正しいハッシュを返す"""
        data = b"x" * (8192 * 3 + 100)  # chunk_size(8192) * 3 + 端数
        f = tmp_path / "large.bin"
        f.write_bytes(data)
        result = calculate_file_hash(str(f))
        expected = hashlib.md5(data).hexdigest()
        assert result == expected
