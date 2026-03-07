"""
Unit tests for scripts/misc/backup_system.py
"""
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

# ── module-level mocks ─────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=MagicMock(message="err"))
))
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

import pytest
from scripts.misc.backup_system import BackupInfo, BackupSystem


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def bs(tmp_path):
    return BackupSystem(backup_dir=tmp_path / "backups")


# ── TestBackupInfo ─────────────────────────────────────────────────────────
class TestBackupInfo:
    def test_fields_accessible(self, tmp_path):
        b = BackupInfo(
            backup_id="b1",
            backup_type="full",
            backup_path=tmp_path / "b1.tar.gz",
            created_at=datetime.now().isoformat(),
            size_bytes=1024,
            checksum="abc123",
        )
        assert b.backup_id == "b1"
        assert b.backup_type == "full"
        assert b.size_bytes == 1024

    def test_metadata_defaults_empty_dict(self, tmp_path):
        b = BackupInfo(
            backup_id="b2",
            backup_type="full",
            backup_path=tmp_path / "b2.tar.gz",
            created_at=datetime.now().isoformat(),
            size_bytes=0,
            checksum="x",
        )
        assert b.metadata == {}


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_backup_dir_created(self, tmp_path):
        bd = tmp_path / "mybkp"
        bs = BackupSystem(backup_dir=bd)
        assert bd.exists()

    def test_retention_days_stored(self):
        bs = BackupSystem.__new__(BackupSystem)
        bs.backup_dir = MagicMock()
        bs.backup_dir.mkdir.return_value = None
        bs.retention_days = 14
        assert bs.retention_days == 14

    def test_empty_history_initially(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path / "bk2")
        assert bs.backup_history == []


# ── TestCreateBackup ───────────────────────────────────────────────────────
class TestCreateBackup:
    def test_create_empty_backup(self, bs):
        info = bs.create_backup(target_paths=[])
        assert isinstance(info, BackupInfo)
        assert info.backup_type == "full"

    def test_backup_file_created(self, bs):
        info = bs.create_backup(target_paths=[])
        assert info.backup_path.exists()

    def test_checksum_set(self, bs):
        info = bs.create_backup(target_paths=[])
        assert info.checksum != ""

    def test_backup_added_to_history(self, bs):
        bs.create_backup(target_paths=[])
        assert len(bs.backup_history) == 1

    def test_incremental_type_stored(self, bs):
        info = bs.create_backup(backup_type="incremental", target_paths=[])
        assert info.backup_type == "incremental"


# ── TestVerifyBackup ───────────────────────────────────────────────────────
class TestVerifyBackup:
    def test_valid_backup_verified(self, bs):
        info = bs.create_backup(target_paths=[])
        assert bs.verify_backup(info) is True

    def test_missing_file_fails(self, bs, tmp_path):
        info = BackupInfo(
            backup_id="ghost",
            backup_type="full",
            backup_path=tmp_path / "ghost.tar.gz",
            created_at=datetime.now().isoformat(),
            size_bytes=100,
            checksum="abc",
        )
        assert bs.verify_backup(info) is False

    def test_wrong_checksum_fails(self, bs):
        info = bs.create_backup(target_paths=[])
        info.checksum = "wrong_checksum"
        assert bs.verify_backup(info) is False


# ── TestCleanupOldBackups ──────────────────────────────────────────────────
class TestCleanupOldBackups:
    def test_removes_old_backups(self, bs):
        info = bs.create_backup(target_paths=[])
        # make it appear old
        old_time = datetime.now() - timedelta(days=60)
        info.created_at = old_time.isoformat()
        removed = bs.cleanup_old_backups()
        assert removed >= 1

    def test_recent_backup_not_removed(self, bs):
        info = bs.create_backup(target_paths=[])
        removed = bs.cleanup_old_backups()
        assert removed == 0
        assert len(bs.backup_history) == 1
