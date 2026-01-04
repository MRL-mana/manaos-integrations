#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS サービス状態確認スクリプト
"""

import sys
import os
import httpx
import asyncio
from datetime import datetime

# WindowsのコンソールエンコーディングをUTF-8に設定
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# チェック対象サービス
SERVICES = {
    "Intent Router": "http://localhost:5100/health",
    "Task Planner": "http://localhost:5101/health",
    "Task Critic": "http://localhost:5102/health",
    "RAG Memory": "http://localhost:5103/health",
    "Task Queue": "http://localhost:5104/health",
    "UI Operations": "http://localhost:5105/health",
    "Unified Orchestrator": "http://localhost:5106/health",
    "Executor Enhanced": "http://localhost:5107/health",
    "Portal Integration": "http://localhost:5108/health",
    "Content Generation": "http://localhost:5109/health",
    "LLM Optimization": "http://localhost:5110/health",
    "System Status API": "http://localhost:5112/health",
    "Personality System": "http://localhost:5123/health",
    "Autonomy System": "http://localhost:5124/health",
    "Secretary System": "http://localhost:5125/health",
    "Learning System API": "http://localhost:5126/health",
    "Metrics Collector": "http://localhost:5127/health",
    "Performance Dashboard": "http://localhost:5128/health",
}

async def check_service(name: str, url: str):
    """サービスをチェック"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return {"name": name, "status": "OK", "url": url, "response": response.json()}
            else:
                return {"name": name, "status": "ERROR", "url": url, "code": response.status_code}
    except httpx.ConnectError:
        return {"name": name, "status": "NOT_RUNNING", "url": url}
    except Exception as e:
        return {"name": name, "status": "ERROR", "url": url, "error": str(e)}

async def main():
    """メイン"""
    print("=" * 60)
    print("ManaOS サービス状態確認")
    print(f"確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    tasks = [check_service(name, url) for name, url in SERVICES.items()]
    results = await asyncio.gather(*tasks)
    
    # 結果を分類
    running = [r for r in results if r["status"] == "OK"]
    not_running = [r for r in results if r["status"] == "NOT_RUNNING"]
    errors = [r for r in results if r["status"] == "ERROR"]
    
    print(f"\n[OK] 起動中: {len(running)}/{len(SERVICES)}")
    for r in running:
        print(f"  - {r['name']}: {r['url']}")
    
    if not_running:
        print(f"\n[NG] 未起動: {len(not_running)}/{len(SERVICES)}")
        for r in not_running:
            print(f"  - {r['name']}: {r['url']}")
    
    if errors:
        print(f"\n[ERROR] エラー: {len(errors)}/{len(SERVICES)}")
        for r in errors:
            error_msg = r.get('error', f"HTTP {r.get('code', 'Unknown')}")
            print(f"  - {r['name']}: {error_msg}")
    
    print("\n" + "=" * 60)
    if len(running) == len(SERVICES):
        print("[OK] すべてのサービスが起動しています")
    else:
        print(f"[WARN] {len(not_running) + len(errors)}個のサービスが起動していません")
    print("=" * 60)
    
    return len(running), len(not_running), len(errors)

if __name__ == "__main__":
    running, not_running, errors = asyncio.run(main())
    sys.exit(0 if running == len(SERVICES) else 1)

