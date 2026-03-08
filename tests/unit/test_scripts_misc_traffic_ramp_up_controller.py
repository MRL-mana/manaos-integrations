"""
Unit tests for scripts/misc/traffic_ramp_up_controller.py
"""
import json
from pathlib import Path

import pytest

from scripts.misc.traffic_ramp_up_controller import TrafficRampUpController


def _make_controller(tmp_path: Path) -> TrafficRampUpController:
    ctrl = TrafficRampUpController()
    ctrl.state_file = tmp_path / "state.json"
    ctrl.log_file = tmp_path / "traffic.log"
    ctrl.metrics_file = tmp_path / "metrics.json"
    return ctrl


class TestStatus:
    def test_missing_state_file_prints_error(self, tmp_path: Path, capsys):
        ctrl = _make_controller(tmp_path)
        ctrl.status()
        out = capsys.readouterr().out
        assert "見つかりません" in out or "not found" in out.lower() or "❌" in out

    def test_shows_current_phase(self, tmp_path: Path, capsys):
        ctrl = _make_controller(tmp_path)
        ctrl.state_file.write_text(json.dumps({"current_phase": "phase2", "timestamp": "2026-01-01T00:00:00"}))
        ctrl.status()
        out = capsys.readouterr().out
        assert "PHASE2" in out

    def test_shows_log_lines_when_log_exists(self, tmp_path: Path, capsys):
        ctrl = _make_controller(tmp_path)
        ctrl.state_file.write_text(json.dumps({"current_phase": "phase1"}))
        ctrl.log_file.write_text("line1\nline2\n")
        ctrl.status()
        out = capsys.readouterr().out
        assert "line1" in out


class TestMetrics:
    def test_missing_metrics_file_prints_error(self, tmp_path: Path, capsys):
        ctrl = _make_controller(tmp_path)
        ctrl.metrics()
        out = capsys.readouterr().out
        assert "見つかりません" in out or "❌" in out

    def test_shows_phase_metrics(self, tmp_path: Path, capsys):
        ctrl = _make_controller(tmp_path)
        metrics_data = {
            "phase1": [{"timestamp": "2026-01-01", "services_up": 3, "services": {}, "average_latency_ms": 120.5, "error_rate": 0.5, "health_check_pass_rate": 99.0}]
        }
        ctrl.metrics_file.write_text(json.dumps(metrics_data))
        ctrl.metrics()
        out = capsys.readouterr().out
        assert "PHASE1" in out


class TestSkipPhase:
    def test_valid_phase_writes_state(self, tmp_path: Path):
        ctrl = _make_controller(tmp_path)
        ctrl.skip_phase("phase2")
        state = json.loads(ctrl.state_file.read_text())
        assert state["current_phase"] == "phase2"

    def test_invalid_phase_prints_error(self, tmp_path: Path, capsys):
        ctrl = _make_controller(tmp_path)
        ctrl.skip_phase("phase99")
        out = capsys.readouterr().out
        assert "無効" in out or "❌" in out
        assert not ctrl.state_file.exists()

    def test_updates_existing_state(self, tmp_path: Path):
        ctrl = _make_controller(tmp_path)
        ctrl.state_file.write_text(json.dumps({"current_phase": "phase1"}))
        ctrl.skip_phase("phase3")
        state = json.loads(ctrl.state_file.read_text())
        assert state["current_phase"] == "phase3"


class TestRollback:
    def test_missing_state_file_prints_error(self, tmp_path: Path, capsys):
        ctrl = _make_controller(tmp_path)
        ctrl.rollback()
        out = capsys.readouterr().out
        assert "見つかりません" in out or "❌" in out

    def test_phase3_rolls_back_to_phase2(self, tmp_path: Path):
        ctrl = _make_controller(tmp_path)
        ctrl.state_file.write_text(json.dumps({"current_phase": "phase3"}))
        ctrl.rollback()
        state = json.loads(ctrl.state_file.read_text())
        assert state["current_phase"] == "phase2"

    def test_phase1_stays_at_phase1(self, tmp_path: Path):
        ctrl = _make_controller(tmp_path)
        ctrl.state_file.write_text(json.dumps({"current_phase": "phase1"}))
        ctrl.rollback()
        state = json.loads(ctrl.state_file.read_text())
        assert state["current_phase"] == "phase1"
