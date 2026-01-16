"""
LLMルーティングシステム 自動最適化
パフォーマンスデータから最適な設定を提案
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
import statistics

LOG_DIR = Path("logs")
PERFORMANCE_LOG_FILE = LOG_DIR / "llm_routing_performance.jsonl"


class LLMRoutingOptimizer:
    """LLMルーティング最適化クラス"""
    
    def __init__(self):
        self.performance_logs = []
        self._load_logs()
    
    def _load_logs(self):
        """パフォーマンスログを読み込み"""
        if PERFORMANCE_LOG_FILE.exists():
            with open(PERFORMANCE_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        self.performance_logs.append(json.loads(line.strip()))
                    except:
                        pass
    
    def analyze_performance(self) -> Dict[str, Any]:
        """パフォーマンスを分析"""
        if not self.performance_logs:
            return {
                "status": "no_data",
                "message": "パフォーマンスデータがありません"
            }
        
        # モデル別の統計
        model_stats = defaultdict(lambda: {"response_times": [], "success_count": 0, "total_count": 0})
        
        for log in self.performance_logs:
            model = log.get("model", "unknown")
            response_time = log.get("response_time_ms", 0)
            success = log.get("success", False)
            
            model_stats[model]["response_times"].append(response_time)
            model_stats[model]["total_count"] += 1
            if success:
                model_stats[model]["success_count"] += 1
        
        # モデル別の平均レスポンス時間と成功率を計算
        model_analysis = {}
        for model, stats in model_stats.items():
            response_times = stats["response_times"]
            if response_times:
                model_analysis[model] = {
                    "mean_response_time": statistics.mean(response_times),
                    "median_response_time": statistics.median(response_times),
                    "success_rate": (stats["success_count"] / stats["total_count"] * 100) if stats["total_count"] > 0 else 0,
                    "total_requests": stats["total_count"]
                }
        
        return {
            "status": "ok",
            "model_analysis": model_analysis,
            "total_logs": len(self.performance_logs)
        }
    
    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """最適化提案を生成"""
        recommendations = []
        
        analysis = self.analyze_performance()
        if analysis["status"] != "ok":
            return recommendations
        
        model_analysis = analysis["model_analysis"]
        
        # 提案1: 最も速いモデルを推奨
        if model_analysis:
            fastest_model = min(
                model_analysis.items(),
                key=lambda x: x[1]["mean_response_time"]
            )
            recommendations.append({
                "type": "speed_optimization",
                "priority": "high",
                "title": "速度最適化",
                "description": f"最も速いモデル '{fastest_model[0]}' を常駐用に推奨",
                "details": {
                    "model": fastest_model[0],
                    "mean_response_time": fastest_model[1]["mean_response_time"],
                    "recommendation": "常駐用モデルとして使用"
                }
            })
        
        # 提案2: 成功率が低いモデルを警告
        for model, stats in model_analysis.items():
            if stats["success_rate"] < 80 and stats["total_requests"] >= 10:
                recommendations.append({
                    "type": "reliability_warning",
                    "priority": "medium",
                    "title": "信頼性警告",
                    "description": f"モデル '{model}' の成功率が低いです",
                    "details": {
                        "model": model,
                        "success_rate": stats["success_rate"],
                        "recommendation": "モデルの確認または変更を検討"
                    }
                })
        
        # 提案3: レスポンス時間が長いモデルを警告
        for model, stats in model_analysis.items():
            if stats["mean_response_time"] > 5000 and stats["total_requests"] >= 10:
                recommendations.append({
                    "type": "performance_warning",
                    "priority": "medium",
                    "title": "パフォーマンス警告",
                    "description": f"モデル '{model}' のレスポンス時間が長いです",
                    "details": {
                        "model": model,
                        "mean_response_time": stats["mean_response_time"],
                        "recommendation": "軽量モデルへの変更を検討"
                    }
                })
        
        return recommendations
    
    def print_optimization_report(self):
        """最適化レポートを表示"""
        print("=" * 70)
        print("  LLMルーティングシステム 最適化レポート")
        print("=" * 70)
        print()
        
        analysis = self.analyze_performance()
        
        if analysis["status"] != "ok":
            print(f"⚠️  {analysis['message']}")
            return
        
        # モデル分析
        print("📊 モデル分析")
        print("-" * 70)
        for model, stats in analysis["model_analysis"].items():
            print(f"  {model}")
            print(f"    平均レスポンス時間: {stats['mean_response_time']:.2f}ms")
            print(f"    中央値: {stats['median_response_time']:.2f}ms")
            print(f"    成功率: {stats['success_rate']:.2f}%")
            print(f"    総リクエスト数: {stats['total_requests']}")
            print()
        
        # 最適化提案
        recommendations = self.generate_recommendations()
        if recommendations:
            print("💡 最適化提案")
            print("-" * 70)
            for i, rec in enumerate(recommendations, 1):
                priority_icon = "🔴" if rec["priority"] == "high" else "🟡"
                print(f"  {i}. {priority_icon} {rec['title']}")
                print(f"     {rec['description']}")
                if "details" in rec:
                    for key, value in rec["details"].items():
                        if key != "recommendation":
                            print(f"     - {key}: {value}")
                print()
        else:
            print("  ✅ 最適化の提案はありません")
            print()


def main():
    """メイン関数"""
    optimizer = LLMRoutingOptimizer()
    optimizer.print_optimization_report()


if __name__ == "__main__":
    main()



















