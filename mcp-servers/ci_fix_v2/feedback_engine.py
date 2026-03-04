#!/usr/bin/env python3
"""
Phase 2: フィードバックエンジン (Feedback Engine)
=================================================
RLAnything の 3 つのフィードバックループを実装:

1. 統合フィードバック (Integration Feedback)
   - 途中経過スコア + 最終結果 → 方策改善シグナル
2. 一貫性フィードバック (Consistency Feedback)
   - 成功事例から逆算 → 報酬モデル（採点基準）自体を修正
3. 評価フィードバック (Evaluation Feedback / Curriculum)
   - 成功率に基づく環境（難易度）の自動調整
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .types import (
    DifficultyLevel,
    FeedbackType,
    RewardSignal,
    Skill,
    TaskOutcome,
    TaskRecord,
    ToolAction,
)

_DIR = Path(__file__).parent


class FeedbackEngine:
    """Phase 2: 3 要素フィードバック分析"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or self._load_config()
        self._reward_cfg = cfg.get("reward_model", {})
        self._curriculum_cfg = cfg.get("curriculum", {})

        # 報酬モデルの採点基準（一貫性フィードバックで動的に更新される）
        self.scoring_criteria: Dict[str, float] = dict(
            self._reward_cfg.get("scoring_criteria", {
                "test_written_first": 0.15,
                "error_handled": 0.10,
                "code_commented": 0.05,
                "single_responsibility": 0.10,
                "no_regressions": 0.20,
                "task_completed": 0.40,
            })
        )

        # カリキュラム設定
        self.target_success_rate: float = self._curriculum_cfg.get("target_success_rate", 0.80)
        self.window_size: int = self._curriculum_cfg.get("window_size", 20)

        # 報酬シグナルの履歴
        self._reward_history: List[RewardSignal] = []
        self._criteria_update_log: List[Dict[str, Any]] = []

        # 永続化パス
        self._data_dir = _DIR.parent / "logs" / "rl_anything"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load_state()

    # ═══════════════════════════════════════════════════════
    # 1. 統合フィードバック (Integration Feedback)
    # ═══════════════════════════════════════════════════════
    def compute_integration_feedback(self, record: TaskRecord) -> RewardSignal:
        """
        途中経過のスコアと最終結果を統合して総合報酬を算出。
        「テストに落ちたけど設計は良かった」→ 設計部分を部分評価する。
        """
        int_weight = self._reward_cfg.get("intermediate_weight", 0.4)
        fin_weight = self._reward_cfg.get("final_weight", 0.6)

        # 中間スコアの平均（なければ 0.5）
        if record.intermediate_scores:
            intermediate_avg = statistics.mean(record.intermediate_scores)
        else:
            intermediate_avg = 0.5

        # 最終スコア（なければ outcome から推定）
        if record.final_score is not None:
            final = record.final_score
        else:
            final = {
                TaskOutcome.SUCCESS: 1.0,
                TaskOutcome.PARTIAL: 0.5,
                TaskOutcome.FAILURE: 0.0,
                TaskOutcome.UNKNOWN: 0.3,
            }.get(record.outcome, 0.3)

        # 統合スコア
        integrated = intermediate_avg * int_weight + final * fin_weight

        # アクション品質ボーナス
        action_bonus = self._evaluate_action_quality(record.actions)
        integrated = min(1.0, integrated + action_bonus * 0.1)

        reasoning_parts = [
            f"intermediate_avg={intermediate_avg:.2f} (weight={int_weight})",
            f"final={final:.2f} (weight={fin_weight})",
            f"action_bonus={action_bonus:.2f}",
            f"outcome={record.outcome.value}",
        ]

        signal = RewardSignal(
            task_id=record.task_id,
            feedback_type=FeedbackType.INTEGRATION,
            score=round(integrated, 4),
            reasoning=" | ".join(reasoning_parts),
        )
        self._reward_history.append(signal)
        self._save_reward(signal)
        return signal

    def _evaluate_action_quality(self, actions: List[ToolAction]) -> float:
        """
        アクション列の品質を 0..1 で評価。
        採点基準 (scoring_criteria) に基づく。
        """
        if not actions:
            return 0.0

        score = 0.0
        total_weight = sum(self.scoring_criteria.values()) or 1.0

        # ヒューリスティクス: ツール名やエラー有無からパターンを検出
        tool_names = [a.tool_name.lower() for a in actions]
        results = [a.result_summary.lower() for a in actions]
        errors = [a for a in actions if a.error]
        all_text = " ".join(tool_names + results)

        # test_written_first: テスト系ツールが前半に登場
        if self.scoring_criteria.get("test_written_first", 0):
            test_tools = [i for i, t in enumerate(tool_names) if "test" in t]
            if test_tools and test_tools[0] < len(tool_names) * 0.4:
                score += self.scoring_criteria["test_written_first"]

        # error_handled: エラーが発生しても回復した
        if self.scoring_criteria.get("error_handled", 0):
            if errors and len(errors) < len(actions):
                # エラー後に正常アクションがある = リカバリー
                last_error_idx = max(
                    i for i, a in enumerate(actions) if a.error
                )
                if last_error_idx < len(actions) - 1:
                    score += self.scoring_criteria["error_handled"]

        # code_commented: コメント記述が含まれる
        if self.scoring_criteria.get("code_commented", 0):
            if "comment" in all_text or "docstring" in all_text or "document" in all_text:
                score += self.scoring_criteria["code_commented"]

        # single_responsibility: ファイル数が多すぎない
        if self.scoring_criteria.get("single_responsibility", 0):
            file_tools = [t for t in tool_names if "file" in t or "edit" in t or "create" in t]
            if 0 < len(file_tools) <= 5:
                score += self.scoring_criteria["single_responsibility"]

        # no_regressions: テスト失敗が途中で起きていない
        if self.scoring_criteria.get("no_regressions", 0):
            regression_keywords = ["fail", "error", "broken", "regression"]
            regression_count = sum(
                1 for r in results if any(k in r for k in regression_keywords)
            )
            if regression_count == 0:
                score += self.scoring_criteria["no_regressions"]

        # task_completed: 最終アクションが成功的
        if self.scoring_criteria.get("task_completed", 0):
            if actions and not actions[-1].error:
                score += self.scoring_criteria["task_completed"]

        return round(score / total_weight, 4)

    # ═══════════════════════════════════════════════════════
    # 2. 一貫性フィードバック (Consistency Feedback)
    # ═══════════════════════════════════════════════════════
    def compute_consistency_feedback(
        self,
        completed_records: List[TaskRecord],
    ) -> RewardSignal:
        """
        成功事例と失敗事例の差分から報酬モデル（採点基準）を更新する。
        「コメントが書かれているコードの方が成功率が高い」
        → scoring_criteria["code_commented"] を引き上げる。
        """
        if len(completed_records) < 5:
            return RewardSignal(
                task_id="system",
                feedback_type=FeedbackType.CONSISTENCY,
                score=0.0,
                reasoning="データ不足（5件未満）",
            )

        successes = [r for r in completed_records if r.outcome == TaskOutcome.SUCCESS]
        failures = [r for r in completed_records if r.outcome == TaskOutcome.FAILURE]

        if not successes or not failures:
            return RewardSignal(
                task_id="system",
                feedback_type=FeedbackType.CONSISTENCY,
                score=0.5,
                reasoning="成功 or 失敗が0件で比較不可",
            )

        # 各パターンの出現率を比較
        patterns = self._extract_patterns(successes, failures)
        adjustments: Dict[str, Any] = {}

        for pattern_name, (success_rate, failure_rate) in patterns.items():
            delta = success_rate - failure_rate
            if abs(delta) > 0.1:  # 10% 以上の差
                # 成功事例で多いパターン → 基準を引き上げ
                criterion_key = self._map_pattern_to_criterion(pattern_name)
                if criterion_key and criterion_key in self.scoring_criteria:
                    old_val = self.scoring_criteria[criterion_key]
                    # 学習率 0.1 で漸進更新
                    new_val = old_val + delta * 0.1
                    new_val = max(0.01, min(0.50, new_val))  # クリッピング
                    self.scoring_criteria[criterion_key] = round(new_val, 4)
                    adjustments[criterion_key] = {
                        "old": old_val,
                        "new": self.scoring_criteria[criterion_key],
                        "delta": round(delta, 4),
                        "pattern": pattern_name,
                    }

        # 正規化（合計 1.0 に）
        total = sum(self.scoring_criteria.values())
        if total > 0:
            for k in self.scoring_criteria:
                self.scoring_criteria[k] = round(self.scoring_criteria[k] / total, 4)

        reasoning = f"patterns_analyzed={len(patterns)} adjustments={len(adjustments)}"
        signal = RewardSignal(
            task_id="system",
            feedback_type=FeedbackType.CONSISTENCY,
            score=len(adjustments) / max(len(patterns), 1),
            reasoning=reasoning,
            adjustments=adjustments,
        )

        self._reward_history.append(signal)
        self._save_reward(signal)

        if adjustments:
            self._criteria_update_log.append({
                "ts": datetime.now().isoformat(),
                "adjustments": adjustments,
                "new_criteria": dict(self.scoring_criteria),
            })
            self._save_criteria()

        return signal

    def _extract_patterns(
        self,
        successes: List[TaskRecord],
        failures: List[TaskRecord],
    ) -> Dict[str, Tuple[float, float]]:
        """成功群・失敗群それぞれのパターン出現率を計算"""
        pattern_names = [
            "test_first",
            "error_recovery",
            "comments_present",
            "few_files_touched",
            "no_errors",
            "short_actions",
            "long_actions",
        ]

        result: Dict[str, Tuple[float, float]] = {}

        for pname in pattern_names:
            s_count = sum(1 for r in successes if self._has_pattern(r, pname))
            f_count = sum(1 for r in failures if self._has_pattern(r, pname))
            s_rate = s_count / len(successes) if successes else 0
            f_rate = f_count / len(failures) if failures else 0
            result[pname] = (s_rate, f_rate)

        return result

    def _has_pattern(self, record: TaskRecord, pattern: str) -> bool:
        """レコードが特定パターンに該当するか"""
        tools = [a.tool_name.lower() for a in record.actions]
        errors = [a for a in record.actions if a.error]

        if pattern == "test_first":
            test_idx = [i for i, t in enumerate(tools) if "test" in t]
            return bool(test_idx and test_idx[0] < len(tools) * 0.3)
        elif pattern == "error_recovery":
            return bool(errors) and record.outcome == TaskOutcome.SUCCESS
        elif pattern == "comments_present":
            all_text = " ".join(a.result_summary.lower() for a in record.actions)
            return "comment" in all_text or "docstring" in all_text
        elif pattern == "few_files_touched":
            return len(record.actions) <= 10
        elif pattern == "no_errors":
            return len(errors) == 0
        elif pattern == "short_actions":
            return len(record.actions) <= 5
        elif pattern == "long_actions":
            return len(record.actions) > 15
        return False

    def _map_pattern_to_criterion(self, pattern: str) -> Optional[str]:
        """パターン名 → scoring_criteria のキーにマップ"""
        mapping = {
            "test_first": "test_written_first",
            "error_recovery": "error_handled",
            "comments_present": "code_commented",
            "few_files_touched": "single_responsibility",
            "no_errors": "no_regressions",
        }
        return mapping.get(pattern)

    # ═══════════════════════════════════════════════════════
    # 3. 評価フィードバック / カリキュラム (Curriculum)
    # ═══════════════════════════════════════════════════════
    def compute_evaluation_feedback(
        self,
        completed_records: List[TaskRecord],
    ) -> Tuple[DifficultyLevel, RewardSignal]:
        """
        直近 window_size 件の成功率から推奨難易度を算出。
        成功率 80% 前後が最も学習効率が高い (zone of proximal development)。
        """
        window = completed_records[-self.window_size:]
        if not window:
            return DifficultyLevel.STANDARD, RewardSignal(
                task_id="system",
                feedback_type=FeedbackType.EVALUATION,
                score=0.5,
                reasoning="データなし → standard",
            )

        success_count = sum(1 for r in window if r.outcome == TaskOutcome.SUCCESS)
        rate = success_count / len(window)

        levels = self._curriculum_cfg.get("difficulty_levels", {})
        recommended = DifficultyLevel.STANDARD

        for level_name, bounds in levels.items():
            if bounds.get("min_rate", 0) <= rate < bounds.get("max_rate", 1):
                try:
                    recommended = DifficultyLevel(level_name)
                except ValueError:
                    pass
                break

        # 現在難易度との比較
        current_difficulties = Counter(r.difficulty for r in window)
        most_common = current_difficulties.most_common(1)
        current = most_common[0][0] if most_common else DifficultyLevel.STANDARD

        reasoning = (
            f"success_rate={rate:.2f} window={len(window)} "
            f"current={current.value} recommended={recommended.value}"
        )

        signal = RewardSignal(
            task_id="system",
            feedback_type=FeedbackType.EVALUATION,
            score=rate,
            reasoning=reasoning,
            adjustments={
                "success_rate": round(rate, 4),
                "current_difficulty": current.value,
                "recommended_difficulty": recommended.value,
                "should_adjust": current != recommended,
            },
        )
        self._reward_history.append(signal)
        self._save_reward(signal)
        return recommended, signal

    # ═══════════════════════════════════════════════════════
    # 統合: 3 フィードバック一括実行
    # ═══════════════════════════════════════════════════════
    def run_full_feedback_cycle(
        self,
        latest_record: TaskRecord,
        all_records: List[TaskRecord],
    ) -> Dict[str, Any]:
        """3 つのフィードバックを一括実行し結果をまとめて返す"""
        # 1) 統合
        integration = self.compute_integration_feedback(latest_record)

        # 2) 一貫性 (一定件数ごと)
        consistency = None
        if len(all_records) >= 5 and len(all_records) % 5 == 0:
            consistency = self.compute_consistency_feedback(all_records)

        # 3) 評価 / カリキュラム
        recommended_difficulty, evaluation = self.compute_evaluation_feedback(all_records)

        return {
            "integration": integration.to_dict(),
            "consistency": consistency.to_dict() if consistency else None,
            "evaluation": evaluation.to_dict(),
            "recommended_difficulty": recommended_difficulty.value,
            "scoring_criteria": dict(self.scoring_criteria),
            "timestamp": datetime.now().isoformat(),
        }

    # ═══════════════════════════════════════════════════════
    # ステート管理
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        return {
            "reward_signals": len(self._reward_history),
            "criteria_updates": len(self._criteria_update_log),
            "scoring_criteria": dict(self.scoring_criteria),
            "target_success_rate": self.target_success_rate,
            "window_size": self.window_size,
        }

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        cfg_path = _DIR / "config.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_state(self) -> None:
        """採点基準の永続状態を読み込み"""
        criteria_file = self._data_dir / "scoring_criteria.json"
        if criteria_file.exists():
            try:
                with open(criteria_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved = data.get("criteria", {})
                    if saved:
                        self.scoring_criteria = saved
            except Exception:
                pass

    def _save_criteria(self) -> None:
        criteria_file = self._data_dir / "scoring_criteria.json"
        try:
            with open(criteria_file, "w", encoding="utf-8") as f:
                json.dump({
                    "criteria": self.scoring_criteria,
                    "update_log": self._criteria_update_log[-20:],
                    "updated_at": datetime.now().isoformat(),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_reward(self, signal: RewardSignal) -> None:
        rewards_file = self._data_dir / "reward_signals.jsonl"
        try:
            with open(rewards_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(signal.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass
