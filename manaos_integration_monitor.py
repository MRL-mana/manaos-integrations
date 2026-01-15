#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ManaOS統合状態監視システム
全サービスの統合状態を監視・最適化
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_unified_client import get_unified_client
from manaos_service_bridge import ManaOSServiceBridge

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("IntegrationMonitor")

app = Flask(__name__)
CORS(app)

# 統合クライアントとブリッジ
client = get_unified_client()
bridge = ManaOSServiceBridge()

# 監視状態
monitoring_state = {
    "last_check": None,
    "service_status": {},
    "integration_status": {},
    "performance_metrics": {},
    "optimization_suggestions": []
}


def check_all_integrations() -> Dict[str, Any]:
    """全統合の状態をチェック"""
    try:
        # サービスヘルスチェック
        service_health = client.check_all_services()
        
        # 統合状態チェック
        integration_status = bridge.get_integration_status()
        
        # 統計情報
        client_stats = client.get_stats()
        
        return {
            "services": service_health,
            "integrations": integration_status,
            "client_stats": client_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"function": "check_all_integrations"},
            user_message="統合状態の確認に失敗しました"
        )
        logger.error(f"統合状態チェックエラー: {error.message}")
        return {
            "error": error.user_message or error.message,
            "timestamp": datetime.now().isoformat()
        }


def analyze_performance() -> Dict[str, Any]:
    """パフォーマンスを分析"""
    try:
        stats = client.get_stats()
        
        # 成功率
        success_rate = stats.get("success_rate", 0)
        
        # キャッシュヒット率
        total_cache_ops = stats.get("cache_hits", 0) + stats.get("cache_misses", 0)
        cache_hit_rate = (
            (stats.get("cache_hits", 0) / total_cache_ops * 100)
            if total_cache_ops > 0 else 0
        )
        
        # 最適化提案
        suggestions = []
        
        if success_rate < 90:
            suggestions.append({
                "type": "warning",
                "message": f"成功率が低いです ({success_rate:.1f}%)。サービス接続を確認してください。",
                "priority": "high"
            })
        
        if cache_hit_rate < 30 and stats.get("cache_misses", 0) > 100:
            suggestions.append({
                "type": "optimization",
                "message": f"キャッシュヒット率が低いです ({cache_hit_rate:.1f}%)。キャッシュ戦略を見直してください。",
                "priority": "medium"
            })
        
        if stats.get("retry_count", 0) > stats.get("total_requests", 0) * 0.1:
            suggestions.append({
                "type": "warning",
                "message": f"リトライ率が高いです。ネットワークまたはサービス側の問題を確認してください。",
                "priority": "high"
            })
        
        return {
            "success_rate": success_rate,
            "cache_hit_rate": cache_hit_rate,
            "total_requests": stats.get("total_requests", 0),
            "suggestions": suggestions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"function": "analyze_performance"},
            user_message="パフォーマンス分析に失敗しました"
        )
        logger.error(f"パフォーマンス分析エラー: {error.message}")
        return {
            "error": error.user_message or error.message,
            "timestamp": datetime.now().isoformat()
        }


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Integration Monitor"})


@app.route('/api/status', methods=['GET'])
def get_status():
    """統合状態を取得"""
    try:
        status = check_all_integrations()
        monitoring_state["last_check"] = datetime.now().isoformat()
        monitoring_state["service_status"] = status.get("services", {})
        monitoring_state["integration_status"] = status.get("integrations", {})
        return jsonify(status)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/status"},
            user_message="状態の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/performance', methods=['GET'])
def get_performance():
    """パフォーマンス分析を取得"""
    try:
        performance = analyze_performance()
        monitoring_state["performance_metrics"] = performance
        monitoring_state["optimization_suggestions"] = performance.get("suggestions", [])
        return jsonify(performance)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/performance"},
            user_message="パフォーマンス分析の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """最適化を実行"""
    try:
        # キャッシュクリア
        client.clear_cache()
        
        # パフォーマンス再分析
        performance = analyze_performance()
        
        return jsonify({
            "status": "success",
            "actions": ["cache_cleared"],
            "performance": performance,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/optimize"},
            user_message="最適化の実行に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/monitoring-state', methods=['GET'])
def get_monitoring_state():
    """監視状態を取得"""
    return jsonify(monitoring_state)


def main():
    """テスト用メイン関数"""
    print("ManaOS統合状態監視システムテスト")
    print("=" * 60)
    
    # 統合状態チェック
    print("\n統合状態をチェック中...")
    status = check_all_integrations()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # パフォーマンス分析
    print("\nパフォーマンスを分析中...")
    performance = analyze_performance()
    print(json.dumps(performance, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5127))
    logger.info(f"📊 Integration Monitor起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")






















