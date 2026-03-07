"""
Unit tests for scripts/misc/cloud_integration.py

Tests: AWSIntegration, AzureIntegration, GCPIntegration availability checks
and early-return behavior when unavailable.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Mock all optional cloud SDKs before importing the target module
for _mod in [
    "boto3", "botocore", "botocore.exceptions",
    "azure", "azure.identity", "azure.storage", "azure.storage.blob",
    "google", "google.cloud", "google.cloud.storage",
]:
    sys.modules.setdefault(_mod, MagicMock())

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))
import cloud_integration as ci  # noqa: E402


# ---------------------------------------------------------------------------
# AWSIntegration
# ---------------------------------------------------------------------------

class TestAWSIntegrationIsAvailable:
    def test_true_when_flag_true_and_client_set(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", True)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = MagicMock()
        obj.ec2_client = None
        assert obj.is_available() is True

    def test_false_when_flag_false(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", False)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = MagicMock()
        assert obj.is_available() is False

    def test_false_when_client_none(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", True)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = None
        assert obj.is_available() is False

    def test_false_when_both_false_and_none(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", False)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = None
        assert obj.is_available() is False


class TestAWSIntegrationUploadToS3:
    def _make_unavailable(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", False)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = None
        return obj

    def _make_available(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", True)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = MagicMock()
        obj.ec2_client = MagicMock()
        return obj

    def test_returns_false_when_not_available(self, monkeypatch):
        obj = self._make_unavailable(monkeypatch)
        assert obj.upload_to_s3("bucket", "file.txt") is False

    def test_returns_true_on_success(self, monkeypatch):
        obj = self._make_available(monkeypatch)
        result = obj.upload_to_s3("my-bucket", "/tmp/file.txt", "file.txt")
        assert result is True
        obj.s3_client.upload_file.assert_called_once_with(
            "/tmp/file.txt", "my-bucket", "file.txt"
        )

    def test_uses_filename_when_object_name_omitted(self, monkeypatch):
        obj = self._make_available(monkeypatch)
        obj.upload_to_s3("my-bucket", "/some/path/data.bin")
        obj.s3_client.upload_file.assert_called_once_with(
            "/some/path/data.bin", "my-bucket", "data.bin"
        )


class TestAWSIntegrationDownloadFromS3:
    def test_returns_false_when_not_available(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", False)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = None
        assert obj.download_from_s3("bucket", "key", "/tmp/out.txt") is False

    def test_returns_true_on_success(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", True)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = MagicMock()
        obj.ec2_client = MagicMock()
        result = obj.download_from_s3("my-bucket", "key.txt", "/tmp/out.txt")
        assert result is True
        obj.s3_client.download_file.assert_called_once_with(
            "my-bucket", "key.txt", "/tmp/out.txt"
        )


class TestAWSIntegrationListS3Objects:
    def test_returns_empty_list_when_not_available(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", False)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = None
        assert obj.list_s3_objects("bucket") == []

    def test_returns_empty_list_when_no_contents(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", True)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = MagicMock()
        obj.ec2_client = MagicMock()
        obj.s3_client.list_objects_v2.return_value = {}
        result = obj.list_s3_objects("my-bucket")
        assert result == []

    def test_returns_objects_on_success(self, monkeypatch):
        monkeypatch.setattr(ci, "AWS_AVAILABLE", True)
        obj = ci.AWSIntegration.__new__(ci.AWSIntegration)
        obj.s3_client = MagicMock()
        obj.ec2_client = MagicMock()
        lm = MagicMock()
        lm.isoformat.return_value = "2024-01-01T00:00:00"
        obj.s3_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "data.txt", "Size": 1024, "LastModified": lm}]
        }
        result = obj.list_s3_objects("my-bucket")
        assert len(result) == 1
        assert result[0]["key"] == "data.txt"
        assert result[0]["size"] == 1024


# ---------------------------------------------------------------------------
# AzureIntegration
# ---------------------------------------------------------------------------

class TestAzureIntegrationIsAvailable:
    def test_true_when_flag_true_and_client_set(self, monkeypatch):
        monkeypatch.setattr(ci, "AZURE_AVAILABLE", True)
        obj = ci.AzureIntegration.__new__(ci.AzureIntegration)
        obj.blob_service_client = MagicMock()
        assert obj.is_available() is True

    def test_false_when_flag_false(self, monkeypatch):
        monkeypatch.setattr(ci, "AZURE_AVAILABLE", False)
        obj = ci.AzureIntegration.__new__(ci.AzureIntegration)
        obj.blob_service_client = MagicMock()
        assert obj.is_available() is False

    def test_false_when_client_none(self, monkeypatch):
        monkeypatch.setattr(ci, "AZURE_AVAILABLE", True)
        obj = ci.AzureIntegration.__new__(ci.AzureIntegration)
        obj.blob_service_client = None
        assert obj.is_available() is False


class TestAzureIntegrationUpload:
    def test_returns_false_when_not_available(self, monkeypatch):
        monkeypatch.setattr(ci, "AZURE_AVAILABLE", False)
        obj = ci.AzureIntegration.__new__(ci.AzureIntegration)
        obj.blob_service_client = None
        assert obj.upload_to_blob("container", "file.txt") is False

    def test_returns_true_on_success(self, monkeypatch):
        monkeypatch.setattr(ci, "AZURE_AVAILABLE", True)
        obj = ci.AzureIntegration.__new__(ci.AzureIntegration)
        obj.blob_service_client = MagicMock()
        # Ensure open() call works with a real tmp file
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp_path = f.name
        try:
            result = obj.upload_to_blob("container", tmp_path, "data.bin")
            assert result is True
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# GCPIntegration
# ---------------------------------------------------------------------------

class TestGCPIntegrationIsAvailable:
    def test_true_when_flag_true_and_client_set(self, monkeypatch):
        monkeypatch.setattr(ci, "GCP_AVAILABLE", True)
        obj = ci.GCPIntegration.__new__(ci.GCPIntegration)
        obj.storage_client = MagicMock()
        assert obj.is_available() is True

    def test_false_when_flag_false(self, monkeypatch):
        monkeypatch.setattr(ci, "GCP_AVAILABLE", False)
        obj = ci.GCPIntegration.__new__(ci.GCPIntegration)
        obj.storage_client = MagicMock()
        assert obj.is_available() is False

    def test_false_when_client_none(self, monkeypatch):
        monkeypatch.setattr(ci, "GCP_AVAILABLE", True)
        obj = ci.GCPIntegration.__new__(ci.GCPIntegration)
        obj.storage_client = None
        assert obj.is_available() is False


class TestGCPIntegrationUpload:
    def test_returns_false_when_not_available(self, monkeypatch):
        monkeypatch.setattr(ci, "GCP_AVAILABLE", False)
        obj = ci.GCPIntegration.__new__(ci.GCPIntegration)
        obj.storage_client = None
        assert obj.upload_to_gcs("bucket", "file.txt") is False

    def test_returns_true_on_success(self, monkeypatch):
        monkeypatch.setattr(ci, "GCP_AVAILABLE", True)
        obj = ci.GCPIntegration.__new__(ci.GCPIntegration)
        obj.storage_client = MagicMock()
        result = obj.upload_to_gcs("bucket", "/tmp/file.txt", "file.txt")
        assert result is True


class TestGCPIntegrationList:
    def test_returns_empty_when_not_available(self, monkeypatch):
        monkeypatch.setattr(ci, "GCP_AVAILABLE", False)
        obj = ci.GCPIntegration.__new__(ci.GCPIntegration)
        obj.storage_client = None
        assert obj.list_gcs_objects("bucket") == []

    def test_returns_objects_on_success(self, monkeypatch):
        monkeypatch.setattr(ci, "GCP_AVAILABLE", True)
        obj = ci.GCPIntegration.__new__(ci.GCPIntegration)
        obj.storage_client = MagicMock()
        blob_mock = MagicMock()
        blob_mock.name = "file.txt"
        blob_mock.size = 512
        blob_mock.updated = MagicMock()
        blob_mock.updated.isoformat.return_value = "2024-06-01T00:00:00"
        obj.storage_client.bucket.return_value.list_blobs.return_value = [blob_mock]
        result = obj.list_gcs_objects("bucket")
        assert len(result) == 1
        assert result[0]["name"] == "file.txt"
        assert result[0]["size"] == 512
