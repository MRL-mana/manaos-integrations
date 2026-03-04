#!/usr/bin/env python3
"""
RunPod Tailscale IP更新スクリプト
"""

import json
from datetime import datetime

# RunPodのTailscale IP
RUNPOD_TAILSCALE_IP = "100.84.82.112"

def update_config():
    """設定ファイルを更新"""
    
    # 設定ファイルパス
    config_file = "/root/runpod_integration/runpod_config.json"
    
    # 設定データ
    config = {
        "runpod": {
            "tailscale_ip": RUNPOD_TAILSCALE_IP,
            "ssh_host": RUNPOD_TAILSCALE_IP,
            "ssh_port": 22,
            "redis_host": RUNPOD_TAILSCALE_IP,
            "redis_port": 6379,
            "last_updated": datetime.now().isoformat(),
            "connection_type": "tailscale"
        },
        "status": "active"
    }
    
    # 設定ファイル保存
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ RunPod設定更新完了:")
    print(f"   Tailscale IP: {RUNPOD_TAILSCALE_IP}")
    print(f"   設定ファイル: {config_file}")
    
    # 接続テスト
    test_connection()

def test_connection():
    """接続テスト"""
    import subprocess
    
    print("\n🔍 接続テスト開始...")
    
    # SSH接続テスト
    try:
        result = subprocess.run([
            "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"root@{RUNPOD_TAILSCALE_IP}", "echo 'SSH接続成功'"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ SSH接続成功: {RUNPOD_TAILSCALE_IP}")
        else:
            print(f"❌ SSH接続失敗: {result.stderr}")
    except Exception as e:
        print(f"❌ SSH接続エラー: {e}")
    
    # Redis接続テスト
    try:
        import redis
        r = redis.Redis(host=RUNPOD_TAILSCALE_IP, port=6379, socket_connect_timeout=5)
        r.ping()
        print(f"✅ Redis接続成功: {RUNPOD_TAILSCALE_IP}:6379")
    except Exception as e:
        print(f"❌ Redis接続失敗: {e}")

if __name__ == "__main__":
    update_config()
