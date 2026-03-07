"""
Unit tests for scripts/misc/cross_platform_file_sync.py
"""
import sys
import json
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

sys.modules.setdefault("watchdog.observers", MagicMock())
sys.modules.setdefault("watchdog.events", MagicMock(FileSystemEventHandler=object))
sys.modules.setdefault("google_drive_integration", MagicMock())

import pytest
from scripts.misc.cross_platform_file_sync import (
    SyncRule,
    FileVersion,
    SyncConflict,
    CrossPlatformFileSync,
)


@pytest.fixture
def sync(tmp_path):
    cfg = tmp_path / "sync_config.json"
    default = {
        "credentials_path": "credentials.json",
        "token_path": "token.json",
        "version_file": str(tmp_path / "versions.json"),
        "conflicts_file": str(tmp_path / "conflicts.json"),
        "sync_rules": [],
    }
    cfg.write_text(json.dumps(default), encoding="utf-8")
    s = CrossPlatformFileSync(config_path=str(cfg))
    return s


# ── TestSyncRule ──────────────────────────────────────────────────────────
class TestSyncRule:
    def _rule(self, **kw):
        defaults = dict(
            rule_id="r1", local_path="/local", sync_path="Remote",
            devices=["a", "b"], sync_mode="bidirectional",
            conflict_resolution="newest", enabled=True,
        )
        defaults.update(kw)
        return SyncRule(**defaults)

    def test_create(self):
        r = self._rule()
        assert r.rule_id == "r1"
        assert r.enabled is True

    def test_devices_list(self):
        r = self._rule(devices=["x", "y", "z"])
        assert len(r.devices) == 3

    def test_disabled(self):
        r = self._rule(enabled=False)
        assert r.enabled is False


# ── TestFileVersion ───────────────────────────────────────────────────────
class TestFileVersion:
    def _ver(self, **kw):
        defaults = dict(
            file_path="/tmp/test.txt", version=1, hash="abc123",
            timestamp="2026-01-01T00:00:00", device="mothership", size=1024,
        )
        defaults.update(kw)
        return FileVersion(**defaults)

    def test_create(self):
        v = self._ver()
        assert v.version == 1
        assert v.size == 1024

    def test_hash_stored(self):
        v = self._ver(hash="deadbeef")
        assert v.hash == "deadbeef"

    def test_device_stored(self):
        v = self._ver(device="x280")
        assert v.device == "x280"


# ── TestSyncConflict ──────────────────────────────────────────────────────
class TestSyncConflict:
    def _conflict(self, conflict_type="modified_both"):
        local_v = FileVersion("/path", 2, "abc", "2026-01-01", "local", 100)
        remote_v = FileVersion("/path", 3, "xyz", "2026-01-02", "remote", 200)
        return SyncConflict(
            file_path="/path",
            local_version=local_v,
            remote_version=remote_v,
            conflict_type=conflict_type,
        )

    def test_conflict_type(self):
        c = self._conflict("modified_both")
        assert c.conflict_type == "modified_both"

    def test_versions_stored(self):
        c = self._conflict()
        assert c.local_version.version == 2
        assert c.remote_version.version == 3


# ── TestGetFileHash ───────────────────────────────────────────────────────
class TestGetFileHash:
    def test_returns_hex_string(self, sync, tmp_path):
        f = tmp_path / "hashme.txt"
        f.write_bytes(b"hello world")
        result = sync._get_file_hash(f)
        assert isinstance(result, str)
        assert len(result) in (32, 64)  # MD5=32, SHA-256=64

    def test_deterministic(self, sync, tmp_path):
        f = tmp_path / "det.txt"
        f.write_bytes(b"consistent data")
        h1 = sync._get_file_hash(f)
        h2 = sync._get_file_hash(f)
        assert h1 == h2

    def test_different_content_different_hash(self, sync, tmp_path):
        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        assert sync._get_file_hash(f1) != sync._get_file_hash(f2)


# ── TestGetLatestVersion ──────────────────────────────────────────────────
class TestGetLatestVersion:
    def test_none_for_unknown_path(self, sync):
        assert sync._get_latest_version("/nonexistent") is None

    def test_returns_latest(self, sync):
        v1 = FileVersion("/f", 1, "h1", "2026-01-01T00:00:00", "d", 100)
        v2 = FileVersion("/f", 2, "h2", "2026-01-02T00:00:00", "d", 200)
        sync.file_versions["/f"] = [v1, v2]
        latest = sync._get_latest_version("/f")
        assert latest.version == 2


# ── TestAddVersion ────────────────────────────────────────────────────────
class TestAddVersion:
    def test_creates_entry(self, sync):
        sync._add_version("/new/file.txt", "mothership", "abc123", 512)
        assert "/new/file.txt" in sync.file_versions

    def test_version_number_increments(self, sync):
        sync._add_version("/v/file.txt", "d", "h1", 100)
        sync._add_version("/v/file.txt", "d", "h2", 200)
        versions = sync.file_versions["/v/file.txt"]
        assert versions[-1].version == 2

    def test_device_stored(self, sync):
        sync._add_version("/d/file.txt", "x280", "hxxx", 100)
        v = sync.file_versions["/d/file.txt"][0]
        assert v.device == "x280"


# ── TestScheduleSync ─────────────────────────────────────────────────────
class TestScheduleSync:
    def test_enqueues_item(self, sync, tmp_path):
        sync.schedule_sync(tmp_path / "some.txt", "modified")
        assert len(sync.sync_queue) == 1

    def test_queue_item_has_path(self, sync, tmp_path):
        p = tmp_path / "q.txt"
        sync.schedule_sync(p, "created")
        assert sync.sync_queue[0]["file_path"] == str(p)
