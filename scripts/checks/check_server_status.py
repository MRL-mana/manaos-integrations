"""サーバーの状態を確認するスクリプト"""
import os
import requests
import time
import json

from _paths import UNIFIED_API_PORT

print("初期化の進行を確認中...")
time.sleep(5)

try:
    base_url = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}").rstrip("/")
    r = requests.get(f"{base_url}/status", timeout=5)
    data = r.json()
    
    print(f"Status: {data.get('status')}")
    print(f"Completed: {len(data.get('initialization', {}).get('completed', []))}")
    print(f"Failed: {len(data.get('initialization', {}).get('failed', []))}")
    print(f"Pending: {len(data.get('initialization', {}).get('pending', []))}")
    
    completed = data.get('initialization', {}).get('completed', [])
    if completed:
        print(f"Completed integrations: {', '.join(completed)}")
    
    failed = data.get('initialization', {}).get('failed', [])
    if failed:
        print(f"Failed integrations: {', '.join(failed)}")
        
except Exception as e:
    print(f"Error: {e}")
