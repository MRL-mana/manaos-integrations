#!/usr/bin/env python3
"""
Safety Constraint Manager — 安全制約管理エンジン (Round 9)
============================================================
RL エージェントの行動に対する安全制約を定義・監視・強制。

概念:
  - Hard Constraints: 絶対に違反不可（例: 連続失敗数上限）
  - Soft Constraints: 違反時に警告+ペナルティ（例: スコア下限目標）
  - Constraint Relaxation: 状況に応じて制約を緩和
  - Recovery Protocol: 違反時の回復手順を提案
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger("rl_anything.safety")

# ── 定数 ──
MAX_VIOLATIONS = 500
MAX_HISTORY = 200


class ConstraintType(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class ConstraintStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    VIOLATED = "violated"
    RELAXED = "relaxed"


@dataclass
class SafetyConstraint:
    """安全制約定義"""
    constraint_id: str
    name: str
    description: str
    constraint_type: str  # "hard" or "soft"
    metric: str          # 対象メトリクス名
    operator: str        # ">=", "<=", "<", ">", "=="
    threshold: float     # 閾値
    penalty: float = 0.1  # 違反時のペナルティ (soft のみ)
    enabled: bool = True
    relaxation_factor: float = 1.0  # 1.0=通常、>1.0=緩和済み
    violation_count: int = 0
    last_check_status: str = "ok"
    last_check_ts: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def check(self, value: float) -> ConstraintStatus:
        """制約をチェック"""
        adjusted_threshold = self.threshold * self.relaxation_factor
        ops = {
            ">=": lambda v, t: v >= t,
            "<=": lambda v, t: v <= t,
            ">": lambda v, t: v > t,
            "<": lambda v, t: v < t,
            "==": lambda v, t: abs(v - t) < 0.001,
        }
        check_fn = ops.get(self.operator, lambda v, t: True)

        if check_fn(value, adjusted_threshold):
            return ConstraintStatus.OK
        elif self.relaxation_factor > 1.0:
            return ConstraintStatus.RELAXED
        elif self.constraint_type == "soft":
            return ConstraintStatus.WARNING
        else:
            return ConstraintStatus.VIOLATED


@dataclass
class Violation:
    """制約違反記録"""
    constraint_id: str
    constraint_name: str
    constraint_type: str
    metric: str
    actual_value: float
    threshold: float
    severity: str  # "warning", "violation", "critical"
    penalty_applied: float
    cycle: int
    ts: str = ""

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecoveryAction:
    """回復アクション提案"""
    action: str
    reason: str
    priority: int  # 1=最優先
    estimated_cycles: int  # 回復にかかる推定サイクル数

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── デフォルト制約 ──
DEFAULT_CONSTRAINTS = [
    SafetyConstraint(
        constraint_id="min_success_rate",
        name="最低成功率",
        description="直近の成功率が20%を下回らないこと",
        constraint_type="soft",
        metric="success_rate",
        operator=">=",
        threshold=0.20,
        penalty=0.05,
    ),
    SafetyConstraint(
        constraint_id="max_consecutive_failures",
        name="連続失敗上限",
        description="連続10回以上の失敗を許さない",
        constraint_type="hard",
        metric="consecutive_failures",
        operator="<=",
        threshold=10.0,
        penalty=0.2,
    ),
    SafetyConstraint(
        constraint_id="min_avg_score",
        name="最低平均スコア",
        description="直近20サイクルの平均スコアが0.15以上",
        constraint_type="soft",
        metric="avg_score",
        operator=">=",
        threshold=0.15,
        penalty=0.08,
    ),
    SafetyConstraint(
        constraint_id="max_error_rate",
        name="エラー率上限",
        description="エラー率が80%を超えないこと",
        constraint_type="hard",
        metric="error_rate",
        operator="<=",
        threshold=0.80,
        penalty=0.15,
    ),
    SafetyConstraint(
        constraint_id="min_exploration",
        name="最低探索率",
        description="探索率が5%を下回らないこと",
        constraint_type="soft",
        metric="exploration_rate",
        operator=">=",
        threshold=0.05,
        penalty=0.03,
    ),
]


class SafetyConstraintManager:
    """
    安全制約管理エンジン。
    
    全制約をチェックし、違反時にペナルティ適用と回復提案を生成。
    Hard制約違反は即座にアクションを強制。
    Soft制約違反は警告+ペナルティ。
    """

    def __init__(
        self,
        persist_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        cfg = (config or {}).get("safety", {})
        self._persist_path = persist_path

        # 制約テーブル
        self._constraints: Dict[str, SafetyConstraint] = {}
        for c in DEFAULT_CONSTRAINTS:
            self._constraints[c.constraint_id] = SafetyConstraint(**asdict(c))

        # 違反履歴
        self._violations: List[Violation] = []
        # 連続違反カウンタ
        self._consecutive_violations: Dict[str, int] = defaultdict(int)
        # 統計
        self._total_checks = 0
        self._total_violations = 0
        self._total_penalties = 0.0

        self._restore()

    # ═══════════════════════════════════════════════════════
    # メトリクス抽出
    # ═══════════════════════════════════════════════════════
    @staticmethod
    def extract_metrics(
        history: List[Dict[str, Any]],
        exploration_rate: float = 0.5,
    ) -> Dict[str, float]:
        """
        履歴からチェック対象メトリクスを抽出。
        """
        if not history:
            return {
                "success_rate": 0.5,
                "consecutive_failures": 0,
                "avg_score": 0.5,
                "error_rate": 0.0,
                "exploration_rate": exploration_rate,
            }

        recent = history[-20:]
        outcomes = [e.get("outcome", "unknown") for e in recent]
        scores = [e.get("score", 0) for e in recent]

        # 成功率
        success_rate = sum(1 for o in outcomes if o == "success") / len(outcomes)

        # 連続失敗数 (末尾から数える)
        consecutive_failures = 0
        for o in reversed(outcomes):
            if o == "failure":
                consecutive_failures += 1
            else:
                break

        # 平均スコア
        avg_score = sum(scores) / len(scores) if scores else 0

        # エラー率
        error_rate = sum(1 for o in outcomes if o == "failure") / len(outcomes)

        return {
            "success_rate": round(success_rate, 4),
            "consecutive_failures": consecutive_failures,
            "avg_score": round(avg_score, 4),
            "error_rate": round(error_rate, 4),
            "exploration_rate": round(exploration_rate, 4),
        }

    # ═══════════════════════════════════════════════════════
    # 制約チェック
    # ═══════════════════════════════════════════════════════
    def check_all(
        self,
        metrics: Dict[str, float],
        cycle: int = 0,
    ) -> Dict[str, Any]:
        """
        全制約をチェックし、結果をまとめて返す。
        
        Returns:
            {
                "safe": bool,
                "total_penalty": float,
                "violations": [...],
                "warnings": [...],
                "recovery": [...],
                "constraint_results": {...},
            }
        """
        self._total_checks += 1
        violations: List[Violation] = []
        warnings: List[Dict[str, Any]] = []
        constraint_results: Dict[str, Dict[str, Any]] = {}
        total_penalty = 0.0
        is_safe = True

        for cid, constraint in self._constraints.items():
            if not constraint.enabled:
                constraint_results[cid] = {"status": "disabled"}
                continue

            value = metrics.get(constraint.metric)
            if value is None:
                constraint_results[cid] = {"status": "no_data"}
                continue

            status = constraint.check(value)
            constraint.last_check_status = status.value
            constraint.last_check_ts = datetime.now().isoformat()

            if status == ConstraintStatus.OK:
                self._consecutive_violations[cid] = 0
                constraint_results[cid] = {
                    "status": "ok",
                    "value": value,
                    "threshold": constraint.threshold,
                }
            elif status in (ConstraintStatus.WARNING, ConstraintStatus.RELAXED):
                # Soft 制約違反 → 警告 + ペナルティ
                penalty = constraint.penalty
                total_penalty += penalty
                self._consecutive_violations[cid] += 1
                constraint.violation_count += 1
                self._total_violations += 1

                severity = "warning"
                if self._consecutive_violations[cid] >= 3:
                    severity = "critical"
                    is_safe = False

                v = Violation(
                    constraint_id=cid,
                    constraint_name=constraint.name,
                    constraint_type=constraint.constraint_type,
                    metric=constraint.metric,
                    actual_value=value,
                    threshold=constraint.threshold * constraint.relaxation_factor,
                    severity=severity,
                    penalty_applied=penalty,
                    cycle=cycle,
                )
                warnings.append(v.to_dict())
                self._violations.append(v)

                constraint_results[cid] = {
                    "status": severity,
                    "value": value,
                    "threshold": constraint.threshold,
                    "penalty": penalty,
                    "consecutive": self._consecutive_violations[cid],
                }
            else:
                # Hard 制約違反 → 即時対応
                penalty = constraint.penalty * 2  # Hard は倍ペナルティ
                total_penalty += penalty
                self._consecutive_violations[cid] += 1
                constraint.violation_count += 1
                self._total_violations += 1
                is_safe = False

                v = Violation(
                    constraint_id=cid,
                    constraint_name=constraint.name,
                    constraint_type=constraint.constraint_type,
                    metric=constraint.metric,
                    actual_value=value,
                    threshold=constraint.threshold,
                    severity="violation",
                    penalty_applied=penalty,
                    cycle=cycle,
                )
                violations.append(v.to_dict())
                self._violations.append(v)

                constraint_results[cid] = {
                    "status": "violated",
                    "value": value,
                    "threshold": constraint.threshold,
                    "penalty": penalty,
                    "consecutive": self._consecutive_violations[cid],
                }

        # 違反履歴の上限管理
        if len(self._violations) > MAX_VIOLATIONS:
            self._violations = self._violations[-MAX_VIOLATIONS:]

        self._total_penalties += total_penalty

        # 回復提案
        recovery = self._suggest_recovery(violations, warnings, metrics)

        self._persist()

        return {
            "safe": is_safe,
            "total_penalty": round(total_penalty, 4),
            "violations": violations,
            "warnings": warnings,
            "recovery": [r.to_dict() for r in recovery],
            "constraint_results": constraint_results,
            "metrics_checked": metrics,
        }

    # ═══════════════════════════════════════════════════════
    # 回復提案
    # ═══════════════════════════════════════════════════════
    def _suggest_recovery(
        self,
        violations: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
        metrics: Dict[str, float],
    ) -> List[RecoveryAction]:
        """違反に基づく回復アクションを提案"""
        actions: List[RecoveryAction] = []

        all_issues = violations + warnings
        if not all_issues:
            return actions

        violated_metrics = set()
        for issue in all_issues:
            violated_metrics.add(issue.get("metric", ""))

        # 成功率低下 → 難易度下げ
        if "success_rate" in violated_metrics:
            actions.append(RecoveryAction(
                action="reduce_difficulty",
                reason="成功率が低下しています。難易度を下げて安定化を図ります。",
                priority=1,
                estimated_cycles=5,
            ))

        # 連続失敗 → 即座に難易度下げ + 探索モード
        if "consecutive_failures" in violated_metrics:
            actions.append(RecoveryAction(
                action="emergency_level_down",
                reason="連続失敗が検出されました。緊急で難易度を下げます。",
                priority=0,
                estimated_cycles=3,
            ))
            actions.append(RecoveryAction(
                action="increase_exploration",
                reason="新しいアプローチを探索する必要があります。",
                priority=2,
                estimated_cycles=10,
            ))

        # 平均スコア低下 → 補助強化
        if "avg_score" in violated_metrics:
            actions.append(RecoveryAction(
                action="boost_guidance",
                reason="スコアが低下しています。ガイダンスレベルを上げます。",
                priority=2,
                estimated_cycles=8,
            ))

        # エラー率超過 → ツール制限
        if "error_rate" in violated_metrics:
            actions.append(RecoveryAction(
                action="restrict_risky_actions",
                reason="エラー率が高すぎます。リスクの高い行動を制限します。",
                priority=1,
                estimated_cycles=5,
            ))

        # 探索不足 → 探索奨励
        if "exploration_rate" in violated_metrics:
            actions.append(RecoveryAction(
                action="encourage_exploration",
                reason="探索率が低下しています。新しいパターンの探索を奨励します。",
                priority=3,
                estimated_cycles=15,
            ))

        actions.sort(key=lambda a: a.priority)
        return actions

    # ═══════════════════════════════════════════════════════
    # 制約管理
    # ═══════════════════════════════════════════════════════
    def add_constraint(
        self,
        constraint_id: str,
        name: str,
        description: str = "",
        constraint_type: str = "soft",
        metric: str = "score",
        operator: str = ">=",
        threshold: float = 0.5,
        penalty: float = 0.1,
    ) -> SafetyConstraint:
        """カスタム制約を追加"""
        c = SafetyConstraint(
            constraint_id=constraint_id,
            name=name,
            description=description,
            constraint_type=constraint_type,
            metric=metric,
            operator=operator,
            threshold=threshold,
            penalty=penalty,
        )
        self._constraints[constraint_id] = c
        self._persist()
        return c

    def remove_constraint(self, constraint_id: str) -> bool:
        """制約を削除"""
        if constraint_id in self._constraints:
            del self._constraints[constraint_id]
            self._persist()
            return True
        return False

    def relax_constraint(self, constraint_id: str, factor: float = 1.2) -> Optional[Dict[str, Any]]:
        """制約を緩和 (factor > 1.0 で閾値を緩める)"""
        c = self._constraints.get(constraint_id)
        if c is None:
            return None
        c.relaxation_factor = max(1.0, factor)
        self._persist()
        return c.to_dict()

    def tighten_constraint(self, constraint_id: str, factor: float = 0.9) -> Optional[Dict[str, Any]]:
        """制約を厳格化 (factor < 1.0 で閾値を厳しくする)"""
        c = self._constraints.get(constraint_id)
        if c is None:
            return None
        c.relaxation_factor = max(0.5, min(1.0, factor))
        self._persist()
        return c.to_dict()

    def get_constraints(self) -> Dict[str, Dict[str, Any]]:
        """全制約を取得"""
        return {cid: c.to_dict() for cid, c in self._constraints.items()}

    # ═══════════════════════════════════════════════════════
    # 統計
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        """安全制約の統計"""
        active = sum(1 for c in self._constraints.values() if c.enabled)
        hard = sum(1 for c in self._constraints.values() if c.constraint_type == "hard" and c.enabled)
        soft = active - hard

        recent_violations = [v.to_dict() for v in self._violations[-10:]]

        # 制約ごとの違反集計
        violation_by_constraint: Dict[str, int] = defaultdict(int)
        for v in self._violations:
            violation_by_constraint[v.constraint_id] += 1

        return {
            "total_checks": self._total_checks,
            "total_violations": self._total_violations,
            "total_penalties": round(self._total_penalties, 4),
            "active_constraints": active,
            "hard_constraints": hard,
            "soft_constraints": soft,
            "constraint_count": len(self._constraints),
            "recent_violations": recent_violations,
            "violation_by_constraint": dict(violation_by_constraint),
        }

    def get_violation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """違反履歴"""
        return [v.to_dict() for v in self._violations[-limit:]]

    def get_safety_score(self) -> float:
        """
        安全性スコア (0-1)。
        全制約の充足度合いを総合評価。
        """
        if not self._constraints:
            return 1.0

        ok_count = sum(
            1 for c in self._constraints.values()
            if c.enabled and c.last_check_status == "ok"
        )
        enabled = sum(1 for c in self._constraints.values() if c.enabled)
        if enabled == 0:
            return 1.0

        # 連続違反ペナルティ
        max_consecutive = max(self._consecutive_violations.values()) if self._consecutive_violations else 0
        consecutive_penalty = min(0.3, max_consecutive * 0.05)

        score = (ok_count / enabled) - consecutive_penalty
        return round(max(0.0, min(1.0, score)), 4)

    # ═══════════════════════════════════════════════════════
    # 永続化
    # ═══════════════════════════════════════════════════════
    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {
                "constraints": {cid: c.to_dict() for cid, c in self._constraints.items()},
                "consecutive_violations": dict(self._consecutive_violations),
                "total_checks": self._total_checks,
                "total_violations": self._total_violations,
                "total_penalties": self._total_penalties,
                "violations": [v.to_dict() for v in self._violations[-100:]],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            _log.warning("safety persist error: %s", e)

    def _restore(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))

            # 制約復元
            for cid, c_dict in data.get("constraints", {}).items():
                self._constraints[cid] = SafetyConstraint(**c_dict)

            self._consecutive_violations = defaultdict(
                int, data.get("consecutive_violations", {})
            )
            self._total_checks = data.get("total_checks", 0)
            self._total_violations = data.get("total_violations", 0)
            self._total_penalties = data.get("total_penalties", 0.0)

            for v_dict in data.get("violations", []):
                self._violations.append(Violation(**v_dict))
        except Exception as e:
            _log.warning("safety restore error: %s", e)
