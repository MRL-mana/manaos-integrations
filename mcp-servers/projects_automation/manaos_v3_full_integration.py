#!/usr/bin/env python3
"""
🚀 ManaOS v3 Full Integration System
ManaOS v3の全機能を統合し、メガブーストシステムと連携

機能:
- ManaOS v3 Orchestrator連携
- 自動タスク実行
- LLM連携（Ollama）
- 自律モード
"""

import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ManaOS v3 サービスURL (コンテナ内部ポート)
MANAOS_V3_ORCHESTRATOR = "http://localhost:9200"
MANAOS_V3_DASHBOARD = "http://localhost:9210"
MANAOS_V3_INSIGHT = "http://localhost:9205"

# Orchestratorヘルスチェック用（コンテナ内は9100ポート）
MANAOS_V3_ORCHESTRATOR_HEALTH = "http://localhost:9200/docs"  # FastAPI docs

# MEGA BOOST システムURL
MEGA_BOOST_API = "http://localhost:5019"
X280_GPU_API = "http://localhost:5022"

# 統計
stats = {
    "start_time": datetime.now(),
    "total_requests": 0,
    "successful_tasks": 0,
    "failed_tasks": 0,
}

# =============================================================================
# ManaOS v3連携
# =============================================================================

async def execute_manaos_task(text: str, actor: str = "remi", priority: int = 5) -> Dict[str, Any]:
    """ManaOS v3でタスク実行"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "text": text,
                "actor": actor,
                "priority": priority,
                "user": "mana",
            }
            
            async with session.post(
                f"{MANAOS_V3_ORCHESTRATOR}/execute",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                result = await response.json()
                return {
                    "success": response.status == 200,
                    "result": result,
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

async def get_manaos_insights() -> Dict[str, Any]:
    """ManaOS v3 Insightデータ取得"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MANAOS_V3_INSIGHT}/recent?limit=10",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                result = await response.json()
                return {
                    "success": response.status == 200,
                    "insights": result,
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

# =============================================================================
# MEGA BOOST連携
# =============================================================================

async def get_system_metrics() -> Dict[str, Any]:
    """MEGA BOOSTシステムメトリクス取得"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MEGA_BOOST_API}/metrics",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                result = await response.json()
                return {
                    "success": response.status == 200,
                    "metrics": result,
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

async def check_all_services() -> Dict[str, Any]:
    """全サービスヘルスチェック"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MEGA_BOOST_API}/health",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                result = await response.json()
                return {
                    "success": response.status == 200,
                    "health": result,
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

# =============================================================================
# X280 GPU連携
# =============================================================================

async def get_x280_gpu_status() -> Dict[str, Any]:
    """X280 GPU状態取得"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{X280_GPU_API}/gpu/status",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                result = await response.json()
                return {
                    "success": response.status == 200,
                    "gpu": result,
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

# =============================================================================
# 統合実行
# =============================================================================

async def integrated_execution(task: str) -> Dict[str, Any]:
    """統合実行：ManaOS v3 + MEGA BOOST + X280 GPU"""
    execution_log = {
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "steps": [],
    }
    
    # ステップ1: システムメトリクス取得
    metrics = await get_system_metrics()
    execution_log["steps"].append({
        "step": "system_metrics",
        "success": metrics["success"],
        "data": metrics.get("metrics", {}).get("system_metrics", {}) if metrics["success"] else None,
    })
    
    # ステップ2: ManaOS v3でタスク実行
    manaos_result = await execute_manaos_task(task)
    execution_log["steps"].append({
        "step": "manaos_execution",
        "success": manaos_result["success"],
        "result": manaos_result.get("result"),
    })
    
    # ステップ3: GPU状態確認（GPU関連タスクの場合）
    if "gpu" in task.lower() or "画像" in task or "学習" in task:
        gpu_status = await get_x280_gpu_status()
        execution_log["steps"].append({
            "step": "x280_gpu_check",
            "success": gpu_status["success"],
            "gpu_available": gpu_status.get("gpu", {}).get("summary", {}).get("available", False),
        })
    
    # ステップ4: Insightデータ取得
    insights = await get_manaos_insights()
    execution_log["steps"].append({
        "step": "insights",
        "success": insights["success"],
        "recent_count": len(insights.get("insights", [])) if insights["success"] else 0,
    })
    
    overall_success = all(step["success"] for step in execution_log["steps"])
    
    if overall_success:
        stats["successful_tasks"] += 1
    else:
        stats["failed_tasks"] += 1
    
    return {
        "success": overall_success,
        "execution_log": execution_log,
    }

# =============================================================================
# REST API
# =============================================================================

@app.route('/')
def index():
    """システム情報"""
    uptime = (datetime.now() - stats["start_time"]).total_seconds()
    
    return jsonify({
        "system": "ManaOS v3 Full Integration System",
        "version": "1.0.0",
        "uptime_seconds": round(uptime, 2),
        "stats": stats,
        "services": {
            "manaos_v3_orchestrator": MANAOS_V3_ORCHESTRATOR,
            "manaos_v3_dashboard": MANAOS_V3_DASHBOARD,
            "mega_boost_api": MEGA_BOOST_API,
            "x280_gpu_api": X280_GPU_API,
        },
        "timestamp": datetime.now().isoformat(),
    })

@app.route('/execute', methods=['POST'])
async def execute():
    """統合タスク実行"""
    stats["total_requests"] += 1
    
    data = request.get_json()
    task = data.get('task', '')
    
    if not task:
        return jsonify({"success": False, "error": "No task provided"}), 400
    
    result = await integrated_execution(task)
    
    return jsonify(result)

@app.route('/status')
async def status():
    """全システム統合ステータス"""
    # 並列で全情報取得
    results = await asyncio.gather(
        get_system_metrics(),
        check_all_services(),
        get_x280_gpu_status(),
        get_manaos_insights(),
        return_exceptions=True
    )
    
    metrics, health, gpu, insights = results
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "mega_boost": {
            "available": metrics.get("success", False) if isinstance(metrics, dict) else False,
            "cpu_usage": metrics.get("metrics", {}).get("system_metrics", {}).get("cpu", {}).get("average_usage", 0) if isinstance(metrics, dict) and metrics.get("success") else 0,
        },
        "trinity_services": {
            "available": health.get("success", False) if isinstance(health, dict) else False,
            "healthy_count": health.get("health", {}).get("summary", {}).get("healthy", 0) if isinstance(health, dict) and health.get("success") else 0,
        },
        "x280_gpu": {
            "available": gpu.get("success", False) if isinstance(gpu, dict) else False,
            "gpu_ready": gpu.get("gpu", {}).get("summary", {}).get("available", False) if isinstance(gpu, dict) and gpu.get("success") else False,
        },
        "manaos_v3": {
            "available": insights.get("success", False) if isinstance(insights, dict) else False,
        },
        "stats": stats,
    })

@app.route('/health')
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })

# =============================================================================
# メイン
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 ManaOS v3 Full Integration System 起動中...")
    print("=" * 80)
    print("🌐 API Port: 5023")
    print("=" * 80)
    print("\n📍 統合サービス:")
    print(f"  - ManaOS v3 Orchestrator: {MANAOS_V3_ORCHESTRATOR}")
    print(f"  - MEGA BOOST API: {MEGA_BOOST_API}")
    print(f"  - X280 GPU API: {X280_GPU_API}")
    print("=" * 80)
    print("\n📍 エンドポイント:")
    print("  - http://localhost:5023/        - システム情報")
    print("  - http://localhost:5023/status  - 全システムステータス")
    print("  - http://localhost:5023/execute - 統合タスク実行")
    print("=" * 80)
    print()
    
    app.run(
        host='0.0.0.0',
        port=5023,
        debug=os.getenv("DEBUG", "False").lower() == "true",
    )

