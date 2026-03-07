"""
Unit tests for scripts/misc/monitor_phase2_auto.py
"""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import scripts.misc.monitor_phase2_auto as mon


# ─────────────────────────────────────────────
# _log
# ─────────────────────────────────────────────

class TestLog:
    def test_writes_info_to_log_file(self, tmp_path):
        mon._log(tmp_path, "hello world")
        log_files = list((tmp_path / "logs").glob("phase2_auto_*.log"))
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "[INFO]" in content
        assert "hello world" in content

    def test_writes_error_prefix_when_is_error(self, tmp_path):
        mon._log(tmp_path, "boom", is_error=True)
        log_files = list((tmp_path / "logs").glob("phase2_auto_*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "[ERROR]" in content
        assert "boom" in content

    def test_appends_multiple_entries(self, tmp_path):
        mon._log(tmp_path, "first")
        mon._log(tmp_path, "second")
        log_files = list((tmp_path / "logs").glob("phase2_auto_*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "first" in content
        assert "second" in content


# ─────────────────────────────────────────────
# _snapshot_path
# ─────────────────────────────────────────────

class TestSnapshotPath:
    def test_returns_json_path(self, tmp_path):
        p = mon._snapshot_path(tmp_path)
        assert p.suffix == ".json"

    def test_creates_snapshots_dir(self, tmp_path):
        mon._snapshot_path(tmp_path)
        assert (tmp_path / "snapshots").exists()

    def test_path_within_date_subdir(self, tmp_path):
        p = mon._snapshot_path(tmp_path)
        assert "snapshots" in str(p)


# ─────────────────────────────────────────────
# main — patch Path.exists + subprocess.run
# ─────────────────────────────────────────────

class TestMain:
    def test_returns_2_when_snapshot_script_missing(self):
        """phase1_metrics_snapshot.py が存在しない → 2"""
        with patch("pathlib.Path.exists", return_value=False):
            rc = mon.main()
        assert rc == 2

    def test_returns_2_on_subprocess_exception(self):
        """subprocess.run が例外 → 2"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("scripts.misc.monitor_phase2_auto.subprocess.run",
                   side_effect=RuntimeError("fail")):
            rc = mon.main()
        assert rc == 2

    def test_returns_nonzero_on_subprocess_error_code(self):
        """subprocess が rc=1 → ≠0"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("scripts.misc.monitor_phase2_auto.subprocess.run",
                   return_value=mock_result):
            rc = mon.main()
        assert rc != 0

    def test_returns_0_on_success(self):
        """subprocess が rc=0 → 0"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("pathlib.Path.exists", return_value=True), \
             patch("scripts.misc.monitor_phase2_auto.subprocess.run",
                   return_value=mock_result):
            rc = mon.main()
        assert rc == 0
