"""
Replay Buffer — 過去のタスク経験を保持して再評価・トレーニングに利用
===========================================================================
固定サイズのリングバッファ。優先度付きサンプリング対応。

使い方:
  buf = ReplayBuffer(max_size=200)
  buf.push(experience)
  batch = buf.sample(n=16)          # ランダム
  batch = buf.sample_prioritized(n=16)  # 失敗/レア事例を優先
"""

from __future__ import annotations

import json
import math
import random
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Experience:
    """1 タスクの経験レコード"""
    task_id: str
    outcome: str
    score: float
    difficulty: str
    cycle: int
    tool_count: int = 0
    error_count: int = 0
    skills_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: float = 1.0  # 高 = サンプルされやすい
    ts: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Experience":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


class ReplayBuffer:
    """
    固定サイズ・リングバッファベースの Replay Buffer。
    - push() で最新経験を追加（max_size 超過→古い順に削除）
    - sample() でランダムバッチ
    - sample_prioritized() で優先度重み付きサンプリング
    - save() / load() で JSONL 永続化
    """

    def __init__(self, max_size: int = 500, persist_path: Optional[Path] = None):
        self._max_size = max_size
        self._buffer: List[Experience] = []
        self._lock = threading.Lock()
        self._persist_path = persist_path
        self._total_pushed = 0

        # 起動時に永続化ファイルから復元
        if persist_path and persist_path.exists():
            self.load(persist_path)

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def total_pushed(self) -> int:
        return self._total_pushed

    def push(self, exp: Experience) -> None:
        """
        経験を追加。優先度を自動設定（失敗・低スコアほど高優先度）。
        バッファが max_size を超えたら最も古いものを削除。
        """
        # 優先度自動設定: 失敗=2.0, partial=1.5, 低スコア boost
        if exp.priority == 1.0:
            base = {"failure": 2.0, "partial": 1.5, "unknown": 1.8}.get(exp.outcome, 1.0)
            score_boost = max(0, 1.0 - exp.score)  # 低スコアほど高優先度
            exp.priority = round(base + score_boost * 0.5, 4)

        with self._lock:
            self._buffer.append(exp)
            self._total_pushed += 1
            if len(self._buffer) > self._max_size:
                self._buffer = self._buffer[-self._max_size:]

        # 自動永続化
        if self._persist_path:
            self.save(self._persist_path)

    def sample(self, n: int = 16) -> List[Experience]:
        """ランダムサンプリング"""
        with self._lock:
            if not self._buffer:
                return []
            n = min(n, len(self._buffer))
            return random.sample(self._buffer, n)

    def sample_prioritized(self, n: int = 16) -> List[Experience]:
        """
        優先度重み付きサンプリング（重複あり）。
        failure / 低スコアのタスクが多くサンプルされる。
        """
        with self._lock:
            if not self._buffer:
                return []
            weights = [exp.priority for exp in self._buffer]
            total = sum(weights)
            if total == 0:
                return random.choices(self._buffer, k=n)
            indices = random.choices(range(len(self._buffer)), weights=weights, k=n)
            return [self._buffer[i] for i in indices]

    def get_all(self) -> List[Experience]:
        """全経験（コピー）"""
        with self._lock:
            return list(self._buffer)

    def get_stats(self) -> Dict[str, Any]:
        """バッファ統計"""
        with self._lock:
            if not self._buffer:
                return {"size": 0, "max_size": self._max_size, "total_pushed": self._total_pushed}
            outcomes = {}
            scores = []
            for e in self._buffer:
                outcomes[e.outcome] = outcomes.get(e.outcome, 0) + 1
                scores.append(e.score)
            return {
                "size": len(self._buffer),
                "max_size": self._max_size,
                "total_pushed": self._total_pushed,
                "outcome_distribution": outcomes,
                "avg_score": round(sum(scores) / len(scores), 4) if scores else 0,
                "avg_priority": round(
                    sum(e.priority for e in self._buffer) / len(self._buffer), 4
                ),
            }

    def clear(self) -> None:
        """バッファクリア"""
        with self._lock:
            self._buffer.clear()

    def save(self, path: Optional[Path] = None) -> None:
        """JSONL に永続化"""
        p = path or self._persist_path
        if not p:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(p, "w", encoding="utf-8") as f:
                for exp in self._buffer:
                    f.write(json.dumps(exp.to_dict(), ensure_ascii=False) + "\n")

    def load(self, path: Optional[Path] = None) -> int:
        """JSONL から復元。返り値: 読み込んだ件数。"""
        p = path or self._persist_path
        if not p or not p.exists():
            return 0
        loaded = []
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        loaded.append(Experience.from_dict(json.loads(line)))
        except Exception:
            return 0
        with self._lock:
            self._buffer = loaded[-self._max_size:]
            self._total_pushed = len(loaded)
        return len(loaded)
