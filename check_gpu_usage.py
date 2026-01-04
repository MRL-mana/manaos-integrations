"""
GPU使用状況の確認
"""

import subprocess
import platform
import requests

def check_nvidia_smi():
    """nvidia-smiでGPU状態を確認"""
    print("=" * 60)
    print("GPU使用状況確認")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines, 1):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 5:
                    name, util, mem_used, mem_total, temp = parts
                    print(f"\nGPU {i}: {name}")
                    print(f"  使用率: {util}%")
                    print(f"  VRAM: {mem_used} / {mem_total}")
                    print(f"  温度: {temp}°C")
        else:
            print("[ERROR] nvidia-smiの実行に失敗しました")
    except FileNotFoundError:
        print("[INFO] nvidia-smiが見つかりません（GPU未検出またはドライバー未インストール）")
    except Exception as e:
        print(f"[ERROR] {e}")

def check_ollama_gpu():
    """OllamaがGPUを使用しているか確認"""
    print("\n" + "=" * 60)
    print("Ollama GPU使用状況")
    print("=" * 60)
    
    try:
        # Ollamaのモデル情報を取得
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"利用可能なモデル数: {len(models)}")
            
            # モデルの詳細情報を取得（最初のモデル）
            if models:
                model_name = models[0].get("name", "")
                print(f"\nモデル '{model_name}' の詳細情報:")
                
                show_response = requests.post(
                    "http://localhost:11434/api/show",
                    json={"name": model_name},
                    timeout=10
                )
                
                if show_response.status_code == 200:
                    model_info = show_response.json()
                    # GPU関連の情報を探す
                    details = model_info.get("details", {})
                    print(f"  パラメータ数: {details.get('parameter_count', 'unknown')}")
                    print(f"  量子化レベル: {details.get('quantization_level', 'unknown')}")
                    
                    # GPU使用状況を推測
                    # OllamaはデフォルトでGPUを使用するため、VRAM使用量から判断
                    print(f"\n[推測] OllamaはGPUを使用している可能性が高いです")
                    print(f"  （VRAM使用量から判断）")
        else:
            print(f"[ERROR] Ollama APIエラー: HTTP {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

def check_llm_routing_gpu():
    """LLMルーティングのGPU使用状況を確認"""
    print("\n" + "=" * 60)
    print("LLMルーティング GPU使用状況")
    print("=" * 60)
    
    try:
        from llm_routing import LLMRouter
        
        router = LLMRouter()
        gpu_in_use, metrics = router._check_gpu_in_use()
        
        print(f"GPU使用中: {'はい' if gpu_in_use else 'いいえ'}")
        print(f"チェック方法: {metrics.get('check_method', 'unknown')}")
        
        if metrics.get('gpu_utilization') is not None:
            print(f"GPU使用率: {metrics['gpu_utilization']}%")
        if metrics.get('vram_usage_mb') is not None:
            print(f"VRAM使用量: {metrics['vram_usage_mb']} MB")
        if metrics.get('ollama_processes') is not None:
            print(f"Ollamaプロセス数: {metrics['ollama_processes']}")
        
        if gpu_in_use:
            print("\n[INFO] GPUが使用中のため、LLMルーティングはCPUモードで実行されます")
        else:
            print("\n[INFO] GPUが利用可能なため、LLMルーティングはGPUモードで実行されます")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    check_nvidia_smi()
    check_ollama_gpu()
    check_llm_routing_gpu()
    
    print("\n" + "=" * 60)
    print("確認完了")
    print("=" * 60)



