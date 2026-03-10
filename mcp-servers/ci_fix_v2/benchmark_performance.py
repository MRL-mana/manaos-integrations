"""
ManaOS Performance Benchmark Script
システム全体の性能を測定し、ボトルネックを特定
"""

import time
import statistics
import requests
import asyncio
import aiohttp
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime
import sys
import os

# _paths から設定をインポート
try:
    from _paths import (
        UNIFIED_API_URL, MRL_MEMORY_URL, LEARNING_SYSTEM_URL,  # type: ignore[attr-defined]
        LLM_ROUTING_URL, OLLAMA_URL, COMFYUI_URL, GALLERY_URL,  # type: ignore[attr-defined]
        N8N_URL, SEARXNG_URL  # type: ignore[attr-defined]
    )
except ImportError:
    print("⚠️ _paths.py が見つかりません。デフォルト値を使用します。")
    UNIFIED_API_URL = "http://127.0.0.1:9502"
    MRL_MEMORY_URL = "http://127.0.0.1:9507"
    LEARNING_SYSTEM_URL = "http://127.0.0.1:9508"
    LLM_ROUTING_URL = "http://127.0.0.1:9509"
    OLLAMA_URL = "http://127.0.0.1:11434"
    COMFYUI_URL = "http://127.0.0.1:8188"
    GALLERY_URL = "http://127.0.0.1:5559"
    N8N_URL = "http://127.0.0.1:5678"
    SEARXNG_URL = "http://127.0.0.1:8080"


@dataclass
class BenchmarkResult:
    """ベンチマーク結果データクラス"""
    service_name: str
    endpoint: str
    response_time_ms: float
    success: bool
    status_code: int = 0
    error: str = ""


@dataclass
class ServiceBenchmark:
    """サービス別ベンチマーク結果"""
    service_name: str
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    std_dev: float
    success_rate: float
    total_requests: int
    successful_requests: int
    failed_requests: int


class PerformanceBenchmark:
    """パフォーマンスベンチマーククラス"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.services = {
            "Unified API": UNIFIED_API_URL,
            "MRL Memory": MRL_MEMORY_URL,
            "Learning System": LEARNING_SYSTEM_URL,
            "LLM Routing": LLM_ROUTING_URL,
            "Ollama": OLLAMA_URL,
            "ComfyUI": COMFYUI_URL,
            "Gallery API": GALLERY_URL,
            "n8n": N8N_URL,
            "SearXNG": SEARXNG_URL
        }
    
    def benchmark_single_request(self, service_name: str, url: str, endpoint: str = "/health") -> BenchmarkResult:
        """単一リクエストのベンチマーク"""
        start_time = time.time()
        
        try:
            response = requests.get(f"{url}{endpoint}", timeout=5)
            response_time = (time.time() - start_time) * 1000  # ミリ秒
            
            return BenchmarkResult(
                service_name=service_name,
                endpoint=endpoint,
                response_time_ms=response_time,
                success=response.status_code == 200,
                status_code=response.status_code
            )
        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            return BenchmarkResult(
                service_name=service_name,
                endpoint=endpoint,
                response_time_ms=response_time,
                success=False,
                error="Timeout"
            )
        except requests.exceptions.ConnectionError:
            response_time = (time.time() - start_time) * 1000
            return BenchmarkResult(
                service_name=service_name,
                endpoint=endpoint,
                response_time_ms=response_time,
                success=False,
                error="Connection Error"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return BenchmarkResult(
                service_name=service_name,
                endpoint=endpoint,
                response_time_ms=response_time,
                success=False,
                error=str(e)
            )
    
    def benchmark_concurrent_requests(self, service_name: str, url: str, num_requests: int = 10) -> List[BenchmarkResult]:
        """並行リクエストのベンチマーク"""
        results = []
        
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [
                executor.submit(self.benchmark_single_request, service_name, url)
                for _ in range(num_requests)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    async def benchmark_async_requests(self, service_name: str, url: str, num_requests: int = 10) -> List[BenchmarkResult]:
        """非同期並行リクエストのベンチマーク"""
        results = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(num_requests):
                tasks.append(self._async_request(session, service_name, url))
            
            results = await asyncio.gather(*tasks)
        
        return results
    
    async def _async_request(self, session: aiohttp.ClientSession, service_name: str, url: str) -> BenchmarkResult:
        """非同期リクエスト処理"""
        start_time = time.time()
        
        try:
            async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_time = (time.time() - start_time) * 1000
                
                return BenchmarkResult(
                    service_name=service_name,
                    endpoint="/health",
                    response_time_ms=response_time,
                    success=response.status == 200,
                    status_code=response.status
                )
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return BenchmarkResult(
                service_name=service_name,
                endpoint="/health",
                response_time_ms=response_time,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return BenchmarkResult(
                service_name=service_name,
                endpoint="/health",
                response_time_ms=response_time,
                success=False,
                error=str(e)
            )
    
    def calculate_statistics(self, results: List[BenchmarkResult]) -> ServiceBenchmark:
        """統計情報を計算"""
        response_times = [r.response_time_ms for r in results]
        successful_results = [r for r in results if r.success]
        
        return ServiceBenchmark(
            service_name=results[0].service_name,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            std_dev=statistics.stdev(response_times) if len(response_times) > 1 else 0,
            success_rate=(len(successful_results) / len(results)) * 100,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(results) - len(successful_results)
        )
    
    def run_sequential_benchmark(self, iterations: int = 5):
        """シーケンシャルベンチマーク実行"""
        print("\n🔄 シーケンシャルベンチマーク実行中...")
        print(f"各サービスに {iterations} 回リクエスト\n")
        
        for service_name, url in self.services.items():
            print(f"  → {service_name}...", end=" ")
            
            results = []
            for _ in range(iterations):
                result = self.benchmark_single_request(service_name, url)
                results.append(result)
                self.results.append(result)
            
            stats = self.calculate_statistics(results)
            
            if stats.success_rate > 0:
                print(f"✅ 平均 {stats.avg_response_time:.2f}ms")
            else:
                print(f"❌ 接続失敗")
    
    def run_concurrent_benchmark(self, concurrent_requests: int = 10):
        """並行ベンチマーク実行"""
        print(f"\n⚡ 並行ベンチマーク実行中...")
        print(f"各サービスに {concurrent_requests} 件の同時リクエスト\n")
        
        for service_name, url in self.services.items():
            print(f"  → {service_name}...", end=" ")
            
            results = self.benchmark_concurrent_requests(service_name, url, concurrent_requests)
            self.results.extend(results)
            
            stats = self.calculate_statistics(results)
            
            if stats.success_rate > 0:
                print(f"✅ 平均 {stats.avg_response_time:.2f}ms (成功率: {stats.success_rate:.1f}%)")
            else:
                print(f"❌ 接続失敗")
    
    def run_async_benchmark(self, concurrent_requests: int = 10):
        """非同期並行ベンチマーク実行"""
        print(f"\n🚀 非同期並行ベンチマーク実行中...")
        print(f"各サービスに {concurrent_requests} 件の非同期同時リクエスト\n")
        
        for service_name, url in self.services.items():
            print(f"  → {service_name}...", end=" ")
            
            results = asyncio.run(self.benchmark_async_requests(service_name, url, concurrent_requests))
            self.results.extend(results)
            
            stats = self.calculate_statistics(results)
            
            if stats.success_rate > 0:
                print(f"✅ 平均 {stats.avg_response_time:.2f}ms (成功率: {stats.success_rate:.1f}%)")
            else:
                print(f"❌ 接続失敗")
    
    def generate_report(self) -> Dict[str, Any]:
        """レポート生成"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "services": []
        }
        
        # サービスごとの集計
        for service_name in set(r.service_name for r in self.results):
            service_results = [r for r in self.results if r.service_name == service_name]
            
            if service_results:
                stats = self.calculate_statistics(service_results)
                report["services"].append(asdict(stats))
        
        # 全体のサマリー
        all_response_times = [r.response_time_ms for r in self.results if r.success]
        if all_response_times:
            report["summary"] = {
                "total_requests": len(self.results),
                "successful_requests": len(all_response_times),
                "failed_requests": len(self.results) - len(all_response_times),
                "avg_response_time": statistics.mean(all_response_times),
                "min_response_time": min(all_response_times),
                "max_response_time": max(all_response_times),
                "overall_success_rate": (len(all_response_times) / len(self.results)) * 100
            }
        
        return report
    
    def print_detailed_report(self):
        """詳細レポートを表示"""
        report = self.generate_report()
        
        print("\n" + "=" * 80)
        print("📊 ManaOS パフォーマンスベンチマーク レポート")
        print("=" * 80)
        
        # 全体サマリー
        if report["summary"]:
            summary = report["summary"]
            print(f"\n🔍 全体サマリー:")
            print(f"  総リクエスト数:   {summary['total_requests']:,}")
            print(f"  成功:             {summary['successful_requests']:,} / {summary['total_requests']:,} ({summary['overall_success_rate']:.1f}%)")
            print(f"  失敗:             {summary['failed_requests']:,}")
            print(f"  平均応答時間:     {summary['avg_response_time']:.2f}ms")
            print(f"  最速応答時間:     {summary['min_response_time']:.2f}ms")
            print(f"  最遅応答時間:     {summary['max_response_time']:.2f}ms")
        
        # サービス別詳細
        print(f"\n📈 サービス別詳細:")
        print("-" * 80)
        
        for service in sorted(report["services"], key=lambda x: x["avg_response_time"]):
            print(f"\n🔹 {service['service_name']}")
            print(f"  リクエスト数:     {service['total_requests']}")
            print(f"  成功率:           {service['success_rate']:.1f}% ({service['successful_requests']}/{service['total_requests']})")
            print(f"  平均応答時間:     {service['avg_response_time']:.2f}ms")
            print(f"  最速/最遅:        {service['min_response_time']:.2f}ms / {service['max_response_time']:.2f}ms")
            print(f"  標準偏差:         {service['std_dev']:.2f}ms")
            
            # パフォーマンスグレード
            avg_time = service['avg_response_time']
            if avg_time < 50:
                grade = "⚡ 優秀"
            elif avg_time < 100:
                grade = "✅ 良好"
            elif avg_time < 300:
                grade = "⚠️ 普通"
            else:
                grade = "🐌 要改善"
            
            print(f"  パフォーマンス:   {grade}")
        
        print("\n" + "=" * 80)
    
    def save_report(self, filename: str = None):  # type: ignore
        """レポートをファイルに保存"""
        if filename is None:
            filename = f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 レポートを保存しました: {filename}")


def main():
    """メイン処理"""
    print("🎯 ManaOS Performance Benchmark")
    print("=" * 80)
    
    benchmark = PerformanceBenchmark()
    
    # 1. シーケンシャルベンチマーク（基本性能測定）
    benchmark.run_sequential_benchmark(iterations=5)
    
    # 2. 並行ベンチマーク（負荷テスト）
    benchmark.run_concurrent_benchmark(concurrent_requests=10)
    
    # 3. 非同期並行ベンチマーク（最大性能測定）
    benchmark.run_async_benchmark(concurrent_requests=20)
    
    # レポート生成・表示
    benchmark.print_detailed_report()
    
    # レポート保存
    benchmark.save_report()
    
    print("\n✅ ベンチマーク完了！")


if __name__ == "__main__":
    main()
