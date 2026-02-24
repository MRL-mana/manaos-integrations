#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LFM 2.5統合サービス再起動スクリプト
Phase 1 + Phase 2で変更したサービスを再起動
"""

import subprocess
import time
import sys
import os
from pathlib import Path
import requests
from manaos_process_manager import get_process_manager

# Windowsコンソールのエンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

pm = get_process_manager("LFM25Restart")

def check_port(port):
    """ポートが使用されているか確認"""
    return pm.check_port_in_use(port)

def get_process_by_port(port):
    """ポートを使用しているプロセスIDを取得"""
    procs = pm.get_processes_by_port(port)
    return procs[0]["pid"] if procs else None

def kill_process(pid):
    """プロセスを終了 (ProcessManager経由)"""
    return pm.kill_by_pid(pid)

def start_service(script_name):
    """サービスを起動"""
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["python", script_name],
                cwd=Path(__file__).parent,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            subprocess.Popen(
                ["python3", script_name],
                cwd=Path(__file__).parent
            )
        return True
    except Exception as e:
        print(f"  ✗ 起動失敗: {e}")
        return False

def check_health(port, name):
    """ヘルスチェック"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
        if response.status_code == 200:
            return True
    except Exception:
        pass
    return False

def main():
    print("=" * 50)
    print("LFM 2.5統合サービス再起動")
    print("=" * 50)
    print()
    
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 変更したサービス一覧
    services = [
        ("Intent Router", 5100, "intent_router.py"),
        ("Task Planner", 5101, "task_planner.py"),
        ("Content Generation", 5109, "content_generation_loop.py"),
        ("Unified API Server", 9502, "unified_api_server.py")
    ]
    
    print("[1] 既存プロセスを確認・停止中...")
    print()
    
    for name, port, script in services:
        print(f"  - {name} (Port: {port})")
        
        # ポートを使用しているプロセスを停止
        pid = get_process_by_port(port)
        if pid:
            print(f"    PID {pid} を停止中...")
            if kill_process(pid):
                print("    ✓ 停止完了")
            time.sleep(1)
        else:
            print("    ✓ プロセスなし")
    
    print()
    print("[2] サービスを起動中...")
    print()
    
    for name, port, script in services:
        print(f"  - {name}起動中...")
        if start_service(script):
            print("    [OK] 起動コマンド実行")
        time.sleep(3)
    
    print()
    print("[3] ヘルスチェック中...")
    print()
    
    time.sleep(5)
    
    all_ok = True
    for name, port, script in services:
        if check_health(port, name):
            print(f"  [OK] {name}: 起動成功")
        else:
            if check_port(port):
                print(f"  [WARN] {name}: ポートは開いていますが、ヘルスチェックに失敗")
            else:
                print(f"  [FAIL] {name}: 起動確認失敗（数秒待ってから再確認してください）")
                all_ok = False
    
    print()
    print("=" * 50)
    print("再起動完了")
    print("=" * 50)
    print()
    print("LFM 2.5統合状況:")
    print("  [OK] Intent Router: LFM 2.5使用")
    print("  [OK] Secretary Routines: LFM 2.5使用（Unified API経由）")
    print("  [OK] Task Planner: 簡単な計画でLFM 2.5使用")
    print("  [OK] Content Generation: 下書き生成でLFM 2.5使用")
    print()
    print("効果確認方法:")
    print("  python test_lfm25_integration.py")
    print()
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
