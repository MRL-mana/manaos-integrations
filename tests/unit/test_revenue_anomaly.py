"""
Tests for revenue_anomaly.py — 収益 × AnomalyDetector ブリッジ
================================================================
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ── Module paths ──
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))


# ═══════════════════════════════════════════════
#  _compute_trend (pure function — detector 不要)
# ═══════════════════════════════════════════════
class TestComputeTrend:
    """_compute_trend の単体テスト"""

    def setup_method(self):
        # 毎テストで遅延ロード状態をリセット
        import image_generation_service.revenue_anomaly as mod
        mod._detector = None
        mod._init_attempted = False
        self.mod = mod

    def test_empty_list(self):
        result = self.mod._compute_trend([])
        assert result["direction"] == "unknown"
        assert result["change_pct"] == 0

    def test_single_value(self):
        result = self.mod._compute_trend([1000])
        assert result["direction"] == "unknown"

    def test_rising_trend(self):
        """前半低い→後半高い → rising"""
        data = [100] * 7 + [500] * 7
        result = self.mod._compute_trend(data)
        assert result["direction"] == "rising"
        assert result["change_pct"] > 5

    def test_falling_trend(self):
        """前半高い→後半低い → falling"""
        data = [500] * 7 + [100] * 7
        result = self.mod._compute_trend(data)
        assert result["direction"] == "falling"
        assert result["change_pct"] < -5

    def test_stable_trend(self):
        """全部同じ → stable"""
        data = [1000] * 14
        result = self.mod._compute_trend(data)
        assert result["direction"] == "stable"
        assert abs(result["change_pct"]) <= 5

    def test_zero_to_positive(self):
        """0→正 → change=100%"""
        data = [0] * 7 + [1000] * 7
        result = self.mod._compute_trend(data)
        assert result["change_pct"] == 100.0

    def test_all_zero(self):
        data = [0] * 14
        result = self.mod._compute_trend(data)
        assert result["direction"] == "stable"
        assert result["change_pct"] == 0

    def test_avg_fields_present(self):
        data = [200] * 7 + [400] * 7
        result = self.mod._compute_trend(data)
        assert "avg_recent_7d" in result
        assert "avg_previous_7d" in result
        assert result["avg_recent_7d"] == 400.0
        assert result["avg_previous_7d"] == 200.0


# ═══════════════════════════════════════════════
#  analyze_revenue_anomalies (detector モック)
# ═══════════════════════════════════════════════
class TestAnalyzeRevenueAnomalies:
    """analyze_revenue_anomalies のテスト"""

    def setup_method(self):
        import image_generation_service.revenue_anomaly as mod
        mod._detector = None
        mod._init_attempted = False
        self.mod = mod

    def test_unavailable_detector(self):
        """detector 読み込み失敗 → status=unavailable"""
        self.mod._init_attempted = True
        self.mod._detector = None
        result = self.mod.analyze_revenue_anomalies([{"revenue": 100, "cost": 10}])
        assert result["status"] == "unavailable"
        assert result["alerts"] == []

    def test_empty_data(self):
        """データなし → ok + empty alerts"""
        mock_detector = MagicMock()
        self.mod._init_attempted = True
        self.mod._detector = mock_detector
        result = self.mod.analyze_revenue_anomalies([])
        assert result["status"] == "ok"
        assert result["alerts"] == []
        mock_detector.check.assert_not_called()

    def test_normal_data_no_alerts(self):
        """正常データ → check 呼び出し + alerts 反映"""
        mock_detector = MagicMock()
        mock_detector.check.return_value = []  # アラートなし
        mock_detector.get_stats.return_value = {
            "total_alerts": 0, "by_type": {}, "by_severity": {}, "recent": [],
        }
        self.mod._init_attempted = True
        self.mod._detector = mock_detector

        daily_data = [
            {"date": f"2026-01-{d:02d}", "revenue": 5000, "cost": 50, "profit": 4950, "products": 5}
            for d in range(1, 15)
        ]

        result = self.mod.analyze_revenue_anomalies(daily_data)
        assert result["status"] == "ok"
        assert result["alert_count"] == 0
        assert result["alerts"] == []
        assert "trend" in result
        assert result["data_points"] == 14
        mock_detector.check.assert_called_once()

    def test_alert_returned(self):
        """detector がアラートを返す → to_dict で変換"""
        mock_alert = MagicMock()
        mock_alert.to_dict.return_value = {
            "alert_type": "score_drop",
            "severity": "warning",
            "message": "Revenue Z-score drop",
            "value": -2.5,
            "threshold": -1.5,
            "cycle": 10,
            "timestamp": "2026-01-15T00:00:00",
        }
        mock_detector = MagicMock()
        mock_detector.check.return_value = [mock_alert]
        mock_detector.get_stats.return_value = {
            "total_alerts": 1, "by_type": {"score_drop": 1},
            "by_severity": {"warning": 1}, "recent": [],
        }
        self.mod._init_attempted = True
        self.mod._detector = mock_detector

        daily_data = [
            {"date": f"2026-01-{d:02d}", "revenue": 5000 if d < 12 else 0, "cost": 50, "profit": 4950 if d < 12 else -50, "products": 5}
            for d in range(1, 15)
        ]

        result = self.mod.analyze_revenue_anomalies(daily_data)
        assert result["alert_count"] == 1
        assert result["alerts"][0]["alert_type"] == "score_drop"
        mock_alert.to_dict.assert_called_once()

    def test_score_normalization(self):
        """収益→スコア正規化: 10,000円=1.0, 超過はclamp"""
        mock_detector = MagicMock()
        mock_detector.check.return_value = []
        mock_detector.get_stats.return_value = {"total_alerts": 0, "by_type": {}, "by_severity": {}, "recent": []}
        self.mod._init_attempted = True
        self.mod._detector = mock_detector

        daily_data = [
            {"date": "2026-01-01", "revenue": 0, "cost": 0},
            {"date": "2026-01-02", "revenue": 5000, "cost": 50},
            {"date": "2026-01-03", "revenue": 10000, "cost": 100},
            {"date": "2026-01-04", "revenue": 20000, "cost": 200},
        ]

        self.mod.analyze_revenue_anomalies(daily_data)
        history_arg = mock_detector.check.call_args[0][0]
        assert history_arg[0]["score"] == 0.0     # 0 → 0.0
        assert history_arg[1]["score"] == 0.5     # 5000 → 0.5
        assert history_arg[2]["score"] == 1.0     # 10000 → 1.0
        assert history_arg[3]["score"] == 1.0     # 20000 → clamped to 1.0

    def test_outcome_mapping(self):
        """revenue>0 → success, revenue=0 → failure"""
        mock_detector = MagicMock()
        mock_detector.check.return_value = []
        mock_detector.get_stats.return_value = {"total_alerts": 0, "by_type": {}, "by_severity": {}, "recent": []}
        self.mod._init_attempted = True
        self.mod._detector = mock_detector

        daily_data = [
            {"date": "2026-01-01", "revenue": 0, "cost": 0},
            {"date": "2026-01-02", "revenue": 100, "cost": 10},
        ]

        self.mod.analyze_revenue_anomalies(daily_data)
        history_arg = mock_detector.check.call_args[0][0]
        assert history_arg[0]["outcome"] == "failure"
        assert history_arg[1]["outcome"] == "success"


# ═══════════════════════════════════════════════
#  get_anomaly_summary
# ═══════════════════════════════════════════════
class TestGetAnomalySummary:
    """get_anomaly_summary テスト"""

    def setup_method(self):
        import image_generation_service.revenue_anomaly as mod
        mod._detector = None
        mod._init_attempted = False
        self.mod = mod

    def test_unavailable(self):
        self.mod._init_attempted = True
        self.mod._detector = None
        result = self.mod.get_anomaly_summary()
        assert result["status"] == "unavailable"

    def test_with_detector(self):
        mock_detector = MagicMock()
        mock_detector.get_stats.return_value = {
            "total_alerts": 3,
            "by_type": {"score_drop": 2, "plateau": 1},
            "by_severity": {"warning": 2, "info": 1},
            "recent": [],
        }
        self.mod._init_attempted = True
        self.mod._detector = mock_detector
        result = self.mod.get_anomaly_summary()
        assert result["status"] == "ok"
        assert result["total_alerts"] == 3
        mock_detector.get_stats.assert_called_once()


# ═══════════════════════════════════════════════
#  _get_detector 遅延ロード
# ═══════════════════════════════════════════════
class TestLazyDetector:
    """_get_detector の遅延ロード挙動"""

    def setup_method(self):
        import image_generation_service.revenue_anomaly as mod
        mod._detector = None
        mod._init_attempted = False
        self.mod = mod

    def test_init_once_only(self):
        """_init_attempted=True なら再ロードしない"""
        self.mod._init_attempted = True
        self.mod._detector = "sentinel"
        result = self.mod._get_detector()
        assert result == "sentinel"

    def test_graceful_degrade_on_import_error(self):
        """AnomalyDetector import 失敗 → None, _init_attempted=True"""
        self.mod._init_attempted = False
        with patch.dict(sys.modules, {"rl_anything.anomaly_detector": None}):
            # None in sys.modules → ImportError
            result = self.mod._get_detector()
        assert result is None
        assert self.mod._init_attempted is True
