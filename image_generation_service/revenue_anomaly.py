"""
Revenue Anomaly Bridge — 収益データ × RLAnything 異常検知
===========================================================
revenue_tracker DB の日次収益データを AnomalyDetector で分析し、
収益急落・停滞・異常スパイクを検知する。

接続パス:
  revenue_tracker.py (DB) → revenue_anomaly.py → AnomalyDetector
  → router.py (/revenue/anomaly) → RevenueView.jsx

異常検知パターン:
  - Z-score: 1日の収益が過去平均から大きく逸脱
  - MA Crossover: 短期MA < 長期MA → 収益トレンド悪化
  - Consecutive Failures: 収益ゼロの日が続く
  - Plateau: 収益が長期間変化なし
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

_log = logging.getLogger("manaos.revenue_anomaly")

# 遅延ロード
_detector = None
_init_attempted = False


def _get_detector():
    """RLAnything AnomalyDetector の遅延取得"""
    global _detector, _init_attempted
    if _init_attempted:
        return _detector
    _init_attempted = True
    try:
        from rl_anything.anomaly_detector import AnomalyDetector
        _detector = AnomalyDetector({
            "anomaly_detection": {
                "z_threshold": 1.5,           # 収益は変動が大きいので緩め
                "short_ma_window": 3,          # 3日短期MA
                "long_ma_window": 7,           # 7日長期MA
                "ma_cross_threshold": 0.15,
                "sr_drop_threshold": 0.3,
                "consecutive_failure_limit": 3,  # 3日連続ゼロで警告
                "plateau_window": 7,
                "plateau_tolerance": 0.05,
            }
        })
        _log.info("Revenue AnomalyDetector initialized")
    except Exception as e:
        _log.warning("AnomalyDetector not available: %s", e)
        _detector = None
    return _detector


def analyze_revenue_anomalies(daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    日次収益データを AnomalyDetector で分析。

    Args:
        daily_data: [{date, revenue, cost, profit, products}, ...] (時系列順)

    Returns:
        {alerts: [...], stats: {...}, trend: {...}}
    """
    detector = _get_detector()
    if detector is None:
        return {"status": "unavailable", "alerts": [], "message": "AnomalyDetector not loaded"}

    if not daily_data:
        return {"status": "ok", "alerts": [], "message": "No data to analyze"}

    # AnomalyDetector は score + outcome のリストを期待
    history = []
    for d in daily_data:
        revenue = d.get("revenue", 0)
        cost = d.get("cost", 0)
        # 収益をスコアに正規化 (0-1 スケール、1万円 = 1.0)
        score = min(1.0, max(0.0, revenue / 10000.0))
        # 収益があれば success、なければ failure
        outcome = "success" if revenue > 0 else "failure"
        history.append({
            "date": d.get("date"),
            "score": score,
            "outcome": outcome,
            "cycle": len(history) + 1,
            "revenue": revenue,
            "cost": cost,
            "profit": d.get("profit", 0),
        })

    alerts = detector.check(history)

    # トレンド分析
    scores = [h["score"] for h in history]
    revenues = [h["revenue"] for h in history]
    trend = _compute_trend(revenues)

    return {
        "status": "ok",
        "alerts": [a.to_dict() for a in alerts],
        "alert_count": len(alerts),
        "trend": trend,
        "stats": detector.get_stats(),
        "data_points": len(history),
    }


def _compute_trend(revenues: List[float]) -> Dict[str, Any]:
    """収益トレンドを計算"""
    if len(revenues) < 2:
        return {"direction": "unknown", "change_pct": 0}

    # 直近7日 vs 前7日
    recent = revenues[-7:] if len(revenues) >= 7 else revenues
    previous = revenues[-14:-7] if len(revenues) >= 14 else revenues[:len(revenues)//2]

    avg_recent = sum(recent) / len(recent) if recent else 0
    avg_previous = sum(previous) / len(previous) if previous else 0

    if avg_previous > 0:
        change = (avg_recent - avg_previous) / avg_previous * 100
    elif avg_recent > 0:
        change = 100.0
    else:
        change = 0.0

    direction = "rising" if change > 5 else "falling" if change < -5 else "stable"

    return {
        "direction": direction,
        "change_pct": round(change, 1),
        "avg_recent_7d": round(avg_recent, 2),
        "avg_previous_7d": round(avg_previous, 2),
    }


def get_anomaly_summary() -> Dict[str, Any]:
    """既存アラート履歴のサマリ（直近チェック結果）"""
    detector = _get_detector()
    if detector is None:
        return {"status": "unavailable"}
    return {"status": "ok", **detector.get_stats()}
