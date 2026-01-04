"""
自動最適化システム
パフォーマンス自動調整とリソース最適化
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from predictive_maintenance import PredictiveMaintenance
from workflow_automation import WorkflowAutomation


class AutoOptimization:
    """自動最適化システム"""
    
    def __init__(self):
        """初期化"""
        self.maintenance = PredictiveMaintenance()
        self.workflow = WorkflowAutomation()
        
        self.optimization_history = []
        self.optimization_rules = []
        self.storage_path = Path("auto_optimization_state.json")
        self._load_state()
        self._initialize_rules()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.optimization_history = state.get("history", [])[-100:]
                    self.optimization_rules = state.get("rules", [])
            except:
                self.optimization_history = []
                self.optimization_rules = []
        else:
            self.optimization_history = []
            self.optimization_rules = []
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "history": self.optimization_history[-100:],
                    "rules": self.optimization_rules,
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
    def _initialize_rules(self):
        """最適化ルールを初期化"""
        if not self.optimization_rules:
            self.optimization_rules = [
                {
                    "name": "高CPU使用率時の最適化",
                    "condition": lambda m: m.get("cpu", 0) > 80,
                    "action": "reduce_workload",
                    "priority": 1
                },
                {
                    "name": "高メモリ使用率時の最適化",
                    "condition": lambda m: m.get("memory", 0) > 85,
                    "action": "clear_cache",
                    "priority": 2
                },
                {
                    "name": "高ディスク使用率時の最適化",
                    "condition": lambda m: m.get("disk", 0) > 90,
                    "action": "cleanup_files",
                    "priority": 3
                },
                {
                    "name": "低リソース使用時の最適化",
                    "condition": lambda m: m.get("cpu", 0) < 20 and m.get("memory", 0) < 30,
                    "action": "increase_workload",
                    "priority": 4
                }
            ]
            self._save_state()
    
    def optimize(self) -> Dict[str, Any]:
        """
        自動最適化を実行
        
        Returns:
            最適化結果
        """
        status = self.maintenance.get_status()
        metrics = status["current_metrics"]
        
        optimizations = []
        
        # ルールを優先度順にソート
        sorted_rules = sorted(self.optimization_rules, key=lambda x: x["priority"])
        
        for rule in sorted_rules:
            if rule["condition"](metrics):
                action_result = self._execute_action(rule["action"], metrics)
                if action_result:
                    optimizations.append({
                        "rule": rule["name"],
                        "action": rule["action"],
                        "result": action_result,
                        "timestamp": datetime.now().isoformat()
                    })
        
        result = {
            "optimizations": optimizations,
            "metrics_before": metrics,
            "metrics_after": self.maintenance.collect_metrics(),
            "timestamp": datetime.now().isoformat()
        }
        
        self.optimization_history.append(result)
        self._save_state()
        
        return result
    
    def _execute_action(self, action: str, metrics: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        アクションを実行
        
        Args:
            action: アクション名
            metrics: メトリクス
            
        Returns:
            実行結果
        """
        if action == "reduce_workload":
            return self._reduce_workload()
        elif action == "clear_cache":
            return self._clear_cache()
        elif action == "cleanup_files":
            return self._cleanup_files()
        elif action == "increase_workload":
            return self._increase_workload()
        else:
            return None
    
    def _reduce_workload(self) -> Dict[str, Any]:
        """ワークロードを削減"""
        # 実際の実装では、実行中のタスクを一時停止または優先度を下げる
        return {
            "action": "reduce_workload",
            "description": "ワークロードを削減しました",
            "success": True
        }
    
    def _clear_cache(self) -> Dict[str, Any]:
        """キャッシュをクリア"""
        # 実際の実装では、キャッシュをクリアする
        return {
            "action": "clear_cache",
            "description": "キャッシュをクリアしました",
            "success": True
        }
    
    def _cleanup_files(self) -> Dict[str, Any]:
        """ファイルをクリーンアップ"""
        # 実際の実装では、一時ファイルを削除する
        return {
            "action": "cleanup_files",
            "description": "一時ファイルをクリーンアップしました",
            "success": True
        }
    
    def _increase_workload(self) -> Dict[str, Any]:
        """ワークロードを増加"""
        # 実際の実装では、待機中のタスクを開始する
        return {
            "action": "increase_workload",
            "description": "ワークロードを増加しました",
            "success": True
        }
    
    def add_optimization_rule(
        self,
        name: str,
        condition: callable,
        action: str,
        priority: int = 5
    ):
        """
        最適化ルールを追加
        
        Args:
            name: ルール名
            condition: 条件関数
            action: アクション名
            priority: 優先度
        """
        self.optimization_rules.append({
            "name": name,
            "condition": condition,
            "action": action,
            "priority": priority
        })
        self._save_state()
    
    def run_continuous_optimization(self, interval: int = 60):
        """
        継続的な最適化を実行
        
        Args:
            interval: 実行間隔（秒）
        """
        print("自動最適化システムを開始...")
        print(f"実行間隔: {interval}秒")
        
        while True:
            try:
                result = self.optimize()
                
                if result["optimizations"]:
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 最適化実行:")
                    for opt in result["optimizations"]:
                        print(f"  - {opt['rule']}: {opt['result']['description']}")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n自動最適化システムを停止します...")
                break
            except Exception as e:
                print(f"最適化エラー: {e}")
                time.sleep(interval)
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "rules_count": len(self.optimization_rules),
            "history_count": len(self.optimization_history),
            "last_optimization": self.optimization_history[-1] if self.optimization_history else None,
            "maintenance_status": self.maintenance.get_status()
        }


def main():
    """テスト用メイン関数"""
    print("自動最適化システムテスト")
    print("=" * 60)
    
    optimizer = AutoOptimization()
    
    # 最適化を実行
    print("\n最適化を実行中...")
    result = optimizer.optimize()
    
    print(f"\n最適化結果:")
    print(f"  実行された最適化: {len(result['optimizations'])}件")
    
    for opt in result["optimizations"]:
        print(f"  - {opt['rule']}: {opt['result']['description']}")
    
    # 状態を表示
    status = optimizer.get_status()
    print(f"\n状態:")
    print(f"  ルール数: {status['rules_count']}")
    print(f"  履歴数: {status['history_count']}")


if __name__ == "__main__":
    main()




















