"""
tests/unit/test_scripts_misc_backup_and_delete_models.py
Unit tests for scripts/misc/backup_and_delete_models.py
"""
import os
import sys
import types
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# google_drive_integration is already mocked in other test files via sys.modules;
# ensure it is stubbed here as well (setdefault is safe).
if "google_drive_integration" not in sys.modules:
    _gdi = types.ModuleType("google_drive_integration")
    _gdi.GoogleDriveIntegration = MagicMock()  # type: ignore
    sys.modules["google_drive_integration"] = _gdi

import scripts.misc.backup_and_delete_models as _sut


# ---------------------------------------------------------------------------
# get_ollama_models_path()
# ---------------------------------------------------------------------------
class TestGetOllamaModelsPath:
    def test_uses_env_var_if_set(self):
        with patch.dict(os.environ, {"OLLAMA_MODELS": "/custom/ollama"}):
            path = _sut.get_ollama_models_path()
        assert path == Path("/custom/ollama")

    def test_falls_back_to_home_ollama(self):
        env = {k: v for k, v in os.environ.items() if k not in ("OLLAMA_MODELS",)}
        with patch.dict(os.environ, env, clear=True):
            path = _sut.get_ollama_models_path()
        assert ".ollama" in str(path)
        assert "models" in str(path)

    def test_returns_path_object(self):
        path = _sut.get_ollama_models_path()
        assert isinstance(path, Path)


# ---------------------------------------------------------------------------
# get_comfyui_models_path()
# ---------------------------------------------------------------------------
class TestGetComfyUIModelsPath:
    def test_uses_env_var_if_set(self):
        with patch.dict(os.environ, {"COMFYUI_PATH": "/data/comfyui"}):
            path = _sut.get_comfyui_models_path()
        assert str(path) == str(Path("/data/comfyui") / "models")

    def test_returns_path_object(self):
        path = _sut.get_comfyui_models_path()
        assert isinstance(path, Path)

    def test_fallback_path_ends_with_models(self):
        env = {k: v for k, v in os.environ.items() if k != "COMFYUI_PATH"}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(Path, "exists", return_value=False):
            path = _sut.get_comfyui_models_path()
        assert path.name == "models"


# ---------------------------------------------------------------------------
# get_directory_size()
# ---------------------------------------------------------------------------
class TestGetDirectorySize:
    def test_returns_zero_if_not_exists(self, tmp_path):
        nonexistent = tmp_path / "ghost"
        assert _sut.get_directory_size(nonexistent) == 0

    def test_counts_single_file_size(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"x" * 100)
        assert _sut.get_directory_size(tmp_path) == 100

    def test_counts_nested_files(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "a.txt").write_bytes(b"a" * 50)
        (tmp_path / "b.txt").write_bytes(b"b" * 30)
        assert _sut.get_directory_size(tmp_path) == 80

    def test_returns_zero_on_permission_error(self, tmp_path):
        with patch("os.walk", side_effect=PermissionError("denied")):
            result = _sut.get_directory_size(tmp_path)
        assert result == 0


# ---------------------------------------------------------------------------
# format_size()
# ---------------------------------------------------------------------------
class TestFormatSize:
    def test_bytes(self):
        result = _sut.format_size(512)
        assert "B" in result
        assert "512" in result

    def test_kilobytes(self):
        result = _sut.format_size(1024)
        assert "KB" in result

    def test_megabytes(self):
        result = _sut.format_size(1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self):
        result = _sut.format_size(1024 ** 3)
        assert "GB" in result

    def test_zero_bytes(self):
        result = _sut.format_size(0)
        assert "0" in result


# ---------------------------------------------------------------------------
# backup_to_google_drive()
# ---------------------------------------------------------------------------
class TestBackupToGoogleDrive:
    def _make_drive(self):
        drive = MagicMock()
        drive.list_files.return_value = []
        drive.upload_file.return_value = True
        return drive

    def test_returns_false_if_path_not_exists(self, tmp_path):
        drive = self._make_drive()
        result = _sut.backup_to_google_drive(
            tmp_path / "nonexistent", "backup_folder", drive
        )
        assert result is False

    def test_uploads_files_and_returns_true(self, tmp_path):
        (tmp_path / "a.bin").write_bytes(b"data")
        drive = self._make_drive()
        result = _sut.backup_to_google_drive(tmp_path, "my_backup", drive)
        assert result is True
        assert drive.upload_file.called

    def test_returns_false_when_all_uploads_fail(self, tmp_path):
        (tmp_path / "a.bin").write_bytes(b"data")
        drive = self._make_drive()
        drive.upload_file.return_value = False
        result = _sut.backup_to_google_drive(tmp_path, "my_backup", drive)
        assert result is False

    def test_gracefully_handles_upload_exception(self, tmp_path):
        (tmp_path / "a.bin").write_bytes(b"data")
        drive = self._make_drive()
        drive.upload_file.side_effect = RuntimeError("upload failed")
        result = _sut.backup_to_google_drive(tmp_path, "my_backup", drive)
        assert result is False

    def test_existing_folder_found_in_drive(self, tmp_path):
        (tmp_path / "a.bin").write_bytes(b"data")
        drive = self._make_drive()
        drive.list_files.return_value = [
            {"name": "my_backup", "mimeType": "application/vnd.google-apps.folder", "id": "folder123"}
        ]
        result = _sut.backup_to_google_drive(tmp_path, "my_backup", drive)
        assert result is True


# ---------------------------------------------------------------------------
# delete_directory()
# ---------------------------------------------------------------------------
class TestDeleteDirectory:
    def test_returns_false_if_not_exists(self, tmp_path):
        result = _sut.delete_directory(tmp_path / "ghost")
        assert result is False

    def test_dry_run_returns_true_without_deletion(self, tmp_path):
        (tmp_path / "keep.txt").write_text("keep")
        result = _sut.delete_directory(tmp_path, dry_run=True)
        assert result is True
        assert (tmp_path / "keep.txt").exists()

    def test_actual_deletion_removes_directory(self, tmp_path):
        target = tmp_path / "to_delete"
        target.mkdir()
        (target / "file.txt").write_text("bye")
        result = _sut.delete_directory(target)
        assert result is True
        assert not target.exists()

    def test_returns_false_on_error(self, tmp_path):
        with patch("shutil.rmtree", side_effect=PermissionError("locked")):
            result = _sut.delete_directory(tmp_path)
        assert result is False
