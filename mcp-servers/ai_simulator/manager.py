"""
Evolution Manager: 実験計画・比較・ロールアウト担当
UCB1 Bandit実装
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class Variant:
    """バリアント（実験候補）"""
    id: str
    task: str
    params: Dict[str, Any]
    pulls: int = 0
    reward_sum: float = 0.0
    reward_avg: float = 0.0
    description: str = ""
    
    def update_reward(self, reward: float):
        """リワード更新"""
        self.pulls += 1
        self.reward_sum += reward
        self.reward_avg = self.reward_sum / self.pulls


class UCB1:
    """UCB1 (Upper Confidence Bound 1) アルゴリズム"""
    
    def __init__(self, variants: List[Variant], exploration_rate: float = 2.0):
        """
        :param variants: バリアントリスト
        :param exploration_rate: 探索係数（デフォルト2.0）
        """
        self.variants = {v.id: v for v in variants}
        self.exploration_rate = exploration_rate
        self.total_pulls = 0
    
    def select(self) -> Variant:
        """次のバリアントを選択"""
        self.total_pulls += 1
        
        # 未試行のバリアントがあれば優先
        untried = [v for v in self.variants.values() if v.pulls == 0]
        if untried:
            selected = random.choice(untried)
            logger.debug(f"UCB1: Selected untried variant {selected.id}")
            return selected
        
        # UCB1式で選択
        def ucb_score(v: Variant) -> float:
            if v.pulls == 0:
                return float('inf')
            # avg_reward + exploration_rate * sqrt(ln(total_pulls) / pulls)
            exploration_bonus = self.exploration_rate * math.sqrt(
                math.log(self.total_pulls) / v.pulls
            )
            return v.reward_avg + exploration_bonus
        
        selected = max(self.variants.values(), key=ucb_score)
        logger.debug(
            f"UCB1: Selected {selected.id} "
            f"(avg={selected.reward_avg:.3f}, pulls={selected.pulls}, "
            f"ucb={ucb_score(selected):.3f})"
        )
        return selected
    
    def update(self, variant_id: str, reward: float):
        """リワード更新"""
        if variant_id in self.variants:
            self.variants[variant_id].update_reward(reward)
        else:
            logger.warning(f"Variant {variant_id} not found for update")
    
    def get_best_variant(self) -> Optional[Variant]:
        """最良バリアントを取得（最低限の試行回数が必要）"""
        min_pulls = 5  # 最低5回試行が必要
        candidates = [v for v in self.variants.values() if v.pulls >= min_pulls]
        if not candidates:
            return None
        return max(candidates, key=lambda v: v.reward_avg)
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "total_pulls": self.total_pulls,
            "variants": [
                {
                    "id": v.id,
                    "pulls": v.pulls,
                    "reward_avg": v.reward_avg,
                    "reward_sum": v.reward_sum,
                }
                for v in self.variants.values()
            ],
            "best_variant": self.get_best_variant().id if self.get_best_variant() else None,
        }
