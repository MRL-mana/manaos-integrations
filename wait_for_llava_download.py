#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llava:latestのダウンロード完了を待つ
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

def check_download_progress():
    """ダウンロードプロセスの状態を確認"""
    try:
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", "ps aux | grep 'ollama pull' | grep -v grep"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except:
        return False

print("=" * 60)
print("llava:latest ダウンロード監視")
print("=" * 60)
print("\n[INFO] ダウンロード完了を待っています...")
print("       完了次第、GPU使用状況を確認します\n")

check_interval = 15  # 15秒ごとに確認
elapsed = 0
last_status = ""

while True:
    # ダウンロードプロセス確認
    downloading = check_download_progress()
    installed = check_llava_installed()
    
    if installed:
        print(f"\n[OK] llava:latestのインストールが完了しました！")
        print(f"     経過時間: {elapsed}秒")
        
        # GPU使用状況確認
        print("\n[INFO] GPU使用状況を確認中...")
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
            output = result.stdout.lower()
            if "gpu" in output:
                print("\n[OK] GPUモードで実行されています！")
            elif "cpu" in output:
                print("\n[WARN] CPUモードで実行されています")
        
        # GPUメモリ使用状況
        gpu_result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if gpu_result.returncode == 0:
            print(f"\n[GPU情報] {gpu_result.stdout.strip()}")
        
        break
    
    if downloading:
        status = f"ダウンロード中... ({elapsed}秒経過)"
        if status != last_status:
            print(f"  {status}")
            last_status = status
    else:
        status = f"待機中... ({elapsed}秒経過)"
        if status != last_status:
            print(f"  {status}")
            last_status = status
    
    time.sleep(check_interval)
    elapsed += check_interval

print("\n" + "=" * 60)
print("完了！Vision LLMを使用する準備ができました。")
print("=" * 60)
