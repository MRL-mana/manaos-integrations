#!/usr/bin/env python3
"""
ManaOS Computer Use System - Dynamic Budget Adjuster
タスク難易度に応じた動的予算調整
"""

import re
from typing import Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskDifficulty(Enum):
    """タスク難易度"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"


class DynamicBudgetAdjuster:
    """動的予算調整器"""
    
    # 難易度キーワード
    DIFFICULTY_KEYWORDS = {
        TaskDifficulty.EASY: [
            "開く", "閉じる", "起動", "終了",
            "open", "close", "launch", "quit"
        ],
        TaskDifficulty.MEDIUM: [
            "入力", "保存", "コピー", "貼り付け",
            "type", "save", "copy", "paste",
            "クリック", "click"
        ],
        TaskDifficulty.HARD: [
            "検索", "編集", "変換", "整理",
            "search", "edit", "convert", "organize",
            "複数", "multiple", "繰り返し", "repeat"
        ],
        TaskDifficulty.VERY_HARD: [
            "自動化", "スクレイピング", "解析",
            "automation", "scraping", "analysis",
            "複雑", "complex", "高度", "advanced"
        ]
    }
    
    # 難易度別のデフォルト予算
    DEFAULT_BUDGETS = {
        TaskDifficulty.EASY: {
            "max_steps": 20,
            "max_cost": 0.3,
            "max_time": 60.0
        },
        TaskDifficulty.MEDIUM: {
            "max_steps": 50,
            "max_cost": 1.0,
            "max_time": 300.0
        },
        TaskDifficulty.HARD: {
            "max_steps": 100,
            "max_cost": 2.0,
            "max_time": 600.0
        },
        TaskDifficulty.VERY_HARD: {
            "max_steps": 200,
            "max_cost": 5.0,
            "max_time": 1200.0
        }
    }
    
    def __init__(self):
        self.history = []  # 過去の実行履歴
    
    def estimate_difficulty(self, task: str) -> TaskDifficulty:
        """
        タスク文字列から難易度を推定
        
        Args:
            task: タスク記述
        
        Returns:
            TaskDifficulty: 推定難易度
        """
        task_lower = task.lower()
        
        # スコアリング
        scores = {difficulty: 0 for difficulty in TaskDifficulty}
        
        for difficulty, keywords in self.DIFFICULTY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_lower:
                    scores[difficulty] += 1
        
        # タスクの長さも考慮
        word_count = len(task.split())
        if word_count > 20:
            scores[TaskDifficulty.VERY_HARD] += 2
        elif word_count > 10:
            scores[TaskDifficulty.HARD] += 1
        
        # 「複数」「繰り返し」などの複雑性指標
        if re.search(r'\d+回|複数|すべて|全て', task_lower):
            scores[TaskDifficulty.HARD] += 2
        
        # 最高スコアの難易度を返す
        max_difficulty = max(scores.items(), key=lambda x: x[1])
        
        # スコアが0の場合はデフォルトでMEDIUM
        if max_difficulty[1] == 0:
            return TaskDifficulty.MEDIUM
        
        return max_difficulty[0]
    
    def adjust_budget(
        self,
        task: str,
        base_budget: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        タスク難易度に基づいて予算を調整
        
        Args:
            task: タスク記述
            base_budget: ベース予算（指定しない場合は難易度デフォルト）
        
        Returns:
            Dict: 調整後の予算
        """
        difficulty = self.estimate_difficulty(task)
        
        logger.info(f"Task difficulty estimated: {difficulty.value}")
        
        # デフォルト予算を取得
        if base_budget is None:
            budget = self.DEFAULT_BUDGETS[difficulty].copy()
        else:
            budget = base_budget.copy()
            
            # 難易度に応じて調整
            multiplier = self._get_difficulty_multiplier(difficulty)
            budget["max_steps"] = int(budget.get("max_steps", 50) * multiplier)
            budget["max_cost"] = budget.get("max_cost", 1.0) * multiplier
            budget["max_time"] = budget.get("max_time", 300.0) * multiplier
        
        # 過去の実行履歴から微調整
        if self.history:
            budget = self._apply_historical_adjustment(task, budget)
        
        logger.info(f"Adjusted budget: steps={budget['max_steps']}, "
                    f"cost=${budget['max_cost']:.2f}, time={budget['max_time']:.0f}s")
        
        return budget
    
    def _get_difficulty_multiplier(self, difficulty: TaskDifficulty) -> float:
        """難易度に対応する倍率を取得"""
        multipliers = {
            TaskDifficulty.EASY: 0.5,
            TaskDifficulty.MEDIUM: 1.0,
            TaskDifficulty.HARD: 2.0,
            TaskDifficulty.VERY_HARD: 4.0
        }
        return multipliers.get(difficulty, 1.0)
    
    def _apply_historical_adjustment(
        self,
        task: str,
        budget: Dict[str, float]
    ) -> Dict[str, float]:
        """過去の実行履歴から微調整"""
        # 類似タスクの実行結果を検索
        similar_tasks = [
            h for h in self.history
            if self._task_similarity(task, h["task"]) > 0.7
        ]
        
        if not similar_tasks:
            return budget
        
        # 平均実行時間を計算
        avg_steps = statistics.mean([h["steps"] for h in similar_tasks])
        avg_cost = statistics.mean([h["cost"] for h in similar_tasks])
        avg_time = statistics.mean([h["time"] for h in similar_tasks])
        
        # 安全マージン（1.3倍）
        budget["max_steps"] = int(avg_steps * 1.3)
        budget["max_cost"] = avg_cost * 1.3
        budget["max_time"] = avg_time * 1.3
        
        logger.info(f"Applied historical adjustment based on {len(similar_tasks)} similar tasks")
        
        return budget
    
    def _task_similarity(self, task1: str, task2: str) -> float:
        """2つのタスクの類似度を計算（簡易版）"""
        words1 = set(task1.lower().split())
        words2 = set(task2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard係数
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def record_execution(
        self,
        task: str,
        steps: int,
        cost: float,
        time_seconds: float,
        success: bool
    ) -> None:
        """実行結果を記録（学習用）"""
        self.history.append({
            "task": task,
            "steps": steps,
            "cost": cost,
            "time": time_seconds,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        
        # 最新100件のみ保持
        if len(self.history) > 100:
            self.history = self.history[-100:]


# ===== テスト用 =====

if __name__ == "__main__":
    print("💰 Dynamic Budget Adjuster - テスト")
    print("=" * 60)
    
    adjuster = DynamicBudgetAdjuster()
    
    # テストタスク
    test_tasks = [
        "メモ帳を開く",
        "ファイルを保存して閉じる",
        "Webページから複数の画像をダウンロード",
        "PDFを解析してExcelに変換し、Googleドライブにアップロード"
    ]
    
    print("\n🎯 Task difficulty estimation:")
    print("-" * 60)
    
    for task in test_tasks:
        difficulty = adjuster.estimate_difficulty(task)
        budget = adjuster.adjust_budget(task)
        
        print(f"\nTask: {task}")
        print(f"  Difficulty: {difficulty.value}")
        print("  Budget:")
        print(f"    Steps: {budget['max_steps']}")
        print(f"    Cost: ${budget['max_cost']:.2f}")
        print(f"    Time: {budget['max_time']:.0f}s")
    
    print("\n✅ Test completed")

