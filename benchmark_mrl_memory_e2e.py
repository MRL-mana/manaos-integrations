#!/usr/bin/env python3
"""
MRL Memory E2E Benchmark
E2Eレイテンシと128K相当の測定
"""

import time
import tempfile
import shutil
from pathlib import Path
from mrl_memory_system import MRLMemorySystem
from mrl_memory_metrics import MRLMemoryMetrics


def benchmark_e2e_latency():
    """
    E2Eレイテンシ測定
    
    入力→抽出→更新→検索→統合→出力の全体
    """
    temp_dir = tempfile.mkdtemp()
    try:
        system = MRLMemorySystem(memory_dir=Path(temp_dir))
        metrics = MRLMemoryMetrics(metrics_dir=Path(temp_dir) / "metrics")
        
        # 様々な入力長でE2E測定
        test_cases = [
            ("短", 100),
            ("中", 1000),
            ("長", 10000),
            ("超長", 100000)
        ]
        
        print("=== E2Eレイテンシ測定 ===")
        for name, length in test_cases:
            text = "テストテキスト " * (length // 10)
            
            # E2E測定開始
            start = time.time()
            
            # 1. 処理（抽出→更新）
            result = system.process(text, source=f"bench_e2e_{name}")
            
            # 2. 検索
            query = "テスト"
            search_results = system.retrieve(query, limit=5)
            
            # 3. コンテキスト取得
            context = system.get_context_for_llm(query, limit=3)
            
            # E2E測定終了
            elapsed = time.time() - start
            
            metrics.record_latency(
                input_length=length,
                processing_time=elapsed,
                operation="e2e"
            )
            
            print(f"{name} ({length}文字): {elapsed:.3f}秒 (E2E)")
        
        # 統計を表示
        stats = metrics.get_latency_stats()
        print(f"\nE2E統計: p50={stats.get('p50', 0):.3f}秒, p95={stats.get('p95', 0):.3f}秒")
        
    finally:
        shutil.rmtree(temp_dir)


def benchmark_chunk_scale():
    """
    128K相当ベンチをチャンク数スケールで測る
    
    チャンク数 16/64/256/1024 で測定
    """
    temp_dir = tempfile.mkdtemp()
    try:
        system = MRLMemorySystem(memory_dir=Path(temp_dir))
        metrics = MRLMemoryMetrics(metrics_dir=Path(temp_dir) / "metrics")
        
        # チャンクサイズ（2048文字）
        chunk_size = 2048
        
        # チャンク数のスケール
        chunk_counts = [16, 64, 256, 1024]
        
        print("=== チャンク数スケール測定 ===")
        for chunk_count in chunk_counts:
            # テキストを生成（チャンク数分）
            text = "テストテキスト " * (chunk_size * chunk_count // 10)
            
            start = time.time()
            result = system.process(text, source=f"bench_chunk_{chunk_count}")
            elapsed = time.time() - start
            
            # メトリクス記録
            metrics.record_latency(
                input_length=len(text),
                processing_time=elapsed,
                operation=f"chunk_{chunk_count}"
            )
            
            # チャンク数と更新回数
            update_count = result["rehearsal"]["total_processed"]
            metrics.record_write_amplification(chunk_count, update_count)
            
            print(f"チャンク数 {chunk_count}: {elapsed:.3f}秒, 更新回数: {update_count}")
        
        # 統計を表示
        stats = metrics.get_latency_stats()
        print(f"\nチャンクスケール統計: p50={stats.get('p50', 0):.3f}秒, p95={stats.get('p95', 0):.3f}秒")
        
        # Write amplification統計
        write_stats = metrics.get_write_amplification_stats()
        print(f"Write Amplification: mean={write_stats.get('mean', 0):.2f}, max={write_stats.get('max', 0):.2f}")
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("MRL Memory E2E Benchmark開始\n")
    
    benchmark_e2e_latency()
    print()
    
    benchmark_chunk_scale()
    
    print("\nE2Eベンチマーク完了")
