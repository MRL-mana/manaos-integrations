#!/usr/bin/env python3
"""
ManaOS Computer Use System - Action Budget Manager
行動予算管理（無限ループ・暴走防止）
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from .manaos_computer_use_types import ActionType
except ImportError:
    from manaos_computer_use_types import ActionType

logger = logging.getLogger(__name__)


class BudgetType(Enum):
    """予算タイプ"""
    STEPS = "steps"      # ステップ数
    COST = "cost"        # コスト（ドル）
    TIME = "time"        # 時間（秒）


@dataclass
class Budget:
    """行動予算"""
    max_steps: Optional[int] = 50
    max_cost: Optional[float] = 1.0  # ドル
    max_time: Optional[float] = 300.0  # 秒（5分）
    
    # 現在の消費量
    current_steps: int = 0
    current_cost: float = 0.0
    current_time: float = 0.0
    
    # 開始時刻
    start_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def is_exhausted(self) -> bool:
        """予算を使い切ったか"""
        if self.max_steps and self.current_steps >= self.max_steps:
            return True
        
        if self.max_cost and self.current_cost >= self.max_cost:
            return True
        
        if self.max_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed >= self.max_time:
                return True
        
        return False
    
    def remaining(self) -> Dict[str, float]:
        """残り予算"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "steps": (self.max_steps - self.current_steps) if self.max_steps else float('inf'),
            "cost": (self.max_cost - self.current_cost) if self.max_cost else float('inf'),
            "time": (self.max_time - elapsed) if self.max_time else float('inf')
        }
    
    def percentage_used(self) -> Dict[str, float]:
        """使用率（%）"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "steps": (self.current_steps / self.max_steps * 100) if self.max_steps else 0,
            "cost": (self.current_cost / self.max_cost * 100) if self.max_cost else 0,
            "time": (elapsed / self.max_time * 100) if self.max_time else 0
        }


# アクションごとのコスト定義
ACTION_COSTS = {
    # 高コスト（AIビジョン使用）
    ActionType.SCREENSHOT: 0.001,  # $0.001 per screenshot
    
    # 中コスト（座標精緻化）
    ActionType.CLICK: 0.0001,
    ActionType.DOUBLE_CLICK: 0.0001,
    ActionType.RIGHT_CLICK: 0.0001,
    
    # 低コスト
    ActionType.TYPE_TEXT: 0.00001,
    ActionType.PRESS_KEY: 0.00001,
    ActionType.HOTKEY: 0.00001,
    ActionType.SCROLL: 0.00001,
    ActionType.DRAG: 0.0001,
    ActionType.WAIT: 0.0,
    ActionType.COMPLETE: 0.0
}


class BudgetTracker:
    """行動予算トラッカー"""
    
    def __init__(
        self,
        max_steps: Optional[int] = 50,
        max_cost: Optional[float] = 1.0,
        max_time: Optional[float] = 300.0
    ):
        """
        Args:
            max_steps: 最大ステップ数
            max_cost: 最大コスト（ドル）
            max_time: 最大時間（秒）
        """
        self.budget = Budget(
            max_steps=max_steps,
            max_cost=max_cost,
            max_time=max_time
        )
        
        logger.info(f"Budget initialized: {max_steps} steps, ${max_cost}, {max_time}s")
    
    def consume(
        self,
        action_type: ActionType,
        custom_cost: Optional[float] = None
    ) -> bool:
        """
        予算を消費
        
        Args:
            action_type: アクションタイプ
            custom_cost: カスタムコスト（指定しない場合はデフォルト）
        
        Returns:
            bool: 消費成功（予算内）
        """
        # ステップ数
        self.budget.current_steps += 1
        
        # コスト
        cost = custom_cost if custom_cost is not None else ACTION_COSTS.get(action_type, 0.0)
        self.budget.current_cost += cost
        
        # 時間は自動更新（start_timeからの経過時間）
        
        # 予算チェック
        if self.budget.is_exhausted():
            logger.warning(f"⚠️ Budget exhausted! Steps: {self.budget.current_steps}, "
                           f"Cost: ${self.budget.current_cost:.4f}, "
                           f"Time: {self.get_elapsed_time():.1f}s")
            return False
        
        return True
    
    def get_elapsed_time(self) -> float:
        """経過時間を取得（秒）"""
        return (datetime.now() - self.budget.start_time).total_seconds()
    
    def get_status(self) -> Dict[str, Any]:
        """予算状況を取得"""
        remaining = self.budget.remaining()
        percentage = self.budget.percentage_used()
        
        return {
            "current": {
                "steps": self.budget.current_steps,
                "cost": self.budget.current_cost,
                "time": self.get_elapsed_time()
            },
            "remaining": remaining,
            "percentage_used": percentage,
            "exhausted": self.budget.is_exhausted()
        }
    
    def warn_if_low(self, threshold: float = 0.8) -> None:
        """予算が少なくなったら警告"""
        percentage = self.budget.percentage_used()
        
        for budget_type, used_pct in percentage.items():
            if used_pct >= threshold * 100:
                remaining = self.budget.remaining()[budget_type]
                logger.warning(f"⚠️ Budget warning: {budget_type} at {used_pct:.1f}% "
                               f"(remaining: {remaining:.2f})")
    
    def estimate_remaining_actions(self, action_type: ActionType) -> int:
        """残り予算で実行可能なアクション数を推定"""
        cost_per_action = ACTION_COSTS.get(action_type, 0.0)
        
        remaining = self.budget.remaining()
        
        # 各予算タイプでの残り実行可能数
        by_steps = remaining["steps"] if self.budget.max_steps else float('inf')
        by_cost = (remaining["cost"] / cost_per_action) if cost_per_action > 0 else float('inf')
        by_time = remaining["time"] / 2.0  # 1アクション=2秒と仮定
        
        # 最小値を返す
        return int(min(by_steps, by_cost, by_time))


# ===== テスト用 =====

if __name__ == "__main__":
    print("💰 Action Budget Manager - テスト")
    print("=" * 60)
    
    # テスト1: 基本的な予算管理
    print("\n📌 Test 1: Basic budget tracking")
    tracker = BudgetTracker(max_steps=10, max_cost=0.01, max_time=5.0)
    
    for i in range(12):
        success = tracker.consume(ActionType.CLICK)
        status = tracker.get_status()
        
        print(f"Step {i+1}: Steps={status['current']['steps']}, "
              f"Cost=${status['current']['cost']:.4f}, "
              f"Time={status['current']['time']:.2f}s, "
              f"Success={success}")
        
        if not success:
            print("❌ Budget exhausted!")
            break
        
        time.sleep(0.2)
    
    # テスト2: 予算警告
    print("\n📌 Test 2: Budget warnings")
    tracker2 = BudgetTracker(max_steps=10, max_cost=0.1, max_time=10.0)
    
    for i in range(8):
        tracker2.consume(ActionType.SCREENSHOT)  # 高コスト
        tracker2.warn_if_low(threshold=0.7)
        time.sleep(0.1)
    
    # テスト3: 残り予算推定
    print("\n📌 Test 3: Estimate remaining actions")
    tracker3 = BudgetTracker(max_steps=100, max_cost=0.05, max_time=60.0)
    
    tracker3.consume(ActionType.SCREENSHOT)
    tracker3.consume(ActionType.SCREENSHOT)
    
    remaining_screenshots = tracker3.estimate_remaining_actions(ActionType.SCREENSHOT)
    remaining_clicks = tracker3.estimate_remaining_actions(ActionType.CLICK)
    
    print(f"Remaining screenshots: {remaining_screenshots}")
    print(f"Remaining clicks: {remaining_clicks}")
    
    print("\n✅ All tests completed")

