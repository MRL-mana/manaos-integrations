"""
tests/unit/test_scripts_checks_env.py
scripts/checks/check_environment_variables.py の純粋関数テスト

対象関数:
  - check_path_exists(path_str)
"""
import sys
from pathlib import Path

# scripts/checks を sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "checks"))

# 'os' や requests が必要な関数だけテスト (check_path_exists は純粋)
from check_environment_variables import check_path_exists  # type: ignore  # noqa: E402


# ─── check_path_exists ────────────────────────────────────────────────────────

class TestCheckPathExists:
    def test_empty_string_returns_false(self):
        assert check_path_exists("") is False

    def test_none_equivalent_empty_returns_false(self):
        # 空文字は前段でガード
        assert check_path_exists("") is False

    def test_nonexistent_path_returns_false(self):
        assert check_path_exists("/nonexistent/path/that/does/not/exist/xyz") is False

    def test_existing_directory_returns_true(self, tmp_path):
        assert check_path_exists(str(tmp_path)) is True

    def test_existing_file_returns_true(self, tmp_path):
        f = tmp_path / "testfile.txt"
        f.write_text("hello")
        assert check_path_exists(str(f)) is True

    def test_invalid_chars_returns_false(self):
        # Path() が例外を出す可能性がある文字列 → False で安全に返す
        # (実際は OSError/ValueError になる環境もある)
        result = check_path_exists("\x00invalid")
        assert result is False

    def test_relative_nonexistent_returns_false(self):
        assert check_path_exists("definitely_does_not_exist_xyz.txt") is False

    def test_windows_style_nonexistent(self):
        assert check_path_exists("C:\\NonExistentPath\\Nothing") is False

    def test_tilde_unexpanded_nonexistent(self):
        # "~/.nonexistent" は Path("~/.nonexistent").exists() → False
        # (expanduser しない挙動)
        result = check_path_exists("~/.definitely_missing_xyz")
        assert result is False
