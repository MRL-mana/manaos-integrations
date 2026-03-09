"""
tests/unit/test_scripts_maintenance_large_files.py
scripts/maintenance/find_large_files_c_drive.py の純粋関数テスト

対象:
  - format_size(size_bytes)
  - should_exclude(path_str)
  - is_ai_related(path_str)
  - get_directory_size(path) — tmp_path 利用
"""
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent / "scripts" / "maintenance"),
)

from find_large_files_c_drive import (  # type: ignore  # noqa: E402
    format_size, should_exclude, is_ai_related, get_directory_size
)


# ─── format_size ──────────────────────────────────────────────────────────────

class TestFormatSize:
    def test_bytes(self):
        result = format_size(500)
        assert "B" in result
        assert "500" in result

    def test_kilobytes(self):
        result = format_size(1024)
        assert "KB" in result

    def test_megabytes(self):
        result = format_size(1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = format_size(1024 ** 3)
        assert "GB" in result

    def test_terabytes(self):
        result = format_size(1024 ** 4)
        assert "TB" in result

    def test_zero_bytes(self):
        result = format_size(0)
        assert "B" in result

    def test_returns_string(self):
        assert isinstance(format_size(12345), str)


# ─── should_exclude ───────────────────────────────────────────────────────────

class TestShouldExclude:
    def test_windows_dir_excluded(self):
        assert should_exclude(r"C:\Windows\system32\ntdll.dll") is True

    def test_program_files_excluded(self):
        assert should_exclude(r"C:\Program Files\App\app.exe") is True

    def test_program_files_x86_excluded(self):
        assert should_exclude(r"C:\Program Files (x86)\App\app.exe") is True

    def test_programdata_excluded(self):
        assert should_exclude(r"C:\ProgramData\foo") is True

    def test_system_volume_excluded(self):
        assert should_exclude(r"C:\System Volume Information\foo") is True

    def test_recycle_bin_excluded(self):
        assert should_exclude(r"C:\$Recycle.Bin\files") is True

    def test_recovery_excluded(self):
        assert should_exclude(r"C:\Recovery\data.dat") is True

    def test_users_dir_not_excluded(self):
        assert should_exclude(r"C:\Users\mana4\Desktop") is False

    def test_temp_not_excluded(self):
        assert should_exclude(r"C:\Temp\file.txt") is False

    def test_case_insensitive(self):
        assert should_exclude(r"c:\windows\system32") is True

    def test_empty_string_not_excluded(self):
        assert should_exclude("") is False


# ─── is_ai_related ────────────────────────────────────────────────────────────

class TestIsAiRelated:
    def test_model_keyword(self):
        assert is_ai_related(r"C:\Users\mana4\models\llm") is True

    def test_safetensors_extension(self):
        assert is_ai_related(r"D:\checkpoints\model.safetensors") is True

    def test_comfyui_path(self):
        assert is_ai_related(r"C:\mana_workspace\ComfyUI\main.py") is True

    def test_huggingface_path(self):
        assert is_ai_related(r"C:\Users\mana4\.cache\huggingface\tokenizer") is True

    def test_pt_extension(self):
        assert is_ai_related(r"D:\weights\model.pt") is True

    def test_onnx_extension(self):
        assert is_ai_related(r"D:\models\runtime.onnx") is True

    def test_normal_python_file(self):
        assert is_ai_related(r"C:\Users\mana4\Desktop\app.py") is False

    def test_documents_not_ai(self):
        assert is_ai_related(r"C:\Users\mana4\Documents\notes.txt") is False

    def test_case_insensitive(self):
        assert is_ai_related(r"C:\ComfyUI\OUTPUT\image.png") is True


# ─── get_directory_size ───────────────────────────────────────────────────────

class TestGetDirectorySize:
    def test_empty_directory_is_zero(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert get_directory_size(str(d)) == 0

    def test_single_file_size(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        f = d / "data.bin"
        f.write_bytes(b"x" * 1000)
        result = get_directory_size(str(d))
        assert result == 1000

    def test_multiple_files(self, tmp_path):
        d = tmp_path / "d2"
        d.mkdir()
        (d / "a.txt").write_bytes(b"a" * 100)
        (d / "b.txt").write_bytes(b"b" * 200)
        result = get_directory_size(str(d))
        assert result == 300

    def test_nested_directory(self, tmp_path):
        d = tmp_path / "parent"
        d.mkdir()
        sub = d / "sub"
        sub.mkdir()
        (d / "file1.txt").write_bytes(b"x" * 50)
        (sub / "file2.txt").write_bytes(b"y" * 150)
        result = get_directory_size(str(d))
        assert result == 200

    def test_nonexistent_returns_zero(self, tmp_path):
        result = get_directory_size(str(tmp_path / "does_not_exist"))
        assert result == 0
