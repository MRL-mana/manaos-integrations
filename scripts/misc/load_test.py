"""
ManaOS Load Testing Tool
API負荷テストとストレステスト
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import argparse
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import sys

try:
    from _paths import UNIFIED_API_URL, MRL_MEMORY_URL, LEARNING_SYSTEM_URL
except ImportError:
    UNIFIED_API_URL = "http://127.0.0.1:9502"
    MRL_MEMORY_URL = "http://127.0.0.1:9507"
    LEARNING_SYSTEM_URL = "http://127.0.0.1:9508"


@dataclass
class LoadTestResult:
    """負荷テスト結果"""
    timestamp: float
    response_time: float
    status_code: int
    success: bool
    error: Optional[str] = None


@dataclass
class LoadTestStats:
    """負荷テスト統計"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    total_duration: float
    errors: Dict[str, int] = field(default_factory=dict)


class LoadTester:
    """負荷テストクラス"""
    
    def __init__(self, base_url: str, endpoint: str = "/health"):
        self.base_url = base_url
        self.endpoint = endpoint
        self.results: List[LoadTestResult] = []
    
    async def send_request(self, session: aiohttp.ClientSession) -> LoadTestResult:
        """単一リクエスト送信"""
        start_time = time.time()
        
        try:
            async with session.get(
                f"{self.base_url}{self.endpoint}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_time = time.time() - start_time
                
                return LoadTestResult(
                    timestamp=start_time,
                    response_time=response_time,
                    status_code=response.status,
                    success=response.status == 200
                )
        
        except asyncio.TimeoutError:
            return LoadTestResult(
                timestamp=start_time,
                response_time=time.time() - start_time,
                status_code=0,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            return LoadTestResult(
                timestamp=start_time,
                response_time=time.time() - start_time,
                status_code=0,
                success=False,
                error=str(e)
            )
    
    async def run_concurrent_requests(
        self, 
        num_requests: int, 
        concurrency: int
    ) -> List[LoadTestResult]:
        """並行リクエスト実行"""
        connector = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self.send_request(session) 
                for _ in range(num_requests)
            ]
            results = await asyncio.gather(*tasks)
        
        return results
    
    async def run_sustained_load(
        self, 
        duration_seconds: int, 
        requests_per_second: int
    ) -> List[LoadTestResult]:
        """持続負荷テスト"""
        results = []
        interval = 1.0 / requests_per_second
        end_time = time.time() + duration_seconds
        
        connector = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(connector=connector) as session:
            while time.time() < end_time:
                batch_start = time.time()
                
                # 1秒あたりの指定数のリクエストを送信
                tasks = [
                    self.send_request(session) 
                    for _ in range(requests_per_second)
                ]
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                
                # 次のバッチまで待機
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
        
        return results
    
    async def run_spike_test(
        self, 
        baseline_rps: int, 
        spike_rps: int, 
        spike_duration: int
    ) -> List[LoadTestResult]:
        """スパイクテスト"""
        results = []
        
        # ベースライン期間（10秒）
        print(f"  📊 ベースライン: {baseline_rps} req/s×10秒")
        baseline_results = await self.run_sustained_load(10, baseline_rps)
        results.extend(baseline_results)
        
        # スパイク期間
        print(f"  ⚡ スパイク: {spike_rps} req/s×{spike_duration}秒")
        spike_results = await self.run_sustained_load(spike_duration, spike_rps)
        results.extend(spike_results)
        
        # 回復期間（10秒）
        print(f"  📊 回復: {baseline_rps} req/s×10秒")
        recovery_results = await self.run_sustained_load(10, baseline_rps)
        results.extend(recovery_results)
        
        return results
    
    def calculate_statistics(self, results: List[LoadTestResult]) -> LoadTestStats:
        """統計情報を計算"""
        if not results:
            return LoadTestStats(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0,
                avg_response_time=0,
                min_response_time=0,
                max_response_time=0,
                p50_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                requests_per_second=0,
                total_duration=0
            )
        
        response_times = [r.response_time for r in results]
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        # エラー集計
        error_counts = {}
        for result in failed:
            error = result.error or f"HTTP {result.status_code}"
            error_counts[error] = error_counts.get(error, 0) + 1
        
        # 時間範囲
        timestamps = [r.timestamp for r in results]
        duration = max(timestamps) - min(timestamps) if timestamps else 0
        
        # パーセンタイル計算
        sorted_times = sorted(response_times)
        
        return LoadTestStats(
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            success_rate=(len(successful) / len(results)) * 100,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=sorted_times[int(len(sorted_times) * 0.5)],
            p95_response_time=sorted_times[int(len(sorted_times) * 0.95)],
            p99_response_time=sorted_times[int(len(sorted_times) * 0.99)],
            requests_per_second=len(results) / duration if duration > 0 else 0,
            total_duration=duration,
            errors=error_counts
        )


class LoadTestRunner:
    """負荷テスト実行管理"""
    
    def __init__(self):
        self.services = {
            "Unified API": UNIFIED_API_URL,
            "MRL Memory": MRL_MEMORY_URL,
            "Learning System": LEARNING_SYSTEM_URL
        }
        self.all_results: Dict[str, LoadTestStats] = {}
    
    async def run_burst_test(self, service_name: str, url: str):
        """バーストテスト（短時間に大量リクエスト）"""
        print(f"\n⚡ {service_name} - バーストテスト")
        print("  1000リクエストを同時実行")
        
        tester = LoadTester(url)
        start_time = time.time()
        
        results = await tester.run_concurrent_requests(
            num_requests=1000,
            concurrency=100
        )
        
        duration = time.time() - start_time
        stats = tester.calculate_statistics(results)
        
        print(f"  ✅ 完了 ({duration:.2f}秒)")
        print(f"  成功率: {stats.success_rate:.1f}%")
        print(f"  平均応答: {stats.avg_response_time*1000:.2f}ms")
        print(f"  RPS: {stats.requests_per_second:.2f}")
        
        return stats
    
    async def run_sustained_test(self, service_name: str, url: str):
        """持続負荷テスト（一定時間持続）"""
        print(f"\n📊 {service_name} - 持続負荷テスト")
        print("  100 req/s × 30秒")
        
        tester = LoadTester(url)
        start_time = time.time()
        
        results = await tester.run_sustained_load(
            duration_seconds=30,
            requests_per_second=100
        )
        
        duration = time.time() - start_time
        stats = tester.calculate_statistics(results)
        
        print(f"  ✅ 完了 ({duration:.2f}秒)")
        print(f"  成功率: {stats.success_rate:.1f}%")
        print(f"  P95応答: {stats.p95_response_time*1000:.2f}ms")
        
        return stats
    
    async def run_spike_test(self, service_name: str, url: str):
        """スパイクテスト（急激な負荷増加）"""
        print(f"\n⚡ {service_name} - スパイクテスト")
        
        tester = LoadTester(url)
        results = await tester.run_spike_test(
            baseline_rps=50,
            spike_rps=500,
            spike_duration=10
        )
        
        stats = tester.calculate_statistics(results)
        
        print(f"  ✅ 完了")
        print(f"  成功率: {stats.success_rate:.1f}%")
        
        return stats
    
    async def run_all_tests(self):
        """全テスト実行"""
        print("🎯 ManaOS Load Testing")
        print("=" * 80)
        
        for service_name, url in self.services.items():
            print(f"\n{'='*80}")
            print(f"🔍 テスト対象: {service_name}")
            print(f"   URL: {url}")
            print(f"{'='*80}")
            
            # 1. バーストテスト
            try:
                burst_stats = await self.run_burst_test(service_name, url)
                self.all_results[f"{service_name} - Burst"] = burst_stats
            except Exception as e:
                print(f"  ❌ バーストテスト失敗: {e}")
            
            await asyncio.sleep(5)  # クールダウン
            
            # 2. 持続負荷テスト
            try:
                sustained_stats = await self.run_sustained_test(service_name, url)
                self.all_results[f"{service_name} - Sustained"] = sustained_stats
            except Exception as e:
                print(f"  ❌ 持続負荷テスト失敗: {e}")
            
            await asyncio.sleep(5)  # クールダウン
            
            # 3. スパイクテスト
            try:
                spike_stats = await self.run_spike_test(service_name, url)
                self.all_results[f"{service_name} - Spike"] = spike_stats
            except Exception as e:
                print(f"  ❌ スパイクテスト失敗: {e}")
            
            await asyncio.sleep(10)  # 次のサービスまでクールダウン
    
    def generate_report(self):
        """レポート生成"""
        print("\n" + "=" * 80)
        print("📊 負荷テスト総合レポート")
        print("=" * 80)
        
        for test_name, stats in self.all_results.items():
            print(f"\n🔹 {test_name}")
            print(f"  リクエスト数:     {stats.total_requests:,}")
            print(f"  成功率:           {stats.success_rate:.2f}%")
            print(f"  平均応答時間:     {stats.avg_response_time*1000:.2f}ms")
            print(f"  P50:              {stats.p50_response_time*1000:.2f}ms")
            print(f"  P95:              {stats.p95_response_time*1000:.2f}ms")
            print(f"  P99:              {stats.p99_response_time*1000:.2f}ms")
            print(f"  最速/最遅:        {stats.min_response_time*1000:.2f}ms / {stats.max_response_time*1000:.2f}ms")
            print(f"  RPS:              {stats.requests_per_second:.2f}")
            
            if stats.errors:
                print(f"  エラー:")
                for error, count in stats.errors.items():
                    print(f"    - {error}: {count}件")
        
        print("\n" + "=" * 80)
    
    def save_report(self, filename: str = None):
        """レポート保存"""
        if filename is None:
            filename = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "results": {
                name: asdict(stats) 
                for name, stats in self.all_results.items()
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 レポートを保存しました: {filename}")


async def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='ManaOS Load Testing Tool')
    parser.add_argument('--service', choices=['unified-api', 'mrl-memory', 'learning-system', 'all'], 
                        default='all', help='テストするサービス')
    parser.add_argument('--test', choices=['burst', 'sustained', 'spike', 'all'], 
                        default='all', help='実行するテストタイプ')
    parser.add_argument('--output', help='レポート出力ファイル名')
    
    args = parser.parse_args()
    
    runner = LoadTestRunner()
    
    # サービスフィルター
    if args.service != 'all':
        service_map = {
            'unified-api': 'Unified API',
            'mrl-memory': 'MRL Memory',
            'learning-system': 'Learning System'
        }
        service_name = service_map[args.service]
        runner.services = {service_name: runner.services[service_name]}
    
    # テスト実行
    await runner.run_all_tests()
    
    # レポート生成
    runner.generate_report()
    runner.save_report(args.output)
    
    print("\n✅ 負荷テスト完了！")


if __name__ == "__main__":
    asyncio.run(main())
