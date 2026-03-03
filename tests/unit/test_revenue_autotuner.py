"""
Tests for revenue_autotuner.py — 収益駆動パラメータ自動調整
================================================================
compute_tune_strategy, auto_tune, apply_tune_to_orchestrator,
TuneAction/TuneReport データクラスの全戦略パターンをテスト。
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from image_generation_service.revenue_autotuner import (
    TuneAction,
    TuneReport,
    auto_tune,
    apply_tune_to_orchestrator,
    compute_tune_strategy,
    _clamp,
    _estimate_post_tune_health,
)


# ═══════════════════════════════════════════════
#  _clamp
# ═══════════════════════════════════════════════
class TestClamp:
    def test_within_range(self):
        assert _clamp(0.5, 0.0, 1.0) == 0.5

    def test_below_min(self):
        assert _clamp(-1.0, 0.0, 1.0) == 0.0

    def test_above_max(self):
        assert _clamp(2.0, 0.0, 1.0) == 1.0

    def test_exact_min(self):
        assert _clamp(0.0, 0.0, 1.0) == 0.0

    def test_exact_max(self):
        assert _clamp(1.0, 0.0, 1.0) == 1.0


# ═══════════════════════════════════════════════
#  compute_tune_strategy — 全5戦略
# ═══════════════════════════════════════════════
class TestComputeTuneStrategy:
    """5 戦略の分岐を網羅テスト"""

    def test_stabilize_on_spike(self):
        """高アラート + 上昇 → stabilize"""
        trend = {"direction": "rising", "change_pct": 15.0}
        alerts = [{"type": "spike"}, {"type": "anomaly"}, {"type": "drift"}]
        assert compute_tune_strategy(trend, alerts, 50.0) == "stabilize"

    def test_explore_on_falling(self):
        """下降トレンド → explore"""
        trend = {"direction": "falling", "change_pct": -20.0}
        assert compute_tune_strategy(trend, [], 50.0) == "explore"

    def test_explore_on_negative_change(self):
        """direction unknown だが change_pct が負 → explore"""
        trend = {"direction": "unknown", "change_pct": -15.0}
        assert compute_tune_strategy(trend, [], 50.0) == "explore"

    def test_plateau_break_with_alerts(self):
        """微変化 + アラートあり → plateau_break"""
        trend = {"direction": "stable", "change_pct": 0.5}
        alerts = [{"type": "concern"}]
        assert compute_tune_strategy(trend, alerts, 50.0) == "plateau_break"

    def test_plateau_break_with_low_health(self):
        """微変化 + 低ヘルス → plateau_break"""
        trend = {"direction": "stable", "change_pct": 1.0}
        assert compute_tune_strategy(trend, [], 20.0) == "plateau_break"

    def test_exploit_on_rising(self):
        """上昇トレンド → exploit"""
        trend = {"direction": "rising", "change_pct": 12.0}
        assert compute_tune_strategy(trend, [], 70.0) == "exploit"

    def test_maintain_default(self):
        """変化なし + 正常 → maintain"""
        trend = {"direction": "stable", "change_pct": 5.0}
        assert compute_tune_strategy(trend, [], 80.0) == "maintain"

    def test_stabilize_takes_priority(self):
        """stabilize はアラート数3+ && 上昇 → exploit より優先"""
        trend = {"direction": "rising", "change_pct": 20.0}
        alerts = [{"a": 1}, {"b": 2}, {"c": 3}]
        assert compute_tune_strategy(trend, alerts, 90.0) == "stabilize"


# ═══════════════════════════════════════════════
#  auto_tune — 戦略別アクション生成
# ═══════════════════════════════════════════════
class TestAutoTune:
    _default_params = {
        "learning_rate": 0.01,
        "temperature": 1.0,
        "anomaly_z_threshold": 2.0,
        "curriculum_up_threshold": 0.75,
        "curriculum_down_threshold": 0.30,
    }

    def test_explore_increases_lr_and_temp(self):
        trend = {"direction": "falling", "change_pct": -20.0}
        report = auto_tune(trend, [], 30.0, self._default_params)
        assert report.strategy == "explore"
        assert len(report.actions) >= 2
        lr_action = next(a for a in report.actions if a.param == "learning_rate")
        temp_action = next(a for a in report.actions if a.param == "temperature")
        assert lr_action.new_value > lr_action.old_value
        assert temp_action.new_value > temp_action.old_value

    def test_exploit_decreases_lr_and_temp(self):
        trend = {"direction": "rising", "change_pct": 15.0}
        report = auto_tune(trend, [], 70.0, self._default_params)
        assert report.strategy == "exploit"
        assert len(report.actions) >= 2
        lr_action = next(a for a in report.actions if a.param == "learning_rate")
        temp_action = next(a for a in report.actions if a.param == "temperature")
        assert lr_action.new_value < lr_action.old_value
        assert temp_action.new_value < temp_action.old_value

    def test_plateau_break_aggressive(self):
        trend = {"direction": "stable", "change_pct": 0.5}
        alerts = [{"type": "concern"}]
        report = auto_tune(trend, alerts, 25.0, self._default_params)
        assert report.strategy == "plateau_break"
        assert len(report.actions) >= 3  # lr, temp, z_threshold
        z_action = next(a for a in report.actions if a.param == "anomaly_z_threshold")
        assert z_action.new_value < z_action.old_value  # 感度UP = 閾値DOWN

    def test_stabilize_decreases_all(self):
        trend = {"direction": "rising", "change_pct": 15.0}
        alerts = [{"a": 1}, {"b": 2}, {"c": 3}]
        report = auto_tune(trend, alerts, 50.0, self._default_params)
        assert report.strategy == "stabilize"
        lr_action = next(a for a in report.actions if a.param == "learning_rate")
        assert lr_action.new_value < lr_action.old_value
        z_action = next(a for a in report.actions if a.param == "anomaly_z_threshold")
        assert z_action.new_value > z_action.old_value  # Z閾値UP = 感度DOWN (安定化)

    def test_maintain_no_actions(self):
        trend = {"direction": "stable", "change_pct": 5.0}
        report = auto_tune(trend, [], 80.0, self._default_params)
        assert report.strategy == "maintain"
        assert len(report.actions) == 0

    def test_no_params_defaults(self):
        """current_rl_params=None でもクラッシュしない"""
        trend = {"direction": "falling", "change_pct": -15.0}
        report = auto_tune(trend, [], 30.0, None)
        assert report.strategy == "explore"
        assert len(report.actions) >= 1

    def test_report_has_timestamp(self):
        trend = {"direction": "stable", "change_pct": 5.0}
        report = auto_tune(trend, [], 80.0, self._default_params)
        assert report.timestamp  # non-empty

    def test_report_revenue_signal(self):
        trend = {"direction": "falling", "change_pct": -20.0}
        report = auto_tune(trend, [{"type": "spike"}], 30.0, self._default_params)
        assert report.revenue_signal["direction"] == "falling"
        assert report.revenue_signal["change_pct"] == -20.0
        assert report.revenue_signal["anomaly_count"] == 1

    def test_clamp_respects_lr_range(self):
        """学習率が上限を超えない"""
        params = {**self._default_params, "learning_rate": 0.099}
        trend = {"direction": "falling", "change_pct": -20.0}
        report = auto_tune(trend, [], 30.0, params)
        lr_action = next(a for a in report.actions if a.param == "learning_rate")
        assert lr_action.new_value <= 0.1

    def test_clamp_respects_temp_range(self):
        """温度が下限を下回らない"""
        params = {**self._default_params, "temperature": 0.31}
        trend = {"direction": "rising", "change_pct": 15.0}
        report = auto_tune(trend, [], 70.0, params)
        temp_action = next(a for a in report.actions if a.param == "temperature")
        assert temp_action.new_value >= 0.3


# ═══════════════════════════════════════════════
#  TuneAction / TuneReport — to_dict()
# ═══════════════════════════════════════════════
class TestDataclasses:
    def test_tune_action_to_dict(self):
        action = TuneAction(
            param="learning_rate",
            old_value=0.01,
            new_value=0.013,
            reason="test",
            strategy="explore",
            confidence=0.7,
        )
        d = action.to_dict()
        assert d["param"] == "learning_rate"
        assert d["old_value"] == 0.01
        assert d["new_value"] == 0.013
        assert d["confidence"] == 0.7

    def test_tune_report_to_dict(self):
        report = TuneReport(
            strategy="explore",
            actions=[
                TuneAction("lr", 0.01, 0.013, "r", "explore", 0.7),
            ],
            revenue_signal={"direction": "falling"},
            rl_signal={"lr": 0.01},
            health_score=45.0,
        )
        d = report.to_dict()
        assert d["strategy"] == "explore"
        assert d["action_count"] == 1
        assert d["health_score"] == 45.0
        assert len(d["actions"]) == 1

    def test_empty_report_to_dict(self):
        report = TuneReport(
            strategy="maintain",
            actions=[],
            revenue_signal={},
            rl_signal={},
            health_score=80.0,
        )
        d = report.to_dict()
        assert d["action_count"] == 0
        assert d["actions"] == []


# ═══════════════════════════════════════════════
#  _estimate_post_tune_health
# ═══════════════════════════════════════════════
class TestEstimateHealth:
    def test_maintain_returns_same(self):
        assert _estimate_post_tune_health(50.0, "maintain", 3) == 50.0

    def test_explore_boost(self):
        # explore: 3.0 per action, 2 actions → +6
        result = _estimate_post_tune_health(40.0, "explore", 2)
        assert result == 46.0

    def test_exploit_boost(self):
        # exploit: 2.0 per action, 2 actions → +4
        result = _estimate_post_tune_health(60.0, "exploit", 2)
        assert result == 64.0

    def test_plateau_break_boost(self):
        # plateau_break: 5.0 per action, 3 actions → +15
        result = _estimate_post_tune_health(30.0, "plateau_break", 3)
        assert result == 45.0

    def test_stabilize_boost(self):
        # stabilize: 4.0 per action, 3 actions → +12
        result = _estimate_post_tune_health(50.0, "stabilize", 3)
        assert result == 62.0

    def test_capped_at_100(self):
        result = _estimate_post_tune_health(95.0, "plateau_break", 5)
        assert result == 100.0


# ═══════════════════════════════════════════════
#  apply_tune_to_orchestrator — Mock テスト
# ═══════════════════════════════════════════════
class TestApplyTune:
    def _make_report(self, actions):
        return TuneReport(
            strategy="explore",
            actions=actions,
            revenue_signal={},
            rl_signal={},
            health_score=50.0,
        )

    def test_apply_lr_and_temp(self):
        mock_rl = MagicMock()
        mock_rl.policy_gradient = MagicMock(lr=0.01, temperature=1.0)
        mock_rl.anomaly_detector = MagicMock(z_threshold=2.0)
        mock_rl.curriculum = MagicMock(up_threshold=0.75, down_threshold=0.30)

        report = self._make_report([
            TuneAction("learning_rate", 0.01, 0.013, "test", "explore", 0.7),
            TuneAction("temperature", 1.0, 1.15, "test", "explore", 0.65),
        ])

        with patch(
            "image_generation_service.rl_bridge._get_orchestrator",
            return_value=mock_rl,
        ):
            result = apply_tune_to_orchestrator(report)

        assert result["applied"] == 2
        assert result["skipped"] == 0
        assert mock_rl.policy_gradient.lr == 0.013
        assert mock_rl.policy_gradient.temperature == 1.15

    def test_apply_z_threshold(self):
        mock_rl = MagicMock()
        mock_rl.policy_gradient = MagicMock(lr=0.01, temperature=1.0)
        mock_rl.anomaly_detector = MagicMock(z_threshold=2.0)

        report = self._make_report([
            TuneAction("anomaly_z_threshold", 2.0, 1.75, "test", "plateau_break", 0.6),
        ])

        with patch(
            "image_generation_service.rl_bridge._get_orchestrator",
            return_value=mock_rl,
        ):
            result = apply_tune_to_orchestrator(report)

        assert result["applied"] == 1
        assert mock_rl.anomaly_detector.z_threshold == 1.75

    def test_apply_curriculum_thresholds(self):
        mock_rl = MagicMock()
        mock_rl.policy_gradient = MagicMock()
        mock_rl.curriculum = MagicMock(up_threshold=0.75, down_threshold=0.30)
        mock_rl.anomaly_detector = MagicMock()

        report = self._make_report([
            TuneAction("curriculum_up_threshold", 0.75, 0.80, "test", "explore", 0.5),
            TuneAction("curriculum_down_threshold", 0.30, 0.25, "test", "explore", 0.5),
        ])

        with patch(
            "image_generation_service.rl_bridge._get_orchestrator",
            return_value=mock_rl,
        ):
            result = apply_tune_to_orchestrator(report)

        assert result["applied"] == 2
        assert mock_rl.curriculum.up_threshold == 0.80
        assert mock_rl.curriculum.down_threshold == 0.25

    def test_unknown_param_skipped(self):
        mock_rl = MagicMock()
        mock_rl.policy_gradient = MagicMock()
        mock_rl.anomaly_detector = MagicMock()

        report = self._make_report([
            TuneAction("nonexistent_param", 0.5, 0.6, "test", "explore", 0.5),
        ])

        with patch(
            "image_generation_service.rl_bridge._get_orchestrator",
            return_value=mock_rl,
        ):
            result = apply_tune_to_orchestrator(report)

        assert result["applied"] == 0
        assert result["skipped"] == 1

    def test_orchestrator_unavailable(self):
        report = self._make_report([
            TuneAction("learning_rate", 0.01, 0.013, "test", "explore", 0.7),
        ])

        with patch(
            "image_generation_service.rl_bridge._get_orchestrator",
            return_value=None,
        ):
            result = apply_tune_to_orchestrator(report)

        assert result["applied"] == 0
        assert result["skipped"] == 1
        assert "error" in result

    def test_empty_actions(self):
        mock_rl = MagicMock()
        report = self._make_report([])

        with patch(
            "image_generation_service.rl_bridge._get_orchestrator",
            return_value=mock_rl,
        ):
            result = apply_tune_to_orchestrator(report)

        assert result["applied"] == 0
        assert result["skipped"] == 0
