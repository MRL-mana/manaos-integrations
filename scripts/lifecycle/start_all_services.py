"""
ManaOS統合システム一括起動スクリプト
すべてのサービスを起動
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# サービス起動スクリプトのパス
SERVICES = {
    "unified_api": {
        "script": "unified_api_server.py",
        "port": 9500,
        "description": "統合APIサーバー"
    },
    "realtime_dashboard": {
        "script": "realtime_dashboard.py",
        "port": 9600,
        "description": "リアルタイムダッシュボード"
    },
    "master_control": {
        "script": "master_control.py",
        "port": 9700,
        "description": "マスターコントロールパネル"
    }
}

def check_port(port: int) -> bool:
    """ポートが使用中かチェック"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def start_service(name: str, config: dict) -> subprocess.Popen:
    """サービスを起動"""
    script_path = Path(__file__).parent / config["script"]
    
    if not script_path.exists():
        print(f"[エラー] {config['script']} が見つかりません")
        return None  # type: ignore
    
    print(f"[起動中] {config['description']} ({name})...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(script_path.parent)
        )
        
        # 少し待ってポートをチェック
        time.sleep(2)
        
        if check_port(config["port"]):
            print(f"[成功] {config['description']} が起動しました (ポート {config['port']})")
            print(f"        URL: http://127.0.0.1:{config['port']}")
        else:
            print(f"[警告] {config['description']} の起動を確認できませんでした")
        
        return process
        
    except Exception as e:
        print(f"[エラー] {config['description']} の起動に失敗: {e}")
        return None  # type: ignore

def main():
    """メイン関数"""
    print("=" * 70)
    print("ManaOS統合システム一括起動")
    print("=" * 70)
    print()
    
    processes = {}
    
    # 各サービスを起動
    for name, config in SERVICES.items():
        if check_port(config["port"]):
            print(f"[スキップ] {config['description']} は既に起動しています (ポート {config['port']})")
            continue
        
        process = start_service(name, config)
        if process:
            processes[name] = process
            time.sleep(1)  # 次のサービス起動前に少し待つ
    
    print()
    print("=" * 70)
    print("起動完了")
    print("=" * 70)
    print()
    print("起動中のサービス:")
    for name, config in SERVICES.items():
        if check_port(config["port"]):
            print(f"  ✓ {config['description']}: http://127.0.0.1:{config['port']}")
    
    print()
    print("停止するには Ctrl+C を押してください")
    print()
    
    try:
        # プロセスを保持
        while True:
            time.sleep(1)
            # プロセスの状態をチェック
            for name, process in list(processes.items()):
                if process.poll() is not None:
                    print(f"[警告] {SERVICES[name]['description']} が停止しました")
                    processes.pop(name)
    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("サービスを停止中...")
        print("=" * 70)
        
        for name, process in processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"[停止] {SERVICES[name]['description']}")
            except Exception:
                process.kill()
                print(f"[強制停止] {SERVICES[name]['description']}")
        
        print()
        print("すべてのサービスを停止しました")

if __name__ == "__main__":
    main()


















