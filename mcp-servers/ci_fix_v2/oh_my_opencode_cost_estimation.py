#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💰 OH MY OPENCODE 見積り表自動生成システム
運用ログから見積り表を自動生成
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("oh-my-opencode-cost-estimation")
error_handler = ManaOSErrorHandler("OHMyOpenCodeCostEstimation")


@dataclass
class TaskTypeEstimate:
    """TaskType別見積り"""
    task_type: str
    avg_cost: float  # 平均コスト
    min_cost: float  # 最小コスト
    max_cost: float  # 最大コスト
    avg_time_minutes: float  # 平均時間（分）
    success_rate: float  # 成功率
    sample_count: int  # サンプル数
    ultra_work_rate: float  # Ultra Work使用率
    estimated_hours: float  # 推定工数（時間）


@dataclass
class PackageEstimate:
    """パック別見積り"""
    package_name: str
    task_types: List[str]  # 使用TaskType
    estimated_cost_min: float  # 最小見積りコスト
    estimated_cost_max: float  # 最大見積りコスト
    estimated_cost_avg: float  # 平均見積りコスト
    estimated_hours: float  # 推定工数（時間）
    estimated_days: float  # 推定日数
    success_rate: float  # 成功率
    confidence: float  # 信頼度（0.0-1.0）


class OHMyOpenCodeCostEstimation:
    """OH MY OPENCODE 見積り表自動生成システム"""
    
    def __init__(
        self,
        observability=None,
        optimizer=None
    ):
        """
        初期化
        
        Args:
            observability: Observabilityインスタンス
            optimizer: Optimizerインスタンス
        """
        self.observability = observability
        self.optimizer = optimizer
        
        logger.info("✅ Cost Estimation initialized")
    
    def generate_task_type_estimates(self) -> Dict[str, TaskTypeEstimate]:
        """
        TaskType別見積りを生成
        
        Returns:
            TaskType別見積り辞書
        """
        if not self.observability:
            return self._get_default_estimates()
        
        # Observabilityからメトリクスを取得
        dashboard_data = self.observability.get_dashboard_data()
        task_type_stats = dashboard_data.get("task_type_stats", {})
        
        estimates = {}
        
        for task_type, stats in task_type_stats.items():
            count = stats.get("count", 0)
            if count == 0:
                continue
            
            success = stats.get("success", 0)
            total_cost = stats.get("total_cost", 0.0)
            avg_time = stats.get("avg_time", 0.0)
            
            avg_cost = stats.get("avg_cost", 0.0)
            success_rate = success / count if count > 0 else 0.0
            
            # Ultra Work使用率（簡易計算）
            ultra_work_rate = 0.0  # NOTE: stub — not yet implemented
            
            # 推定工数（時間）= 平均時間（秒） / 3600
            estimated_hours = avg_time / 3600 if avg_time > 0 else 0.0
            
            # 最小・最大コスト（簡易計算）
            min_cost = avg_cost * 0.5
            max_cost = avg_cost * 1.5
            
            estimates[task_type] = TaskTypeEstimate(
                task_type=task_type,
                avg_cost=avg_cost,
                min_cost=min_cost,
                max_cost=max_cost,
                avg_time_minutes=avg_time / 60 if avg_time > 0 else 0.0,
                success_rate=success_rate,
                sample_count=count,
                ultra_work_rate=ultra_work_rate,
                estimated_hours=estimated_hours
            )
        
        return estimates
    
    def generate_package_estimate(
        self,
        package_name: str,
        task_types: List[str]
    ) -> PackageEstimate:
        """
        パック別見積りを生成
        
        Args:
            package_name: パック名
            task_types: 使用TaskTypeリスト
        
        Returns:
            パック別見積り
        """
        task_type_estimates = self.generate_task_type_estimates()
        
        total_cost_min = 0.0
        total_cost_max = 0.0
        total_cost_avg = 0.0
        total_hours = 0.0
        total_samples = 0
        total_success = 0
        
        for task_type in task_types:
            if task_type in task_type_estimates:
                estimate = task_type_estimates[task_type]
                total_cost_min += estimate.min_cost
                total_cost_max += estimate.max_cost
                total_cost_avg += estimate.avg_cost
                total_hours += estimate.estimated_hours
                total_samples += estimate.sample_count
                total_success += int(estimate.sample_count * estimate.success_rate)
        
        # 成功率
        success_rate = total_success / total_samples if total_samples > 0 else 0.0
        
        # 信頼度（サンプル数に基づく）
        confidence = min(1.0, total_samples / 10.0)
        
        # 推定日数（1日8時間として）
        estimated_days = total_hours / 8.0
        
        return PackageEstimate(
            package_name=package_name,
            task_types=task_types,
            estimated_cost_min=total_cost_min,
            estimated_cost_max=total_cost_max,
            estimated_cost_avg=total_cost_avg,
            estimated_hours=total_hours,
            estimated_days=estimated_days,
            success_rate=success_rate,
            confidence=confidence
        )
    
    def generate_estimation_report(self) -> Dict[str, Any]:
        """
        見積りレポートを生成
        
        Returns:
            見積りレポート
        """
        task_type_estimates = self.generate_task_type_estimates()
        
        # パック別見積り
        packages = {
            "管理アプリ即納パック": ["specification", "architecture_design", "code_generation", "code_review"],
            "スクレイピング＋要約パック": ["specification", "architecture_design", "code_generation"],
            "業務ツール統合パック": ["specification", "architecture_design", "code_generation", "code_review", "refactoring"]
        }
        
        package_estimates = {}
        for package_name, task_types in packages.items():
            package_estimates[package_name] = asdict(
                self.generate_package_estimate(package_name, task_types)
            )
        
        return {
            "task_type_estimates": {
                k: asdict(v) for k, v in task_type_estimates.items()
            },
            "package_estimates": package_estimates,
            "generated_at": datetime.now().isoformat(),
            "data_source": "observability" if self.observability else "default"
        }
    
    def _get_default_estimates(self) -> Dict[str, TaskTypeEstimate]:
        """
        デフォルト見積りを取得
        
        Returns:
            デフォルト見積り辞書
        """
        defaults = {
            "specification": TaskTypeEstimate(
                task_type="specification",
                avg_cost=10.0,
                min_cost=5.0,
                max_cost=15.0,
                avg_time_minutes=45.0,
                success_rate=0.85,
                sample_count=0,
                ultra_work_rate=0.0,
                estimated_hours=0.75
            ),
            "complex_bug": TaskTypeEstimate(
                task_type="complex_bug",
                avg_cost=20.0,
                min_cost=10.0,
                max_cost=30.0,
                avg_time_minutes=120.0,
                success_rate=0.70,
                sample_count=0,
                ultra_work_rate=0.0,
                estimated_hours=2.0
            ),
            "architecture_design": TaskTypeEstimate(
                task_type="architecture_design",
                avg_cost=25.0,
                min_cost=15.0,
                max_cost=40.0,
                avg_time_minutes=180.0,
                success_rate=0.80,
                sample_count=0,
                ultra_work_rate=0.0,
                estimated_hours=3.0
            ),
            "code_generation": TaskTypeEstimate(
                task_type="code_generation",
                avg_cost=5.0,
                min_cost=2.0,
                max_cost=10.0,
                avg_time_minutes=20.0,
                success_rate=0.90,
                sample_count=0,
                ultra_work_rate=0.0,
                estimated_hours=0.33
            ),
            "code_review": TaskTypeEstimate(
                task_type="code_review",
                avg_cost=5.0,
                min_cost=3.0,
                max_cost=8.0,
                avg_time_minutes=25.0,
                success_rate=0.85,
                sample_count=0,
                ultra_work_rate=0.0,
                estimated_hours=0.42
            ),
            "refactoring": TaskTypeEstimate(
                task_type="refactoring",
                avg_cost=12.0,
                min_cost=5.0,
                max_cost=20.0,
                avg_time_minutes=60.0,
                success_rate=0.75,
                sample_count=0,
                ultra_work_rate=0.0,
                estimated_hours=1.0
            ),
            "general": TaskTypeEstimate(
                task_type="general",
                avg_cost=8.0,
                min_cost=2.0,
                max_cost=15.0,
                avg_time_minutes=30.0,
                success_rate=0.80,
                sample_count=0,
                ultra_work_rate=0.0,
                estimated_hours=0.5
            )
        }
        
        return defaults


# 使用例
if __name__ == "__main__":
    estimation = OHMyOpenCodeCostEstimation()
    
    # TaskType別見積り
    task_type_estimates = estimation.generate_task_type_estimates()
    print("TaskType別見積り:")
    for task_type, estimate in task_type_estimates.items():
        print(f"  {task_type}: ${estimate.avg_cost:.2f} (平均: {estimate.avg_time_minutes:.1f}分)")
    
    # パック別見積り
    package_estimate = estimation.generate_package_estimate(
        "管理アプリ即納パック",
        ["specification", "architecture_design", "code_generation", "code_review"]
    )
    print(f"\nパック別見積り:")
    print(f"  {package_estimate.package_name}: ${package_estimate.estimated_cost_avg:.2f} ({package_estimate.estimated_days:.1f}日)")
    
    # 見積りレポート
    report = estimation.generate_estimation_report()
    print(f"\n見積りレポート生成完了: {report['generated_at']}")
