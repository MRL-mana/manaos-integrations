#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPU使用状況をテスト"""

import sys
import os
import time
import subprocess
import requests

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("GPU使用状況テスト")
print("=" * 60)

# 1. 初期GPU状態
print("\n【1】初期GPU状態:")
result = subprocess.run(
    ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader'],
    capture_output=True,
    text=True,
    timeout=5
)
print(f"  {result.stdout.strip()}")

# 2. LLM API呼び出し（GPU指定）
print("\n【2】LLM API呼び出し（GPU指定）:")
os.environ['OLLAMA_USE_GPU'] = '1'

from local_llm_helper import generate

print("  実行中...")
start_time = time.time()

# GPU使用率を監視しながら実行
gpu_before = subprocess.run(
    ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader'],
    capture_output=True,
    text=True,
    timeout=5
).stdout.strip()

result = generate('qwen2.5:7b', '「ハイオク」という単語を正しく認識してください。', timeout=30)

elapsed = time.time() - start_time

gpu_after = subprocess.run(
    ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader'],
    capture_output=True,
    text=True,
    timeout=5
).stdout.strip()

print(f"  実行時間: {elapsed:.1f}秒")
print(f"  GPU使用率（実行前）: {gpu_before}")
print(f"  GPU使用率（実行後）: {gpu_after}")
print(f"  結果: {'成功' if 'response' in result or 'message' in result else '失敗'}")

# 3. Ollama ps確認
print("\n【3】Ollama ps確認:")
try:
    result_ps = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=5)
    print(result_ps.stdout)
except Exception as e:
    print(f"  エラー: {e}")

print("\n" + "=" * 60)
