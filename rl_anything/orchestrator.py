#!/usr/bin/env python3
"""
RLAnything オーケストレータ
===========================
3 要素（方策・報酬・環境）を束ね、自己進化ループを駆動する司令塔。

使い方:
  from rl_anything.orchestrator import RLAnythingOrchestrator

  rl = RLAnythingOrchestrator()

  # タスク開始
  rl.begin_task("task-001", "Reactコンポーネントにテストを追加")

  # ツール使用を記録 (post_tool_use_hook)
  rl.log_tool("read_file", {"path": "src/App.tsx"}, result="...")
  rl.log_tool("create_file", {"path": "src/App.test.tsx"}, result="...")

  # 途中スコア (例: lint 通過)
  rl.score_intermediate("task-001", 0.8, "lint pass")

  # タスク終了 → 自動で 3 フィードバック + 進化
  result = rl.end_task("task-001", outcome="success", score=0.95)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import DifficultyLevel, TaskOutcome, TaskRecord
from .observation_hook import ObservationHook
from .feedback_engine import FeedbackEngine
from .evolution_engine import EvolutionEngine

_DIR = Path(__file__).parent


class RLAnythingOrchestrator:
    """
    3 要素同時最適化の司令塔。
    各フェーズを統合し、タスクごとに自己進化ループを回す。
    """

    def __init__(self, config_path: Optional[Path] = None):
        cfg = self._load_config(config_path)

        # 3 コンポーネント
        self.observer = ObservationHook(config=cfg)
        self.feedback = FeedbackEngine(config=cfg)
        self.evolution = EvolutionEngine(config=cfg)

        # ループカウンタ
        self._cycle_count = 0

    # ═══════════════════════════════════════════════════════
    # タスクライフサイクル
    # ═══════════════════════════════════════════════════════
    def begin_task(
        self,
        task_id: str,
        description: str,
        difficulty: Optional[str] = None,
    ) -> None:
        """タスク開始 — 難易度は指定がなければ進化エンジンの推奨値"""
        diff = difficulty or self.evolution.current_difficulty.value
        self.observer.on_task_start(task_id, description, difficulty=diff)

    def log_tool(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        result: Any = None,
        error: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """ツール使用を記録 (post_tool_use_hook 相当)"""
        self.observer.on_tool_start(tool_name, params or {}, task_id=task_id)
        self.observer.on_tool_end(tool_name, result=result, error=error, task_id=task_id)

    def score_intermediate(self, task_id: str, score: float, reason: str = "") -> None:
        """途中経過スコア (統合フィードバック用)"""
        self.observer.on_intermediate_score(task_id, score, reason)

    def end_task(
        self,
        task_id: str,
        outcome: str = "unknown",
        score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        タスク終了 → 自動スコアリング + 3 フィードバック + 進化サイクルを自動実行。
        score が None の場合、ヒューリスティックで自動計算する。
        """
        # 0) 自動スコアリング (score 未指定時)
        if score is None:
            score = self._auto_score(task_id, outcome)

        # 1) 観測完了
        record = self.observer.on_task_end(
            task_id, outcome=outcome, final_score=score, metadata=metadata
        )
        all_records = self.observer.get_completed_records(limit=200)

        # 2) フィードバック
        fb_result = self.feedback.run_full_feedback_cycle(record, all_records)

        # 3) 進化
        recommended = DifficultyLevel(fb_result["recommended_difficulty"])
        eval_data = fb_result.get("evaluation", {})
        success_rate = (eval_data.get("adjustments") or {}).get("success_rate", 0.5)

        evo_result = self.evolution.run_evolution_cycle(
            all_records, recommended, success_rate
        )

        self._cycle_count += 1

        return {
            "task_id": task_id,
            "outcome": outcome,
            "cycle": self._cycle_count,
            "feedback": fb_result,
            "evolution": evo_result,
            "stats": self.get_dashboard(),
        }

    # ═══════════════════════════════════════════════════════
    # 自動スコアリング
    # ═══════════════════════════════════════════════════════
    def _auto_score(self, task_id: str, outcome: str) -> float:
        """
        スコア未指定時のヒューリスティック自動計算。
        - outcome ベース (success=0.7, partial=0.5, failure=0.2, unknown=0.4)
        - エラー率で減点 (error / total_actions)
        - 中間スコアがあればその平均を加味
        - アクション数が極端に少ない or 多い場合の補正
        """
        # ベーススコア
        base_scores = {
            "success": 0.75,
            "partial": 0.50,
            "failure": 0.20,
            "unknown": 0.40,
        }
        score = base_scores.get(outcome, 0.40)

        # アクティブタスクの情報を参照
        record = self.observer._active_tasks.get(task_id)
        if record is None:
            return round(score, 4)

        actions = record.actions
        total = len(actions)

        if total > 0:
            # エラー率で減点 (最大 -0.25)
            error_count = sum(1 for a in actions if a.error)
            error_ratio = error_count / total
            score -= error_ratio * 0.25

            # アクション数のスイートスポット補正 (3-15 が理想)
            if total <= 2:
                score -= 0.05  # 少なすぎ: やっとけ感
            elif total > 30:
                score -= 0.10  # 多すぎ: 試行錯誤しすぎ

        # 中間スコアの平均を加味 (30%ウェイト)
        intermediate = record.intermediate_scores
        if intermediate:
            avg_inter = sum(intermediate) / len(intermediate)
            score = score * 0.7 + avg_inter * 0.3

        return round(max(0.0, min(1.0, score)), 4)

    # ═══════════════════════════════════════════════════════
    # ダッシュボード
    # ═══════════════════════════════════════════════════════
    def get_dashboard(self) -> Dict[str, Any]:
        """システム全体のステータス"""
        return {
            "observation": self.observer.get_stats(),
            "feedback": self.feedback.get_stats(),
            "evolution": self.evolution.get_stats(),
            "cycle_count": self._cycle_count,
            "current_difficulty": self.evolution.current_difficulty.value,
            "scoring_criteria": dict(self.feedback.scoring_criteria),
            "timestamp": datetime.now().isoformat(),
        }

    def get_skills_for_prompt(self) -> str:
        """
        現在のスキルをプロンプトに含められる形式で返す。
        CLAUDE.md や MEMORY.md に注入して方策を改善する。
        """
        if not self.evolution.skills:
            return ""

        lines = ["# 学習済み行動パターン（自動生成）", ""]
        sorted_skills = sorted(
            self.evolution.skills, key=lambda s: s.success_rate, reverse=True
        )
        for skill in sorted_skills[:10]:
            lines.append(
                f"- {skill.name}: {skill.description} "
                f"(成功率 {skill.success_rate:.0%})"
            )

        difficulty_hint = self.evolution._difficulty_to_instruction_hint(
            self.evolution.current_difficulty
        )
        lines.append("")
        lines.append(f"# 現在の難易度: {self.evolution.current_difficulty.value}")
        lines.append(difficulty_hint)

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    # 設定
    # ═══════════════════════════════════════════════════════
    @staticmethod
    def _load_config(path: Optional[Path] = None) -> Dict[str, Any]:
        cfg_path = path or (_DIR / "config.json")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
