"""Tests for scripts/misc/enhanced_civitai_downloader.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _prep(monkeypatch):
    sys.modules.pop("enhanced_civitai_downloader", None)
    # stubs
    cmd_mock = MagicMock()
    monkeypatch.setitem(sys.modules, "download_civitai_models", _make_stub(
        "download_civitai_models", CivitaiModelDownloader=MagicMock()
    ))
    monkeypatch.setitem(sys.modules, "civitai_integration", _make_stub(
        "civitai_integration", CivitAIIntegration=MagicMock()
    ))
    monkeypatch.setitem(sys.modules, "google_drive_integration", _make_stub(
        "google_drive_integration", GoogleDriveIntegration=MagicMock()
    ))
    monkeypatch.setitem(sys.modules, "obsidian_integration", _make_stub(
        "obsidian_integration", ObsidianIntegration=MagicMock()
    ))
    monkeypatch.setitem(sys.modules, "mem0_integration", _make_stub(
        "mem0_integration", Mem0Integration=MagicMock()
    ))
    monkeypatch.syspath_prepend(str(_MISC))
    import enhanced_civitai_downloader as m
    return m


class TestEnhancedCivitaiDownloaderImport:
    def test_imports(self, monkeypatch):
        m = _prep(monkeypatch)
        assert hasattr(m, "EnhancedCivitaiDownloader")

    def test_class_instantiation(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.EnhancedCivitaiDownloader(output_dir="test_models")
        assert obj is not None

    def test_output_dir_set(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.EnhancedCivitaiDownloader(output_dir="my_models")
        assert obj.output_dir == Path("my_models")


class TestDownloadWithEnhancements:
    def _make_obj(self, monkeypatch):
        m = _prep(monkeypatch)
        obj = m.EnhancedCivitaiDownloader()
        return obj

    def test_no_model_info_returns_error(self, monkeypatch):
        obj = self._make_obj(monkeypatch)
        obj.civitai.get_model_info = MagicMock(return_value=None)
        result = obj.download_with_enhancements("12345")
        assert result["download_success"] is False
        assert "error" in result

    def test_successful_download(self, monkeypatch):
        obj = self._make_obj(monkeypatch)
        obj.civitai.get_model_info = MagicMock(return_value={"name": "TestModel"})
        obj.civitai.get_model_stats = MagicMock(return_value={})
        obj.downloader.download_model = MagicMock(return_value=Path("models/test.safetensors"))
        obj.drive.upload_file = MagicMock(return_value="drive_id")
        obj.obsidian.create_note = MagicMock(return_value=True)
        obj.mem0.save_memory = MagicMock(return_value=True)
        with patch("builtins.print"):
            result = obj.download_with_enhancements("12345", backup_to_drive=False, create_note=False)
        assert result["model_id"] == "12345"

    def test_result_keys_present(self, monkeypatch):
        obj = self._make_obj(monkeypatch)
        obj.civitai.get_model_info = MagicMock(return_value=None)
        result = obj.download_with_enhancements("99")
        for key in ("model_id", "download_success", "backup_success", "note_created", "memory_saved"):
            assert key in result

    def test_model_id_in_result(self, monkeypatch):
        obj = self._make_obj(monkeypatch)
        obj.civitai.get_model_info = MagicMock(return_value=None)
        result = obj.download_with_enhancements("ABC")
        assert result["model_id"] == "ABC"
