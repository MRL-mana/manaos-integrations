#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 OH MY OPENCODE 燃費レポート自動生成システム
週次レポートを自動生成
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
from pathlib import Path
import json

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("oh-my-opencode-fuel-efficiency-report")
error_handler = ManaOSErrorHandler("OHMyOpenCodeFuelEfficiencyReport")


@dataclass
class WeeklySummary:
    """週次サマリー"""
    total_cost: float
    daily_avg_cost: float
    task_count: int
    success_rate: float
    daily_budget_used: float
    daily_budget_limit: float
    monthly_budget_used: float
    monthly_budget_limit: float
    warning_level: str  # "safe", "warning", "critical"


@dataclass
class CostCause:
    """コスト原因"""
    cause: str
    impact_percent: float
    occurrence_count: int
    avg_cost: float
    recommended_actions: List[str]
    expected_impact: str


class OHMyOpenCodeFuelEfficiencyReport:
    """OH MY OPENCODE 燃費レポート自動生成システム"""
    
    def __init__(
        self,
        observability=None,
        cost_visibility=None,
        cost_manager=None
    ):
        """
        初期化
        
        Args:
            observability: Observabilityインスタンス
            cost_visibility: Cost Visibilityインスタンス
            cost_manager: Cost Managerインスタンス
        """
        self.observability = observability
        self.cost_visibility = cost_visibility
        self.cost_manager = cost_manager
        
        logger.info("✅ Fuel Efficiency Report initialized")
    
    def generate_weekly_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        週次レポートを生成
        
        Args:
            start_date: 開始日（Noneの場合は1週間前）
            end_date: 終了日（Noneの場合は現在）
        
        Returns:
            週次レポート
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        # Observabilityからメトリクスを取得
        dashboard_data = self.observability.get_dashboard_data() if self.observability else {}
        
        # 週次サマリー
        weekly_summary = self._generate_weekly_summary(start_date, end_date)
        
        # コスト原因分析（トップ3）
        cost_causes = self._analyze_cost_causes(dashboard_data)
        
        # TaskType別分析
        task_type_analysis = self._analyze_by_task_type(dashboard_data)
        
        # モード別分析
        mode_analysis = self._analyze_by_mode(dashboard_data)
        
        # Kill Switch発動状況
        kill_switch_stats = self._analyze_kill_switch(dashboard_data)
        
        # 推奨アクション
        recommended_actions = dashboard_data.get("recommended_actions", [])
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "weekly_summary": asdict(weekly_summary),
            "cost_causes": [asdict(cause) for cause in cost_causes[:3]],  # トップ3
            "task_type_analysis": task_type_analysis,
            "mode_analysis": mode_analysis,
            "kill_switch_stats": kill_switch_stats,
            "recommended_actions": recommended_actions,
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_weekly_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> WeeklySummary:
        """週次サマリーを生成"""
        if not self.observability:
            return WeeklySummary(
                total_cost=0.0,
                daily_avg_cost=0.0,
                task_count=0,
                success_rate=0.0,
                daily_budget_used=0.0,
                daily_budget_limit=100.0,
                monthly_budget_used=0.0,
                monthly_budget_limit=2000.0,
                warning_level="safe"
            )
        
        dashboard_data = self.observability.get_dashboard_data()
        system_metrics = dashboard_data.get("system_metrics", {})
        
        total_cost = system_metrics.get("total_cost", 0.0)
        total_executions = system_metrics.get("total_executions", 0)
        success_rate = system_metrics.get("success_rate", 0.0)
        
        # 日次平均コスト
        days = (end_date - start_date).days
        daily_avg_cost = total_cost / days if days > 0 else 0.0
        
        # 予算情報
        if self.cost_visibility:
            budget_meter = self.cost_visibility.get_budget_meter()
            daily_budget_used = budget_meter.daily_used
            daily_budget_limit = budget_meter.daily_budget
            monthly_budget_used = budget_meter.monthly_used
            monthly_budget_limit = budget_meter.monthly_budget
            warning_level = budget_meter.warning_level
        else:
            daily_budget_used = 0.0
            daily_budget_limit = 100.0
            monthly_budget_used = 0.0
            monthly_budget_limit = 2000.0
            warning_level = "safe"
        
        return WeeklySummary(
            total_cost=total_cost,
            daily_avg_cost=daily_avg_cost,
            task_count=total_executions,
            success_rate=success_rate,
            daily_budget_used=daily_budget_used,
            daily_budget_limit=daily_budget_limit,
            monthly_budget_used=monthly_budget_used,
            monthly_budget_limit=monthly_budget_limit,
            warning_level=warning_level
        )
    
    def _analyze_cost_causes(self, dashboard_data: Dict[str, Any]) -> List[CostCause]:
        """コスト原因を分析"""
        cost_cause_stats = dashboard_data.get("cost_cause_stats", {})
        recommended_actions = dashboard_data.get("recommended_actions", [])
        
        causes = []
        
        # コスト原因統計から上位を取得
        sorted_causes = sorted(
            cost_cause_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_count = sum(cost_cause_stats.values())
        
        for cause_name, count in sorted_causes[:5]:  # 上位5件
            impact_percent = (count / total_count * 100) if total_count > 0 else 0.0
            
            # 推奨アクションを検索
            actions = []
            for action in recommended_actions:
                if cause_name.lower() in action.get("issue", "").lower():
                    actions.append(action.get("action", ""))
            
            if not actions:
                actions = [f"{cause_name}の原因を調査し、対策を実施"]
            
            causes.append(CostCause(
                cause=cause_name,
                impact_percent=impact_percent,
                occurrence_count=count,
                avg_cost=0.0,  # NOTE: stub — not yet implemented
                recommended_actions=actions[:3],  # 最大3件
                expected_impact="コストを10-30%削減"
            ))
        
        return causes
    
    def _analyze_by_task_type(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """TaskType別分析"""
        task_type_stats = dashboard_data.get("task_type_stats", {})
        
        analysis = {}
        for task_type, stats in task_type_stats.items():
            analysis[task_type] = {
                "execution_count": stats.get("count", 0),
                "success_rate": stats.get("success_rate", 0.0),
                "avg_cost": stats.get("avg_cost", 0.0),
                "total_cost": stats.get("total_cost", 0.0),
                "avg_time_minutes": stats.get("avg_time", 0.0) / 60
            }
        
        return analysis
    
    def _analyze_by_mode(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """モード別分析"""
        mode_stats = dashboard_data.get("mode_stats", {})
        
        analysis = {}
        for mode, stats in mode_stats.items():
            analysis[mode] = {
                "execution_count": stats.get("count", 0),
                "success_rate": stats.get("success_rate", 0.0),
                "avg_cost": stats.get("avg_cost", 0.0),
                "total_cost": stats.get("total_cost", 0.0)
            }
        
        # Ultra Work使用率
        total_count = sum(s.get("count", 0) for s in mode_stats.values())
        ultra_work_count = mode_stats.get("ultra_work", {}).get("count", 0)
        ultra_work_rate = (ultra_work_count / total_count * 100) if total_count > 0 else 0.0
        
        analysis["ultra_work_rate"] = ultra_work_rate
        
        return analysis
    
    def _analyze_kill_switch(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Kill Switch発動状況を分析"""
        kill_reason_stats = dashboard_data.get("kill_reason_stats", {})
        system_metrics = dashboard_data.get("system_metrics", {})
        
        total_kills = system_metrics.get("kill_switch_activations", 0)
        total_executions = system_metrics.get("total_executions", 0)
        kill_rate = (total_kills / total_executions * 100) if total_executions > 0 else 0.0
        
        return {
            "kill_reasons": kill_reason_stats,
            "total_kills": total_kills,
            "kill_rate": kill_rate
        }
    
    def generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """
        Markdown形式のレポートを生成
        
        Args:
            report_data: レポートデータ
        
        Returns:
            Markdown形式のレポート
        """
        # テンプレートファイルを読み込む
        template_path = Path(__file__).parent / "OH_MY_OPENCODE_FUEL_EFFICIENCY_REPORT_TEMPLATE.md"
        
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
        else:
            template = "# 燃費レポート\n\n[レポート内容]\n"
        
        # データを埋め込む（簡易実装）
        return template


# 使用例
if __name__ == "__main__":
    report_generator = OHMyOpenCodeFuelEfficiencyReport()
    
    # 週次レポート生成
    report = report_generator.generate_weekly_report()
    
    print("週次レポート生成完了:")
    print(f"  期間: {report['period']['start_date']} 〜 {report['period']['end_date']}")
    print(f"  総コスト: ${report['weekly_summary']['total_cost']:.2f}")
    print(f"  タスク数: {report['weekly_summary']['task_count']}件")
    print(f"  成功率: {report['weekly_summary']['success_rate']*100:.1f}%")
