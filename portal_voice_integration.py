#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔗 ManaOS Portal統合拡張
Portal Integration (5108) に音声・Slack統合を追加
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from manaos_integrations._paths import (
        ORCHESTRATOR_PORT,
        SLACK_INTEGRATION_PORT,
        WINDOWS_AUTOMATION_PORT,
    )
except Exception:  # pragma: no cover
    try:
        from _paths import ORCHESTRATOR_PORT, SLACK_INTEGRATION_PORT, WINDOWS_AUTOMATION_PORT  # type: ignore
    except Exception:  # pragma: no cover
        ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "5106"))
        SLACK_INTEGRATION_PORT = int(os.getenv("SLACK_INTEGRATION_PORT", "5114"))
        WINDOWS_AUTOMATION_PORT = int(os.getenv("WINDOWS_AUTOMATION_PORT", "5115"))

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PortalVoice")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# 設定
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", f"http://127.0.0.1:{ORCHESTRATOR_PORT}")
SLACK_INTEGRATION_URL = os.getenv("SLACK_INTEGRATION_URL", f"http://127.0.0.1:{SLACK_INTEGRATION_PORT}")
WEB_VOICE_URL = os.getenv("WEB_VOICE_URL", f"http://127.0.0.1:{WINDOWS_AUTOMATION_PORT}")

def execute_via_orchestrator(text: str, source: str = "portal", user: str = "portal_user") -> Dict[str, Any]:
    """Unified Orchestrator経由で実行"""
    try:
        timeout = timeout_config.get("workflow_execution", 300.0)
        response = httpx.post(
            f"{ORCHESTRATOR_URL}/api/execute",
            json={
                "text": text,
                "mode": "auto",
                "auto_evaluate": True,
                "save_to_memory": True,
                "metadata": {
                    "source": source,
                    "user": user
                }
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error = error_handler.handle_exception(
                Exception(f"Unified Orchestrator接続失敗: HTTP {response.status_code}"),
                context={"service": "Unified Orchestrator", "url": ORCHESTRATOR_URL},
                user_message="コマンドの実行に失敗しました"
            )
            return {
                "status": "error",
                "error": error.user_message or f"HTTP {response.status_code}"
            }
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"service": "Unified Orchestrator", "url": ORCHESTRATOR_URL, "text": text},
            user_message="コマンドの実行に失敗しました"
        )
        logger.error(f"実行エラー: {error.message}")
        return {
            "status": "error",
            "error": error.user_message or error.message
        }

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Portal Voice Integration"})

@app.route('/api/voice/execute', methods=['POST'])
def voice_execute():
    """音声コマンド実行（Portal経由）"""
    data = request.get_json()
    text = data.get("text", "")
    user = data.get("user", "portal_user")
    
    if not text:
        return jsonify({"status": "error", "error": "text is required"})
    
    logger.info(f"Portal音声コマンド: {text}")
    result = execute_via_orchestrator(text, "portal_voice", user)
    return jsonify(result)

@app.route('/api/slack/execute', methods=['POST'])
def slack_execute():
    """Slackコマンド実行（Portal経由）"""
    data = request.get_json()
    text = data.get("text", "")
    user = data.get("user", "slack_user")
    channel = data.get("channel", "general")
    
    if not text:
        return jsonify({"status": "error", "error": "text is required"})
    
    logger.info(f"Portal Slackコマンド: {text} (Channel: {channel})")
    result = execute_via_orchestrator(text, "portal_slack", user)
    return jsonify(result)

@app.route('/api/integrations/status', methods=['GET'])
def integrations_status():
    """統合サービスステータス"""
    status = {
        "orchestrator": "unknown",
        "slack_integration": "unknown",
        "web_voice": "unknown"
    }
    
    # Orchestrator
    try:
        response = httpx.get(f"{ORCHESTRATOR_URL}/health", timeout=2)
        status["orchestrator"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        status["orchestrator"] = "down"
    
    # Slack Integration
    try:
        response = httpx.get(f"{SLACK_INTEGRATION_URL}/health", timeout=2)
        status["slack_integration"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        status["slack_integration"] = "down"
    
    # Web Voice
    try:
        response = httpx.get(f"{WEB_VOICE_URL}/health", timeout=2)
        status["web_voice"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        status["web_voice"] = "down"
    
    return jsonify({
        "status": "ok",
        "integrations": status
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5116))
    logger.info(f"🔗 Portal Voice Integration起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

