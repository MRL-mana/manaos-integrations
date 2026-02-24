"""
パフォーマンスベンチマークツール
各サービスのレスポンスタイム、スループット、リソース使用率を測定
"""
import time
import requests
import psutil
import statistics
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class BenchmarkResult:
    """ベンチマーク結果を格納するデータクラス"""
    service_name: str
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    error_rate: float
    cpu_usage_percent: float
    memory_usage_mb: float


class ServiceBenchmark:
    """サービスベンチマーククラス"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    def benchmark_endpoint(
        self,
        service_name: str,
        url: str,
        num_requests: int = 100,
        concurrent_requests: int = 10,
        timeout: int = 30
    ) -> BenchmarkResult:
        """
        エンドポイントのベンチマークを実行
        
        Args:
            service_name: サービス名
            url: テスト対象URL
            num_requests: 総リクエスト数
            concurrent_requests: 同時リクエスト数
            timeout: タイムアウト（秒）
        
        Returns:
            BenchmarkResult: ベンチマーク結果
        """
        print(f"\n🔧 Benchmarking {service_name}: {url}")
        print(f"   Total requests: {num_requests}, Concurrent: {concurrent_requests}")
        
        response_times: List[float] = []
        successful = 0
        failed = 0
        
        # CPU・メモリ使用率の測定開始
        cpu_before = psutil.cpu_percent(interval=0.1)
        memory_before = psutil.virtual_memory().used / (1024 * 1024)  # MB
        
        start_time = time.time()
        
        def make_request() -> Tuple[bool, float]:
            """単一リクエストを実行"""
            req_start = time.time()
            try:
                response = requests.get(url, timeout=timeout)
                elapsed = (time.time() - req_start) * 1000  # ミリ秒
                return (response.status_code == 200, elapsed)
            except Exception as e:
                elapsed = (time.time() - req_start) * 1000
                return (False, elapsed)
        
        # 並列リクエスト実行
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            
            for future in as_completed(futures):
                success, elapsed_time = future.result()
                response_times.append(elapsed_time)
                if success:
                    successful += 1
                else:
                    failed += 1
                
                # プログレス表示
                total_completed = successful + failed
                if total_completed % max(1, num_requests // 10) == 0:
                    print(f"   Progress: {total_completed}/{num_requests} requests")
        
        total_time = time.time() - start_time
        
        # CPU・メモリ使用率の測定終了
        cpu_after = psutil.cpu_percent(interval=0.1)
        memory_after = psutil.virtual_memory().used / (1024 * 1024)  # MB
        
        # 統計計算
        response_times.sort()
        avg_response = statistics.mean(response_times)
        min_response = min(response_times)
        max_response = max(response_times)
        p50_response = response_times[len(response_times) // 2]
        p95_response = response_times[int(len(response_times) * 0.95)]
        p99_response = response_times[int(len(response_times) * 0.99)]
        rps = num_requests / total_time
        error_rate = failed / num_requests
        
        cpu_usage = (cpu_after + cpu_before) / 2
        memory_usage = memory_after - memory_before
        
        result = BenchmarkResult(
            service_name=service_name,
            endpoint=url,
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time_ms=avg_response,
            min_response_time_ms=min_response,
            max_response_time_ms=max_response,
            p50_response_time_ms=p50_response,
            p95_response_time_ms=p95_response,
            p99_response_time_ms=p99_response,
            requests_per_second=rps,
            error_rate=error_rate,
            cpu_usage_percent=cpu_usage,
            memory_usage_mb=max(0, memory_usage)  # 負の値は0にする
        )
        
        self.results.append(result)
        return result
    
    def print_result(self, result: BenchmarkResult):
        """ベンチマーク結果を表示"""
        print(f"\n📊 Results for {result.service_name}:")
        print(f"   Endpoint: {result.endpoint}")
        print(f"   Success Rate: {result.successful_requests}/{result.total_requests} " +
              f"({(1-result.error_rate)*100:.1f}%)")
        print(f"   Response Time:")
        print(f"      Avg: {result.avg_response_time_ms:.2f}ms")
        print(f"      Min: {result.min_response_time_ms:.2f}ms")
        print(f"      Max: {result.max_response_time_ms:.2f}ms")
        print(f"      P50: {result.p50_response_time_ms:.2f}ms")
        print(f"      P95: {result.p95_response_time_ms:.2f}ms")
        print(f"      P99: {result.p99_response_time_ms:.2f}ms")
        print(f"   Throughput: {result.requests_per_second:.2f} req/s")
        print(f"   Resource Usage:")
        print(f"      CPU: {result.cpu_usage_percent:.1f}%")
        print(f"      Memory: {result.memory_usage_mb:.1f} MB")
    
    def export_results(self, filename: str = "benchmark_results.json"):
        """結果をJSON形式でエクスポート"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "results": [
                {
                    "service_name": r.service_name,
                    "endpoint": r.endpoint,
                    "total_requests": r.total_requests,
                    "successful_requests": r.successful_requests,
                    "failed_requests": r.failed_requests,
                    "avg_response_time_ms": r.avg_response_time_ms,
                    "min_response_time_ms": r.min_response_time_ms,
                    "max_response_time_ms": r.max_response_time_ms,
                    "p50_response_time_ms": r.p50_response_time_ms,
                    "p95_response_time_ms": r.p95_response_time_ms,
                    "p99_response_time_ms": r.p99_response_time_ms,
                    "requests_per_second": r.requests_per_second,
                    "error_rate": r.error_rate,
                    "cpu_usage_percent": r.cpu_usage_percent,
                    "memory_usage_mb": r.memory_usage_mb
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results exported to {filename}")


def main():
    """メインベンチマーク実行"""
    print("="*70)
    print("🚀 ManaOS Services Performance Benchmark")
    print("="*70)
    
    benchmark = ServiceBenchmark()
    
    # ベンチマーク対象サービス
    services = [
        ("MRL Memory", "http://localhost:5105/health"),
        ("Learning System", "http://localhost:5126/health"),
        ("LLM Routing", "http://localhost:5117/health"),
        ("Unified API", "http://localhost:9502/health"),
        ("Video Pipeline", "http://localhost:5112/health"),
        ("Gallery API", "http://localhost:5559/health"),
    ]
    
    # 各サービスをベンチマーク
    for service_name, url in services:
        try:
            # まず接続確認
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                result = benchmark.benchmark_endpoint(
                    service_name=service_name,
                    url=url,
                    num_requests=100,
                    concurrent_requests=10
                )
                benchmark.print_result(result)
            else:
                print(f"\n⚠️  {service_name} returned status {response.status_code}, skipping")
        except requests.exceptions.ConnectionError:
            print(f"\n⚠️  {service_name} is not running, skipping")
        except requests.exceptions.Timeout:
            print(f"\n⚠️  {service_name} timed out, skipping")
        except Exception as e:
            print(f"\n❌ Error benchmarking {service_name}: {e}")
    
    # 結果をエクスポート
    if benchmark.results:
        benchmark.export_results()
        
        print("\n" + "="*70)
        print("📈 Benchmark Summary")
        print("="*70)
        
        # サマリー表示
        for result in benchmark.results:
            print(f"{result.service_name:20s} | " +
                  f"Avg: {result.avg_response_time_ms:6.2f}ms | " +
                  f"P95: {result.p95_response_time_ms:6.2f}ms | " +
                  f"RPS: {result.requests_per_second:6.2f} | " +
                  f"Success: {(1-result.error_rate)*100:5.1f}%")
        
        print("="*70)
    else:
        print("\n⚠️  No services were benchmarked")


if __name__ == "__main__":
    main()
