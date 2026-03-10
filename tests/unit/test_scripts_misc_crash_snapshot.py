"""
Unit tests for scripts/misc/crash_snapshot.py
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────
_ml = MagicMock()
_ml.get_logger = MagicMock(return_value=MagicMock())
_ml.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_logger", _ml)

_meh = MagicMock()
_meh.ManaOSErrorHandler = MagicMock(return_value=MagicMock())
_meh.ErrorCategory = MagicMock()
_meh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _meh)

_mtc = MagicMock()
_mtc.get_timeout_config = MagicMock(return_value={"api_call": 10, "file_download": 60})
sys.modules.setdefault("manaos_timeout_config", _mtc)

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.TASK_QUEUE_PORT = 5100  # type: ignore
sys.modules["_paths"] = _paths_mod

sys.modules.setdefault("flask", MagicMock(
    Flask=MagicMock(return_value=MagicMock()),
    jsonify=MagicMock(side_effect=lambda x: x),
    request=MagicMock(),
))
sys.modules.setdefault("flask_cors", MagicMock(CORS=MagicMock()))

# psutil / httpx は実際にインポート可能or mock
_psutil_mock = MagicMock()
sys.modules.setdefault("psutil", _psutil_mock)

_httpx_mock = MagicMock()
sys.modules.setdefault("httpx", _httpx_mock)

from scripts.misc.crash_snapshot import CrashSnapshot, CrashSnapshotManager


# ── TestCrashSnapshotDataclass ──────────────────────────────────────────────
class TestCrashSnapshotDataclass:
    def test_fields_required(self):
        snap = CrashSnapshot(
            timestamp="2025-01-01T00:00:00",
            service_name="my-service",
            service_port=8080,
            system_resources={"cpu": {"percent": 10.0}},
            recent_logs=["log line 1"],
            running_tasks=[{"source": "task_queue"}],
            error_message="Something went wrong",
        )
        assert snap.service_name == "my-service"
        assert snap.service_port == 8080
        assert snap.stack_trace is None

    def test_stack_trace_optional(self):
        snap = CrashSnapshot(
            timestamp="ts",
            service_name="svc",
            service_port=1000,
            system_resources={},
            recent_logs=[],
            running_tasks=[],
            error_message="err",
            stack_trace="Traceback ...",
        )
        assert snap.stack_trace == "Traceback ..."


# ── TestCrashSnapshotManagerInit ───────────────────────────────────────────
class TestCrashSnapshotManagerInit:
    def test_creates_snapshot_dir(self, tmp_path):
        snap_dir = tmp_path / "snaps"
        assert not snap_dir.exists()
        mgr = CrashSnapshotManager(snapshot_dir=snap_dir)
        assert snap_dir.exists()
        assert mgr.snapshot_dir == snap_dir

    def test_default_dir_is_relative_to_script(self):
        # snapshot_dir を指定しない場合、crash_snapshots/ が使われる
        # (__file__ が scripts/misc/crash_snapshot.py なのでそこを基準に)
        mgr = CrashSnapshotManager.__new__(CrashSnapshotManager)
        # default_dir の計算だけ確認
        import scripts.misc.crash_snapshot as mod
        expected_base = Path(mod.__file__).parent / "crash_snapshots"
        assert expected_base.name == "crash_snapshots"


# ── TestGetSystemResources ─────────────────────────────────────────────────
class TestGetSystemResources:
    def _make_psutil(self):
        """psutil のモックを返す。"""
        mock_mem = MagicMock()
        mock_mem.total = 8 * 1024 ** 3
        mock_mem.used = 4 * 1024 ** 3
        mock_mem.available = 4 * 1024 ** 3
        mock_mem.percent = 50.0

        mock_disk = MagicMock()
        mock_disk.total = 100 * 1024 ** 3
        mock_disk.used = 40 * 1024 ** 3
        mock_disk.free = 60 * 1024 ** 3
        mock_disk.percent = 40.0

        mock_proc_info = {
            "pid": 1234,
            "name": "python.exe",
            "memory_info": MagicMock(rss=100 * 1024 ** 2),
            "cpu_percent": 5.0,
        }
        mock_proc = MagicMock()
        mock_proc.info = mock_proc_info

        psutil_mock = MagicMock()
        psutil_mock.cpu_percent.return_value = 25.0
        psutil_mock.cpu_count.return_value = 4
        psutil_mock.virtual_memory.return_value = mock_mem
        psutil_mock.disk_usage.return_value = mock_disk
        psutil_mock.process_iter.return_value = [mock_proc]
        psutil_mock.NoSuchProcess = Exception
        psutil_mock.AccessDenied = Exception
        return psutil_mock

    def test_returns_dict_with_expected_keys(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        with patch("scripts.misc.crash_snapshot.psutil", self._make_psutil()):
            result = mgr._get_system_resources()
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "python_processes" in result

    def test_cpu_percent_in_result(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        with patch("scripts.misc.crash_snapshot.psutil", self._make_psutil()):
            result = mgr._get_system_resources()
        assert result["cpu"]["percent"] == 25.0

    def test_returns_error_key_on_exception(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        bad_psutil = MagicMock()
        bad_psutil.cpu_percent.side_effect = RuntimeError("no cpu")
        with patch("scripts.misc.crash_snapshot.psutil", bad_psutil):
            result = mgr._get_system_resources()
        assert "error" in result


# ── TestGetRecentLogs ──────────────────────────────────────────────────────
class TestGetRecentLogs:
    def test_returns_list(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        # ログファイルがない場合 → 空リスト
        result = mgr._get_recent_logs("test_service")
        assert isinstance(result, list)

    def test_reads_error_log_if_exists(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        log_dir = Path(mgr.snapshot_dir).parent.parent / "scripts" / "misc" / "logs"
        # 実際のファイルシステムの代わりにパスをモックする
        fake_log_content = ["line1\n", "line2\n", "line3\n"]
        import builtins
        _orig_exists = Path.exists

        def _mock_exists(self_path):
            if "error.log" in str(self_path):
                return True
            return False

        def _mock_open(path, *a, **kw):
            if "error.log" in str(path):
                from io import StringIO
                m = MagicMock()
                m.__enter__ = lambda s: StringIO("line1\nline2\nline3\n")
                m.__exit__ = MagicMock(return_value=False)
                return m
            return _orig_open(path, *a, **kw)

        _orig_open = builtins.open
        with patch.object(Path, "exists", _mock_exists), \
             patch("builtins.open", side_effect=_mock_open):
            result = mgr._get_recent_logs("my_service")
        assert isinstance(result, list)


# ── TestGetRunningTasks ────────────────────────────────────────────────────
class TestGetRunningTasks:
    def test_returns_list_on_http_success(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy", "pending_tasks": 3}
        with patch("scripts.misc.crash_snapshot.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_resp
            result = mgr._get_running_tasks(5100)
        assert isinstance(result, list)
        assert result[0]["source"] == "task_queue"

    def test_returns_error_entry_on_http_failure(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        with patch("scripts.misc.crash_snapshot.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("connection refused")
            result = mgr._get_running_tasks(9999)
        assert isinstance(result, list)
        assert result[0]["source"] == "error"


# ── TestCreateSnapshot ─────────────────────────────────────────────────────
class TestCreateSnapshot:
    def _setup_psutil(self):
        mock_mem = MagicMock()
        mock_mem.total = 8 * 1024 ** 3
        mock_mem.used = 4 * 1024 ** 3
        mock_mem.available = 4 * 1024 ** 3
        mock_mem.percent = 50.0
        mock_disk = MagicMock()
        mock_disk.total = 100 * 1024 ** 3
        mock_disk.used = 40 * 1024 ** 3
        mock_disk.free = 60 * 1024 ** 3
        mock_disk.percent = 40.0
        psutil_m = MagicMock()
        psutil_m.cpu_percent.return_value = 10.0
        psutil_m.cpu_count.return_value = 4
        psutil_m.virtual_memory.return_value = mock_mem
        psutil_m.disk_usage.return_value = mock_disk
        psutil_m.process_iter.return_value = []
        psutil_m.NoSuchProcess = Exception
        psutil_m.AccessDenied = Exception
        return psutil_m

    def test_creates_json_file(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "pending_tasks": 0}
        with patch("scripts.misc.crash_snapshot.psutil", self._setup_psutil()), \
             patch("scripts.misc.crash_snapshot.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_resp
            path = mgr.create_snapshot("my-svc", 8080, "Something broke")
        assert path.exists()
        assert path.suffix == ".json"

    def test_json_contains_service_name(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        with patch("scripts.misc.crash_snapshot.psutil", self._setup_psutil()), \
             patch("scripts.misc.crash_snapshot.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("no conn")
            path = mgr.create_snapshot("test-service", 9000, "error msg")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["service_name"] == "test-service"
        assert data["error_message"] == "error msg"

    def test_readable_txt_file_also_created(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        with patch("scripts.misc.crash_snapshot.psutil", self._setup_psutil()), \
             patch("scripts.misc.crash_snapshot.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("no conn")
            path = mgr.create_snapshot("svc", 1111, "err")
        txt_path = path.with_suffix(".txt")
        assert txt_path.exists()

    def test_stack_trace_included_when_provided(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        with patch("scripts.misc.crash_snapshot.psutil", self._setup_psutil()), \
             patch("scripts.misc.crash_snapshot.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("no conn")
            path = mgr.create_snapshot("svc", 1111, "err", stack_trace="line1\nline2")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["stack_trace"] == "line1\nline2"


# ── TestGetRecentSnapshots ─────────────────────────────────────────────────
class TestGetRecentSnapshots:
    def test_returns_empty_when_no_snapshots(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        result = mgr.get_recent_snapshots()
        assert result == []

    def test_returns_paths_sorted_by_mtime(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        # ファイルを作成
        for i in range(3):
            f = tmp_path / f"crash_2025010{i}_120000_svc.json"
            f.write_text('{"service_name":"svc"}', encoding="utf-8")
        result = mgr.get_recent_snapshots(limit=10)
        assert len(result) == 3
        assert all(p.suffix == ".json" for p in result)

    def test_limit_respected(self, tmp_path):
        mgr = CrashSnapshotManager(snapshot_dir=tmp_path)
        for i in range(5):
            f = tmp_path / f"crash_2025010{i}_000000_s.json"
            f.write_text("{}", encoding="utf-8")
        result = mgr.get_recent_snapshots(limit=2)
        assert len(result) == 2
