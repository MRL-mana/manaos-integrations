"""
tests/unit/test_scripts_misc_backup_recovery.py

scripts/misc/backup_recovery.py の単体テスト
- configure_backup / list_backups (設定・一覧)
- create_backup (tar.gz 生成・ハッシュ記録)
- verify_backup (ハッシュ検証)
- cleanup_old_backups (期限切れ削除)
- get_backup_status (ステータス集計)
- _calculate_hash (ハッシュ計算)
"""

import sys
import json
import tarfile
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))

from backup_recovery import BackupRecovery


# ===========================
# ヘルパー
# ===========================

def make_br(tmp_path):
    """テスト用 BackupRecovery インスタンス（tmp_path 内に隔離）"""
    br = BackupRecovery.__new__(BackupRecovery)
    br.backup_dir = tmp_path / "backups"
    br.backup_dir.mkdir(parents=True, exist_ok=True)
    br.backup_config = {}
    br.backup_history = []
    br.storage_path = tmp_path / "state.json"
    return br


# ===========================
# configure_backup
# ===========================

class TestConfigureBackup:
    def test_adds_config_entry(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("test", ["/tmp/src"], schedule="daily", retention_days=7)
        assert "test" in br.backup_config

    def test_source_paths_stored(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("cfg", ["/a", "/b"])
        assert br.backup_config["cfg"]["source_paths"] == ["/a", "/b"]

    def test_schedule_stored(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("cfg", [], schedule="weekly")
        assert br.backup_config["cfg"]["schedule"] == "weekly"

    def test_retention_days_stored(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("cfg", [], retention_days=30)
        assert br.backup_config["cfg"]["retention_days"] == 30

    def test_enabled_default_true(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("cfg", [])
        assert br.backup_config["cfg"]["enabled"] is True

    def test_last_backup_none(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("cfg", [])
        assert br.backup_config["cfg"]["last_backup"] is None

    def test_saves_state_file(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("cfg", [])
        assert br.storage_path.exists()


# ===========================
# list_backups
# ===========================

class TestListBackups:
    def test_empty_history_returns_empty(self, tmp_path):
        br = make_br(tmp_path)
        assert br.list_backups() == []

    def test_list_all(self, tmp_path):
        br = make_br(tmp_path)
        br.backup_history = [
            {"name": "a", "backup_path": "p1"},
            {"name": "b", "backup_path": "p2"},
        ]
        assert len(br.list_backups()) == 2

    def test_list_filtered_by_name(self, tmp_path):
        br = make_br(tmp_path)
        br.backup_history = [
            {"name": "a", "backup_path": "p1"},
            {"name": "b", "backup_path": "p2"},
            {"name": "a", "backup_path": "p3"},
        ]
        result = br.list_backups("a")
        assert len(result) == 2
        assert all(r["name"] == "a" for r in result)

    def test_list_unknown_name_returns_empty(self, tmp_path):
        br = make_br(tmp_path)
        br.backup_history = [{"name": "a", "backup_path": "p"}]
        assert br.list_backups("z") == []


# ===========================
# create_backup
# ===========================

class TestCreateBackup:
    def test_unknown_name_returns_none(self, tmp_path):
        br = make_br(tmp_path)
        assert br.create_backup("nonexistent") is None

    def test_disabled_config_returns_none(self, tmp_path):
        br = make_br(tmp_path)
        br.backup_config["cfg"] = {"enabled": False, "source_paths": []}
        assert br.create_backup("cfg") is None

    def test_creates_tar_gz(self, tmp_path):
        br = make_br(tmp_path)
        src = tmp_path / "mysrc.txt"
        src.write_text("hello")
        br.configure_backup("myb", [str(src)], retention_days=7)
        result = br.create_backup("myb")
        assert result is not None
        assert Path(result).exists()
        assert result.endswith(".tar.gz")

    def test_records_history_entry(self, tmp_path):
        br = make_br(tmp_path)
        src = tmp_path / "src.txt"
        src.write_text("data")
        br.configure_backup("myb", [str(src)])
        br.create_backup("myb")
        assert len(br.backup_history) == 1

    def test_history_entry_has_hash(self, tmp_path):
        br = make_br(tmp_path)
        src = tmp_path / "src.txt"
        src.write_text("data")
        br.configure_backup("myb", [str(src)])
        br.create_backup("myb")
        assert "backup_hash" in br.backup_history[0]
        assert len(br.backup_history[0]["backup_hash"]) == 64  # sha256 hex

    def test_history_entry_has_size(self, tmp_path):
        br = make_br(tmp_path)
        src = tmp_path / "src.txt"
        src.write_text("data")
        br.configure_backup("myb", [str(src)])
        br.create_backup("myb")
        assert br.backup_history[0]["size"] > 0

    def test_nonexistent_source_still_creates_archive(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("myb", ["/nonexistent/path/xyz"])
        result = br.create_backup("myb")
        # シーまだ成功：存在しないファイルはスキップされる
        assert result is not None


# ===========================
# _calculate_hash
# ===========================

class TestCalculateHash:
    def test_returns_hex_string(self, tmp_path):
        f = tmp_path / "file.bin"
        f.write_bytes(b"test data")
        br = make_br(tmp_path)
        h = br._calculate_hash(f)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_deterministic(self, tmp_path):
        f = tmp_path / "file.bin"
        f.write_bytes(b"consistent data")
        br = make_br(tmp_path)
        assert br._calculate_hash(f) == br._calculate_hash(f)

    def test_different_files_different_hashes(self, tmp_path):
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        br = make_br(tmp_path)
        assert br._calculate_hash(f1) != br._calculate_hash(f2)

    def test_known_hash(self, tmp_path):
        f = tmp_path / "known.bin"
        f.write_bytes(b"")  # empty file
        br = make_br(tmp_path)
        # sha256 of empty bytes
        expected = hashlib.sha256(b"").hexdigest()
        assert br._calculate_hash(f) == expected


# ===========================
# verify_backup
# ===========================

class TestVerifyBackup:
    def test_nonexistent_file_returns_false(self, tmp_path):
        br = make_br(tmp_path)
        assert br.verify_backup("/nonexistent/file.tar.gz") is False

    def test_no_history_record_returns_false(self, tmp_path):
        f = tmp_path / "orphan.tar.gz"
        f.write_bytes(b"data")
        br = make_br(tmp_path)
        assert br.verify_backup(str(f)) is False

    def test_matching_hash_returns_true(self, tmp_path):
        br = make_br(tmp_path)
        src = tmp_path / "src.txt"
        src.write_text("verify_me")
        br.configure_backup("v", [str(src)])
        backup_path = br.create_backup("v")
        assert br.verify_backup(backup_path) is True

    def test_tampered_file_returns_false(self, tmp_path):
        br = make_br(tmp_path)
        src = tmp_path / "src.txt"
        src.write_text("original")
        br.configure_backup("v", [str(src)])
        backup_path = br.create_backup("v")
        # ファイルを改ざん
        Path(backup_path).write_bytes(b"tampered_content")
        assert br.verify_backup(backup_path) is False


# ===========================
# cleanup_old_backups
# ===========================

class TestCleanupOldBackups:
    def test_removes_old_files(self, tmp_path):
        from datetime import datetime, timedelta
        br = make_br(tmp_path)
        br.configure_backup("old_b", [], retention_days=7)

        # 10日前のバックアップファイルを作る
        old_file = tmp_path / "backups" / "old_b_old.tar.gz"
        old_file.write_bytes(b"old data")
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        br.backup_history.append({
            "name": "old_b",
            "backup_path": str(old_file),
            "timestamp": old_ts,
        })

        br.cleanup_old_backups()
        assert not old_file.exists()

    def test_keeps_recent_files(self, tmp_path):
        from datetime import datetime, timedelta
        br = make_br(tmp_path)
        br.configure_backup("new_b", [], retention_days=7)

        new_file = tmp_path / "backups" / "new_b_new.tar.gz"
        new_file.write_bytes(b"fresh data")
        new_ts = datetime.now().isoformat()
        br.backup_history.append({
            "name": "new_b",
            "backup_path": str(new_file),
            "timestamp": new_ts,
        })

        br.cleanup_old_backups()
        assert new_file.exists()

    def test_removes_old_history_entries(self, tmp_path):
        from datetime import datetime, timedelta
        br = make_br(tmp_path)
        br.configure_backup("old_b", [], retention_days=7)

        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        br.backup_history.append({
            "name": "old_b",
            "backup_path": str(tmp_path / "backups" / "nofile.tar.gz"),
            "timestamp": old_ts,
        })
        br.cleanup_old_backups()
        assert all(b["name"] != "old_b" for b in br.backup_history)


# ===========================
# get_backup_status
# ===========================

class TestGetBackupStatus:
    def test_returns_dict(self, tmp_path):
        br = make_br(tmp_path)
        assert isinstance(br.get_backup_status(), dict)

    def test_configured_backups_count(self, tmp_path):
        br = make_br(tmp_path)
        br.configure_backup("a", [])
        br.configure_backup("b", [])
        status = br.get_backup_status()
        assert status["configured_backups"] == 2

    def test_total_backups_count(self, tmp_path):
        br = make_br(tmp_path)
        br.backup_history = [
            {"backup_path": "/nonexistent1"},
            {"backup_path": "/nonexistent2"},
        ]
        status = br.get_backup_status()
        assert status["total_backups"] == 2

    def test_backup_dir_in_status(self, tmp_path):
        br = make_br(tmp_path)
        status = br.get_backup_status()
        assert "backup_dir" in status

    def test_total_size_zero_when_no_files(self, tmp_path):
        br = make_br(tmp_path)
        br.backup_history = [{"backup_path": "/nonexistent_xyz.tar.gz"}]
        status = br.get_backup_status()
        assert status["total_size"] == 0
