#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llava:latestのダウンロード進捗を監視
"""

import subprocess
import time
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_llava_installed():
    """llava:latestがインストールされているか確認"""
    try:
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", "ollama list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return "llava" in result.stdout.lower()
    except:
        pass
    return False

def check_ollama_running():
    """Ollamaが実行中か確認"""
    try:
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", "curl -s http://localhost:11434/api/tags"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

print("=" * 60)
print("llava:latest ダウンロード監視")
print("=" * 60)

if not check_ollama_running():
    print("\n[ERROR] WSL2内のOllamaが起動していません")
    print("実行: .\\start_ollama_wsl2_gpu.ps1")
    sys.exit(1)

print("\n[INFO] WSL2内のOllamaは起動しています")
print("\n[INFO] llava:latestのインストール状況を確認中...")

max_wait = 300  # 最大5分待つ
check_interval = 10  # 10秒ごとに確認
elapsed = 0

while elapsed < max_wait:
    if check_llava_installed():
        print(f"\n[OK] llava:latestのインストールが完了しました！")
        print("\nGPU使用状況を確認中...")
        
        # GPU使用状況確認
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", "ollama ps"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("\n実行中のモデル:")
            print(result.stdout)
            
            # GPU使用確認
            if "GPU" in result.stdout or "gpu" in result.stdout.lower():
                print("\n[OK] GPUモードで実行されています！")
            elif "CPU" in result.stdout:
                print("\n[WARN] CPUモードで実行されています")
        
        break
    
    print(f"  待機中... ({elapsed}秒経過)")
    time.sleep(check_interval)
    elapsed += check_interval

if elapsed >= max_wait:
    print(f"\n[WARN] タイムアウト: {max_wait}秒経過しました")
    print("手動で確認: wsl -d Ubuntu-22.04 -- ollama list")

print("\n" + "=" * 60)
