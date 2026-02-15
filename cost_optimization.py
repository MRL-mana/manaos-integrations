"""
コスト最適化システム
リソース使用のコスト分析と最適化
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import psutil
from manaos_logger import get_logger

logger = get_logger(__name__)


class CostOptimization:
    """コスト最適化システム"""
    
    def __init__(self):
        """初期化"""
        self.resource_costs = {
            "cpu_per_hour": 0.01,  # 仮想的なコスト（実際の値に置き換え可能）
            "memory_per_gb_hour": 0.005,
            "disk_per_gb_hour": 0.001,
            "network_per_gb": 0.01
        }
        
        self.usage_history = []
        self.cost_history = []
        self.optimization_suggestions = []
        self.storage_path = Path("cost_optimization_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.resource_costs = state.get("resource_costs", self.resource_costs)
                    self.usage_history = state.get("usage_history", [])[-1000:]
                    self.cost_history = state.get("cost_history", [])[-1000:]
                    self.optimization_suggestions = state.get("suggestions", [])[-100:]
            except Exception as e:
                logger.debug("状態ファイル読み込み失敗: %s", e)
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "resource_costs": self.resource_costs,
                    "usage_history": self.usage_history[-1000:],
                    "cost_history": self.cost_history[-1000:],
                    "suggestions": self.optimization_suggestions[-100:],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
    def calculate_resource_cost(
        self,
        cpu_percent: float,
        memory_gb: float,
        disk_gb: float,
        network_gb: float,
        hours: float = 1.0
    ) -> Dict[str, float]:
        """
        リソースコストを計算
        
        Args:
            cpu_percent: CPU使用率
            memory_gb: メモリ使用量（GB）
            disk_gb: ディスク使用量（GB）
            network_gb: ネットワーク使用量（GB）
            hours: 時間
            
        Returns:
            コストの内訳
        """
        costs = {
            "cpu": (cpu_percent / 100) * self.resource_costs["cpu_per_hour"] * hours,
            "memory": memory_gb * self.resource_costs["memory_per_gb_hour"] * hours,
            "disk": disk_gb * self.resource_costs["disk_per_gb_hour"] * hours,
            "network": network_gb * self.resource_costs["network_per_gb"],
            "total": 0
        }
        
        costs["total"] = sum(costs.values())
        return costs
    
    def record_usage(self, duration_hours: float = 1.0):
        """
        使用量を記録
        
        Args:
            duration_hours: 記録期間（時間）
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            memory_gb = memory.total / (1024 ** 3)
            disk_gb = disk.used / (1024 ** 3)
            network_gb = (network.bytes_sent + network.bytes_recv) / (1024 ** 3)
            
            usage = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_gb": memory_gb,
                "disk_gb": disk_gb,
                "network_gb": network_gb,
                "duration_hours": duration_hours
            }
            
            costs = self.calculate_resource_cost(
                cpu_percent, memory_gb, disk_gb, network_gb, duration_hours
            )
            
            cost_record = {
                **usage,
                "costs": costs
            }
            
            self.usage_history.append(usage)
            self.cost_history.append(cost_record)
            
            self._save_state()
            
            return cost_record
            
        except Exception as e:
            print(f"使用量記録エラー: {e}")
            return {}
    
    def analyze_costs(self, days: int = 7) -> Dict[str, Any]:
        """
        コストを分析
        
        Args:
            days: 分析期間（日）
            
        Returns:
            分析結果
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_costs = [
            c for c in self.cost_history
            if datetime.fromisoformat(c["timestamp"]) > cutoff
        ]
        
        if not recent_costs:
            return {}
        
        total_costs = {
            "cpu": sum(c["costs"]["cpu"] for c in recent_costs),
            "memory": sum(c["costs"]["memory"] for c in recent_costs),
            "disk": sum(c["costs"]["disk"] for c in recent_costs),
            "network": sum(c["costs"]["network"] for c in recent_costs),
            "total": sum(c["costs"]["total"] for c in recent_costs)
        }
        
        average_daily = {
            "cpu": total_costs["cpu"] / days,
            "memory": total_costs["memory"] / days,
            "disk": total_costs["disk"] / days,
            "network": total_costs["network"] / days,
            "total": total_costs["total"] / days
        }
        
        # 最もコストが高いリソース
        max_cost_resource = max(
            ["cpu", "memory", "disk", "network"],
            key=lambda r: total_costs[r]
        )
        
        return {
            "period_days": days,
            "total_costs": total_costs,
            "average_daily": average_daily,
            "max_cost_resource": max_cost_resource,
            "projected_monthly": {
                k: v * 30 for k, v in average_daily.items()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """
        最適化を提案
        
        Returns:
            最適化提案のリスト
        """
        suggestions = []
        
        # 最近のコストを分析
        analysis = self.analyze_costs(days=7)
        if not analysis:
            return suggestions
        
        total_costs = analysis["total_costs"]
        max_resource = analysis["max_cost_resource"]
        
        # CPUコストが高い場合
        if max_resource == "cpu" and total_costs["cpu"] > total_costs["total"] * 0.4:
            suggestions.append({
                "type": "reduce_cpu",
                "priority": "high",
                "current_cost": total_costs["cpu"],
                "suggestion": "CPU使用率が高いです。不要なプロセスを終了するか、より効率的なアルゴリズムを使用してください。",
                "potential_savings": total_costs["cpu"] * 0.3
            })
        
        # メモリコストが高い場合
        if max_resource == "memory" and total_costs["memory"] > total_costs["total"] * 0.4:
            suggestions.append({
                "type": "reduce_memory",
                "priority": "high",
                "current_cost": total_costs["memory"],
                "suggestion": "メモリ使用量が高いです。キャッシュを最適化するか、メモリリークを確認してください。",
                "potential_savings": total_costs["memory"] * 0.2
            })
        
        # ディスクコストが高い場合
        if max_resource == "disk" and total_costs["disk"] > total_costs["total"] * 0.3:
            suggestions.append({
                "type": "reduce_disk",
                "priority": "medium",
                "current_cost": total_costs["disk"],
                "suggestion": "ディスク使用量が高いです。不要なファイルを削除するか、圧縮を検討してください。",
                "potential_savings": total_costs["disk"] * 0.25
            })
        
        # ネットワークコストが高い場合
        if max_resource == "network" and total_costs["network"] > total_costs["total"] * 0.2:
            suggestions.append({
                "type": "reduce_network",
                "priority": "medium",
                "current_cost": total_costs["network"],
                "suggestion": "ネットワーク使用量が高いです。データの圧縮やキャッシュを検討してください。",
                "potential_savings": total_costs["network"] * 0.15
            })
        
        self.optimization_suggestions.extend(suggestions)
        self._save_state()
        
        return suggestions
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """コストサマリーを取得"""
        analysis = self.analyze_costs(days=7)
        suggestions = self.suggest_optimizations()
        
        return {
            "current_analysis": analysis,
            "optimization_suggestions": suggestions,
            "total_suggested_savings": sum(s.get("potential_savings", 0) for s in suggestions),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("コスト最適化システムテスト")
    print("=" * 60)
    
    cost_opt = CostOptimization()
    
    # 使用量を記録
    print("\n使用量を記録中...")
    cost_record = cost_opt.record_usage(duration_hours=1.0)
    print(f"コスト記録: {cost_record.get('costs', {})}")
    
    # コストを分析
    print("\nコストを分析中...")
    analysis = cost_opt.analyze_costs(days=7)
    print(f"分析結果: {analysis.get('total_costs', {})}")
    print(f"1日平均: {analysis.get('average_daily', {})}")
    print(f"月間予測: {analysis.get('projected_monthly', {})}")
    
    # 最適化を提案
    print("\n最適化を提案中...")
    suggestions = cost_opt.suggest_optimizations()
    print(f"提案数: {len(suggestions)}")
    for suggestion in suggestions:
        print(f"  - {suggestion['suggestion']}")
        print(f"    潜在的な節約: ${suggestion.get('potential_savings', 0):.4f}")


if __name__ == "__main__":
    main()



















