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

from _paths import (
    AUTONOMY_SYSTEM_PORT,
    CONTENT_GENERATION_PORT,
    EXECUTOR_ENHANCED_PORT,
    GALLERY_PORT,
    INTENT_ROUTER_PORT,
    LEARNING_SYSTEM_PORT,
    LLM_ROUTING_PORT,
    MCP_API_SERVER_PORT,
    METRICS_COLLECTOR_PORT,
    MRL_MEMORY_PORT,
    ORCHESTRATOR_PORT,
    PERFORMANCE_DASHBOARD_PORT,
    PERSONALITY_SYSTEM_PORT,
    PICO_HID_PORT,
    PORTAL_INTEGRATION_PORT,
    RAG_MEMORY_PORT,
    SECRETARY_SYSTEM_PORT,
    TASK_CRITIC_PORT,
    TASK_PLANNER_PORT,
    TASK_QUEUE_PORT,
    UNIFIED_API_PORT,
    VIDEO_PIPELINE_PORT,
)

# WindowsのコンソールエンコーディングをUTF-8に設定
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# チェック対象サービス
SERVICES = {
    "Intent Router": f"http://127.0.0.1:{INTENT_ROUTER_PORT}/health",
    "Task Planner": f"http://127.0.0.1:{TASK_PLANNER_PORT}/health",
    "Task Critic": f"http://127.0.0.1:{TASK_CRITIC_PORT}/health",
    "RAG Memory": f"http://127.0.0.1:{RAG_MEMORY_PORT}/health",
    "Task Queue": f"http://127.0.0.1:{TASK_QUEUE_PORT}/health",
    "MRL Memory": f"http://127.0.0.1:{MRL_MEMORY_PORT}/health",
    "Unified Orchestrator": f"http://127.0.0.1:{ORCHESTRATOR_PORT}/health",
    "Executor Enhanced": f"http://127.0.0.1:{EXECUTOR_ENHANCED_PORT}/health",
    "Portal Integration": f"http://127.0.0.1:{PORTAL_INTEGRATION_PORT}/health",
    "Content Generation": f"http://127.0.0.1:{CONTENT_GENERATION_PORT}/health",
    "LLM Routing MCP": f"http://127.0.0.1:{LLM_ROUTING_PORT}/health",
    "Video Pipeline": f"http://127.0.0.1:{VIDEO_PIPELINE_PORT}/health",
    "Personality System": f"http://127.0.0.1:{PERSONALITY_SYSTEM_PORT}/health",
    "Autonomy System": f"http://127.0.0.1:{AUTONOMY_SYSTEM_PORT}/health",
    "Secretary System": f"http://127.0.0.1:{SECRETARY_SYSTEM_PORT}/health",
    "Learning System API": f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}/health",
    "Metrics Collector": f"http://127.0.0.1:{METRICS_COLLECTOR_PORT}/health",
    "Performance Dashboard": f"http://127.0.0.1:{PERFORMANCE_DASHBOARD_PORT}/health",
    "Pico HID MCP": f"http://127.0.0.1:{PICO_HID_PORT}/health",
    "Unified API": f"http://127.0.0.1:{UNIFIED_API_PORT}/health",
    "MCP API Server": f"http://127.0.0.1:{MCP_API_SERVER_PORT}/health",
    "Gallery API": f"http://127.0.0.1:{GALLERY_PORT}/health",
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

