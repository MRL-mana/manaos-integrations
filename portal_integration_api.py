#!/usr/bin/env python3
"""
🎮 Portal Integration API - Unified Portal v2統合用API
UI操作機能をUnified Portal v2に統合
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PortalIntegration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# サービスURL
SERVICES = {
    "unified_orchestrator": "http://localhost:5106",
    "ui_operations": "http://localhost:5105",
    "task_queue": "http://localhost:5104"
}


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Portal Integration API"})


@app.route('/api/execute', methods=['POST'])
def execute_task():
    """タスク実行エンドポイント（Unified Orchestrator経由）"""
    data = request.get_json() or {}
    input_text = data.get("text", "")
    mode = data.get("mode")
    
    if not input_text:
        return jsonify({"error": "text is required"}), 400
    
    try:
        timeout = timeout_config.get("workflow_execution", 300.0)
        response = httpx.post(
            f"{SERVICES['unified_orchestrator']}/api/execute",
            json={
                "text": input_text,
                "mode": mode,
                "auto_evaluate": True,
                "save_to_memory": True
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error = error_handler.handle_exception(
                Exception(f"Unified Orchestrator接続失敗: HTTP {response.status_code}"),
                context={"service": "Unified Orchestrator", "url": SERVICES['unified_orchestrator']},
                user_message="タスクの実行に失敗しました"
            )
            return jsonify(error.to_json_response()), response.status_code
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/execute"},
            user_message="タスク実行エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/mode', methods=['GET'])
def get_mode():
    """モード取得エンドポイント"""
    try:
        timeout = timeout_config.get("api_call", 10.0)
        response = httpx.get(f"{SERVICES['ui_operations']}/api/mode", timeout=timeout)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"mode": "auto"}), 200
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"service": "UI Operations", "url": SERVICES['ui_operations']},
            user_message="モード取得に失敗しました"
        )
        logger.warning(f"モード取得エラー: {error.message}")
        return jsonify({"mode": "auto"}), 200


@app.route('/api/mode', methods=['POST'])
def set_mode():
    """モード設定エンドポイント"""
    data = request.get_json() or {}
    mode = data.get("mode")
    
    if not mode:
        return jsonify({"error": "mode is required"}), 400
    
    try:
        timeout = timeout_config.get("api_call", 10.0)
        response = httpx.post(
            f"{SERVICES['ui_operations']}/api/mode",
            json={"mode": mode},
            timeout=timeout
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error = error_handler.handle_exception(
                Exception(f"UI Operations接続失敗: HTTP {response.status_code}"),
                context={"service": "UI Operations", "url": SERVICES['ui_operations']},
                user_message="モード設定に失敗しました"
            )
            return jsonify(error.to_json_response()), response.status_code
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/mode", "mode": mode},
            user_message="モード設定エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/cost', methods=['GET'])
def get_cost():
    """コスト取得エンドポイント"""
    days = request.args.get("days", 1, type=int)
    
    try:
        response = httpx.get(
            f"{SERVICES['ui_operations']}/api/cost?days={days}",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/queue/status', methods=['GET'])
def get_queue_status():
    """キュー状態取得エンドポイント"""
    try:
        response = httpx.get(f"{SERVICES['task_queue']}/api/status", timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_execution_history():
    """実行履歴取得エンドポイント"""
    limit = request.args.get("limit", 10, type=int)
    
    try:
        response = httpx.get(
            f"{SERVICES['unified_orchestrator']}/api/history?limit={limit}",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/execution/<execution_id>', methods=['GET'])
def get_execution(execution_id: str):
    """実行結果取得エンドポイント"""
    try:
        response = httpx.get(
            f"{SERVICES['unified_orchestrator']}/api/execution/{execution_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5108))
    logger.info(f"🎮 Portal Integration API起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

