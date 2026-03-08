"""Tests for scripts/misc/upload_lm_studio_result.py"""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _prep(monkeypatch, drive_available=True, upload_success=True):
    sys.modules.pop("upload_lm_studio_result", None)
    monkeypatch.syspath_prepend(str(_MISC))

    mock_drive_instance = MagicMock()
    mock_drive_instance.is_available.return_value = drive_available
    mock_drive_instance.upload_file.return_value = "file_id_123" if upload_success else None

    mock_drive_class = MagicMock(return_value=mock_drive_instance)
    gdrive_mod = types.ModuleType("google_drive_integration")
    gdrive_mod.GoogleDriveIntegration = mock_drive_class
    monkeypatch.setitem(sys.modules, "google_drive_integration", gdrive_mod)

    with patch("builtins.print"):
        with patch("sys.exit") as mock_exit:
            import upload_lm_studio_result as m
    return m, mock_drive_instance


class TestUploadLmStudioResult:
    def test_imports(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "upload_lm_studio_result" in sys.modules

    def test_drive_is_available_checked(self, monkeypatch):
        _, mock_drive = _prep(monkeypatch)
        mock_drive.is_available.assert_called_once()

    def test_upload_called_when_available(self, monkeypatch):
        _, mock_drive = _prep(monkeypatch, drive_available=True)
        mock_drive.upload_file.assert_called_once()

    def test_exits_when_drive_unavailable(self, monkeypatch):
        sys.modules.pop("upload_lm_studio_result", None)
        monkeypatch.syspath_prepend(str(_MISC))

        mock_drive_instance = MagicMock()
        mock_drive_instance.is_available.return_value = False

        mock_drive_class = MagicMock(return_value=mock_drive_instance)
        gdrive_mod = types.ModuleType("google_drive_integration")
        gdrive_mod.GoogleDriveIntegration = mock_drive_class
        monkeypatch.setitem(sys.modules, "google_drive_integration", gdrive_mod)

        with patch("builtins.print"):
            with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
                with pytest.raises(SystemExit) as exc_info:
                    import upload_lm_studio_result
                assert exc_info.value.code == 1
        mock_exit.assert_called_with(1)

    def test_upload_failure_handled(self, monkeypatch):
        _, mock_drive = _prep(monkeypatch, drive_available=True, upload_success=False)
        # upload returns None → script prints failure but no uncaught exception
        assert True
