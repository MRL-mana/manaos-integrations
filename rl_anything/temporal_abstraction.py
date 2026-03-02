#!/usr/bin/env python3
"""
TemporalAbstraction — 時間認識状態表現 & 時系列パターン検出
==========================================================
Round 11 モジュール (1/3)

タスク履歴を時間軸で分析し、パフォーマンスの周期性・トレンド・
セッション間遷移パターンを学習する。

主な機能:
  - 時系列状態エンコーディング（時刻/曜日/セッション長特徴）
  - 移動平均ベースのトレンド検出（上昇/下降/横ばい）
  - 周期パターン抽出（時間帯/曜日別パフォーマンス）
  - Temporal Difference 学習による価値推定
  - セッション境界検出と復帰率分析
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── 定数 ──

MAX_EVENTS = 5000
WINDOW_SHORT = 5       # 短期移動平均
WINDOW_LONG = 20       # 長期移動平均
TD_ALPHA = 0.05        # TD学習率
TD_GAMMA = 0.95        # TD割引率
SESSION_GAP_SEC = 1800 # 30分以上空くと新セッション
TREND_THRESHOLD = 0.02 # トレンド判定閾値


# ── データ型 ──

@dataclass
class TemporalEvent:
    """1タスク完了イベント"""
    timestamp: float
    score: float
    difficulty: str
    session_id: int = 0
    hour: int = 0
    weekday: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrendInfo:
    """トレンド分析結果"""
    direction: str          # "rising" | "falling" | "stable"
    short_avg: float
    long_avg: float
    momentum: float         # short - long
    slope: float            # 線形回帰の傾き
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PeriodicPattern:
    """周期パターン"""
    by_hour: Dict[int, float] = field(default_factory=dict)
    by_weekday: Dict[int, float] = field(default_factory=dict)
    best_hour: int = 0
    worst_hour: int = 0
    best_weekday: int = 0
    peak_performance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "by_hour": self.by_hour,
            "by_weekday": self.by_weekday,
            "best_hour": self.best_hour,
            "worst_hour": self.worst_hour,
            "best_weekday": self.best_weekday,
            "peak_performance": self.peak_performance,
        }


@dataclass
class SessionInfo:
    """セッション情報"""
    session_id: int
    start_ts: float
    end_ts: float
    event_count: int
    avg_score: float
    trend: str


# ── メインクラス ──

class TemporalAbstraction:
    """時間軸での状態表現と学習パターン分析"""

    def __init__(self, *, persist_path: Optional[Path] = None,
                 config: Optional[Dict] = None):
        self._events: List[TemporalEvent] = []
        self._session_counter = 0
        self._current_session_start = 0.0

        # TD学習: 時間帯別の価値推定
        self._td_values: Dict[str, float] = defaultdict(float)
        self._td_counts: Dict[str, int] = defaultdict(int)

        self._persist = persist_path
        cfg = config or {}
        self._window_short = cfg.get("temporal_window_short", WINDOW_SHORT)
        self._window_long = cfg.get("temporal_window_long", WINDOW_LONG)
        self._td_alpha = cfg.get("temporal_td_alpha", TD_ALPHA)
        self._td_gamma = cfg.get("temporal_td_gamma", TD_GAMMA)

        self._restore()

    # ── 記録 ──

    def record_event(self, score: float, difficulty: str,
                     timestamp: Optional[float] = None) -> TemporalEvent:
        """タスク完了イベントを記録"""
        ts = timestamp or time.time()
        dt = datetime.fromtimestamp(ts)

        # セッション判定
        if not self._events or (ts - self._events[-1].timestamp) > SESSION_GAP_SEC:
            self._session_counter += 1
            self._current_session_start = ts

        event = TemporalEvent(
            timestamp=ts,
            score=score,
            difficulty=difficulty,
            session_id=self._session_counter,
            hour=dt.hour,
            weekday=dt.weekday(),
        )
        self._events.append(event)

        # TD学習更新
        self._td_update(event)

        # 容量制限
        if len(self._events) > MAX_EVENTS:
            self._events = self._events[-MAX_EVENTS:]

        self._persist_state()
        return event

    def _td_update(self, event: TemporalEvent) -> None:
        """Temporal Difference(0)で時間帯別価値を更新"""
        key = f"h{event.hour}_d{event.weekday}"
        old_v = self._td_values[key]
        # 次の状態の価値（同じ時間帯の現在推定値をブートストラップ）
        next_v = self._td_values.get(key, 0.0)
        td_target = event.score + self._td_gamma * next_v
        self._td_values[key] = old_v + self._td_alpha * (td_target - old_v)
        self._td_counts[key] = self._td_counts.get(key, 0) + 1

    # ── トレンド分析 ──

    def get_trend(self) -> TrendInfo:
        """現在のパフォーマンストレンドを分析"""
        if len(self._events) < 3:
            return TrendInfo("stable", 0.0, 0.0, 0.0, 0.0, 0.0)

        scores = [e.score for e in self._events]

        # 移動平均
        short_w = min(self._window_short, len(scores))
        long_w = min(self._window_long, len(scores))
        short_avg = sum(scores[-short_w:]) / short_w
        long_avg = sum(scores[-long_w:]) / long_w
        momentum = short_avg - long_avg

        # 線形回帰の傾き（直近short_w）
        recent = scores[-short_w:]
        n = len(recent)
        x_mean = (n - 1) / 2.0
        y_mean = sum(recent) / n
        num = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den > 0 else 0.0

        # 方向判定
        if momentum > TREND_THRESHOLD:
            direction = "rising"
        elif momentum < -TREND_THRESHOLD:
            direction = "falling"
        else:
            direction = "stable"

        confidence = min(1.0, len(scores) / self._window_long)

        return TrendInfo(direction, round(short_avg, 4), round(long_avg, 4),
                         round(momentum, 4), round(slope, 6), round(confidence, 3))

    # ── 周期パターン ──

    def get_periodic_pattern(self) -> PeriodicPattern:
        """時間帯/曜日別のパフォーマンスパターンを抽出"""
        if not self._events:
            return PeriodicPattern()

        by_hour: Dict[int, List[float]] = defaultdict(list)
        by_weekday: Dict[int, List[float]] = defaultdict(list)

        for e in self._events:
            by_hour[e.hour].append(e.score)
            by_weekday[e.weekday].append(e.score)

        hour_avg = {h: round(sum(s) / len(s), 4) for h, s in by_hour.items()}
        day_avg = {d: round(sum(s) / len(s), 4) for d, s in by_weekday.items()}

        best_h = max(hour_avg, key=hour_avg.get) if hour_avg else 0
        worst_h = min(hour_avg, key=hour_avg.get) if hour_avg else 0
        best_d = max(day_avg, key=day_avg.get) if day_avg else 0
        peak = max(hour_avg.values()) if hour_avg else 0.0

        return PeriodicPattern(
            by_hour=hour_avg, by_weekday=day_avg,
            best_hour=best_h, worst_hour=worst_h,
            best_weekday=best_d, peak_performance=peak,
        )

    # ── セッション分析 ──

    def get_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """セッション一覧（直近limit件）"""
        if not self._events:
            return []

        sessions: Dict[int, List[TemporalEvent]] = defaultdict(list)
        for e in self._events:
            sessions[e.session_id].append(e)

        result = []
        for sid in sorted(sessions.keys(), reverse=True)[:limit]:
            evts = sessions[sid]
            scores = [e.score for e in evts]
            avg = sum(scores) / len(scores)

            # セッション内トレンド
            if len(scores) >= 3:
                first_half = sum(scores[:len(scores)//2]) / max(1, len(scores)//2)
                second_half = sum(scores[len(scores)//2:]) / max(1, len(scores) - len(scores)//2)
                trend = "rising" if second_half > first_half + 0.02 else (
                    "falling" if second_half < first_half - 0.02 else "stable")
            else:
                trend = "stable"

            result.append({
                "session_id": sid,
                "start_ts": evts[0].timestamp,
                "end_ts": evts[-1].timestamp,
                "event_count": len(evts),
                "avg_score": round(avg, 4),
                "trend": trend,
            })
        return result

    # ── TD価値マップ ──

    def get_td_values(self) -> Dict[str, Any]:
        """TD学習済みの時間帯別価値マップ"""
        return {
            "values": dict(self._td_values),
            "counts": dict(self._td_counts),
            "total_updates": sum(self._td_counts.values()),
        }

    # ── 統計 ──

    def get_stats(self) -> Dict[str, Any]:
        """全体統計"""
        if not self._events:
            return {"total_events": 0, "sessions": 0, "td_states": 0}
        scores = [e.score for e in self._events]
        return {
            "total_events": len(self._events),
            "sessions": self._session_counter,
            "td_states": len(self._td_values),
            "score_mean": round(sum(scores) / len(scores), 4),
            "score_min": round(min(scores), 4),
            "score_max": round(max(scores), 4),
            "earliest_ts": self._events[0].timestamp,
            "latest_ts": self._events[-1].timestamp,
        }

    # ── 永続化 ──

    def _persist_state(self) -> None:
        if not self._persist:
            return
        try:
            data = {
                "events": [e.to_dict() for e in self._events[-MAX_EVENTS:]],
                "session_counter": self._session_counter,
                "td_values": dict(self._td_values),
                "td_counts": dict(self._td_counts),
            }
            self._persist.parent.mkdir(parents=True, exist_ok=True)
            self._persist.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _restore(self) -> None:
        if not self._persist or not self._persist.exists():
            return
        try:
            data = json.loads(self._persist.read_text(encoding="utf-8"))
            for ed in data.get("events", []):
                self._events.append(TemporalEvent(**ed))
            self._session_counter = data.get("session_counter", 0)
            self._td_values = defaultdict(float, data.get("td_values", {}))
            self._td_counts = defaultdict(int, data.get("td_counts", {}))
        except Exception:
            pass
