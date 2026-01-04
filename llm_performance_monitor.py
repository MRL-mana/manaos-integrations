"""
📊 LLMパフォーマンス監視システム
レイテンシ、スループット、キャッシュヒット率などを監視
"""

import time
import json
import requests
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    timestamp: str
    model: str
    task_type: str
    latency_ms: float
    cached: bool
    tokens: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


class LLMPerformanceMonitor:
    """LLMパフォーマンス監視システム"""
    
    def __init__(
        self,
        client: AlwaysReadyLLMClient,
        window_size: int = 100,  # スライディングウィンドウサイズ
        metrics_file: str = "llm_metrics.json"
    ):
        """
        初期化
        
        Args:
            client: LLMクライアント
            window_size: スライディングウィンドウサイズ
            metrics_file: メトリクス保存ファイル
        """
        self.client = client
        self.window_size = window_size
        self.metrics_file = metrics_file
        self.metrics: deque = deque(maxlen=window_size)
        self.start_time = time.time()
    
    def record(
        self,
        message: str,
        model: ModelType,
        task_type: TaskType,
        response: Optional[Any] = None,
        error: Optional[Exception] = None
    ):
        """
        メトリクス記録
        
        Args:
            message: メッセージ
            model: モデル
            task_type: タスクタイプ
            response: レスポンス（成功時）
            error: エラー（失敗時）
        """
        if response:
            metric = PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                model=model.value,
                task_type=task_type.value,
                latency_ms=response.latency_ms,
                cached=response.cached,
                tokens=response.tokens,
                success=True
            )
        else:
            metric = PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                model=model.value,
                task_type=task_type.value,
                latency_ms=0.0,
                cached=False,
                success=False,
                error_message=str(error) if error else "Unknown error"
            )
        
        self.metrics.append(metric)
        self._save_metrics()
    
    def _save_metrics(self):
        """メトリクスをファイルに保存"""
        try:
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(m) for m in self.metrics], f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_stats(self, model: Optional[str] = None, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        統計情報取得
        
        Args:
            model: モデルフィルタ（Noneの場合は全モデル）
            task_type: タスクタイプフィルタ（Noneの場合は全タスク）
        
        Returns:
            統計情報
        """
        # フィルタリング
        filtered_metrics = list(self.metrics)
        if model:
            filtered_metrics = [m for m in filtered_metrics if m.model == model]
        if task_type:
            filtered_metrics = [m for m in filtered_metrics if m.task_type == task_type]
        
        if not filtered_metrics:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "cache_hit_rate": 0.0,
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0
            }
        
        # 成功/失敗統計
        total = len(filtered_metrics)
        successful = [m for m in filtered_metrics if m.success]
        success_count = len(successful)
        
        # キャッシュ統計
        cached_count = sum(1 for m in successful if m.cached)
        
        # レイテンシ統計
        latencies = [m.latency_ms for m in successful]
        
        return {
            "total_requests": total,
            "success_count": success_count,
            "failure_count": total - success_count,
            "success_rate": success_count / total if total > 0 else 0.0,
            "cache_hit_count": cached_count,
            "cache_hit_rate": cached_count / success_count if success_count > 0 else 0.0,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0.0,
            "min_latency_ms": min(latencies) if latencies else 0.0,
            "max_latency_ms": max(latencies) if latencies else 0.0,
            "p50_latency_ms": statistics.median(latencies) if latencies else 0.0,
            "p95_latency_ms": self._percentile(latencies, 95) if latencies else 0.0,
            "p99_latency_ms": self._percentile(latencies, 99) if latencies else 0.0,
            "total_tokens": sum(m.tokens or 0 for m in successful),
            "avg_tokens_per_request": (
                sum(m.tokens or 0 for m in successful) / success_count
                if success_count > 0 else 0
            ),
            "uptime_seconds": time.time() - self.start_time
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """パーセンタイル計算"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_model_comparison(self) -> Dict[str, Any]:
        """モデル比較統計"""
        models = set(m.model for m in self.metrics)
        comparison = {}
        
        for model in models:
            comparison[model] = self.get_stats(model=model)
        
        return comparison
    
    def get_task_type_comparison(self) -> Dict[str, Any]:
        """タスクタイプ比較統計"""
        task_types = set(m.task_type for m in self.metrics)
        comparison = {}
        
        for task_type in task_types:
            comparison[task_type] = self.get_stats(task_type=task_type)
        
        return comparison
    
    def print_dashboard(self):
        """ダッシュボード表示"""
        print("=" * 60)
        print("📊 LLMパフォーマンスダッシュボード")
        print("=" * 60)
        
        # 全体統計
        stats = self.get_stats()
        print("\n【全体統計】")
        print(f"  総リクエスト数: {stats['total_requests']}")
        print(f"  成功率: {stats['success_rate']*100:.2f}%")
        print(f"  キャッシュヒット率: {stats['cache_hit_rate']*100:.2f}%")
        print(f"  平均レイテンシ: {stats['avg_latency_ms']:.2f}ms")
        print(f"  P50レイテンシ: {stats['p50_latency_ms']:.2f}ms")
        print(f"  P95レイテンシ: {stats['p95_latency_ms']:.2f}ms")
        print(f"  P99レイテンシ: {stats['p99_latency_ms']:.2f}ms")
        
        # モデル比較
        print("\n【モデル別統計】")
        model_comparison = self.get_model_comparison()
        for model, model_stats in model_comparison.items():
            print(f"\n  {model}:")
            print(f"    リクエスト数: {model_stats['total_requests']}")
            print(f"    成功率: {model_stats['success_rate']*100:.2f}%")
            print(f"    平均レイテンシ: {model_stats['avg_latency_ms']:.2f}ms")
            print(f"    キャッシュヒット率: {model_stats['cache_hit_rate']*100:.2f}%")
        
        # タスクタイプ比較
        print("\n【タスクタイプ別統計】")
        task_comparison = self.get_task_type_comparison()
        for task_type, task_stats in task_comparison.items():
            print(f"\n  {task_type}:")
            print(f"    リクエスト数: {task_stats['total_requests']}")
            print(f"    成功率: {task_stats['success_rate']*100:.2f}%")
            print(f"    平均レイテンシ: {task_stats['avg_latency_ms']:.2f}ms")
        
        print("\n" + "=" * 60)


# 使用例
if __name__ == "__main__":
    from always_ready_llm_client import AlwaysReadyLLMClient
    
    # クライアントとモニター初期化
    client = AlwaysReadyLLMClient()
    monitor = LLMPerformanceMonitor(client)
    
    # テストリクエスト
    test_messages = [
        "こんにちは",
        "今日の天気は？",
        "Pythonでクイックソートを実装してください",
        "ありがとう"
    ]
    
    print("=== パフォーマンステスト開始 ===")
    
    for i, message in enumerate(test_messages):
        print(f"\n[{i+1}/{len(test_messages)}] {message[:30]}...")
        
        try:
            response = client.chat(message, ModelType.LIGHT, TaskType.CONVERSATION)
            monitor.record(message, ModelType.LIGHT, TaskType.CONVERSATION, response=response)
            print(f"  ✅ 成功 (レイテンシ: {response.latency_ms:.2f}ms, キャッシュ: {response.cached})")
        except Exception as e:
            monitor.record(message, ModelType.LIGHT, TaskType.CONVERSATION, error=e)
            print(f"  ❌ 失敗: {e}")
    
    # ダッシュボード表示
    monitor.print_dashboard()

