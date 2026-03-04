#!/usr/bin/env python3
"""
⚖️ ManaOS Auto Scaler & Load Balancer
自動スケーリング＆負荷分散システム

機能:
- CPU/メモリ使用率に基づく自動スケーリング
- サービス間の負荷分散
- 自動リソース最適化
- 異常検知＆自動修復
"""

import os
import psutil
import time
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# =============================================================================
# 設定
# =============================================================================

# スケーリングしきい値
SCALE_UP_CPU_THRESHOLD = 70.0  # CPU使用率70%以上でスケールアップ
SCALE_DOWN_CPU_THRESHOLD = 30.0  # CPU使用率30%以下でスケールダウン
SCALE_UP_MEMORY_THRESHOLD = 80.0  # メモリ使用率80%以上
SCALE_DOWN_MEMORY_THRESHOLD = 50.0  # メモリ使用率50%以下

# 監視対象サービス
MONITORED_SERVICES = {
    "mega_boost": {"port": 5019, "min_instances": 1, "max_instances": 4},
    "x280_gpu": {"port": 5022, "min_instances": 1, "max_instances": 2},
    "v3_integration": {"port": 5023, "min_instances": 1, "max_instances": 3},
}

# 統計
stats = {
    "start_time": datetime.now(),
    "scale_up_count": 0,
    "scale_down_count": 0,
    "auto_heal_count": 0,
    "total_checks": 0,
}

# スケーリング履歴
scaling_history = []

# =============================================================================
# システムモニタリング
# =============================================================================

def get_resource_usage() -> Dict[str, Any]:
    """システムリソース使用状況"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "load_average": psutil.getloadavg(),
        "process_count": len(psutil.pids()),
    }

def get_service_health(port: int) -> Dict[str, Any]:
    """個別サービス健全性チェック"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        return {
            "available": response.status_code < 500,
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }

# =============================================================================
# スケーリング判定
# =============================================================================

def should_scale_up(resource_usage: Dict[str, Any]) -> bool:
    """スケールアップが必要か判定"""
    cpu_high = resource_usage["cpu_percent"] > SCALE_UP_CPU_THRESHOLD
    memory_high = resource_usage["memory_percent"] > SCALE_UP_MEMORY_THRESHOLD
    
    return cpu_high or memory_high

def should_scale_down(resource_usage: Dict[str, Any]) -> bool:
    """スケールダウンが可能か判定"""
    cpu_low = resource_usage["cpu_percent"] < SCALE_DOWN_CPU_THRESHOLD
    memory_low = resource_usage["memory_percent"] < SCALE_DOWN_MEMORY_THRESHOLD
    
    return cpu_low and memory_low

# =============================================================================
# スケーリング実行
# =============================================================================

def scale_service(service_name: str, action: str) -> Dict[str, Any]:
    """サービスのスケーリング実行"""
    timestamp = datetime.now()
    
    result = {
        "timestamp": timestamp.isoformat(),
        "service": service_name,
        "action": action,
        "success": False,
        "message": "",
    }
    
    # 実際のスケーリングロジック（簡易版）
    if action == "scale_up":
        result["success"] = True
        result["message"] = f"{service_name} scaled up (simulated)"
        stats["scale_up_count"] += 1
    elif action == "scale_down":
        result["success"] = True
        result["message"] = f"{service_name} scaled down (simulated)"
        stats["scale_down_count"] += 1
    
    # 履歴に追加
    scaling_history.append(result)
    if len(scaling_history) > 100:
        scaling_history.pop(0)
    
    return result

# =============================================================================
# 自動ヒーリング
# =============================================================================

def auto_heal_service(service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
    """サービス自動修復"""
    port = service_config["port"]
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "service": service_name,
        "port": port,
        "action": "auto_heal",
        "success": False,
    }
    
    # サービス再起動（簡易版）
    try:
        # 実際の環境では適切な再起動コマンドを使用
        result["success"] = True
        result["message"] = f"{service_name} auto-healed (simulated)"
        stats["auto_heal_count"] += 1
    except Exception as e:
        result["error"] = str(e)
    
    return result

# =============================================================================
# 負荷分散
# =============================================================================

def balance_load() -> Dict[str, Any]:
    """負荷分散実行"""
    resource_usage = get_resource_usage()
    
    actions = []
    
    # 各サービスの健全性チェック
    for service_name, config in MONITORED_SERVICES.items():
        health = get_service_health(config["port"])
        
        # サービスが利用不可の場合、自動修復
        if not health["available"]:
            heal_result = auto_heal_service(service_name, config)
            actions.append(heal_result)
    
    # スケーリング判定
    if should_scale_up(resource_usage):
        for service_name in MONITORED_SERVICES.keys():
            scale_result = scale_service(service_name, "scale_up")
            actions.append(scale_result)
    elif should_scale_down(resource_usage):
        for service_name in MONITORED_SERVICES.keys():
            scale_result = scale_service(service_name, "scale_down")
            actions.append(scale_result)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "resource_usage": resource_usage,
        "actions_taken": actions,
        "action_count": len(actions),
    }

# =============================================================================
# 最適化提案
# =============================================================================

def get_optimization_suggestions() -> List[str]:
    """リソース最適化提案"""
    suggestions = []
    resource_usage = get_resource_usage()
    
    if resource_usage["cpu_percent"] > 80:
        suggestions.append("⚠️ CPU使用率が高いです。不要なプロセスを終了してください。")
    
    if resource_usage["memory_percent"] > 85:
        suggestions.append("⚠️ メモリ使用率が高いです。メモリキャッシュをクリアしてください。")
    
    if resource_usage["disk_percent"] > 85:
        suggestions.append("⚠️ ディスク使用率が高いです。不要なファイルを削除してください。")
    
    if resource_usage["cpu_percent"] < 20 and resource_usage["memory_percent"] < 50:
        suggestions.append("✅ リソースに余裕があります。追加サービスを起動できます。")
    
    if not suggestions:
        suggestions.append("✅ システムは最適な状態です。")
    
    return suggestions

# =============================================================================
# REST API
# =============================================================================

@app.route('/')
def index():
    """システム情報"""
    uptime = (datetime.now() - stats["start_time"]).total_seconds()
    
    return jsonify({
        "system": "ManaOS Auto Scaler & Load Balancer",
        "version": "1.0.0",
        "uptime_seconds": round(uptime, 2),
        "stats": stats,
        "monitored_services": len(MONITORED_SERVICES),
        "timestamp": datetime.now().isoformat(),
    })

@app.route('/status')
def status():
    """システムステータス"""
    resource_usage = get_resource_usage()
    
    # 全サービスの健全性チェック
    service_health = {}
    for service_name, config in MONITORED_SERVICES.items():
        service_health[service_name] = get_service_health(config["port"])
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "resource_usage": resource_usage,
        "service_health": service_health,
        "scaling": {
            "should_scale_up": should_scale_up(resource_usage),
            "should_scale_down": should_scale_down(resource_usage),
        },
        "stats": stats,
    })

@app.route('/balance', methods=['POST'])
def balance():
    """負荷分散実行"""
    stats["total_checks"] += 1
    result = balance_load()
    return jsonify(result)

@app.route('/optimize')
def optimize():
    """最適化提案取得"""
    suggestions = get_optimization_suggestions()
    resource_usage = get_resource_usage()
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "resource_usage": resource_usage,
        "suggestions": suggestions,
        "suggestion_count": len(suggestions),
    })

@app.route('/history')
def history():
    """スケーリング履歴"""
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "history": scaling_history[-20:],  # 最新20件
        "total_events": len(scaling_history),
    })

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })

# =============================================================================
# バックグラウンド自動監視
# =============================================================================

def auto_monitor_loop():
    """自動監視ループ（バックグラウンド）"""
    while True:
        try:
            stats["total_checks"] += 1
            balance_load()
            time.sleep(30)  # 30秒ごとにチェック
        except Exception as e:
            print(f"⚠️ Auto monitor error: {e}")
            time.sleep(30)

# =============================================================================
# メイン
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("⚖️ ManaOS Auto Scaler & Load Balancer 起動中...")
    print("=" * 80)
    print("🌐 API Port: 5024")
    print(f"📊 監視サービス数: {len(MONITORED_SERVICES)}")
    print("=" * 80)
    print("\n📍 しきい値:")
    print(f"  - スケールアップ CPU: {SCALE_UP_CPU_THRESHOLD}%")
    print(f"  - スケールダウン CPU: {SCALE_DOWN_CPU_THRESHOLD}%")
    print(f"  - スケールアップ メモリ: {SCALE_UP_MEMORY_THRESHOLD}%")
    print(f"  - スケールダウン メモリ: {SCALE_DOWN_MEMORY_THRESHOLD}%")
    print("=" * 80)
    print("\n📍 エンドポイント:")
    print("  - http://localhost:5024/        - システム情報")
    print("  - http://localhost:5024/status  - システムステータス")
    print("  - http://localhost:5024/balance - 負荷分散実行")
    print("  - http://localhost:5024/optimize - 最適化提案")
    print("  - http://localhost:5024/history - スケーリング履歴")
    print("=" * 80)
    print()
    
    # バックグラウンド監視は起動時に別スレッドで実行可能
    # threading.Thread(target=auto_monitor_loop, daemon=True).start()
    
    app.run(
        host='0.0.0.0',
        port=5024,
        debug=os.getenv("DEBUG", "False").lower() == "true",
    )

