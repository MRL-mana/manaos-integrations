"""Unit tests for tools/trinity_cloud_integration.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_cloud_integration import CloudIntegrationSystem


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_cis(enabled: dict | None = None):
    """__init__ をバイパスしてインスタンスを構築する。"""
    with patch.object(CloudIntegrationSystem, "__init__", lambda self: None):
        cis = CloudIntegrationSystem()
    cis.config = {"auto_sync": False}
    services = {
        "google_drive": {"enabled": False, "client": None},
        "aws_s3": {"enabled": False, "client": None},
        "dropbox": {"enabled": False, "client": None},
        "azure_blob": {"enabled": False, "client": None},
    }
    if enabled:
        for svc in enabled:
            services[svc]["enabled"] = True
    cis.cloud_services = services
    return cis


# ─────────────────────────────────────────────────────────────────────────────
# get_cloud_status
# ─────────────────────────────────────────────────────────────────────────────

class TestGetCloudStatus:
    def test_returns_dict_with_expected_keys(self):
        cis = _make_cis()
        status = cis.get_cloud_status()
        assert "services" in status
        assert "total_enabled" in status
        assert "last_sync" in status

    def test_no_services_enabled(self):
        cis = _make_cis()
        status = cis.get_cloud_status()
        assert status["total_enabled"] == 0

    def test_one_service_enabled(self):
        cis = _make_cis(enabled={"google_drive"})  # type: ignore
        status = cis.get_cloud_status()
        assert status["total_enabled"] == 1

    def test_two_services_enabled(self):
        cis = _make_cis(enabled={"google_drive", "aws_s3"})  # type: ignore
        status = cis.get_cloud_status()
        assert status["total_enabled"] == 2

    def test_disabled_service_status_is_disabled(self):
        cis = _make_cis()
        status = cis.get_cloud_status()
        assert status["services"]["google_drive"]["status"] == "disabled"

    def test_enabled_service_status_is_connected(self):
        cis = _make_cis(enabled={"dropbox"})  # type: ignore
        status = cis.get_cloud_status()
        assert status["services"]["dropbox"]["status"] == "connected"

    def test_all_four_services_present(self):
        cis = _make_cis()
        status = cis.get_cloud_status()
        for svc in ("google_drive", "aws_s3", "dropbox", "azure_blob"):
            assert svc in status["services"]


# ─────────────────────────────────────────────────────────────────────────────
# sync_generated_images
# ─────────────────────────────────────────────────────────────────────────────

class TestSyncGeneratedImages:
    def test_missing_source_dir_returns_zero_totals(self, tmp_path):
        cis = _make_cis()
        result = cis.sync_generated_images(str(tmp_path / "nonexistent"))
        assert result["total_files"] == 0
        assert result["successful_uploads"] == 0

    def test_empty_dir_returns_zero_files(self, tmp_path):
        cis = _make_cis()
        result = cis.sync_generated_images(str(tmp_path))
        assert result["total_files"] == 0

    def test_image_files_counted(self, tmp_path):
        for name in ("a.png", "b.jpg", "c.jpeg"):
            (tmp_path / name).write_bytes(b"\x00")
        cis = _make_cis()
        result = cis.sync_generated_images(str(tmp_path))
        assert result["total_files"] == 3

    def test_non_image_files_excluded(self, tmp_path):
        (tmp_path / "doc.txt").write_bytes(b"\x00")
        (tmp_path / "img.png").write_bytes(b"\x00")
        cis = _make_cis()
        result = cis.sync_generated_images(str(tmp_path))
        assert result["total_files"] == 1

    def test_all_uploads_fail_without_enabled_services(self, tmp_path):
        (tmp_path / "img.png").write_bytes(b"\x00")
        cis = _make_cis()  # no services enabled
        result = cis.sync_generated_images(str(tmp_path))
        assert result["failed_uploads"] == 1

    def test_result_has_services_used_list(self, tmp_path):
        cis = _make_cis()
        result = cis.sync_generated_images(str(tmp_path))
        assert isinstance(result["services_used"], list)


# ─────────────────────────────────────────────────────────────────────────────
# upload stubs (always return False — クラウドライブラリ未インストール)
# ─────────────────────────────────────────────────────────────────────────────

class TestUploadStubs:
    def test_upload_to_google_drive_returns_false(self):
        cis = _make_cis()
        assert cis.upload_to_google_drive("/tmp/img.png") is False

    def test_upload_to_aws_s3_returns_false(self):
        cis = _make_cis()
        assert cis.upload_to_aws_s3("/tmp/img.png", "my-bucket") is False

    def test_upload_to_dropbox_returns_false(self):
        cis = _make_cis()
        assert cis.upload_to_dropbox("/tmp/img.png") is False
