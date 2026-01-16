"""
LLMルーティングシステム パフォーマンス監視
レスポンス時間、成功率、モデル使用率などを監視
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict
import statistics

# APIエンドポイント
UNIFIED_API_URL = "http://localhost:9500"


class LLMPerformanceMonitor:
    """LLMパフォーマンス監視クラス"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "model_usage": defaultdict(int),
            "difficulty_distribution": defaultdict(int),
            "requests_by_hour": defaultdict(int)
        }
    
    def record_request(
        self,
        model: str,
        difficulty_score: float,
        difficulty_level: str,
        response_time_ms: int,
        success: bool
    ):
        """リクエストを記録"""
        self.metrics["total_requests"] += 1
        
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        self.metrics["response_times"].append(response_time_ms)
        self.metrics["model_usage"][model] += 1
        self.metrics["difficulty_distribution"][difficulty_level] += 1
        
        current_hour = datetime.now().strftime("%Y-%m-%d %H:00")
        self.metrics["requests_by_hour"][current_hour] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        response_times = self.metrics["response_times"]
        
        stats = {
            "total_requests": self.metrics["total_requests"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0
                else 0
            ) * 100,
            "response_time": {
                "mean": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
            },
            "model_usage": dict(self.metrics["model_usage"]),
            "difficulty_distribution": dict(self.metrics["difficulty_distribution"]),
            "requests_by_hour": dict(self.metrics["requests_by_hour"])
        }
        
        return stats
    
    def print_statistics(self):
        """統計情報を表示"""
        stats = self.get_statistics()
        
        print("\n" + "=" * 60)
        print("  LLMパフォーマンス統計")
        print("=" * 60)
        
        print(f"\n📊 リクエスト統計")
        print(f"  総リクエスト数: {stats['total_requests']}")
        print(f"  成功: {stats['successful_requests']}")
        print(f"  失敗: {stats['failed_requests']}")
        print(f"  成功率: {stats['success_rate']:.2f}%")
        
        if stats['response_time']['mean'] > 0:
            print(f"\n⏱️  レスポンス時間")
            print(f"  平均: {stats['response_time']['mean']:.2f}ms")
            print(f"  中央値: {stats['response_time']['median']:.2f}ms")
            print(f"  最小: {stats['response_time']['min']:.2f}ms")
            print(f"  最大: {stats['response_time']['max']:.2f}ms")
        
        if stats['model_usage']:
            print(f"\n🤖 モデル使用率")
            total = sum(stats['model_usage'].values())
            for model, count in sorted(stats['model_usage'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total) * 100 if total > 0 else 0
                print(f"  {model}: {count}回 ({percentage:.1f}%)")
        
        if stats['difficulty_distribution']:
            print(f"\n📈 難易度分布")
            total = sum(stats['difficulty_distribution'].values())
            for level, count in sorted(stats['difficulty_distribution'].items()):
                percentage = (count / total) * 100 if total > 0 else 0
                print(f"  {level}: {count}回 ({percentage:.1f}%)")
        
        print("\n" + "=" * 60)


def test_performance(monitor: LLMPerformanceMonitor, num_requests: int = 10):
    """パフォーマンステストを実行"""
    print(f"\n📊 パフォーマンステストを実行中... ({num_requests}リクエスト)")
    
    test_prompts = [
        {
            "prompt": "この関数のタイポを修正して",
            "code_context": "def hello():\n    print('helo')"
        },
        {
            "prompt": "このコードをリファクタリングして",
            "code_context": "def process(data):\n    for item in data:\n        print(item)"
        }
    ]
    
    for i in range(num_requests):
        test_case = test_prompts[i % len(test_prompts)]
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{UNIFIED_API_URL}/api/llm/route-enhanced",
                json={
                    "prompt": test_case["prompt"],
                    "context": {
                        "code_context": test_case["code_context"]
                    },
                    "preferences": {
                        "prefer_speed": True
                    }
                },
                timeout=300
            )
            
            elapsed_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                monitor.record_request(
                    model=result.get('model', 'unknown'),
                    difficulty_score=result.get('difficulty_score', 0),
                    difficulty_level=result.get('difficulty_level', 'unknown'),
                    response_time_ms=result.get('response_time_ms', elapsed_time_ms),
                    success=result.get('success', False)
                )
                print(f"  [{i+1}/{num_requests}] ✅ {result.get('model')} ({result.get('response_time_ms', 0)}ms)")
            else:
                monitor.record_request(
                    model='unknown',
                    difficulty_score=0,
                    difficulty_level='unknown',
                    response_time_ms=elapsed_time_ms,
                    success=False
                )
                print(f"  [{i+1}/{num_requests}] ❌ HTTP {response.status_code}")
        
        except Exception as e:
            monitor.record_request(
                model='unknown',
                difficulty_score=0,
                difficulty_level='unknown',
                response_time_ms=0,
                success=False
            )
            print(f"  [{i+1}/{num_requests}] ❌ エラー: {e}")


def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print("  LLMパフォーマンス監視")
    print("=" * 60)
    
    monitor = LLMPerformanceMonitor()
    
    # APIサーバーの確認
    try:
        response = requests.get(f"{UNIFIED_API_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ APIサーバーに接続できません")
            return
    except:
        print("❌ APIサーバーに接続できません")
        print(f"   URL: {UNIFIED_API_URL}")
        return
    
    print("✅ APIサーバーに接続できました")
    
    # パフォーマンステスト
    user_input = input("\nパフォーマンステストを実行しますか？ (y/n): ")
    if user_input.lower() == 'y':
        num_requests = input("リクエスト数 (デフォルト: 10): ")
        num_requests = int(num_requests) if num_requests.isdigit() else 10
        
        test_performance(monitor, num_requests)
        
        # 統計情報を表示
        monitor.print_statistics()
    else:
        print("パフォーマンステストをスキップしました")
    
    print("\n✅ 監視完了")


if __name__ == "__main__":
    main()



















