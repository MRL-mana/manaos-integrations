#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ OH MY OPENCODE 最適化システム
実行履歴分析・モデル選択最適化・並列実行最適化
"""

import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from statistics import mean, median

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("oh-my-opencode-optimizer")
error_handler = ManaOSErrorHandler("OHMyOpenCodeOptimizer")


@dataclass
class TaskPattern:
    """タスクパターン"""
    task_type: str
    mode: str
    success_rate: float
    avg_cost: float
    avg_execution_time: float
    avg_iterations: int
    common_errors: List[str]
    recommended_model: Optional[str] = None
    sample_count: int = 0


@dataclass
class OptimizationRecommendation:
    """最適化推奨事項"""
    task_type: str
    recommended_mode: str
    recommended_model: str
    estimated_cost: float
    estimated_time: float
    confidence: float
    reasoning: str


class OHMyOpenCodeOptimizer:
    """OH MY OPENCODE最適化システム"""
    
    def __init__(
        self,
        execution_history_path: Optional[Path] = None,
        cost_history_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            execution_history_path: 実行履歴ファイルのパス
            cost_history_path: コスト履歴ファイルのパス
        """
        self.execution_history_path = execution_history_path or Path(__file__).parent / "oh_my_opencode_execution_history.json"
        self.cost_history_path = cost_history_path or Path(__file__).parent / "oh_my_opencode_cost_history.json"
        
        # 実行履歴
        self.execution_history: List[Dict[str, Any]] = []
        
        # コスト履歴
        self.cost_history: List[Dict[str, Any]] = []
        
        # パターン分析結果
        self.task_patterns: Dict[str, TaskPattern] = {}
        
        self._load_history()
        self._analyze_patterns()
        
        logger.info("✅ Optimizer initialized")
    
    def _load_history(self):
        """履歴を読み込み"""
        # 実行履歴の読み込み
        if self.execution_history_path.exists():
            try:
                with open(self.execution_history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.execution_history = data.get("history", [])
                logger.info(f"実行履歴を読み込みました: {len(self.execution_history)}件")
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"path": str(self.execution_history_path)},
                    user_message="実行履歴の読み込みに失敗しました"
                )
                logger.warning(f"実行履歴読み込みエラー: {error.message}")
                self.execution_history = []
        
        # コスト履歴の読み込み
        if self.cost_history_path.exists():
            try:
                with open(self.cost_history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cost_history = data.get("records", [])
                logger.info(f"コスト履歴を読み込みました: {len(self.cost_history)}件")
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"path": str(self.cost_history_path)},
                    user_message="コスト履歴の読み込みに失敗しました"
                )
                logger.warning(f"コスト履歴読み込みエラー: {error.message}")
                self.cost_history = []
    
    def _analyze_patterns(self):
        """パターンを分析"""
        if not self.execution_history:
            return
        
        # タスクタイプとモードの組み合わせごとに分析
        pattern_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        
        for record in self.execution_history:
            task_type = record.get("task_type", "general")
            mode = record.get("mode", "normal")
            pattern_groups[(task_type, mode)].append(record)
        
        # 各パターンを分析
        for (task_type, mode), records in pattern_groups.items():
            pattern_key = f"{task_type}_{mode}"
            
            # 成功率の計算
            success_count = sum(1 for r in records if r.get("status") == "success")
            success_rate = success_count / len(records) if records else 0.0
            
            # コストの平均
            costs = [r.get("cost", 0.0) for r in records]
            avg_cost = mean(costs) if costs else 0.0
            
            # 実行時間の平均
            execution_times = [r.get("execution_time", 0.0) for r in records]
            avg_execution_time = mean(execution_times) if execution_times else 0.0
            
            # 反復回数の平均
            iterations = [r.get("iterations", 0) for r in records]
            avg_iterations = int(mean(iterations)) if iterations else 0
            
            # よくあるエラー
            errors = [r.get("error") for r in records if r.get("error")]
            error_counter = Counter(errors)
            common_errors = [error for error, count in error_counter.most_common(3)]
            
            # 推奨モデル（将来実装予定）
            recommended_model = None
            
            pattern = TaskPattern(
                task_type=task_type,
                mode=mode,
                success_rate=success_rate,
                avg_cost=avg_cost,
                avg_execution_time=avg_execution_time,
                avg_iterations=avg_iterations,
                common_errors=common_errors,
                recommended_model=recommended_model,
                sample_count=len(records)
            )
            
            self.task_patterns[pattern_key] = pattern
        
        logger.info(f"パターン分析完了: {len(self.task_patterns)}パターン")
    
    def get_optimization_recommendation(
        self,
        task_type: str,
        task_description: str = ""
    ) -> OptimizationRecommendation:
        """
        最適化推奨事項を取得
        
        Args:
            task_type: タスクタイプ
            task_description: タスクの説明（将来使用予定）
        
        Returns:
            最適化推奨事項
        """
        # タスクタイプに一致するパターンを検索
        matching_patterns = [
            pattern for pattern in self.task_patterns.values()
            if pattern.task_type == task_type
        ]
        
        if not matching_patterns:
            # パターンが見つからない場合、デフォルト値を返す
            return OptimizationRecommendation(
                task_type=task_type,
                recommended_mode="normal",
                recommended_model="default",
                estimated_cost=10.0,
                estimated_time=300.0,
                confidence=0.5,
                reasoning="履歴データが不足しています"
            )
        
        # 最も成功率が高いパターンを選択
        best_pattern = max(matching_patterns, key=lambda p: p.success_rate)
        
        # 推奨モードの決定
        recommended_mode = best_pattern.mode
        
        # 推定コストと時間
        estimated_cost = best_pattern.avg_cost
        estimated_time = best_pattern.avg_execution_time
        
        # 信頼度の計算（サンプル数に基づく）
        confidence = min(1.0, best_pattern.sample_count / 10.0)
        
        # 推論の生成
        reasoning = (
            f"過去{best_pattern.sample_count}件の実行履歴に基づく推奨。"
            f"成功率: {best_pattern.success_rate*100:.1f}%, "
            f"平均コスト: ${best_pattern.avg_cost:.2f}, "
            f"平均実行時間: {best_pattern.avg_execution_time:.1f}秒"
        )
        
        return OptimizationRecommendation(
            task_type=task_type,
            recommended_mode=recommended_mode,
            recommended_model=best_pattern.recommended_model or "default",
            estimated_cost=estimated_cost,
            estimated_time=estimated_time,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def record_execution(
        self,
        task_id: str,
        task_type: str,
        mode: str,
        status: str,
        cost: float,
        execution_time: float,
        iterations: int,
        error: Optional[str] = None
    ):
        """
        実行履歴を記録
        
        Args:
            task_id: タスクID
            task_type: タスクタイプ
            mode: 実行モード
            status: ステータス
            cost: コスト
            execution_time: 実行時間
            iterations: 反復回数
            error: エラーメッセージ
        """
        record = {
            "task_id": task_id,
            "task_type": task_type,
            "mode": mode,
            "status": status,
            "cost": cost,
            "execution_time": execution_time,
            "iterations": iterations,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_history.append(record)
        
        # パターンを再分析
        self._analyze_patterns()
        
        # 履歴を保存
        self._save_history()
        
        logger.debug(f"実行履歴を記録しました: {task_id}")
    
    def _save_history(self):
        """履歴を保存"""
        try:
            data = {
                "history": self.execution_history,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.execution_history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"path": str(self.execution_history_path)},
                user_message="実行履歴の保存に失敗しました"
            )
            logger.error(f"実行履歴保存エラー: {error.message}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Returns:
            統計情報
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_cost": 0.0,
                "avg_execution_time": 0.0,
                "task_patterns": {}
            }
        
        # 全体統計
        total_executions = len(self.execution_history)
        success_count = sum(1 for r in self.execution_history if r.get("status") == "success")
        success_rate = success_count / total_executions if total_executions > 0 else 0.0
        
        costs = [r.get("cost", 0.0) for r in self.execution_history]
        avg_cost = mean(costs) if costs else 0.0
        
        execution_times = [r.get("execution_time", 0.0) for r in self.execution_history]
        avg_execution_time = mean(execution_times) if execution_times else 0.0
        
        # パターン別統計
        pattern_stats = {}
        for pattern_key, pattern in self.task_patterns.items():
            pattern_stats[pattern_key] = asdict(pattern)
        
        return {
            "total_executions": total_executions,
            "success_rate": success_rate,
            "avg_cost": avg_cost,
            "avg_execution_time": avg_execution_time,
            "task_patterns": pattern_stats
        }


# 使用例
if __name__ == "__main__":
    optimizer = OHMyOpenCodeOptimizer()
    
    # 実行履歴を記録
    optimizer.record_execution(
        task_id="test_task_1",
        task_type="code_generation",
        mode="normal",
        status="success",
        cost=5.0,
        execution_time=120.0,
        iterations=3
    )
    
    # 最適化推奨事項を取得
    recommendation = optimizer.get_optimization_recommendation("code_generation")
    print(f"推奨事項: {recommendation}")
    
    # 統計情報を取得
    stats = optimizer.get_statistics()
    print(f"統計情報: {stats}")
