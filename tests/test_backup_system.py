#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: backup_system.py
BackupInfo dataclass / BackupSystem の主要メソッドを純粋単体テスト
"""

import json
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# ---- 依存モジュールを全てモック化 ----------------------------------------
_mock_logger = MagicMock()
_mock_service_logger = MagicMock(return_value=_mock_logger)
_mock_error_handler_cls = MagicMock()
_mock_error_handler_inst = MagicMock()
_mock_error_handler_cls.return_value = _mock_error_handler_inst
_mock_error_handler_inst.handle_exception.return_value = MagicMock(message="err")

import sys
sys.modules.setdefault("manaos_logger", MagicMock(
    get_logger=MagicMock(return_value=_mock_logger),
    get_service_logger=_mock_service_logger,
))
sys.modules.setdefault("manaos_error_handler", MagicMock(
    ManaOSErrorHandler=_mock_error_handler_cls,
    ErrorCategory=MagicMock(),
    ErrorSeverity=MagicMock(),
))
sys.modules.setdefault("schedule", MagicMock())

from backup_system import BackupInfo, BackupSystem  # noqa: E402


# =========================================================================
# BackupInfo dataclass
# =========================================================================
class TestBackupInfo:

    def test_basic_fields(self):
        info = BackupInfo(
            backup_id="b001",
            backup_type="full",
            backup_path=Path("/tmp/b001.tar.gz"),
            created_at="2026-01-01T00:00:00",
            size_bytes=1024,
            checksum="abc123",
        )
        assert info.backup_id == "b001"
        assert info.backup_type == "full"
        assert info.size_bytes == 1024
        assert info.checksum == "abc123"

    def test_metadata_default_empty_dict(self):
        info = BackupInfo(
            backup_id="b002",
            backup_type="incremental",
            backup_path=Path("/tmp/b002.tar.gz"),
            created_at="2026-01-01T00:00:00",
            size_bytes=512,
            checksum="xyz",
        )
        assert info.metadata == {}

    def test_metadata_custom(self):
        info = BackupInfo(
            backup_id="b003",
            backup_type="full",
            backup_path=Path("/tmp/b003.tar.gz"),
            created_at="2026-01-01T00:00:00",
            size_bytes=0,
            checksum="",
            metadata={"note": "test"},
        )
        assert info.metadata["note"] == "test"

    def test_path_stored_as_path(self):
        p = Path("/tmp/check.tar.gz")
        info = BackupInfo(
            backup_id="b004",
            backup_type="full",
            backup_path=p,
            created_at="2026-01-01T00:00:00",
            size_bytes=0,
            checksum="",
        )
        assert isinstance(info.backup_path, Path)


# =========================================================================
# BackupSystem.__init__ / _load_backup_history
# =========================================================================
class TestBackupSystemInit:

    def test_init_creates_backup_dir(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        assert (tmp_path / "bk").exists()

    def test_init_default_retention(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path)
        assert bs.retention_days == 30

    def test_init_custom_params(self, tmp_path):
        bs = BackupSystem(
            backup_dir=tmp_path,
            retention_days=7,
            backup_interval_hours=12,
        )
        assert bs.retention_days == 7
        assert bs.backup_interval_hours == 12

    def test_init_empty_history(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path)
        assert bs.backup_history == []

    def test_load_backup_history_from_file(self, tmp_path):
        history_data = [
            {
                "backup_id": "b001",
                "backup_type": "full",
                "backup_path": str(tmp_path / "b001.tar.gz"),
                "created_at": "2026-01-01T00:00:00",
                "size_bytes": 100,
                "checksum": "abc",
                "metadata": {},
            }
        ]
        (tmp_path / "backup_history.json").write_text(
            json.dumps(history_data), encoding="utf-8"
        )
        bs = BackupSystem(backup_dir=tmp_path)
        assert len(bs.backup_history) == 1
        assert bs.backup_history[0].backup_id == "b001"

    def test_load_backup_history_path_converted(self, tmp_path):
        history_data = [
            {
                "backup_id": "b002",
                "backup_type": "full",
                "backup_path": "/some/path.tar.gz",
                "created_at": "2026-01-01T00:00:00",
                "size_bytes": 0,
                "checksum": "",
                "metadata": {},
            }
        ]
        (tmp_path / "backup_history.json").write_text(
            json.dumps(history_data), encoding="utf-8"
        )
        bs = BackupSystem(backup_dir=tmp_path)
        assert isinstance(bs.backup_history[0].backup_path, Path)


# =========================================================================
# _calculate_checksum
# =========================================================================
class TestCalculateChecksum:

    def test_returns_hex_string(self, tmp_path):
        data = b"hello backup"
        f = tmp_path / "data.bin"
        f.write_bytes(data)
        bs = BackupSystem(backup_dir=tmp_path)
        checksum = bs._calculate_checksum(f)
        assert isinstance(checksum, str)
        assert len(checksum) == 32  # MD5 hex length

    def test_same_content_same_checksum(self, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"same")
        f2.write_bytes(b"same")
        bs = BackupSystem(backup_dir=tmp_path)
        assert bs._calculate_checksum(f1) == bs._calculate_checksum(f2)

    def test_different_content_different_checksum(self, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        bs = BackupSystem(backup_dir=tmp_path)
        assert bs._calculate_checksum(f1) != bs._calculate_checksum(f2)


# =========================================================================
# create_backup
# =========================================================================
class TestCreateBackup:

    def test_create_backup_produces_file(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        info = bs.create_backup(backup_type="full", target_paths=[src])
        assert info.backup_path.exists()

    def test_create_backup_returns_backup_info(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        info = bs.create_backup(target_paths=[src])
        assert isinstance(info, BackupInfo)
        assert info.backup_type == "full"
        assert info.size_bytes > 0

    def test_create_backup_appends_to_history(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("x")
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        assert len(bs.backup_history) == 0
        bs.create_backup(target_paths=[src])
        assert len(bs.backup_history) == 1

    def test_create_backup_checksum_set(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("checksum test")
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        info = bs.create_backup(target_paths=[src])
        assert len(info.checksum) == 32

    def test_create_incremental_type(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("inc")
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        info = bs.create_backup(backup_type="incremental", target_paths=[src])
        assert info.backup_type == "incremental"


# =========================================================================
# verify_backup
# =========================================================================
class TestVerifyBackup:

    def _make_backup(self, tmp_path) -> BackupInfo:
        src = tmp_path / "src.txt"
        src.write_text("verify me")
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        return bs, bs.create_backup(target_paths=[src])

    def test_verify_valid_backup(self, tmp_path):
        bs, info = self._make_backup(tmp_path)
        assert bs.verify_backup(info) is True

    def test_verify_missing_file_returns_false(self, tmp_path):
        bs, info = self._make_backup(tmp_path)
        info.backup_path.unlink()
        assert bs.verify_backup(info) is False

    def test_verify_wrong_size_returns_false(self, tmp_path):
        bs, info = self._make_backup(tmp_path)
        info.size_bytes = 9999999
        assert bs.verify_backup(info) is False

    def test_verify_wrong_checksum_returns_false(self, tmp_path):
        bs, info = self._make_backup(tmp_path)
        info.checksum = "badchecksum00000000000000000000"
        assert bs.verify_backup(info) is False


# =========================================================================
# cleanup_old_backups
# =========================================================================
class TestCleanupOldBackups:

    def test_removes_old_backup(self, tmp_path):
        src = tmp_path / "s.txt"
        src.write_text("old")
        bs = BackupSystem(backup_dir=tmp_path / "bk", retention_days=1)
        info = bs.create_backup(target_paths=[src])
        # 古い日付に書き換え
        info.created_at = (datetime.now() - timedelta(days=3)).isoformat()
        removed = bs.cleanup_old_backups()
        assert removed == 1
        assert len(bs.backup_history) == 0

    def test_keeps_recent_backup(self, tmp_path):
        src = tmp_path / "s.txt"
        src.write_text("new")
        bs = BackupSystem(backup_dir=tmp_path / "bk", retention_days=30)
        bs.create_backup(target_paths=[src])
        removed = bs.cleanup_old_backups()
        assert removed == 0
        assert len(bs.backup_history) == 1

    def test_returns_count(self, tmp_path):
        src = tmp_path / "s.txt"
        src.write_text("data")
        bs = BackupSystem(backup_dir=tmp_path / "bk", retention_days=1)
        for _ in range(3):
            info = bs.create_backup(target_paths=[src])
            info.created_at = (datetime.now() - timedelta(days=5)).isoformat()
        removed = bs.cleanup_old_backups()
        assert removed == 3


# =========================================================================
# restore_backup
# =========================================================================
class TestRestoreBackup:

    def test_restore_to_directory(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("restore content")
        bs = BackupSystem(backup_dir=tmp_path / "bk")
        info = bs.create_backup(target_paths=[src])
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        result = bs.restore_backup(info, restore_dir=restore_dir)
        assert result is True

    def test_restore_invalid_backup_returns_false(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path)
        fake_info = BackupInfo(
            backup_id="fake",
            backup_type="full",
            backup_path=tmp_path / "nonexistent.tar.gz",
            created_at=datetime.now().isoformat(),
            size_bytes=0,
            checksum="",
        )
        result = bs.restore_backup(fake_info, restore_dir=tmp_path)
        assert result is False


# =========================================================================
# start_auto_backup / stop_auto_backup
# =========================================================================
class TestAutoBackupScheduler:

    def test_start_sets_scheduling_flag(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path)
        bs.start_auto_backup()
        assert bs.scheduling is True
        bs.stop_auto_backup()

    def test_stop_clears_scheduling_flag(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path)
        bs.start_auto_backup()
        bs.stop_auto_backup()
        assert bs.scheduling is False

    def test_double_start_is_idempotent(self, tmp_path):
        bs = BackupSystem(backup_dir=tmp_path)
        bs.start_auto_backup()
        bs.start_auto_backup()  # 2回目は無視される
        assert bs.scheduling is True
        bs.stop_auto_backup()
