#!/usr/bin/env python3
"""
⚙️ ManaOS 自己調整システム
パラメータの自動調整、設定の動的変更、環境への適応
"""

import json
import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_service_logger("self-adjustment-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SelfAdjustmentSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("SelfAdjustmentSystem")


@dataclass
class AdjustmentAction:
    """調整アクション"""
    action_id: str
    parameter_name: str
    old_value: Any
    new_value: Any
    reason: str
    executed_at: str
    result: Dict[str, Any]


class SelfAdjustmentSystem:
    """自己調整システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "self_adjustment_config.json"
        self.config = self._load_config()
        
        # 調整履歴
        self.adjustment_history: List[AdjustmentAction] = []
        self.adjustment_storage = Path("adjustment_history.json")
        self._load_adjustment_history()
        
        # 現在のパラメータ
        self.current_parameters: Dict[str, Any] = {}
        
        logger.info("✅ Self Adjustment System初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        
        return {
            "enable_auto_adjustment": True,
            "adjustment_interval_minutes": 30,
            "enable_timeout_adjustment": True,
            "enable_rate_limit_adjustment": True,
            "enable_cache_size_adjustment": True,
            "max_adjustment_per_hour": 10
        }
    
    def _load_adjustment_history(self):
        """調整履歴を読み込む"""
        if self.adjustment_storage.exists():
            try:
                with open(self.adjustment_storage, 'r', encoding='utf-8') as f:
                    adjustments_data = json.load(f)
                    self.adjustment_history = [
                        AdjustmentAction(**item) for item in adjustments_data
                    ]
            except Exception as e:
                logger.warning(f"調整履歴読み込みエラー: {e}")
    
    def _save_adjustment_history(self):
        """調整履歴を保存"""
        try:
            adjustments_data = [asdict(adj) for adj in self.adjustment_history[-100:]]
            with open(self.adjustment_storage, 'w', encoding='utf-8') as f:
                json.dump(adjustments_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"調整履歴保存エラー: {e}")
    
    def adjust_timeout(self, service_name: str, current_timeout: float, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        タイムアウトを調整
        
        Args:
            service_name: サービス名
            current_timeout: 現在のタイムアウト値（秒）
            context: コンテキスト情報
            
        Returns:
            調整結果
        """
        if not self.config.get("enable_timeout_adjustment", True):
            return {"skipped": True, "reason": "タイムアウト調整が無効です"}
        
        # エラー率やレイテンシに基づいてタイムアウトを調整
        error_rate = context.get("error_rate", 0.0)
        avg_latency = context.get("avg_latency", 0.0)
        
        new_timeout = current_timeout
        
        # エラー率が高い場合はタイムアウトを増やす
        if error_rate > 0.1:  # 10%以上
            new_timeout = current_timeout * 1.5
        elif error_rate < 0.01 and avg_latency < current_timeout * 0.5:  # エラー率が低く、レイテンシが短い場合
            new_timeout = max(current_timeout * 0.8, avg_latency * 2)  # タイムアウトを減らす
        
        # 調整を実行
        if abs(new_timeout - current_timeout) > 0.1:  # 10%以上の変化がある場合のみ調整
            action = AdjustmentAction(
                action_id=f"timeout_{int(time.time())}",
                parameter_name=f"{service_name}_timeout",
                old_value=current_timeout,
                new_value=new_timeout,
                reason=f"エラー率: {error_rate:.2%}, 平均レイテンシ: {avg_latency:.2f}秒",
                executed_at=datetime.now().isoformat(),
                result={"success": True}
            )
            
            self.adjustment_history.append(action)
            self._save_adjustment_history()
            
            # タイムアウト設定を更新
            timeout_config.set_timeout(service_name, new_timeout)
            
            return {
                "success": True,
                "parameter": f"{service_name}_timeout",
                "old_value": current_timeout,
                "new_value": new_timeout,
                "reason": action.reason
            }
        
        return {"skipped": True, "reason": "調整の必要がありません"}
    
    def adjust_rate_limit(self, service_name: str, current_rate: float, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        レート制限を調整
        
        Args:
            service_name: サービス名
            current_rate: 現在のレート制限値
            context: コンテキスト情報
            
        Returns:
            調整結果
        """
        if not self.config.get("enable_rate_limit_adjustment", True):
            return {"skipped": True, "reason": "レート制限調整が無効です"}
        
        # リソース使用率に基づいてレート制限を調整
        cpu_percent = context.get("cpu_percent", 0.0)
        memory_percent = context.get("memory_percent", 0.0)
        
        new_rate = current_rate
        
        # CPUまたはメモリ使用率が高い場合はレート制限を下げる
        if cpu_percent > 85 or memory_percent > 85:
            new_rate = current_rate * 0.7  # 30%削減
        elif cpu_percent < 50 and memory_percent < 50:
            new_rate = current_rate * 1.2  # 20%増加
        
        # 調整を実行
        if abs(new_rate - current_rate) > current_rate * 0.1:  # 10%以上の変化がある場合のみ調整
            action = AdjustmentAction(
                action_id=f"rate_limit_{int(time.time())}",
                parameter_name=f"{service_name}_rate_limit",
                old_value=current_rate,
                new_value=new_rate,
                reason=f"CPU: {cpu_percent:.1f}%, メモリ: {memory_percent:.1f}%",
                executed_at=datetime.now().isoformat(),
                result={"success": True}
            )
            
            self.adjustment_history.append(action)
            self._save_adjustment_history()
            
            return {
                "success": True,
                "parameter": f"{service_name}_rate_limit",
                "old_value": current_rate,
                "new_value": new_rate,
                "reason": action.reason
            }
        
        return {"skipped": True, "reason": "調整の必要がありません"}
    
    def adjust_cache_size(self, cache_name: str, current_size: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        キャッシュサイズを調整
        
        Args:
            cache_name: キャッシュ名
            current_size: 現在のキャッシュサイズ
            context: コンテキスト情報
            
        Returns:
            調整結果
        """
        if not self.config.get("enable_cache_size_adjustment", True):
            return {"skipped": True, "reason": "キャッシュサイズ調整が無効です"}
        
        # ヒット率とメモリ使用率に基づいてキャッシュサイズを調整
        hit_rate = context.get("hit_rate", 0.0)
        memory_percent = context.get("memory_percent", 0.0)
        
        new_size = current_size
        
        # ヒット率が高く、メモリに余裕がある場合はキャッシュサイズを増やす
        if hit_rate > 0.8 and memory_percent < 70:
            new_size = int(current_size * 1.5)
        # ヒット率が低く、メモリが不足している場合はキャッシュサイズを減らす
        elif hit_rate < 0.3 or memory_percent > 85:
            new_size = int(current_size * 0.7)
        
        # 調整を実行
        if abs(new_size - current_size) > current_size * 0.1:  # 10%以上の変化がある場合のみ調整
            action = AdjustmentAction(
                action_id=f"cache_size_{int(time.time())}",
                parameter_name=f"{cache_name}_cache_size",
                old_value=current_size,
                new_value=new_size,
                reason=f"ヒット率: {hit_rate:.2%}, メモリ: {memory_percent:.1f}%",
                executed_at=datetime.now().isoformat(),
                result={"success": True}
            )
            
            self.adjustment_history.append(action)
            self._save_adjustment_history()
            
            return {
                "success": True,
                "parameter": f"{cache_name}_cache_size",
                "old_value": current_size,
                "new_value": new_size,
                "reason": action.reason
            }
        
        return {"skipped": True, "reason": "調整の必要がありません"}
    
    def auto_adjust(self) -> Dict[str, Any]:
        """
        自動調整を実行
        
        Returns:
            調整結果
        """
        if not self.config.get("enable_auto_adjustment", True):
            return {"skipped": True, "reason": "自動調整が無効です"}
        
        adjustments = []
        
        # リソース使用率を取得
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        context = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent
        }
        
        # レート制限の調整
        rate_limit_result = self.adjust_rate_limit("default", 100.0, context)
        if rate_limit_result.get("success"):
            adjustments.append(rate_limit_result)
        
        return {
            "success": True,
            "adjustments": adjustments,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_adjustment_summary(self) -> Dict[str, Any]:
        """
        調整サマリーを取得
        
        Returns:
            調整サマリー
        """
        recent_adjustments = [
            adj for adj in self.adjustment_history
            if datetime.fromisoformat(adj.executed_at) > datetime.now() - timedelta(hours=24)
        ]
        
        parameter_counts = {}
        for adj in recent_adjustments:
            param_name = adj.parameter_name
            parameter_counts[param_name] = parameter_counts.get(param_name, 0) + 1
        
        return {
            "total_adjustments_24h": len(recent_adjustments),
            "parameter_counts": parameter_counts,
            "recent_adjustments": [asdict(adj) for adj in recent_adjustments[-10:]],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "adjustment_history_count": len(self.adjustment_history),
            "current_parameters": self.current_parameters,
            "config": self.config,
            "adjustment_summary": self.get_adjustment_summary(),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    system = SelfAdjustmentSystem()
    
    # テスト: 自動調整
    result = system.auto_adjust()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # テスト: 状態取得
    status = system.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()








