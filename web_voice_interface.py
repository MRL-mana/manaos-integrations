#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎤 ManaOS Web音声インターフェース
ブラウザから音声入力→テキスト変換→Intent Router→実行
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

try:
    from manaos_integrations._paths import ORCHESTRATOR_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import ORCHESTRATOR_PORT  # type: ignore
    except Exception:  # pragma: no cover
        ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "5106"))

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("WebVoice")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# 設定
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", f"http://127.0.0.1:{ORCHESTRATOR_PORT}")

# 音声認識API（Web Speech APIを使用するため、フロントエンドで処理）
# バックエンドはテキストを受け取って実行するだけ

def execute_command(text: str, user: str = "web_user", source: str = "web_voice") -> Dict[str, Any]:
    """コマンドを実行"""
    try:
        # Unified Orchestratorに送信
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
            result = response.json()
            return {
                "status": "success",
                "execution_id": result.get("execution_id"),
                "result": result
            }
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
        logger.error(f"コマンド実行エラー: {error.message}")
        return {
            "status": "error",
            "error": error.user_message or error.message
        }

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Web Voice Interface"})

@app.route('/api/voice/execute', methods=['POST'])
def voice_execute():
    """音声認識結果を実行"""
    data = request.get_json()
    
    text = data.get("text", "")
    user = data.get("user", "web_user")
    
    if not text:
        return jsonify({
            "status": "error",
            "error": "text is required"
        })
    
    logger.info(f"音声コマンド受信: {text} (User: {user})")
    
    # コマンド実行
    result = execute_command(text, user, "web_voice")
    
    return jsonify(result)

@app.route('/api/text/execute', methods=['POST'])
def text_execute():
    """テキストコマンドを実行"""
    data = request.get_json()
    
    text = data.get("text", "")
    user = data.get("user", "web_user")
    
    if not text:
        return jsonify({
            "status": "error",
            "error": "text is required"
        })
    
    logger.info(f"テキストコマンド受信: {text} (User: {user})")
    
    # コマンド実行
    result = execute_command(text, user, "web_text")
    
    return jsonify(result)

@app.route('/api/status', methods=['GET'])
def get_status():
    """ステータス取得"""
    try:
        # Orchestratorの状態確認
        response = httpx.get(
            f"{ORCHESTRATOR_URL}/health",
            timeout=2
        )
        orchestrator_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        orchestrator_status = "down"
    
    return jsonify({
        "status": "healthy",
        "orchestrator_status": orchestrator_status,
        "orchestrator_url": ORCHESTRATOR_URL
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5115))
    logger.info(f"🎤 Web Voice Interface起動中... (ポート: {port})")
    logger.info(f"Orchestrator URL: {ORCHESTRATOR_URL}")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

