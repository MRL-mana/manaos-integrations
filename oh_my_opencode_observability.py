#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 OH MY OPENCODE 観測設計システム
ログ・メトリクス・可視化
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("OHMyOpenCodeObservability")


@dataclass
class ExecutionMetric:
    """実行メトリクス"""
    task_id: str
    task_type: str
    mode: str
    status: str
    execution_time: float
    cost: float
    iterations: int
    errors: int
    timestamp: str
    kill_reason: Optional[str] = None
    cost_breakdown: Optional[Dict[str, float]] = None
    cost_causes: Optional[List[str]] = None


@dataclass
class SystemMetrics:
    """システムメトリクス"""
    total_executions: int
    success_rate: float
    avg_execution_time: float
    avg_cost: float
    total_cost: float
    kill_switch_activations: int
    ultra_work_downgrades: int
    cost_limit_exceeded: int
    timestamp: str


class OHMyOpenCodeObservability:
    """OH MY OPENCODE 観測設計システム"""
    
    def __init__(
        self,
        metrics_storage_path: Optional[Path] = None,
        log_level: str = "INFO"
    ):
        """
        初期化
        
        Args:
            metrics_storage_path: メトリクス保存パス
            log_level: ログレベル
        """
        self.metrics_storage_path = metrics_storage_path or Path(__file__).parent / "oh_my_opencode_metrics.json"
        self.log_level = log_level
        
        # メトリクス履歴
        self.metrics_history: List[ExecutionMetric] = []
        
        # システムメトリクス
        self.system_metrics: Optional[SystemMetrics] = None
        
        self._load_metrics()
        self._calculate_system_metrics()
        
        logger.info("✅ Observability initialized")
    
    def _load_metrics(self):
        """メトリクスを読み込み"""
        if self.metrics_storage_path.exists():
            try:
                with open(self.metrics_storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metrics_history = [
                        ExecutionMetric(**metric) for metric in data.get("metrics", [])
                    ]
                logger.info(f"メトリクスを読み込みました: {len(self.metrics_history)}件")
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"path": str(self.metrics_storage_path)},
                    user_message="メトリクスの読み込みに失敗しました"
                )
                logger.warning(f"メトリクス読み込みエラー: {error.message}")
                self.metrics_history = []
    
    def _save_metrics(self):
        """メトリクスを保存"""
        try:
            data = {
                "metrics": [asdict(metric) for metric in self.metrics_history],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.metrics_storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"path": str(self.metrics_storage_path)},
                user_message="メトリクスの保存に失敗しました"
            )
            logger.error(f"メトリクス保存エラー: {error.message}")
    
    def record_execution(
        self,
        task_id: str,
        task_type: str,
        mode: str,
        status: str,
        execution_time: float,
        cost: float,
        iterations: int,
        errors: int = 0,
        kill_reason: Optional[str] = None,
        cost_breakdown: Optional[Dict[str, float]] = None,
        cost_causes: Optional[List[str]] = None
    ):
        """
        実行メトリクスを記録
        
        Args:
            task_id: タスクID
            task_type: タスクタイプ
            mode: 実行モード
            status: ステータス
            execution_time: 実行時間
            cost: コスト
            iterations: 反復回数
            errors: エラー数
            kill_reason: Kill Switch理由
            cost_breakdown: コスト内訳
            cost_causes: コスト原因
        """
        metric = ExecutionMetric(
            task_id=task_id,
            task_type=task_type,
            mode=mode,
            status=status,
            execution_time=execution_time,
            cost=cost,
            iterations=iterations,
            errors=errors,
            timestamp=datetime.now().isoformat(),
            kill_reason=kill_reason,
            cost_breakdown=cost_breakdown,
            cost_causes=cost_causes
        )
        
        self.metrics_history.append(metric)
        
        # システムメトリクスを再計算
        self._calculate_system_metrics()
        
        # メトリクスを保存
        self._save_metrics()
        
        logger.debug(f"実行メトリクスを記録しました: {task_id}")
    
    def _calculate_system_metrics(self):
        """システムメトリクスを計算"""
        if not self.metrics_history:
            self.system_metrics = SystemMetrics(
                total_executions=0,
                success_rate=0.0,
                avg_execution_time=0.0,
                avg_cost=0.0,
                total_cost=0.0,
                kill_switch_activations=0,
                ultra_work_downgrades=0,
                cost_limit_exceeded=0,
                timestamp=datetime.now().isoformat()
            )
            return
        
        total = len(self.metrics_history)
        success_count = sum(1 for m in self.metrics_history if m.status == "success")
        success_rate = success_count / total if total > 0 else 0.0
        
        avg_execution_time = sum(m.execution_time for m in self.metrics_history) / total
        avg_cost = sum(m.cost for m in self.metrics_history) / total
        total_cost = sum(m.cost for m in self.metrics_history)
        
        kill_switch_activations = sum(1 for m in self.metrics_history if m.kill_reason is not None)
        ultra_work_downgrades = sum(
            1 for m in self.metrics_history
            if m.mode == "ultra_work" and m.status == "success" and m.cost < 50.0  # 簡易判定
        )
        cost_limit_exceeded = sum(1 for m in self.metrics_history if m.status == "cost_limit_exceeded")
        
        self.system_metrics = SystemMetrics(
            total_executions=total,
            success_rate=success_rate,
            avg_execution_time=avg_execution_time,
            avg_cost=avg_cost,
            total_cost=total_cost,
            kill_switch_activations=kill_switch_activations,
            ultra_work_downgrades=ultra_work_downgrades,
            cost_limit_exceeded=cost_limit_exceeded,
            timestamp=datetime.now().isoformat()
        )
    
    def get_system_metrics(self) -> SystemMetrics:
        """
        システムメトリクスを取得
        
        Returns:
            システムメトリクス
        """
        if not self.system_metrics:
            self._calculate_system_metrics()
        
        return self.system_metrics
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        ダッシュボードデータを取得
        
        Returns:
            ダッシュボードデータ
        """
        system_metrics = self.get_system_metrics()
        
        # タスクタイプ別統計
        task_type_stats = defaultdict(lambda: {
            "count": 0,
            "success": 0,
            "total_cost": 0.0,
            "avg_cost": 0.0,
            "avg_time": 0.0
        })
        
        for metric in self.metrics_history:
            stats = task_type_stats[metric.task_type]
            stats["count"] += 1
            if metric.status == "success":
                stats["success"] += 1
            stats["total_cost"] += metric.cost
            stats["avg_time"] += metric.execution_time
        
        for stats in task_type_stats.values():
            if stats["count"] > 0:
                stats["avg_cost"] = stats["total_cost"] / stats["count"]
                stats["avg_time"] = stats["avg_time"] / stats["count"]
                stats["success_rate"] = stats["success"] / stats["count"]
        
        # モード別統計
        mode_stats = defaultdict(lambda: {
            "count": 0,
            "success": 0,
            "total_cost": 0.0,
            "avg_cost": 0.0
        })
        
        for metric in self.metrics_history:
            stats = mode_stats[metric.mode]
            stats["count"] += 1
            if metric.status == "success":
                stats["success"] += 1
            stats["total_cost"] += metric.cost
        
        for stats in mode_stats.values():
            if stats["count"] > 0:
                stats["avg_cost"] = stats["total_cost"] / stats["count"]
                stats["success_rate"] = stats["success"] / stats["count"]
        
        # Kill Switch理由別統計
        kill_reason_stats = defaultdict(int)
        for metric in self.metrics_history:
            if metric.kill_reason:
                kill_reason_stats[metric.kill_reason] += 1
        
        # コスト原因別統計
        cost_cause_stats = defaultdict(int)
        for metric in self.metrics_history:
            if metric.cost_causes:
                for cause in metric.cost_causes:
                    cost_cause_stats[cause] += 1
        
        # アクション推奨（診断→処方箋）
        recommended_actions = self._generate_recommended_actions(
            cost_cause_stats,
            kill_reason_stats,
            task_type_stats
        )
        
        return {
            "system_metrics": asdict(system_metrics),
            "task_type_stats": dict(task_type_stats),
            "mode_stats": dict(mode_stats),
            "kill_reason_stats": dict(kill_reason_stats),
            "cost_cause_stats": dict(cost_cause_stats),
            "recommended_actions": recommended_actions,  # アクション推奨
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_recommended_actions(
        self,
        cost_cause_stats: Dict[str, int],
        kill_reason_stats: Dict[str, int],
        task_type_stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        推奨アクションを生成（診断→処方箋）
        
        Args:
            cost_cause_stats: コスト原因統計
            kill_reason_stats: Kill Switch理由統計
            task_type_stats: タスクタイプ統計
        
        Returns:
            推奨アクションのリスト
        """
        actions = []
        
        # 高コスト原因が「検索多い」
        if cost_cause_stats.get("検索が多い（検索コストが20%超）", 0) > 0:
            actions.append({
                "priority": "high",
                "category": "cost_optimization",
                "issue": "検索コストが高い",
                "recommendation": "検索回数の上限を下げる or 先に要件確認を挟む",
                "action": "検索回数の上限を下げる（config.yamlのsearch_limitを調整）",
                "expected_impact": "検索コストを20-30%削減"
            })
        
        # 原因が「ループ多い」
        if cost_cause_stats.get("ループが多い（ループコストが40%超）", 0) > 0:
            actions.append({
                "priority": "high",
                "category": "cost_optimization",
                "issue": "ループコストが高い",
                "recommendation": "途中で人間レビュー挟む or Oracleに強制エスカレーション",
                "action": "ループ回数が5回を超えたら人間レビューを挟む設定を追加",
                "expected_impact": "ループコストを30-50%削減"
            })
        
        # 原因が「コンテキスト長い」
        if cost_cause_stats.get("コンテキストが長い（コンテキストコストが30%超）", 0) > 0:
            actions.append({
                "priority": "medium",
                "category": "cost_optimization",
                "issue": "コンテキストコストが高い",
                "recommendation": "直近の要点だけ抽出して再投入（自動圧縮）",
                "action": "コンテキスト自動圧縮機能を有効化",
                "expected_impact": "コンテキストコストを40-60%削減"
            })
        
        # Kill Switchが頻繁に発動
        total_kills = sum(kill_reason_stats.values())
        if total_kills > 5:
            actions.append({
                "priority": "critical",
                "category": "safety",
                "issue": "Kill Switchが頻繁に発動",
                "recommendation": "タスクの分割やスコープ縮小を検討",
                "action": "タスクを小さなステップに分割するテンプレートを使用",
                "expected_impact": "Kill Switch発動率を50%削減"
            })
        
        # 成功率が低いタスクタイプ
        for task_type, stats in task_type_stats.items():
            success_rate = stats.get("success_rate", 1.0)
            if success_rate < 0.5 and stats.get("count", 0) >= 3:
                actions.append({
                    "priority": "medium",
                    "category": "quality",
                    "issue": f"{task_type}の成功率が低い（{success_rate*100:.1f}%）",
                    "recommendation": "成功パターンテンプレートの見直し",
                    "action": f"{task_type}用のテンプレートを最適化",
                    "expected_impact": f"成功率を{success_rate*100:.1f}%→70%以上に改善"
                })
        
        return actions
    
    def get_recent_metrics(self, limit: int = 10) -> List[ExecutionMetric]:
        """
        最近のメトリクスを取得
        
        Args:
            limit: 取得件数
        
        Returns:
            最近のメトリクス
        """
        return self.metrics_history[-limit:] if self.metrics_history else []


# 使用例
if __name__ == "__main__":
    observability = OHMyOpenCodeObservability()
    
    # 実行メトリクスを記録
    observability.record_execution(
        task_id="test_task_1",
        task_type="code_generation",
        mode="normal",
        status="success",
        execution_time=120.0,
        cost=5.0,
        iterations=3,
        cost_breakdown={"search": 10.0, "loop": 30.0, "model": 40.0, "context": 20.0},
        cost_causes=["ループが多い"]
    )
    
    # システムメトリクスを取得
    system_metrics = observability.get_system_metrics()
    print(f"システムメトリクス: {system_metrics}")
    
    # ダッシュボードデータを取得
    dashboard = observability.get_dashboard_data()
    print(f"ダッシュボードデータ: {dashboard}")
