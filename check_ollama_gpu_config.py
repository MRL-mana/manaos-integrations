"""
OllamaのGPU設定を確認
"""

import subprocess
import os
import requests

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

print("=" * 60)
print("Ollama GPU設定確認")
print("=" * 60)

# 環境変数確認
print("\n[1] 環境変数")
print(f"  OLLAMA_NUM_GPU: {os.getenv('OLLAMA_NUM_GPU', '未設定')}")
print(f"  OLLAMA_GPU_LAYERS: {os.getenv('OLLAMA_GPU_LAYERS', '未設定')}")
print(f"  CUDA_VISIBLE_DEVICES: {os.getenv('CUDA_VISIBLE_DEVICES', '未設定')}")

# Ollamaプロセス確認
print("\n[2] Ollamaプロセス")
try:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq ollama.exe", "/V"],
        capture_output=True,
        text=True,
        timeout=5
    )
    lines = [line for line in result.stdout.split('\n') if 'ollama.exe' in line]
    print(f"  プロセス数: {len(lines)}")
    for line in lines[:2]:
        print(f"    {line[:100]}...")
except Exception as e:
    print(f"  エラー: {e}")

# GPU使用状況
print("\n[3] GPU使用状況")
try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        parts = result.stdout.strip().split(',')
        if len(parts) >= 3:
            print(f"  GPU使用率: {parts[0].strip()}")
            print(f"  VRAM使用量: {parts[1].strip()} / {parts[2].strip()}")
except Exception as e:
    print(f"  エラー: {e}")

# Ollama APIテスト
print("\n[4] Ollama APIテスト（GPU指定）")
try:
    response = requests.post(
        f"{DEFAULT_OLLAMA_URL}/api/generate",
        json={
            "model": "qwen2.5:7b",
            "prompt": "こんにちは",
            "options": {
                "num_gpu": 99
            },
            "stream": False
        },
        timeout=30
    )
    if response.status_code == 200:
        print("  [OK] API呼び出し成功")
        # GPU使用率を再確認
        import time
        time.sleep(3)
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(',')
            if len(parts) >= 2:
                print(f"  GPU使用率（呼び出し後）: {parts[0].strip()}")
                print(f"  VRAM使用量（呼び出し後）: {parts[1].strip()}")
    else:
        print(f"  [ERROR] HTTP {response.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# ollama ps確認
print("\n[5] Ollama ps確認")
try:
    result = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        output = result.stdout.strip()
        if output:
            print(f"  {output}")
            if "GPU" in output or "gpu" in output.lower():
                print("  [OK] GPUが使用されています")
            elif "CPU" in output or "100% CPU" in output:
                print("  [WARN] CPUモードで実行されています")
        else:
            print("  [INFO] モデルがロードされていません")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "=" * 60)
print("確認完了")
print("=" * 60)



