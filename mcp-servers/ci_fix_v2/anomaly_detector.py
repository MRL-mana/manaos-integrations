"""
Anomaly Detector — パフォーマンス異常検知 & アラートシステム
================================================================
スコア・成功率の急激な変動、パフォーマンス劣化、長期的なドリフトを
リアルタイムで検知し、イベント/アラートを発火する。

検知手法:
  1) Z-score: 直近スコアが移動平均から何 σ 外れているか
  2) Moving Average Crossover: 短期 MA vs 長期 MA の交差
  3) Success Rate Drop: ウィンドウ成功率の急落
  4) Consecutive Failures: 連続失敗の検出
  5) Score Plateau: スコアが長期間変化しない停滞

使い方:
  detector = AnomalyDetector(config)
  alerts = detector.check(history)
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Alert:
    """異常検知アラート"""
    alert_type: str          # "score_spike", "score_drop", "success_rate_drop", etc.
    severity: str            # "info", "warning", "critical"
    message: str
    value: float             # 検出された値
    threshold: float         # 閾値
    cycle: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "value": round(self.value, 4),
            "threshold": round(self.threshold, 4),
            "cycle": self.cycle,
            "timestamp": self.timestamp,
        }


class AnomalyDetector:
    """
    パフォーマンス異常検知エンジン。
    check() を呼び出すたびに、全チェックを実行しアラートリストを返す。
    """

    # デフォルトパラメータ
    Z_THRESHOLD = 2.0              # Z-score 閾値 (2σ 超 = 異常)
    SHORT_MA_WINDOW = 5            # 短期移動平均ウィンドウ
    LONG_MA_WINDOW = 15            # 長期移動平均ウィンドウ
    MA_CROSS_THRESHOLD = 0.10      # MA 交差時の差分閾値
    SR_DROP_THRESHOLD = 0.25       # 成功率ドロップ閾値 (25% 以上低下)
    SR_WINDOW = 10                 # 成功率計算ウィンドウ
    CONSECUTIVE_FAILURE_LIMIT = 3  # 連続失敗アラート閾値
    PLATEAU_WINDOW = 10            # 停滞検出ウィンドウ
    PLATEAU_TOLERANCE = 0.03       # この range 内なら停滞扱い

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("anomaly_detection", {})
        self.z_threshold = cfg.get("z_threshold", self.Z_THRESHOLD)
        self.short_ma = cfg.get("short_ma_window", self.SHORT_MA_WINDOW)
        self.long_ma = cfg.get("long_ma_window", self.LONG_MA_WINDOW)
        self.ma_cross_thr = cfg.get("ma_cross_threshold", self.MA_CROSS_THRESHOLD)
        self.sr_drop_thr = cfg.get("sr_drop_threshold", self.SR_DROP_THRESHOLD)
        self.sr_window = cfg.get("sr_window", self.SR_WINDOW)
        self.consec_fail = cfg.get("consecutive_failure_limit", self.CONSECUTIVE_FAILURE_LIMIT)
        self.plateau_window = cfg.get("plateau_window", self.PLATEAU_WINDOW)
        self.plateau_tol = cfg.get("plateau_tolerance", self.PLATEAU_TOLERANCE)

        # アラート履歴（重複防止用）
        self._alert_history: List[Alert] = []
        self._max_history = 200

    @property
    def alert_history(self) -> List[Alert]:
        return list(self._alert_history)

    def check(self, history: List[Dict[str, Any]]) -> List[Alert]:
        """
        全チェックを実行し、発生したアラートをリストで返す。
        history: metrics.jsonl のエントリリスト
        """
        if len(history) < 3:
            return []

        alerts: List[Alert] = []
        scores = [e.get("score", 0.0) for e in history]
        outcomes = [e.get("outcome", "unknown") for e in history]
        last_cycle = history[-1].get("cycle") if history else None

        # 1) Z-score チェック
        z_alerts = self._check_zscore(scores, last_cycle)
        alerts.extend(z_alerts)

        # 2) MA Crossover チェック
        ma_alerts = self._check_ma_crossover(scores, last_cycle)
        alerts.extend(ma_alerts)

        # 3) 成功率ドロップ
        sr_alerts = self._check_success_rate_drop(outcomes, last_cycle)
        alerts.extend(sr_alerts)

        # 4) 連続失敗
        cf_alerts = self._check_consecutive_failures(outcomes, last_cycle)
        alerts.extend(cf_alerts)

        # 5) 停滞検出
        pl_alerts = self._check_plateau(scores, last_cycle)
        alerts.extend(pl_alerts)

        # 履歴に追加
        self._alert_history.extend(alerts)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]

        return alerts

    def get_stats(self) -> Dict[str, Any]:
        """アラート統計"""
        by_type: Dict[str, int] = defaultdict(int)
        by_severity: Dict[str, int] = defaultdict(int)
        for a in self._alert_history:
            by_type[a.alert_type] += 1
            by_severity[a.severity] += 1
        return {
            "total_alerts": len(self._alert_history),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "recent": [a.to_dict() for a in self._alert_history[-10:]],
        }

    def clear_history(self) -> None:
        """アラート履歴クリア"""
        self._alert_history.clear()

    # ─────────────── チェック実装 ───────────────

    def _check_zscore(self, scores: List[float], cycle: Optional[int]) -> List[Alert]:
        """直近スコアの Z-score チェック"""
        if len(scores) < 5:
            return []
        window = scores[-20:]  # 直近20で統計
        if len(window) < 3:
            return []

        mean = statistics.mean(window[:-1])
        std = statistics.stdev(window[:-1]) if len(window) > 2 else 0
        if std < 0.01:
            return []

        latest = scores[-1]
        z = (latest - mean) / std

        alerts = []
        if z < -self.z_threshold:
            alerts.append(Alert(
                alert_type="score_drop",
                severity="warning" if z > -3 else "critical",
                message=f"スコア急落: z={z:.2f} (latest={latest:.3f}, mean={mean:.3f})",
                value=z,
                threshold=-self.z_threshold,
                cycle=cycle,
            ))
        elif z > self.z_threshold:
            alerts.append(Alert(
                alert_type="score_spike",
                severity="info",
                message=f"スコア急上昇: z={z:.2f} (latest={latest:.3f}, mean={mean:.3f})",
                value=z,
                threshold=self.z_threshold,
                cycle=cycle,
            ))
        return alerts

    def _check_ma_crossover(self, scores: List[float], cycle: Optional[int]) -> List[Alert]:
        """短期 MA が長期 MA を下回ったら警告"""
        if len(scores) < self.long_ma:
            return []

        short = statistics.mean(scores[-self.short_ma:])
        long_ = statistics.mean(scores[-self.long_ma:])
        diff = short - long_

        alerts = []
        if diff < -self.ma_cross_thr:
            alerts.append(Alert(
                alert_type="ma_bearish_cross",
                severity="warning",
                message=f"短期MA({short:.3f}) < 長期MA({long_:.3f}), diff={diff:.3f}",
                value=diff,
                threshold=-self.ma_cross_thr,
                cycle=cycle,
            ))
        elif diff > self.ma_cross_thr:
            alerts.append(Alert(
                alert_type="ma_bullish_cross",
                severity="info",
                message=f"短期MA({short:.3f}) > 長期MA({long_:.3f}), diff={diff:.3f}",
                value=diff,
                threshold=self.ma_cross_thr,
                cycle=cycle,
            ))
        return alerts

    def _check_success_rate_drop(
        self, outcomes: List[str], cycle: Optional[int]
    ) -> List[Alert]:
        """直近ウィンドウの成功率が大幅低下"""
        if len(outcomes) < self.sr_window * 2:
            return []

        prev = outcomes[-(self.sr_window * 2):-self.sr_window]
        curr = outcomes[-self.sr_window:]

        prev_sr = sum(1 for o in prev if o == "success") / len(prev) if prev else 0
        curr_sr = sum(1 for o in curr if o == "success") / len(curr) if curr else 0
        drop = prev_sr - curr_sr

        alerts = []
        if drop >= self.sr_drop_thr:
            alerts.append(Alert(
                alert_type="success_rate_drop",
                severity="critical" if drop > 0.4 else "warning",
                message=f"成功率急落: {prev_sr:.0%} → {curr_sr:.0%} (Δ={drop:.0%})",
                value=drop,
                threshold=self.sr_drop_thr,
                cycle=cycle,
            ))
        return alerts

    def _check_consecutive_failures(
        self, outcomes: List[str], cycle: Optional[int]
    ) -> List[Alert]:
        """末尾からの連続失敗をチェック"""
        streak = 0
        for o in reversed(outcomes):
            if o == "failure":
                streak += 1
            else:
                break

        alerts = []
        if streak >= self.consec_fail:
            alerts.append(Alert(
                alert_type="consecutive_failures",
                severity="critical" if streak >= self.consec_fail * 2 else "warning",
                message=f"連続失敗 {streak} 回",
                value=float(streak),
                threshold=float(self.consec_fail),
                cycle=cycle,
            ))
        return alerts

    def _check_plateau(self, scores: List[float], cycle: Optional[int]) -> List[Alert]:
        """スコアが長期間停滞していないかチェック"""
        if len(scores) < self.plateau_window:
            return []

        window = scores[-self.plateau_window:]
        score_range = max(window) - min(window)

        alerts = []
        if score_range <= self.plateau_tol:
            avg = sum(window) / len(window)
            alerts.append(Alert(
                alert_type="score_plateau",
                severity="info",
                message=f"スコア停滞: 直近{self.plateau_window}サイクルの range={score_range:.4f}, avg={avg:.3f}",
                value=score_range,
                threshold=self.plateau_tol,
                cycle=cycle,
            ))
        return alerts
