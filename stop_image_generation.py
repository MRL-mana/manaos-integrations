#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像生成サービス（ComfyUI）を停止するスクリプト"""

import subprocess
import sys
import io
import time
import requests

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_PORT = 8188

def check_comfyui_running():
    """ComfyUIが実行中か確認"""
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=3)
        return response.status_code == 200
    except Exception:
        return False

def stop_comfyui_by_port():
    """ポート8188を使用しているプロセスを停止"""
    print("[1] ポート8188を使用しているプロセスを確認中...")
    
    try:
        # netstatでポート8188を使用しているプロセスを確認
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        pids = []
        for line in result.stdout.split('\n'):
            if f':{COMFYUI_PORT}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    pids.append(pid)
        
        if not pids:
            print("  ✓ ポート8188を使用しているプロセスは見つかりませんでした")
            return True
        
        print(f"  ⚠️ ポート8188を使用しているプロセス: {len(pids)}個")
        
        # プロセスを終了
        for pid in pids:
            try:
                print(f"  🛑 プロセス {pid} を終了中...")
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, check=True)
                print(f"    ✓ プロセス {pid} を終了しました")
            except subprocess.CalledProcessError as e:
                print(f"    ⚠️ プロセス {pid} の終了エラー: {e}")
            except Exception as e:
                print(f"    ⚠️ プロセス {pid} の終了エラー: {e}")
        
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"  ⚠️ ポート確認エラー: {e}")
        return False

def stop_comfyui_by_name():
    """ComfyUIプロセスを名前で検索して停止"""
    print("[2] ComfyUIプロセスを検索中...")
    
    try:
        # Pythonプロセスを検索
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        processes = []
        lines = result.stdout.split('\n')
        for line in lines[1:]:  # ヘッダーをスキップ
            if 'ComfyUI' in line or 'comfyui' in line.lower() or 'main.py' in line:
                parts = line.split('","')
                if len(parts) >= 2:
                    pid = parts[1].strip('"')
                    cmdline = line
                    processes.append((pid, cmdline))
        
        if not processes:
            print("  ✓ ComfyUIプロセスは見つかりませんでした")
            return True
        
        print(f"  ⚠️ ComfyUIプロセスを検出: {len(processes)}個")
        
        # プロセスを終了
        for pid, cmdline in processes:
            try:
                print(f"  🛑 プロセス {pid} を終了中...")
                print(f"    コマンド: {cmdline[:80]}...")
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, check=True)
                print(f"    ✓ プロセス {pid} を終了しました")
            except subprocess.CalledProcessError as e:
                print(f"    ⚠️ プロセス {pid} の終了エラー: {e}")
            except Exception as e:
                print(f"    ⚠️ プロセス {pid} の終了エラー: {e}")
        
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"  ⚠️ プロセス検索エラー: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 70)
    print("画像生成サービス（ComfyUI）停止スクリプト")
    print("=" * 70)
    print()
    
    # ComfyUIが実行中か確認
    if check_comfyui_running():
        print("⚠️ ComfyUIが実行中です")
        print()
    else:
        print("ℹ️ ComfyUIは既に停止している可能性があります")
        print()
    
    # ポート8188を使用しているプロセスを停止
    stop_comfyui_by_port()
    print()
    
    # ComfyUIプロセスを名前で検索して停止
    stop_comfyui_by_name()
    print()
    
    # 最終確認
    print("[3] 最終確認中...")
    time.sleep(1)
    
    if check_comfyui_running():
        print("  ⚠️ ComfyUIはまだ実行中です")
        print("  💡 手動でタスクマネージャーから終了してください")
    else:
        print("  ✅ ComfyUIを停止しました")
    
    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)

if __name__ == "__main__":
    main()
