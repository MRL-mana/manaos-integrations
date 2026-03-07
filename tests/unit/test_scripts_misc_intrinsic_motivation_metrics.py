"""
Unit tests for scripts/misc/intrinsic_motivation_metrics.py
"""
import sys
import types
from unittest.mock import MagicMock
from datetime import date, timedelta
from pathlib import Path

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

sys.modules.setdefault("httpx", MagicMock())

# Flask mocks
_flask = types.ModuleType("flask")
_flask.Flask = MagicMock(return_value=MagicMock())
_flask.jsonify = MagicMock(return_value=MagicMock())
sys.modules.setdefault("flask", _flask)

_flask_cors = types.ModuleType("flask_cors")
_flask_cors.CORS = MagicMock()
sys.modules.setdefault("flask_cors", _flask_cors)

import pytest
from scripts.misc.intrinsic_motivation_metrics import (
    MotivationMetrics,
    IntrinsicMotivationMetrics,
)


# ── Helpers ───────────────────────────────────────────────────────────────
def make_imm(tmp_path):
    return IntrinsicMotivationMetrics(
        storage_path=tmp_path / "metrics.json"
    )


def make_metric(d=None, score=60.0, exec_rate=0.5,
                generated=5, executed=3, playbooks=2, learning=4):
    if d is None:
        d = date.today().isoformat()
    return MotivationMetrics(
        date=d,
        improvement_desire_score=score,
        self_improvement_execution_rate=exec_rate,
        tasks_generated=generated,
        tasks_executed=executed,
        playbooks_created=playbooks,
        learning_actions=learning,
    )


# ── MotivationMetrics dataclass ───────────────────────────────────────────
class TestMotivationMetrics:
    def test_create(self):
        m = make_metric()
        assert m.improvement_desire_score == 60.0
        assert m.self_improvement_execution_rate == 0.5

    def test_fields(self):
        m = make_metric()
        assert m.tasks_generated == 5
        assert m.tasks_executed == 3
        assert m.playbooks_created == 2
        assert m.learning_actions == 4


# ── IntrinsicMotivationMetrics init ──────────────────────────────────────
class TestInit:
    def test_metrics_history_empty(self, tmp_path):
        imm = make_imm(tmp_path)
        assert imm.metrics_history == []

    def test_storage_path_set(self, tmp_path):
        imm = make_imm(tmp_path)
        assert imm.storage_path == tmp_path / "metrics.json"

    def test_urls_set(self, tmp_path):
        imm = make_imm(tmp_path)
        assert "127.0.0.1" in imm.intrinsic_motivation_url
        assert "127.0.0.1" in imm.learning_system_url


# ── _save_metrics / _load_metrics ─────────────────────────────────────────
class TestSaveLoadMetrics:
    def test_save_and_load_roundtrip(self, tmp_path):
        imm = make_imm(tmp_path)
        imm.metrics_history = [make_metric()]
        imm._save_metrics()

        imm2 = make_imm(tmp_path)
        assert len(imm2.metrics_history) == 1

    def test_load_when_no_file_empty(self, tmp_path):
        imm = make_imm(tmp_path)
        assert imm.metrics_history == []

    def test_saved_values_preserved(self, tmp_path):
        imm = make_imm(tmp_path)
        m = make_metric(score=88.0)
        imm.metrics_history = [m]
        imm._save_metrics()

        imm2 = make_imm(tmp_path)
        assert imm2.metrics_history[0].improvement_desire_score == 88.0


# ── calculate_execution_rate ─────────────────────────────────────────────
class TestCalculateExecutionRate:
    def test_empty_history_returns_zero(self, tmp_path):
        imm = make_imm(tmp_path)
        assert imm.calculate_execution_rate() == 0.0

    def test_basic_rate(self, tmp_path):
        imm = make_imm(tmp_path)
        imm.metrics_history = [
            make_metric(generated=10, executed=5),
        ]
        assert imm.calculate_execution_rate() == pytest.approx(0.5)

    def test_zero_generated_returns_zero(self, tmp_path):
        imm = make_imm(tmp_path)
        imm.metrics_history = [make_metric(generated=0, executed=0)]
        assert imm.calculate_execution_rate() == 0.0

    def test_excludes_old_data(self, tmp_path):
        imm = make_imm(tmp_path)
        old_date = (date.today() - timedelta(days=30)).isoformat()
        imm.metrics_history = [make_metric(d=old_date, generated=10, executed=10)]
        assert imm.calculate_execution_rate() == 0.0

    def test_sums_multiple_days(self, tmp_path):
        imm = make_imm(tmp_path)
        d1 = date.today().isoformat()
        d2 = (date.today() - timedelta(days=2)).isoformat()
        imm.metrics_history = [
            make_metric(d=d1, generated=4, executed=2),
            make_metric(d=d2, generated=6, executed=3),
        ]
        # (2+3)/(4+6) = 0.5
        assert imm.calculate_execution_rate() == pytest.approx(0.5)


# ── get_weekly_trend ──────────────────────────────────────────────────────
class TestGetWeeklyTrend:
    def test_empty_history(self, tmp_path):
        imm = make_imm(tmp_path)
        result = imm.get_weekly_trend()
        assert result["trend"] == []
        assert result["average_score"] == 0.0

    def test_returns_trend_list(self, tmp_path):
        imm = make_imm(tmp_path)
        imm.metrics_history = [make_metric(score=70.0)]
        result = imm.get_weekly_trend()
        assert len(result["trend"]) == 1

    def test_trend_entry_keys(self, tmp_path):
        imm = make_imm(tmp_path)
        imm.metrics_history = [make_metric()]
        trend = imm.get_weekly_trend()["trend"][0]
        for key in ("date", "improvement_desire_score", "execution_rate",
                    "tasks_generated", "tasks_executed"):
            assert key in trend

    def test_average_score(self, tmp_path):
        imm = make_imm(tmp_path)
        d1 = date.today().isoformat()
        d2 = (date.today() - timedelta(days=1)).isoformat()
        imm.metrics_history = [
            make_metric(d=d1, score=80.0),
            make_metric(d=d2, score=60.0),
        ]
        result = imm.get_weekly_trend()
        assert result["average_score"] == pytest.approx(70.0)

    def test_excludes_old_data(self, tmp_path):
        imm = make_imm(tmp_path)
        old_date = (date.today() - timedelta(days=30)).isoformat()
        imm.metrics_history = [make_metric(d=old_date, score=99.0)]
        result = imm.get_weekly_trend()
        assert result["trend"] == []

    def test_total_tasks(self, tmp_path):
        imm = make_imm(tmp_path)
        d1 = date.today().isoformat()
        d2 = (date.today() - timedelta(days=1)).isoformat()
        imm.metrics_history = [
            make_metric(d=d1, generated=5, executed=3),
            make_metric(d=d2, generated=4, executed=2),
        ]
        result = imm.get_weekly_trend()
        assert result["total_tasks_generated"] == 9
        assert result["total_tasks_executed"] == 5


# ── _count_playbooks ──────────────────────────────────────────────────────
class TestCountPlaybooks:
    def test_returns_zero_when_no_vault(self, tmp_path):
        imm = make_imm(tmp_path)
        # No vault directory → returns 0
        result = imm._count_playbooks()
        assert result == 0

    def test_counts_md_files(self, tmp_path):
        imm = make_imm(tmp_path)
        # Create a fake playbook directory structure matching real path
        playbooks_dir = (
            tmp_path / "Documents" / "Obsidian Vault" / "ManaOS" / "System" / "Playbooks"
        )
        playbooks_dir.mkdir(parents=True)
        (playbooks_dir / "pb1.md").write_text("# Playbook 1")
        (playbooks_dir / "pb2.md").write_text("# Playbook 2")

        from unittest.mock import patch
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            result = imm._count_playbooks()
        assert result == 2
