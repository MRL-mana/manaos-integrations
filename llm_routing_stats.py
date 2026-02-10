"""
LLMルーティングシステム 統計ダッシュボード
ログから統計情報を生成
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, List

LOG_DIR = Path("logs")
REQUEST_LOG_FILE = LOG_DIR / "llm_routing_requests.jsonl"
ERROR_LOG_FILE = LOG_DIR / "llm_routing_errors.jsonl"
PERFORMANCE_LOG_FILE = LOG_DIR / "llm_routing_performance.jsonl"


class StatisticsGenerator:
    """統計情報生成クラス"""
    
    def __init__(self):
        self.request_logs = []
        self.error_logs = []
        self.performance_logs = []
        self._load_logs()
    
    def _load_logs(self):
        """ログファイルを読み込み"""
        # リクエストログ
        if REQUEST_LOG_FILE.exists():
            with open(REQUEST_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        self.request_logs.append(json.loads(line.strip()))
                    except Exception:
                        pass
        
        # エラーログ
        if ERROR_LOG_FILE.exists():
            with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        self.error_logs.append(json.loads(line.strip()))
                    except Exception:
                        pass
        
        # パフォーマンスログ
        if PERFORMANCE_LOG_FILE.exists():
            with open(PERFORMANCE_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        self.performance_logs.append(json.loads(line.strip()))
                    except Exception:
                        pass
    
    def generate_statistics(self) -> Dict[str, Any]:
        """統計情報を生成"""
        stats = {
            "summary": self._generate_summary(),
            "model_usage": self._generate_model_usage(),
            "difficulty_distribution": self._generate_difficulty_distribution(),
            "performance": self._generate_performance_stats(),
            "errors": self._generate_error_stats(),
            "recent_activity": self._generate_recent_activity()
        }
        
        return stats
    
    def _generate_summary(self) -> Dict[str, Any]:
        """サマリー統計"""
        total_requests = len(self.request_logs)
        total_errors = len(self.error_logs)
        success_count = sum(1 for log in self.performance_logs if log.get("success", False))
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "success_count": success_count,
            "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
            "success_rate": (success_count / total_requests * 100) if total_requests > 0 else 0
        }
    
    def _generate_model_usage(self) -> Dict[str, int]:
        """モデル使用統計"""
        model_usage = defaultdict(int)
        
        for log in self.performance_logs:
            model = log.get("model", "unknown")
            model_usage[model] += 1
        
        return dict(model_usage)
    
    def _generate_difficulty_distribution(self) -> Dict[str, int]:
        """難易度分布統計"""
        distribution = defaultdict(int)
        
        for log in self.performance_logs:
            score = log.get("difficulty_score", 0)
            if score < 10:
                level = "low"
            elif score < 30:
                level = "medium"
            else:
                level = "high"
            distribution[level] += 1
        
        return dict(distribution)
    
    def _generate_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計"""
        response_times = [log.get("response_time_ms", 0) for log in self.performance_logs if log.get("response_time_ms", 0) > 0]
        
        if not response_times:
            return {
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "count": 0
            }
        
        response_times.sort()
        
        return {
            "mean": sum(response_times) / len(response_times),
            "median": response_times[len(response_times) // 2],
            "min": min(response_times),
            "max": max(response_times),
            "count": len(response_times)
        }
    
    def _generate_error_stats(self) -> Dict[str, Any]:
        """エラー統計"""
        error_types = defaultdict(int)
        
        for log in self.error_logs:
            error = log.get("error", "unknown")
            error_types[error[:50]] += 1  # 最初の50文字
        
        return {
            "total_errors": len(self.error_logs),
            "error_types": dict(error_types),
            "recent_errors": self.error_logs[-10:] if self.error_logs else []
        }
    
    def _generate_recent_activity(self) -> List[Dict[str, Any]]:
        """最近のアクティビティ"""
        recent = []
        
        # リクエストログから最近の10件
        for log in self.request_logs[-10:]:
            recent.append({
                "timestamp": log.get("timestamp"),
                "type": "request",
                "prompt": log.get("prompt", "")[:50]
            })
        
        return recent


def print_statistics(stats: Dict[str, Any]):
    """統計情報を表示"""
    print("=" * 70)
    print("  LLMルーティングシステム 統計ダッシュボード")
    print("=" * 70)
    print()
    
    # サマリー
    summary = stats["summary"]
    print("📊 サマリー")
    print("-" * 70)
    print(f"  総リクエスト数: {summary['total_requests']}")
    print(f"  成功数: {summary['success_count']}")
    print(f"  エラー数: {summary['total_errors']}")
    print(f"  成功率: {summary['success_rate']:.2f}%")
    print(f"  エラー率: {summary['error_rate']:.2f}%")
    print()
    
    # モデル使用率
    if stats["model_usage"]:
        print("🤖 モデル使用率")
        print("-" * 70)
        total = sum(stats["model_usage"].values())
        for model, count in sorted(stats["model_usage"].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {model}: {count}回 ({percentage:.1f}%)")
        print()
    
    # 難易度分布
    if stats["difficulty_distribution"]:
        print("📈 難易度分布")
        print("-" * 70)
        total = sum(stats["difficulty_distribution"].values())
        for level, count in sorted(stats["difficulty_distribution"].items()):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {level}: {count}回 ({percentage:.1f}%)")
        print()
    
    # パフォーマンス
    perf = stats["performance"]
    if perf["count"] > 0:
        print("⏱️  パフォーマンス")
        print("-" * 70)
        print(f"  平均レスポンス時間: {perf['mean']:.2f}ms")
        print(f"  中央値: {perf['median']:.2f}ms")
        print(f"  最小: {perf['min']:.2f}ms")
        print(f"  最大: {perf['max']:.2f}ms")
        print()
    
    # エラー統計
    errors = stats["errors"]
    if errors["total_errors"] > 0:
        print("❌ エラー統計")
        print("-" * 70)
        print(f"  総エラー数: {errors['total_errors']}")
        if errors["error_types"]:
            print("  エラータイプ:")
            for error_type, count in list(errors["error_types"].items())[:5]:
                print(f"    - {error_type}: {count}回")
        print()


def main():
    """メイン関数"""
    generator = StatisticsGenerator()
    stats = generator.generate_statistics()
    print_statistics(stats)


if __name__ == "__main__":
    main()



















