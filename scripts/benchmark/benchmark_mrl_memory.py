#!/usr/bin/env python3
"""
MRL Memory Benchmark
パフォーマンス測定スクリプト
"""

import time
import tempfile
import shutil
from pathlib import Path
from mrl_memory_system import MRLMemorySystem
from mrl_memory_metrics import MRLMemoryMetrics


def benchmark_latency():
    """レイテンシ測定"""
    temp_dir = tempfile.mkdtemp()
    try:
        system = MRLMemorySystem(memory_dir=Path(temp_dir))
        metrics = MRLMemoryMetrics(metrics_dir=Path(temp_dir) / "metrics")
        
        # 様々な入力長でテスト
        test_cases = [
            ("短", 100),
            ("中", 1000),
            ("長", 10000),
            ("超長", 100000)
        ]
        
        print("=== レイテンシ測定 ===")
        for name, length in test_cases:
            text = "テストテキスト " * (length // 10)
            
            start = time.time()
            result = system.process(text, source=f"bench_{name}")
            elapsed = time.time() - start
            
            metrics.record_latency(
                input_length=length,
                processing_time=elapsed,
                operation="process"
            )
            
            print(f"{name} ({length}文字): {elapsed:.3f}秒")
        
        # 統計を表示
        stats = metrics.get_latency_stats()
        print(f"\n統計: p50={stats.get('p50', 0):.3f}秒, p95={stats.get('p95', 0):.3f}秒")
        
    finally:
        shutil.rmtree(temp_dir)


def benchmark_slot_utilization():
    """スロット使用分布測定"""
    temp_dir = tempfile.mkdtemp()
    try:
        system = MRLMemorySystem(memory_dir=Path(temp_dir))
        metrics = MRLMemoryMetrics(metrics_dir=Path(temp_dir) / "metrics")
        
        # 大量のテキストを処理
        print("=== スロット使用分布測定 ===")
        for i in range(100):
            text = f"テストテキスト {i} " * 10
            system.process(text, source=f"bench_{i}")
        
        # スロット使用状況を取得（簡易実装）
        # 実際の実装では、ChunkMemoryProcessorから取得
        slot_usage = {"slot_1": 10, "slot_2": 5, "slot_3": 20}  # 例
        metrics.record_slot_usage(slot_usage, total_slots=100)
        
        # 統計を表示
        stats = metrics.get_slot_utilization_stats()
        print(f"平均使用率: {stats.get('mean_utilization', 0):.2%}")
        print(f"平均分散: {stats.get('mean_variance', 0):.2f}")
        
    finally:
        shutil.rmtree(temp_dir)


def benchmark_write_amplification():
    """Write amplification測定"""
    temp_dir = tempfile.mkdtemp()
    try:
        system = MRLMemorySystem(memory_dir=Path(temp_dir))
        metrics = MRLMemoryMetrics(metrics_dir=Path(temp_dir) / "metrics")
        
        # 長文を処理
        print("=== Write Amplification測定 ===")
        long_text = "テストテキスト " * 1000
        
        start = time.time()
        result = system.process(long_text, source="bench_write")
        elapsed = time.time() - start
        
        # チャンク数と更新回数を取得（簡易実装）
        chunk_count = len(long_text) // 2048 + 1
        update_count = result["rehearsal"]["total_processed"]
        
        metrics.record_write_amplification(chunk_count, update_count)
        
        # 統計を表示
        stats = metrics.get_write_amplification_stats()
        print(f"Write Amplification: {stats.get('mean', 0):.2f}")
        print(f"チャンク数: {chunk_count}, 更新回数: {update_count}")
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("MRL Memory Benchmark開始\n")
    
    benchmark_latency()
    print()
    
    benchmark_slot_utilization()
    print()
    
    benchmark_write_amplification()
    
    print("\nベンチマーク完了")
