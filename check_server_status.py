"""サーバーの状態を確認するスクリプト"""
import requests
import time
import json

print("初期化の進行を確認中...")
time.sleep(5)

try:
    r = requests.get('http://127.0.0.1:9500/status', timeout=5)
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
