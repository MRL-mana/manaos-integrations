"""
Unit tests for scripts/misc/reward_loop.py
"""
import sys
import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_oi = MagicMock()
_oi.ObsidianIntegration = MagicMock(return_value=MagicMock())
sys.modules.setdefault("obsidian_integration", _oi)

_paths = MagicMock()
_paths.LEARNING_SYSTEM_PORT = 8080
_paths.METRICS_COLLECTOR_PORT = 8081
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.reward_loop import RewardEvent, RewardLoop


@pytest.fixture
def rl(tmp_path):
    storage = tmp_path / "reward_loop.json"
    return RewardLoop(storage_path=storage)


# ── TestRewardEvent ───────────────────────────────────────────────────────
class TestRewardEvent:
    def test_fields_stored(self):
        ev = RewardEvent(
            event_id="ev001",
            event_type="playbook_promoted",
            message="テスト",
            achievement_level="bronze",
        )
        assert ev.event_id == "ev001"
        assert ev.event_type == "playbook_promoted"
        assert ev.achievement_level == "bronze"

    def test_timestamp_auto_set(self):
        ev = RewardEvent(
            event_id="ev002",
            event_type="milestone_reached",
            message="m",
            achievement_level="silver",
        )
        assert ev.timestamp  # 空でない

    def test_explicit_timestamp(self):
        ev = RewardEvent(
            event_id="ev003",
            event_type="t",
            message="m",
            achievement_level="gold",
            timestamp="2026-01-01T00:00:00",
        )
        assert ev.timestamp == "2026-01-01T00:00:00"


# ── TestRewardLoopInit ────────────────────────────────────────────────────
class TestRewardLoopInit:
    def test_empty_history_on_new(self, rl):
        assert rl.reward_history == []
        assert rl.playbook_count_history == []
        assert rl.last_reward_date is None

    def test_loads_existing_data(self, tmp_path):
        storage = tmp_path / "rl_existing.json"
        ev = RewardEvent("e1", "t", "msg", "bronze")
        data = {
            "rewards": [{"event_id": "e1", "event_type": "t", "message": "msg",
                          "achievement_level": "bronze", "timestamp": "2026-01-01"}],
            "playbook_history": [{"date": "2026-01-01", "count": 3}],
            "last_reward_date": "2026-01-01",
        }
        storage.write_text(json.dumps(data), encoding="utf-8")
        rl2 = RewardLoop(storage_path=storage)
        assert len(rl2.reward_history) == 1
        assert rl2.reward_history[0].event_id == "e1"
        assert rl2.last_reward_date == "2026-01-01"

    def test_thresholds_defined(self):
        assert RewardLoop.BRONZE_THRESHOLD == 1
        assert RewardLoop.SILVER_THRESHOLD == 5
        assert RewardLoop.GOLD_THRESHOLD == 10
        assert RewardLoop.PLATINUM_THRESHOLD == 20


# ── TestSaveData ──────────────────────────────────────────────────────────
class TestSaveData:
    def test_save_creates_file(self, rl):
        ev = RewardEvent("sv1", "playbook_promoted", "msg", "bronze")
        rl.reward_history.append(ev)
        rl._save_data()
        assert rl.storage_path.exists()

    def test_save_load_roundtrip(self, rl):
        ev = RewardEvent("rt1", "playbook_promoted", "roundtrip", "silver")
        rl.reward_history.append(ev)
        rl.last_reward_date = "2026-06-01"
        rl._save_data()

        rl2 = RewardLoop(storage_path=rl.storage_path)
        assert len(rl2.reward_history) == 1
        assert rl2.reward_history[0].message == "roundtrip"
        assert rl2.last_reward_date == "2026-06-01"


# ── TestCheckAchievements ─────────────────────────────────────────────────
class TestCheckAchievements:
    def test_rate_limit_returns_none_same_day(self, rl):
        today = date.today().isoformat()
        rl.last_reward_date = today
        result = rl.check_achievements()
        assert result is None

    def test_no_playbooks_returns_none(self, rl):
        # _count_playbooks returns 0 (vault does not exist in CI)
        # previous_count also 0 → increase==0 → None
        with patch.object(rl, "_count_playbooks", return_value=0):
            result = rl.check_achievements()
        assert result is None

    def test_bronze_achievement(self, rl):
        # previous=0, current=1 → bronze
        with patch.object(rl, "_count_playbooks", return_value=1):
            result = rl.check_achievements()
        assert result is not None
        assert result.achievement_level == "bronze"

    def test_silver_achievement(self, rl):
        # previous=0, current=5 → silver
        with patch.object(rl, "_count_playbooks", return_value=5):
            result = rl.check_achievements()
        assert result is not None
        assert result.achievement_level == "silver"

    def test_gold_achievement(self, rl):
        with patch.object(rl, "_count_playbooks", return_value=10):
            result = rl.check_achievements()
        assert result is not None
        assert result.achievement_level == "gold"

    def test_platinum_achievement(self, rl):
        with patch.object(rl, "_count_playbooks", return_value=20):
            result = rl.check_achievements()
        assert result is not None
        assert result.achievement_level == "platinum"

    def test_growth_achievement(self, rl):
        # previous=6, current=9 → increase=3>0 → growth
        rl.playbook_count_history = [
            {"date": (date.today()).isoformat(), "count": 6}
        ]
        with patch.object(rl, "_count_playbooks", return_value=9):
            result = rl.check_achievements()
        assert result is not None
        assert result.achievement_level == "growth"

    def test_event_stored_in_history(self, rl):
        with patch.object(rl, "_count_playbooks", return_value=1):
            result = rl.check_achievements()
        assert len(rl.reward_history) == 1
        assert rl.last_reward_date == date.today().isoformat()
