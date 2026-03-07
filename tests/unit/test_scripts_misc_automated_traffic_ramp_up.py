"""
Unit tests for scripts/misc/automated_traffic_ramp_up.py
"""
import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# httpx は実際にインストール済み、そのまま使える
# logging は標準ライブラリ – モック不要

from scripts.misc.automated_traffic_ramp_up import (
    TrafficRampUpSystem,
    SERVICES,
    PHASES,
)


# ── helpers ────────────────────────────────────────────────────────────────
def _make_system(tmp_path):
    """CWD を tmp_path にして TrafficRampUpSystem を作成する。"""
    import os
    orig = os.getcwd()
    os.chdir(tmp_path)
    sys_obj = TrafficRampUpSystem()
    os.chdir(orig)
    return sys_obj, tmp_path


# ── TestConstants ──────────────────────────────────────────────────────────
class TestConstants:
    def test_services_contains_known_keys(self):
        assert "mrl_memory" in SERVICES
        assert "ollama" in SERVICES
        assert all(s.startswith("http") for s in SERVICES.values())

    def test_phases_has_three_phases(self):
        assert set(PHASES.keys()) == {"phase1", "phase2", "phase3"}

    def test_phase3_has_no_duration(self):
        assert PHASES["phase3"]["duration_minutes"] is None

    def test_phases_traffic_percentages_increasing(self):
        p1 = PHASES["phase1"]["traffic_percentage"]
        p2 = PHASES["phase2"]["traffic_percentage"]
        p3 = PHASES["phase3"]["traffic_percentage"]
        assert p1 < p2 < p3


# ── TestTrafficRampUpSystemInit ────────────────────────────────────────────
class TestTrafficRampUpSystemInit:
    def test_default_phase_is_phase1(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        assert sys_obj.current_phase == "phase1"

    def test_metrics_keys_match_phases(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        assert set(sys_obj.metrics.keys()) == {"phase1", "phase2", "phase3"}

    def test_load_state_restores_phase(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state_file = tmp_path / "traffic_rampup_state.json"
        state_file.write_text(json.dumps({
            "current_phase": "phase2",
            "start_time": datetime.utcnow().isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }))
        sys_obj = TrafficRampUpSystem()
        assert sys_obj.current_phase == "phase2"

    def test_load_state_handles_corrupt_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "traffic_rampup_state.json").write_text("not-json!!!")
        sys_obj = TrafficRampUpSystem()
        assert sys_obj.current_phase == "phase1"  # defaults


# ── TestSaveState ──────────────────────────────────────────────────────────
class TestSaveState:
    def test_save_creates_state_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.save_state()
        state_file = tmp_path / "traffic_rampup_state.json"
        assert state_file.exists()

    def test_save_contains_current_phase(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.current_phase = "phase2"
        sys_obj.save_state()
        data = json.loads((tmp_path / "traffic_rampup_state.json").read_text())
        assert data["current_phase"] == "phase2"


# ── TestCheckServiceHealth ─────────────────────────────────────────────────
class TestCheckServiceHealth:
    @pytest.mark.asyncio
    async def test_returns_up_on_200(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()

        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scripts.misc.automated_traffic_ramp_up.httpx.AsyncClient",
                   return_value=mock_client):
            result = await sys_obj.check_service_health()

        assert all(v["status"] == "UP" for v in result.values())

    @pytest.mark.asyncio
    async def test_returns_down_on_exception(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("scripts.misc.automated_traffic_ramp_up.httpx.AsyncClient",
                   return_value=mock_client):
            result = await sys_obj.check_service_health()

        assert all(v["status"] == "DOWN" for v in result.values())


# ── TestEvaluatePhaseMetrics ───────────────────────────────────────────────
class TestEvaluatePhaseMetrics:
    @pytest.mark.asyncio
    async def test_all_up_gives_100_pass_rate(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        health = {name: {"status": "UP", "code": 200, "latency_ms": 10.0}
                  for name in SERVICES}

        with patch.object(sys_obj, "check_service_health", AsyncMock(return_value=health)):
            metrics = await sys_obj.evaluate_phase_metrics()

        assert metrics["health_check_pass_rate"] == 100.0
        assert metrics["error_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_all_down_gives_0_pass_rate(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        health = {name: {"status": "DOWN", "latency_ms": 9999.0}
                  for name in SERVICES}

        with patch.object(sys_obj, "check_service_health", AsyncMock(return_value=health)):
            metrics = await sys_obj.evaluate_phase_metrics()

        assert metrics["health_check_pass_rate"] == 0.0
        assert metrics["error_rate"] == 100.0


# ── TestShouldEscalatePhase ────────────────────────────────────────────────
class TestShouldEscalatePhase:
    @pytest.mark.asyncio
    async def test_phase3_never_escalates(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.current_phase = "phase3"
        result = await sys_obj.should_escalate_phase()
        assert result is False

    @pytest.mark.asyncio
    async def test_phase1_escalates_after_duration(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.current_phase = "phase1"
        # phase start is utcnow - 5 min, duration is 30 min
        # so phase_end > utcnow → should NOT escalate yet
        result = await sys_obj.should_escalate_phase()
        # with 5-min window the simplified logic: utcnow >= phase_start + 30min?
        # phase_start = utcnow - 5min; phase_end = phase_start + 30min = utcnow + 25min
        assert result is False


# ── TestTransitionPhase ────────────────────────────────────────────────────
class TestTransitionPhase:
    @pytest.mark.asyncio
    async def test_phase1_transitions_to_phase2(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.current_phase = "phase1"
        await sys_obj.transition_phase()
        assert sys_obj.current_phase == "phase2"

    @pytest.mark.asyncio
    async def test_phase2_transitions_to_phase3(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.current_phase = "phase2"
        await sys_obj.transition_phase()
        assert sys_obj.current_phase == "phase3"

    @pytest.mark.asyncio
    async def test_phase3_stays_phase3(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.current_phase = "phase3"
        await sys_obj.transition_phase()
        assert sys_obj.current_phase == "phase3"


# ── TestSaveMetrics ────────────────────────────────────────────────────────
class TestSaveMetrics:
    def test_creates_metrics_dir_and_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.save_metrics()
        metrics_file = tmp_path / "metrics" / "traffic_rampup_metrics.json"
        assert metrics_file.exists()

    def test_saved_metrics_is_valid_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        sys_obj.save_metrics()
        data = json.loads((tmp_path / "metrics" / "traffic_rampup_metrics.json").read_text())
        assert "phase1" in data


# ── TestGracefulShutdown ───────────────────────────────────────────────────
class TestGracefulShutdown:
    @pytest.mark.asyncio
    async def test_graceful_shutdown_saves_state(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sys_obj = TrafficRampUpSystem()
        await sys_obj.graceful_shutdown()
        assert (tmp_path / "traffic_rampup_state.json").exists()
        assert (tmp_path / "metrics" / "traffic_rampup_metrics.json").exists()
