"""
GPU使用状況のテスト
実際にLLMを呼び出してGPU使用率を確認
"""

import requests
import time
import subprocess
import platform

API_BASE = "http://localhost:9500"

def get_gpu_usage():
    """現在のGPU使用率を取得"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(',')
            if len(parts) >= 2:
                return int(parts[0].strip()), int(parts[1].strip())
    except:
        pass
    return None, None

def test_llm_with_gpu_monitoring():
    """LLM呼び出し中にGPU使用率を監視"""
    print("=" * 60)
    print("GPU使用状況テスト（LLM呼び出し中）")
    print("=" * 60)
    
    # 呼び出し前のGPU使用率
    gpu_before, vram_before = get_gpu_usage()
    print(f"\n[呼び出し前]")
    print(f"  GPU使用率: {gpu_before}%")
    print(f"  VRAM使用量: {vram_before} MB")
    
    # LLMを呼び出す
    print(f"\n[LLM呼び出し中...]")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE}/api/llm/chat",
            json={
                "messages": [
                    {"role": "user", "content": "こんにちは！あなたは誰ですか？自己紹介をしてください。"}
                ],
                "task_type": "conversation"
            },
            timeout=120
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"[成功] 応答時間: {elapsed:.2f}秒")
            print(f"  応答: {result.get('response', '')[:100]}...")
            print(f"  モデル: {result.get('model', 'unknown')}")
            print(f"  CPUモード: {result.get('cpu_mode', False)}")
        else:
            print(f"[エラー] HTTP {response.status_code}")
            print(f"  エラー: {response.text}")
    except Exception as e:
        print(f"[エラー] {e}")
        elapsed = time.time() - start_time
    
    # 呼び出し後のGPU使用率
    time.sleep(2)  # GPU使用率が反映されるまで少し待つ
    gpu_after, vram_after = get_gpu_usage()
    print(f"\n[呼び出し後]")
    print(f"  GPU使用率: {gpu_after}%")
    print(f"  VRAM使用量: {vram_after} MB")
    
    if gpu_before is not None and gpu_after is not None:
        gpu_diff = gpu_after - gpu_before
        vram_diff = vram_after - vram_before
        print(f"\n[変化]")
        print(f"  GPU使用率変化: {gpu_diff:+d}%")
        print(f"  VRAM使用量変化: {vram_diff:+d} MB")
        
        if gpu_diff > 10:
            print(f"  [OK] GPUが使用されています！")
        elif gpu_diff > 0:
            print(f"  [WARN] GPU使用率が少し上がりましたが、低いです")
        else:
            print(f"  [ERROR] GPUが使用されていません（CPUモードの可能性）")

def check_ollama_gpu_setting():
    """OllamaのGPU設定を確認"""
    print("\n" + "=" * 60)
    print("Ollama GPU設定確認")
    print("=" * 60)
    
    # 環境変数を確認
    import os
    print(f"\n環境変数:")
    print(f"  CUDA_VISIBLE_DEVICES: {os.getenv('CUDA_VISIBLE_DEVICES', '未設定')}")
    print(f"  OLLAMA_NUM_GPU: {os.getenv('OLLAMA_NUM_GPU', '未設定')}")
    print(f"  OLLAMA_GPU_LAYERS: {os.getenv('OLLAMA_GPU_LAYERS', '未設定')}")
    
    # Ollamaのプロセス情報
    print(f"\nOllamaプロセス:")
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ollama.exe", "/V"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = [line for line in result.stdout.split('\n') if 'ollama.exe' in line]
            print(f"  プロセス数: {len(lines)}")
            for line in lines[:3]:
                print(f"    {line[:80]}...")
    except:
        pass

if __name__ == "__main__":
    check_ollama_gpu_setting()
    test_llm_with_gpu_monitoring()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)



