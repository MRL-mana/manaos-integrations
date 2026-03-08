"""
Unit tests for scripts/misc/delete_comfyui_models.py
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.misc.delete_comfyui_models import (
    format_size,
    get_comfyui_models_path,
    get_directory_size,
    delete_comfyui_models,
)


class TestFormatSize:
    def test_bytes_label(self):
        assert "B" in format_size(512)

    def test_kb_label(self):
        assert "KB" in format_size(1024)

    def test_mb_label(self):
        assert "MB" in format_size(1024 * 1024)

    def test_gb_label(self):
        assert "GB" in format_size(1024 ** 3)

    def test_returns_string(self):
        assert isinstance(format_size(0), str)

    def test_zero_bytes(self):
        result = format_size(0)
        assert "0" in result


class TestGetDirectorySize:
    def test_empty_dir_returns_zero(self, tmp_path: Path):
        d = tmp_path / "empty"
        d.mkdir()
        assert get_directory_size(d) == 0

    def test_nonexistent_returns_zero(self, tmp_path: Path):
        assert get_directory_size(tmp_path / "nonexistent") == 0

    def test_counts_file_size(self, tmp_path: Path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"x" * 100)
        assert get_directory_size(tmp_path) == 100

    def test_counts_nested_files(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "a.bin").write_bytes(b"y" * 50)
        (tmp_path / "b.bin").write_bytes(b"z" * 30)
        assert get_directory_size(tmp_path) == 80


class TestGetComfyuiModelsPath:
    def test_uses_env_var_when_set(self, monkeypatch):
        monkeypatch.setenv("COMFYUI_PATH", "D:/TestComfyUI")
        result = get_comfyui_models_path()
        assert "models" in str(result)
        assert "TestComfyUI" in str(result)

    def test_returns_path_object(self, monkeypatch):
        monkeypatch.delenv("COMFYUI_PATH", raising=False)
        result = get_comfyui_models_path()
        assert isinstance(result, Path)


class TestDeleteComfyuiModelsDryRun:
    def test_dry_run_on_nonexistent_path_doesnt_raise(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "no_models"
        with patch("scripts.misc.delete_comfyui_models.get_comfyui_models_path", return_value=nonexistent):
            # Should just print "path does not exist" and return
            delete_comfyui_models(dry_run=True)  # no exception

    def test_dry_run_on_empty_dir_doesnt_raise(self, tmp_path, monkeypatch):
        d = tmp_path / "models"
        d.mkdir()
        with patch("scripts.misc.delete_comfyui_models.get_comfyui_models_path", return_value=d):
            delete_comfyui_models(dry_run=True)  # no exception

    def test_dry_run_does_not_delete(self, tmp_path):
        d = tmp_path / "models"
        d.mkdir()
        (d / "model.safetensors").write_bytes(b"x" * 200)
        with patch("scripts.misc.delete_comfyui_models.get_comfyui_models_path", return_value=d):
            delete_comfyui_models(dry_run=True)
        assert d.exists()
