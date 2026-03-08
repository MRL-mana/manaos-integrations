"""tests/unit/test_scripts_misc_upload_generated_images.py

upload_generated_images.py の単体テスト
"""
import json
import pytest

import scripts.misc.upload_generated_images as _mod


class TestListRecentOutputs:
    def test_nonexistent_output_dir_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_mod, "OUTPUT_DIR", tmp_path / "nonexistent")
        monkeypatch.setattr(_mod, "GENERATION_METADATA_DB", tmp_path / "meta.json")
        paths, meta = _mod.list_recent_outputs()
        assert paths == []
        assert meta == {}

    def test_empty_output_dir_returns_empty(self, tmp_path, monkeypatch):
        out = tmp_path / "output"
        out.mkdir()
        monkeypatch.setattr(_mod, "OUTPUT_DIR", out)
        monkeypatch.setattr(_mod, "GENERATION_METADATA_DB", tmp_path / "meta.json")
        paths, meta = _mod.list_recent_outputs()
        assert paths == []
        assert meta == {}

    def test_finds_recent_png(self, tmp_path, monkeypatch):
        out = tmp_path / "output"
        out.mkdir()
        (out / "image1.png").write_bytes(b"PNG")
        monkeypatch.setattr(_mod, "OUTPUT_DIR", out)
        monkeypatch.setattr(_mod, "GENERATION_METADATA_DB", tmp_path / "meta.json")
        paths, meta = _mod.list_recent_outputs(max_age_hours=24)
        assert len(paths) == 1
        assert paths[0].endswith("image1.png")
        assert meta == {}

    def test_ignores_non_png_files(self, tmp_path, monkeypatch):
        out = tmp_path / "output"
        out.mkdir()
        (out / "image.jpg").write_bytes(b"JPEG")
        (out / "data.txt").write_bytes(b"text")
        monkeypatch.setattr(_mod, "OUTPUT_DIR", out)
        monkeypatch.setattr(_mod, "GENERATION_METADATA_DB", tmp_path / "meta.json")
        paths, meta = _mod.list_recent_outputs()
        assert paths == []

    def test_reads_metadata_db(self, tmp_path, monkeypatch):
        out = tmp_path / "output"
        out.mkdir()
        img_path = out / "image1.png"
        img_path.write_bytes(b"PNG")
        meta_db = tmp_path / "meta.json"
        meta_db.write_text(json.dumps({
            "pid1": {
                "output_paths": [str(img_path)],
                "model": "sdxl",
                "loras": ["lora1"],
                "prompt": "a cat",
                "profile": "safe",
            }
        }), encoding="utf-8")
        monkeypatch.setattr(_mod, "OUTPUT_DIR", out)
        monkeypatch.setattr(_mod, "GENERATION_METADATA_DB", meta_db)
        paths, meta = _mod.list_recent_outputs(max_age_hours=24)
        assert len(paths) == 1
        assert str(img_path) in meta
        assert meta[str(img_path)]["model"] == "sdxl"

    def test_returns_tuple(self, tmp_path, monkeypatch):
        out = tmp_path / "output"
        out.mkdir()
        monkeypatch.setattr(_mod, "OUTPUT_DIR", out)
        monkeypatch.setattr(_mod, "GENERATION_METADATA_DB", tmp_path / "meta.json")
        result = _mod.list_recent_outputs()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], dict)
