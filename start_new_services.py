#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 新規サービス起動スクリプト
"""

import subprocess
import time
import socket
import sys
import os
from pathlib import Path

# Windows環境でのエンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

services = [
    {"name": "Personality System", "port": 5123, "script": "personality_system.py"},
    {"name": "Autonomy System", "port": 5124, "script": "autonomy_system.py"},
    {"name": "Secretary System", "port": 5125, "script": "secretary_system.py"},
    {"name": "Learning System API", "port": 5126, "script": "learning_system_api.py"},
    {"name": "Metrics Collector", "port": 5127, "script": "metrics_collector.py"},
    {"name": "Performance Dashboard", "port": 5128, "script": "performance_dashboard.py"},
]

def is_port_in_use(port: int) -> bool:
    """ポートが使用中かチェック"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True

def main():
    script_dir = Path(__file__).parent
    log_dir = script_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    print("ManaOS 新規サービス起動中...\n")
    
    started = 0
    skipped = 0
    failed = 0
    
    for service in services:
        script_path = script_dir / service["script"]
        
        if not script_path.exists():
            print(f"[WARNING] スクリプトが見つかりません: {service['script']}")
            failed += 1
            continue
        
        # ポートが既に使用されているかチェック
        if is_port_in_use(service["port"]):
            print(f"[OK] {service['name']}: 既に起動中 (ポート {service['port']})")
            skipped += 1
            continue
        
        print(f"[START] {service['name']} 起動中... (ポート {service['port']})")
        
        log_file = log_dir / f"{service['name'].replace(' ', '_')}.log"
        error_log_file = log_dir / f"{service['name'].replace(' ', '_')}_error.log"
        
        try:
            # バックグラウンドで起動
            with open(log_file, 'w', encoding='utf-8') as log, \
                 open(error_log_file, 'w', encoding='utf-8') as err_log:
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=log,
                    stderr=err_log,
                    cwd=str(script_dir)
                )
            
            time.sleep(2)
            
            # 起動確認
            if is_port_in_use(service["port"]):
                print(f"[OK] {service['name']}: 起動成功")
                started += 1
            else:
                print(f"[WARNING] {service['name']}: 起動確認できませんでした（ログを確認してください）")
                failed += 1
        except Exception as e:
            print(f"[ERROR] {service['name']}: 起動エラー: {e}")
            failed += 1
    
    print(f"\n新規サービス起動処理が完了しました。")
    print(f"  起動: {started} サービス")
    print(f"  既存: {skipped} サービス")
    print(f"  失敗: {failed} サービス")

if __name__ == "__main__":
    main()
