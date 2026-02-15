#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary 運用管理スクリプト
一括起動・停止・状態確認
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# プロセス管理
processes: Dict[str, subprocess.Popen] = {}

def start_indexer():
    """Indexer起動"""
    print("📂 Indexer起動中...")
    env = os.environ.copy()
    env['INBOX_PATH'] = str(Path(__file__).parent / "00_INBOX")
    env['FILE_SECRETARY_DB_PATH'] = "file_secretary.db"
    
    proc = subprocess.Popen(
        [sys.executable, "file_secretary_start.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes['indexer'] = proc
    print(f"✅ Indexer起動完了 (PID: {proc.pid})")
    return proc

def start_api():
    """APIサーバー起動"""
    print("🔌 APIサーバー起動中...")
    env = os.environ.copy()
    env['PORT'] = "5120"
    env['FILE_SECRETARY_DB_PATH'] = "file_secretary.db"
    env['INBOX_PATH'] = str(Path(__file__).parent / "00_INBOX")
    
    proc = subprocess.Popen(
        [sys.executable, "file_secretary_api.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes['api'] = proc
    print(f"✅ APIサーバー起動完了 (PID: {proc.pid})")
    return proc

def stop_all():
    """全プロセス停止"""
    print("\n⏹️ 全プロセス停止中...")
    for name, proc in processes.items():
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"✅ {name}停止完了")
        except subprocess.TimeoutExpired:
            proc.kill()
            print(f"⚠️ {name}強制停止")
        except Exception as e:
            print(f"⚠️ {name}停止エラー: {e}")
    processes.clear()

def check_status():
    """状態確認"""
    print("\n📊 状態確認中...")
    
    # プロセス確認
    for name, proc in processes.items():
        if proc.poll() is None:
            print(f"✅ {name}: 実行中 (PID: {proc.pid})")
        else:
            print(f"⚠️ {name}: 停止中")
    
    # API確認
    try:
        import httpx
        from _paths import FILE_SECRETARY_PORT

        response = httpx.get(f"http://127.0.0.1:{FILE_SECRETARY_PORT}/health", timeout=2.0)
        if response.status_code == 200:
            print("✅ APIサーバー: 正常応答")
        else:
            print(f"⚠️ APIサーバー: HTTP {response.status_code}")
    except Exception:
        print("⚠️ APIサーバー: 接続不可")

def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='File Secretary 運用管理')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'restart'],
                       help='実行するアクション')
    parser.add_argument('--indexer', action='store_true', help='Indexerのみ起動')
    parser.add_argument('--api', action='store_true', help='APIのみ起動')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        if args.indexer:
            start_indexer()
        elif args.api:
            start_api()
        else:
            start_indexer()
            time.sleep(2)
            start_api()
            print("\n✅ 全サービス起動完了")
            print("停止するには Ctrl+C または 'python file_secretary_manager.py stop'")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_all()
    
    elif args.action == 'stop':
        stop_all()
    
    elif args.action == 'status':
        check_status()
    
    elif args.action == 'restart':
        stop_all()
        time.sleep(2)
        start_indexer()
        time.sleep(2)
        start_api()

if __name__ == '__main__':
    main()






















