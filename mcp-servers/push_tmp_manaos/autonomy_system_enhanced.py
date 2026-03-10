#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 ManaOS 自律システム（強化版）
予測的実行・学習連携・自動最適化
"""

import json
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# 最適化モジュールのインポート
from unified_cache_system import get_unified_cache
from config_cache import get_config_cache
from learning_system_enhanced import LearningSystemEnhanced
from manaos_async_client import AsyncUnifiedAPIClient

# ロガーの初期化
logger = get_service_logger("autonomy-system-enhanced")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("AutonomySystemEnhanced")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# キャッシュシステムの取得
cache_system = get_unified_cache()
config_cache = get_config_cache()


class AutonomySystemEnhanced:
    """自律システム（強化版）"""
    
    def __init__(
        self,
        orchestrator_url: str = "http://127.0.0.1:5106",
        learning_system_url: Optional[str] = None,
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            orchestrator_url: Unified Orchestrator API URL
            learning_system_url: Learning System API URL
            config_path: 設定ファイルのパス
        """
        from autonomy_system import AutonomySystem
        
        # 基本システム
        self.base_system = AutonomySystem(orchestrator_url, learning_system_url, config_path)  # type: ignore
        
        # 学習システム
        self.learning = LearningSystemEnhanced()
        
        logger.info(f"✅ Autonomy System Enhanced初期化完了")
    
    async def predict_and_execute_tasks(self) -> List[Dict[str, Any]]:
        """
        タスクを予測して実行（予測的実行）
        
        Returns:
            実行結果のリスト
        """
        # 次のアクションを予測
        predictions = self.learning.predict_next_action({
            "type": "autonomy_task",
            "timestamp": datetime.now().isoformat()
        })
        
        results = []
        
        # 予測されたアクションを実行
        async with AsyncUnifiedAPIClient() as client:
            for pred in predictions[:3]:  # 上位3件
                action = pred["action"]
                probability = pred["probability"]
                
                if probability > 0.7:  # 70%以上の確率
                    try:
                        # タスクを実行
                        result = await client.call_service(
                            service="unified_orchestrator",
                            endpoint="/api/execute",
                            method="POST",
                            data={
                                "text": action,
                                "mode": "auto",
                                "auto_evaluate": True
                            }
                        )
                        
                        results.append({
                            "action": action,
                            "probability": probability,
                            "result": result,
                            "status": "success"
                        })
                        
                        # 学習・記憶に記録
                        self.learning.record_usage(
                            action=f"autonomy_predictive_{action}",
                            context={"prediction": pred},
                            result=result
                        )
                    except Exception as e:
                        error = error_handler.handle_exception(
                            e,
                            context={"action": action},
                            user_message="予測的タスクの実行に失敗しました"
                        )
                        results.append({
                            "action": action,
                            "probability": probability,
                            "status": "error",
                            "error": error.user_message or error.message
                        })
        
        return results
    
    def optimize_autonomy_level(self) -> Dict[str, Any]:
        """
        自律レベルを最適化（学習結果に基づく）
        
        Returns:
            最適化結果
        """
        # 学習統計を取得
        try:
            if self.learning and hasattr(self.learning, 'analyze_patterns'):
                analysis = self.learning.analyze_patterns()
            else:
                analysis = {"success_rates": {}}
        except Exception as e:
            logger.warning(f"学習パターン分析エラー: {e}")
            analysis = {"success_rates": {}}
        
        # 成功率を分析
        success_rates = analysis.get("success_rates", {})
        avg_success_rate = (
            sum(stats["rate"] for stats in success_rates.values()) / len(success_rates)
            if success_rates else 0
        )
        
        # 自律レベルを決定
        current_level = self.base_system.autonomy_level.value
        recommended_level = current_level
        
        if avg_success_rate > 80:
            # 成功率が高い場合はレベルを上げる
            if current_level == "low":
                recommended_level = "medium"
            elif current_level == "medium":
                recommended_level = "high"
        elif avg_success_rate < 50:
            # 成功率が低い場合はレベルを下げる
            if current_level == "high":
                recommended_level = "medium"
            elif current_level == "medium":
                recommended_level = "low"
        
        return {
            "current_level": current_level,
            "recommended_level": recommended_level,
            "avg_success_rate": avg_success_rate,
            "reason": f"平均成功率: {avg_success_rate:.1f}%",
            "timestamp": datetime.now().isoformat()
        }
    
    def get_autonomy_stats(self) -> Dict[str, Any]:
        """自律統計情報を取得"""
        return {
            "autonomy_level": self.base_system.autonomy_level.value,
            "tasks_count": len(self.base_system.tasks),
            "execution_history_count": len(self.base_system.execution_history),
            "learning_stats": {
                "total_actions": sum(
                    len(records) for records in self.learning.usage_patterns.values()
                    if "autonomy" in records[0].get("action", "")
                ) if self.learning.usage_patterns else 0
            },
            "optimization": self.optimize_autonomy_level(),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("自律システム（強化版）テスト")
    print("=" * 60)
    
    autonomy = AutonomySystemEnhanced()
    
    # 統計情報を取得
    stats = autonomy.get_autonomy_stats()
    print(f"\n統計情報:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()















