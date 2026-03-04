"""
A/B Experiment Tracker — 設定並行比較とベスト戦略選択
=====================================================
複数の config バリアントを同時に実行し、成績を比較して
最良のパラメータセットを自動選択する。

使い方:
  tracker = ExperimentTracker(experiments_dir=Path("logs/experiments"))
  exp_id = tracker.create("higher_weight", {"reward_model": {"intermediate_weight": 0.6}})
  tracker.record_result(exp_id, outcome="success", score=0.85)
  report = tracker.compare()
  best = tracker.get_best()
"""

from __future__ import annotations

import json
import threading
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class Experiment:
    """1 つの実験バリアント"""

    def __init__(self, exp_id: str, name: str, config_overrides: Dict[str, Any]):
        self.exp_id = exp_id
        self.name = name
        self.config_overrides = config_overrides
        self.created_at = datetime.now().isoformat()
        self.results: List[Dict[str, Any]] = []
        self.active = True

    @property
    def sample_count(self) -> int:
        return len(self.results)

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        successes = sum(1 for r in self.results if r.get("outcome") == "success")
        return round(successes / len(self.results), 4)

    @property
    def avg_score(self) -> float:
        scores = [r["score"] for r in self.results if "score" in r]
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    @property
    def score_stddev(self) -> float:
        scores = [r["score"] for r in self.results if "score" in r]
        if len(scores) < 2:
            return 0.0
        return round(statistics.stdev(scores), 4)

    def record(self, outcome: str, score: float, metadata: Optional[Dict] = None) -> None:
        self.results.append({
            "outcome": outcome,
            "score": score,
            "ts": datetime.now().isoformat(),
            **(metadata or {}),
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exp_id": self.exp_id,
            "name": self.name,
            "config_overrides": self.config_overrides,
            "created_at": self.created_at,
            "active": self.active,
            "sample_count": self.sample_count,
            "success_rate": self.success_rate,
            "avg_score": self.avg_score,
            "score_stddev": self.score_stddev,
            "results": self.results,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Experiment":
        exp = cls(d["exp_id"], d["name"], d.get("config_overrides", {}))
        exp.created_at = d.get("created_at", exp.created_at)
        exp.active = d.get("active", True)
        exp.results = d.get("results", [])
        return exp


class ExperimentTracker:
    """
    A/B テスト管理。複数の設定バリアントを同時追跡し、統計的に比較。

    - create(): 新規実験を作成
    - record_result(): 結果を記録
    - compare(): 全実験の横比較レポート
    - get_best(): 最良バリアントの config_overrides を返す
    - conclude(): 実験を終了（active=False）
    """

    def __init__(self, experiments_dir: Optional[Path] = None):
        self._dir = experiments_dir or Path("logs/experiments")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._experiments: Dict[str, Experiment] = {}
        self._lock = threading.Lock()
        self._next_id = 1
        self._load_all()

    def create(
        self,
        name: str,
        config_overrides: Dict[str, Any],
        exp_id: Optional[str] = None,
    ) -> str:
        """新規実験バリアントを作成"""
        with self._lock:
            eid = exp_id or f"exp_{self._next_id:04d}"
            self._next_id += 1
            exp = Experiment(eid, name, config_overrides)
            self._experiments[eid] = exp
            self._save(exp)
        return eid

    def record_result(
        self,
        exp_id: str,
        outcome: str,
        score: float,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """実験に結果を追加"""
        with self._lock:
            exp = self._experiments.get(exp_id)
            if not exp or not exp.active:
                return False
            exp.record(outcome, score, metadata)
            self._save(exp)
        return True

    def compare(self, min_samples: int = 3) -> Dict[str, Any]:
        """
        全実験の横比較レポート。
        min_samples 未満のバリアントは「insufficient_data」。
        """
        with self._lock:
            rows = []
            for exp in self._experiments.values():
                row = {
                    "exp_id": exp.exp_id,
                    "name": exp.name,
                    "active": exp.active,
                    "sample_count": exp.sample_count,
                }
                if exp.sample_count >= min_samples:
                    row.update({
                        "success_rate": exp.success_rate,
                        "avg_score": exp.avg_score,
                        "score_stddev": exp.score_stddev,
                        "status": "ready",
                    })
                else:
                    row["status"] = "insufficient_data"
                rows.append(row)

            # ソート: ready > insufficient; avg_score desc
            rows.sort(key=lambda r: (r.get("status") == "ready", r.get("avg_score", 0)), reverse=True)
            return {"experiments": rows, "total": len(rows)}

    def get_best(self, min_samples: int = 3) -> Optional[Dict[str, Any]]:
        """
        最良バリアントの config_overrides を返す。
        十分なサンプルがある実験のうち avg_score 最高のものを選択。
        """
        with self._lock:
            candidates = [
                exp for exp in self._experiments.values()
                if exp.sample_count >= min_samples and exp.active
            ]
            if not candidates:
                return None
            best = max(candidates, key=lambda e: e.avg_score)
            return {
                "exp_id": best.exp_id,
                "name": best.name,
                "avg_score": best.avg_score,
                "success_rate": best.success_rate,
                "sample_count": best.sample_count,
                "config_overrides": best.config_overrides,
            }

    def conclude(self, exp_id: str) -> bool:
        """実験を終了 (active=False)"""
        with self._lock:
            exp = self._experiments.get(exp_id)
            if not exp:
                return False
            exp.active = False
            self._save(exp)
        return True

    def get_experiment(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """実験詳細を返す"""
        with self._lock:
            exp = self._experiments.get(exp_id)
            return exp.to_dict() if exp else None

    def list_experiments(self) -> List[Dict[str, Any]]:
        """全実験の概要リスト"""
        with self._lock:
            return [
                {
                    "exp_id": e.exp_id,
                    "name": e.name,
                    "active": e.active,
                    "sample_count": e.sample_count,
                    "success_rate": e.success_rate,
                    "avg_score": e.avg_score,
                }
                for e in self._experiments.values()
            ]

    def get_stats(self) -> Dict[str, Any]:
        """トラッカー統計"""
        with self._lock:
            active = sum(1 for e in self._experiments.values() if e.active)
            total_results = sum(e.sample_count for e in self._experiments.values())
            return {
                "total_experiments": len(self._experiments),
                "active_experiments": active,
                "total_results": total_results,
            }

    # ─── 永続化 ───────────────────────────────────
    def _save(self, exp: Experiment) -> None:
        """個別の実験を JSON ファイルに保存"""
        path = self._dir / f"{exp.exp_id}.json"
        path.write_text(
            json.dumps(exp.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _load_all(self) -> None:
        """起動時に保存済み実験を復元"""
        max_id = 0
        for p in self._dir.glob("exp_*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                exp = Experiment.from_dict(data)
                self._experiments[exp.exp_id] = exp
                # ID カウンタ復元
                try:
                    num = int(exp.exp_id.split("_")[1])
                    max_id = max(max_id, num)
                except (ValueError, IndexError):
                    pass
            except Exception:
                pass
        self._next_id = max_id + 1
