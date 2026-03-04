#!/usr/bin/env python3
"""
GPUパフォーマンステストスクリプト
複数のGPUタスクを実行してパフォーマンスを確認
"""

import torch
import time
from datetime import datetime

def test_gpu_basic():
    """基本的なGPU計算テスト"""
    print("=" * 60)
    print("GPU基本計算テスト")
    print("=" * 60)
    
    if not torch.cuda.is_available():
        print("[ERROR] CUDAが利用できません")
        return False
    
    print(f"[OK] GPU: {torch.cuda.get_device_name(0)}")
    print(f"[OK] CUDA Version: {torch.version.cuda}")
    
    # メモリ情報
    print(f"[OK] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    
    # 計算テスト
    size = 5000
    print(f"\n計算テスト（{size}x{size}行列）...")
    
    start_time = time.time()
    x = torch.randn(size, size, device='cuda')
    y = torch.randn(size, size, device='cuda')
    z = torch.matmul(x, y)
    torch.cuda.synchronize()
    elapsed = time.time() - start_time
    
    print(f"[OK] 計算時間: {elapsed:.3f}秒")
    print(f"[OK] 結果形状: {z.shape}")
    
    return True

def test_gpu_memory():
    """GPUメモリテスト"""
    print("\n" + "=" * 60)
    print("GPUメモリテスト")
    print("=" * 60)
    
    if not torch.cuda.is_available():
        return False
    
    # メモリ使用状況
    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    
    print(f"割り当て済み: {allocated:.2f} GB")
    print(f"予約済み: {reserved:.2f} GB")
    print(f"合計: {total:.2f} GB")
    print(f"使用率: {(allocated/total)*100:.1f}%")
    
    return True

def test_gpu_throughput():
    """GPUスループットテスト"""
    print("\n" + "=" * 60)
    print("GPUスループットテスト")
    print("=" * 60)
    
    if not torch.cuda.is_available():
        return False
    
    # 複数の計算を連続実行
    iterations = 10
    size = 2000
    
    start_time = time.time()
    for i in range(iterations):
        x = torch.randn(size, size, device='cuda')
        y = torch.randn(size, size, device='cuda')
        z = torch.matmul(x, y)
    torch.cuda.synchronize()
    elapsed = time.time() - start_time
    
    throughput = (iterations * size * size * size * 2) / elapsed / 1e9  # GFLOPS概算
    print(f"[OK] {iterations}回の計算時間: {elapsed:.3f}秒")
    print(f"[OK] 平均1回あたり: {elapsed/iterations:.3f}秒")
    print(f"[OK] 概算スループット: {throughput:.2f} GFLOPS")
    
    return True

if __name__ == "__main__":
    print(f"\nGPUパフォーマンステスト開始")
    print(f"日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    results.append(("基本計算", test_gpu_basic()))
    results.append(("メモリ", test_gpu_memory()))
    results.append(("スループット", test_gpu_throughput()))
    
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    for name, result in results:
        status = "[OK] 成功" if result else "[ERROR] 失敗"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    print(f"\n{'[OK] すべてのテストが成功しました' if all_passed else '[ERROR] 一部のテストが失敗しました'}")

