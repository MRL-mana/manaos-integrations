"""
Unit tests for scripts/misc/update_baseline_from_snapshots.py
"""
import json
from pathlib import Path

import pytest

from scripts.misc.update_baseline_from_snapshots import (
    _list_snapshot_files,
    main,
)


def _make_snapshot(snapshot_dir: Path, date: str, hour: str, metrics: dict) -> Path:
    d = snapshot_dir / date
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{hour}.json"
    p.write_text(json.dumps({"metrics": metrics}), encoding="utf-8")
    return p


class TestListSnapshotFiles:
    def test_returns_empty_for_nonexistent_dir(self, tmp_path: Path):
        assert _list_snapshot_files(tmp_path / "nope") == []

    def test_returns_matching_files(self, tmp_path: Path):
        _make_snapshot(tmp_path, "2026-01-01", "10", {})
        result = _list_snapshot_files(tmp_path)
        assert len(result) == 1

    def test_ignores_non_matching_files(self, tmp_path: Path):
        (tmp_path / "readme.md").write_text("ignore me")
        result = _list_snapshot_files(tmp_path)
        assert len(result) == 0

    def test_max_count_limits_results(self, tmp_path: Path):
        for day in range(5):
            _make_snapshot(tmp_path, f"2026-01-0{day+1}", "08", {})
        result = _list_snapshot_files(tmp_path, max_count=2)
        assert len(result) == 2

    def test_files_sorted_descending(self, tmp_path: Path):
        _make_snapshot(tmp_path, "2026-01-01", "08", {})
        _make_snapshot(tmp_path, "2026-01-02", "08", {})
        result = _list_snapshot_files(tmp_path)
        # latest first
        assert result[0].parent.name > result[1].parent.name


class TestMain:
    def test_main_no_snapshots_returns_1(self, tmp_path: Path, monkeypatch):
        # Point __file__ at tmp_path so snapshots_dir = tmp_path/snapshots (empty)
        monkeypatch.setattr(
            "scripts.misc.update_baseline_from_snapshots.__file__",
            str(tmp_path / "update_baseline_from_snapshots.py"),
        )
        result = main()
        assert result == 1

    def test_main_with_snapshots_updates_baseline(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            "scripts.misc.update_baseline_from_snapshots.__file__",
            str(tmp_path / "update_baseline_from_snapshots.py"),
        )
        snap_dir = tmp_path / "snapshots"
        _make_snapshot(snap_dir, "2026-01-01", "08", {
            "e2e_p95_sec": 1.5,
            "writes_per_min": 100,
            "contradiction_rate": 0.02,
            "gate_block_rate": 0.01,
        })
        result = main()
        assert result == 0
        baseline = json.loads((tmp_path / "phase1_metrics_snapshot_baseline.json").read_text())
        assert "metrics" in baseline
        assert baseline["metrics"]["e2e_p95_sec"] == 1.5

    def test_main_preserves_existing_config(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            "scripts.misc.update_baseline_from_snapshots.__file__",
            str(tmp_path / "update_baseline_from_snapshots.py"),
        )
        existing = {"phase": "Phase X", "config": {"key": "val"}, "security": {}, "storage": {}, "errors": {}, "api_status": {}}
        (tmp_path / "phase1_metrics_snapshot_baseline.json").write_text(
            json.dumps(existing), encoding="utf-8"
        )
        snap_dir = tmp_path / "snapshots"
        _make_snapshot(snap_dir, "2026-01-01", "09", {"e2e_p95_sec": 2.0, "writes_per_min": 50, "contradiction_rate": 0.0, "gate_block_rate": 0.0})
        main()
        result = json.loads((tmp_path / "phase1_metrics_snapshot_baseline.json").read_text())
        assert result["phase"] == "Phase X"
        assert result["config"]["key"] == "val"
