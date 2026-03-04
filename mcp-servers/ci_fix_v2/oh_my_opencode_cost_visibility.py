#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💰 OH MY OPENCODE コスト見える化システム
見積り・残予算メーター・原因分類
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("oh-my-opencode-cost-visibility")
error_handler = ManaOSErrorHandler("OHMyOpenCodeCostVisibility")


@dataclass
class CostEstimate:
    """コスト見積り"""
    task_type: str
    mode: str
    estimated_cost_min: float  # 最小見積り
    estimated_cost_max: float  # 最大見積り
    estimated_cost_avg: float  # 平均見積り
    confidence: float  # 信頼度（0.0-1.0）
    sample_count: int  # サンプル数
    reasoning: str  # 見積り根拠


@dataclass
class CostBreakdown:
    """コスト内訳"""
    total_cost: float
    search_cost: float  # 検索コスト
    loop_cost: float  # ループコスト
    model_cost: float  # モデルコスト
    context_cost: float  # コンテキストコスト
    breakdown_percentages: Dict[str, float]  # 内訳パーセンテージ


@dataclass
class BudgetMeter:
    """残予算メーター"""
    daily_budget: float
    daily_used: float
    daily_remaining: float
    daily_usage_percent: float
    monthly_budget: float
    monthly_used: float
    monthly_remaining: float
    monthly_usage_percent: float
    estimated_remaining_tasks: int  # 推定残りタスク数
    warning_level: str  # "safe", "warning", "critical"


class OHMyOpenCodeCostVisibility:
    """OH MY OPENCODE コスト見える化システム"""
    
    def __init__(
        self,
        cost_manager=None,
        optimizer=None
    ):
        """
        初期化
        
        Args:
            cost_manager: コスト管理インスタンス
            optimizer: 最適化システムインスタンス
        """
        self.cost_manager = cost_manager
        self.optimizer = optimizer
        
        logger.info("✅ Cost Visibility initialized")
    
    def estimate_cost(
        self,
        task_type: str,
        mode: str,
        task_description: str = ""
    ) -> CostEstimate:
        """
        コスト見積りを取得
        
        Args:
            task_type: タスクタイプ
            mode: 実行モード
            task_description: タスクの説明
        
        Returns:
            コスト見積り
        """
        # 最適化システムから履歴を取得
        if self.optimizer:
            stats = self.optimizer.get_statistics()
            pattern_key = f"{task_type}_{mode}"
            
            if pattern_key in stats.get("task_patterns", {}):
                pattern = stats["task_patterns"][pattern_key]
                avg_cost = pattern.get("avg_cost", 10.0)
                sample_count = pattern.get("sample_count", 0)
                
                # 見積り範囲（平均の±50%）
                estimated_min = avg_cost * 0.5
                estimated_max = avg_cost * 1.5
                estimated_avg = avg_cost
                
                # 信頼度（サンプル数に基づく）
                confidence = min(1.0, sample_count / 10.0)
                
                reasoning = (
                    f"過去{sample_count}件の実行履歴に基づく見積り。"
                    f"平均コスト: ${avg_cost:.2f}"
                )
                
                return CostEstimate(
                    task_type=task_type,
                    mode=mode,
                    estimated_cost_min=estimated_min,
                    estimated_cost_max=estimated_max,
                    estimated_cost_avg=estimated_avg,
                    confidence=confidence,
                    sample_count=sample_count,
                    reasoning=reasoning
                )
        
        # デフォルト見積り（履歴がない場合）
        if mode == "ultra_work":
            default_min, default_max, default_avg = 50.0, 150.0, 100.0
        else:
            default_min, default_max, default_avg = 2.0, 20.0, 10.0
        
        return CostEstimate(
            task_type=task_type,
            mode=mode,
            estimated_cost_min=default_min,
            estimated_cost_max=default_max,
            estimated_cost_avg=default_avg,
            confidence=0.3,
            sample_count=0,
            reasoning="履歴データが不足しています。デフォルト見積りを使用します。"
        )
    
    def get_budget_meter(self) -> BudgetMeter:
        """
        残予算メーターを取得
        
        Returns:
            残予算メーター
        """
        if not self.cost_manager:
            return BudgetMeter(
                daily_budget=100.0,
                daily_used=0.0,
                daily_remaining=100.0,
                daily_usage_percent=0.0,
                monthly_budget=2000.0,
                monthly_used=0.0,
                monthly_remaining=2000.0,
                monthly_usage_percent=0.0,
                estimated_remaining_tasks=0,
                warning_level="safe"
            )
        
        stats = self.cost_manager.get_statistics()
        
        daily_budget = stats.get("daily_limit", 100.0)
        daily_used = stats.get("daily_cost", 0.0)
        daily_remaining = daily_budget - daily_used
        daily_usage_percent = (daily_used / daily_budget * 100) if daily_budget > 0 else 0.0
        
        monthly_budget = stats.get("monthly_limit", 2000.0)
        monthly_used = stats.get("monthly_cost", 0.0)
        monthly_remaining = monthly_budget - monthly_used
        monthly_usage_percent = (monthly_used / monthly_budget * 100) if monthly_budget > 0 else 0.0
        
        # 推定残りタスク数（平均コストから計算）
        avg_cost = stats.get("avg_cost", 10.0)
        estimated_remaining_tasks = int(daily_remaining / avg_cost) if avg_cost > 0 else 0
        
        # 警告レベル
        if daily_usage_percent >= 90 or monthly_usage_percent >= 90:
            warning_level = "critical"
        elif daily_usage_percent >= 80 or monthly_usage_percent >= 80:
            warning_level = "warning"
        else:
            warning_level = "safe"
        
        return BudgetMeter(
            daily_budget=daily_budget,
            daily_used=daily_used,
            daily_remaining=daily_remaining,
            daily_usage_percent=daily_usage_percent,
            monthly_budget=monthly_budget,
            monthly_used=monthly_used,
            monthly_remaining=monthly_remaining,
            monthly_usage_percent=monthly_usage_percent,
            estimated_remaining_tasks=estimated_remaining_tasks,
            warning_level=warning_level
        )
    
    def analyze_cost_breakdown(
        self,
        task_id: str,
        total_cost: float,
        execution_data: Optional[Dict[str, Any]] = None
    ) -> CostBreakdown:
        """
        コスト内訳を分析
        
        Args:
            task_id: タスクID
            total_cost: 総コスト
            execution_data: 実行データ（検索回数、ループ回数、モデル、コンテキスト長など）
        
        Returns:
            コスト内訳
        """
        if not execution_data:
            # デフォルト内訳（データがない場合）
            return CostBreakdown(
                total_cost=total_cost,
                search_cost=total_cost * 0.1,
                loop_cost=total_cost * 0.3,
                model_cost=total_cost * 0.4,
                context_cost=total_cost * 0.2,
                breakdown_percentages={
                    "search": 10.0,
                    "loop": 30.0,
                    "model": 40.0,
                    "context": 20.0
                }
            )
        
        # 実行データから内訳を計算
        iterations = execution_data.get("iterations", 1)
        search_count = execution_data.get("search_count", 0)
        model_name = execution_data.get("model", "default")
        context_length = execution_data.get("context_length", 0)
        
        # 簡易的なコスト計算（実際のAPI仕様に基づいて調整が必要）
        # 検索コスト: 1回あたり$0.01
        search_cost = search_count * 0.01
        
        # ループコスト: 反復回数に比例（1回あたり$0.5）
        loop_cost = iterations * 0.5
        
        # モデルコスト: モデルとコンテキスト長に基づく（簡易計算）
        if "gpt-4" in model_name.lower() or "claude" in model_name.lower():
            model_base_cost = 0.03  # 1Kトークンあたり
        else:
            model_base_cost = 0.001  # ローカルモデル
        
        model_cost = (context_length / 1000) * model_base_cost * iterations
        
        # コンテキストコスト: コンテキスト長に比例
        context_cost = (context_length / 1000) * 0.002 * iterations
        
        # 合計がtotal_costを超えないように調整
        calculated_total = search_cost + loop_cost + model_cost + context_cost
        if calculated_total > total_cost:
            # 比率を保ったまま調整
            ratio = total_cost / calculated_total
            search_cost *= ratio
            loop_cost *= ratio
            model_cost *= ratio
            context_cost *= ratio
        else:
            # 残りをモデルコストに追加
            model_cost += (total_cost - calculated_total)
        
        # パーセンテージ計算
        breakdown_percentages = {
            "search": (search_cost / total_cost * 100) if total_cost > 0 else 0.0,
            "loop": (loop_cost / total_cost * 100) if total_cost > 0 else 0.0,
            "model": (model_cost / total_cost * 100) if total_cost > 0 else 0.0,
            "context": (context_cost / total_cost * 100) if total_cost > 0 else 0.0
        }
        
        return CostBreakdown(
            total_cost=total_cost,
            search_cost=search_cost,
            loop_cost=loop_cost,
            model_cost=model_cost,
            context_cost=context_cost,
            breakdown_percentages=breakdown_percentages
        )
    
    def classify_cost_cause(
        self,
        cost_breakdown: CostBreakdown,
        execution_data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        高コストの原因を分類
        
        Args:
            cost_breakdown: コスト内訳
            execution_data: 実行データ
        
        Returns:
            原因分類のリスト
        """
        causes = []
        
        # 検索が多い
        if cost_breakdown.breakdown_percentages.get("search", 0) > 20:
            causes.append("検索が多い（検索コストが20%超）")
        
        # ループが多い
        if cost_breakdown.breakdown_percentages.get("loop", 0) > 40:
            causes.append("ループが多い（ループコストが40%超）")
        
        # モデルが重い
        if cost_breakdown.breakdown_percentages.get("model", 0) > 60:
            causes.append("モデルが重い（モデルコストが60%超）")
        
        # コンテキストが長い
        if cost_breakdown.breakdown_percentages.get("context", 0) > 30:
            causes.append("コンテキストが長い（コンテキストコストが30%超）")
        
        # 実行データから追加の原因を特定
        if execution_data:
            iterations = execution_data.get("iterations", 0)
            if iterations > 10:
                causes.append(f"反復回数が多い（{iterations}回）")
            
            search_count = execution_data.get("search_count", 0)
            if search_count > 5:
                causes.append(f"検索回数が多い（{search_count}回）")
        
        if not causes:
            causes.append("原因不明（標準的なコスト分布）")
        
        return causes


# 使用例
if __name__ == "__main__":
    visibility = OHMyOpenCodeCostVisibility()
    
    # コスト見積り
    estimate = visibility.estimate_cost("code_generation", "normal")
    print(f"コスト見積り: ${estimate.estimated_cost_min:.2f} - ${estimate.estimated_cost_max:.2f}")
    
    # 残予算メーター
    meter = visibility.get_budget_meter()
    print(f"日次残予算: ${meter.daily_remaining:.2f} ({meter.daily_usage_percent:.1f}%使用)")
    
    # コスト内訳
    breakdown = visibility.analyze_cost_breakdown(
        "test_task_1",
        10.0,
        {"iterations": 3, "search_count": 2, "model": "gpt-4", "context_length": 5000}
    )
    print(f"コスト内訳: {breakdown.breakdown_percentages}")
    
    # 原因分類
    causes = visibility.classify_cost_cause(breakdown, {"iterations": 3, "search_count": 2})
    print(f"高コストの原因: {causes}")
