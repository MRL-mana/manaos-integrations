"""tests/unit/test_scripts_misc_learn_from_existing_images.py

learn_from_existing_images.py の単体テスト
"""
from pathlib import Path
import pytest

import scripts.misc.learn_from_existing_images as _mod


class TestFindImageDirectories:
    def test_empty_when_no_dirs_exist(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_mod, "POSSIBLE_IMAGE_DIRS", [tmp_path / "nonexistent123"])
        result = _mod.find_image_directories()
        assert result == []

    def test_finds_dir_with_single_png(self, tmp_path, monkeypatch):
        d = tmp_path / "gallery"
        d.mkdir()
        (d / "image.png").write_bytes(b"PNG")
        monkeypatch.setattr(_mod, "POSSIBLE_IMAGE_DIRS", [d])
        result = _mod.find_image_directories()
        assert len(result) == 1
        assert result[0][0] == d
        assert result[0][1] == 1

    def test_counts_multiple_pngs(self, tmp_path, monkeypatch):
        d = tmp_path / "generated"
        d.mkdir()
        (d / "a.png").write_bytes(b"PNG")
        (d / "b.png").write_bytes(b"PNG")
        (d / "c.png").write_bytes(b"PNG")
        monkeypatch.setattr(_mod, "POSSIBLE_IMAGE_DIRS", [d])
        result = _mod.find_image_directories()
        assert result[0][1] == 3

    def test_skips_dir_without_pngs(self, tmp_path, monkeypatch):
        d = tmp_path / "empty_dir"
        d.mkdir()
        (d / "readme.txt").write_text("hello")
        monkeypatch.setattr(_mod, "POSSIBLE_IMAGE_DIRS", [d])
        result = _mod.find_image_directories()
        assert result == []

    def test_multiple_dirs_returns_all_with_pngs(self, tmp_path, monkeypatch):
        d1 = tmp_path / "dir1"
        d2 = tmp_path / "dir2"
        d3 = tmp_path / "dir3"
        d1.mkdir(); d2.mkdir(); d3.mkdir()
        (d1 / "img.png").write_bytes(b"PNG")
        (d2 / "img.png").write_bytes(b"PNG")
        # d3 has no PNGs
        monkeypatch.setattr(_mod, "POSSIBLE_IMAGE_DIRS", [d1, d2, d3])
        result = _mod.find_image_directories()
        assert len(result) == 2

    def test_returns_list_of_tuples(self, tmp_path, monkeypatch):
        d = tmp_path / "imgs"
        d.mkdir()
        (d / "x.png").write_bytes(b"PNG")
        monkeypatch.setattr(_mod, "POSSIBLE_IMAGE_DIRS", [d])
        result = _mod.find_image_directories()
        assert isinstance(result, list)
        assert isinstance(result[0], tuple)
