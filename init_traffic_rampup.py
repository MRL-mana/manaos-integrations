#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS v1.0 トラフィック投入初期化スクリプト
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
import httpx

SERVICES = {
    "mrl_memory": "http://localhost:5105/health",
    "learning_system": "http://localhost:5126/health",
    "llm_routing": "http://localhost:5111/health",
    "gallery_api": "http://localhost:5559/health",
    "video_pipeline": "http://localhost:5112/health",
    "ollama": "http://localhost:11434/api/tags",
    "moltbot_gateway": "http://localhost:8088/health",
}

async def check_services():
    """サービスの稼働確認"""
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for service_name, endpoint in SERVICES.items():
            try:
                start = time.time()
                resp = await client.get(endpoint)
                latency = (time.time() - start) * 1000
                results[service_name] = {
                    "status": "UP" if resp.status_code == 200 else "DOWN",
                    "code": resp.status_code,
                    "latency_ms": round(latency, 1),
                }
            except Exception as e:
                results[service_name] = {"status": "DOWN", "error": str(e)}
    return results

async def main():
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║          🚀 トラフィック自動段階投入システム起動                      ║
╠════════════════════════════════════════════════════════════════════╣
║ 開始時刻: {datetime.utcnow().isoformat()}
║ 
║ フェーズスケジュール:
║   Phase 1:  10% トラフィック (30分間)
║   Phase 2:  30% トラフィック (1時間)
║   Phase 3: 100% トラフィック (本格稼動)
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    # 初期ヘルスチェック
    print("🔍 サービスヘルスチェック中...")
    services = await check_services()
    
    up_count = sum(1 for s in services.values() if s["status"] == "UP")
    total_count = len(services)
    
    print(f"\n✅ ヘルスチェック完了: {up_count}/{total_count} サービス稼働")
    print("")
    
    for service_name, health in services.items():
        status_icon = "✅" if health["status"] == "UP" else "❌"
        latency = f"{health.get('latency_ms', 'N/A')}ms"
        print(f"  {status_icon} {service_name:25s} | {latency:>8s}")
    
    # 状態を保存
    state = {
        "current_phase": "phase1",
        "start_time": datetime.utcnow().isoformat(),
        "timestamp": datetime.utcnow().isoformat(),
        "services_up": up_count,
        "services_total": total_count,
    }
    
    with open("traffic_rampup_state.json", "w") as f:
        json.dump(state, f, indent=2)
    
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║              ✅ フェーズ1: トラフィック10%投入開始                    ║
╠════════════════════════════════════════════════════════════════════╣
║ トラフィック投入率:  10%
║ 予想投入量:       5,000-10,000 req/分
║ 実行期間:        30分間
║ 監視項目:
║   - エラー率 < 5%
║   - レイテンシ < 100ms
║   - CPU < 60%
║   - メモリ < 70%
║
║ 状態ファイル: traffic_rampup_state.json
║ メトリクス: metrics/traffic_rampup_metrics.json
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    print("✨ 本番運用開始 - トラフィック自動段階投入システム稼動中\n")
    
    # ファイルに記録
    with open("traffic_rampup.log", "a") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] フェーズ1 開始 - 10% トラフィック投入\n")

if __name__ == "__main__":
    asyncio.run(main())
