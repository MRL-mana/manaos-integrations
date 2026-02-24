#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📡 ManaOS SSOT API
manaos_status.jsonを提供するAPI
"""

import os
import json
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_service_logger("ssot-api")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SSOT")

app = Flask(__name__)
CORS(app)

SSOT_FILE = Path(__file__).parent / "manaos_status.json"

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "SSOT API"})

@app.route('/api/ssot', methods=['GET'])
def get_ssot():
    """SSOT取得"""
    try:
        if not SSOT_FILE.exists():
            return jsonify({
                "status": "error",
                "error": "SSOT file not found. Run ssot_generator.py first."
            }), 404
        
        with open(SSOT_FILE, 'r', encoding='utf-8') as f:
            ssot = json.load(f)
        
        return jsonify(ssot)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/ssot", "ssot_file": str(SSOT_FILE)},
            user_message="SSOTの取得に失敗しました"
        )
        logger.error(f"SSOT取得エラー: {error.message}")
        return jsonify(error.to_json_response()), 500

@app.route('/api/ssot/summary', methods=['GET'])
def get_ssot_summary():
    """SSOTサマリー取得"""
    try:
        if not SSOT_FILE.exists():
            return jsonify({
                "status": "error",
                "error": "SSOT file not found"
            }), 404
        
        with open(SSOT_FILE, 'r', encoding='utf-8') as f:
            ssot = json.load(f)
        
        return jsonify({
            "timestamp": ssot.get("timestamp"),
            "summary": ssot.get("summary"),
            "system": {
                "cpu_percent": ssot.get("system", {}).get("cpu", {}).get("percent"),
                "ram_percent": ssot.get("system", {}).get("ram", {}).get("percent"),
                "disk_percent": ssot.get("system", {}).get("disk", {}).get("percent")
            },
            "active_tasks": ssot.get("active_tasks"),
            "last_error": ssot.get("last_error")
        })
    except Exception as e:
        logger.error(f"SSOTサマリー取得エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/ssot/services', methods=['GET'])
def get_services_status():
    """サービス状態のみ取得"""
    try:
        if not SSOT_FILE.exists():
            return jsonify({
                "status": "error",
                "error": "SSOT file not found"
            }), 404
        
        with open(SSOT_FILE, 'r', encoding='utf-8') as f:
            ssot = json.load(f)
        
        return jsonify({
            "services": ssot.get("services", []),
            "summary": ssot.get("summary", {})
        })
    except Exception as e:
        logger.error(f"サービス状態取得エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/ssot/recent', methods=['GET'])
def get_recent_inputs():
    """最新指令取得"""
    try:
        if not SSOT_FILE.exists():
            return jsonify({
                "status": "error",
                "error": "SSOT file not found"
            }), 404
        
        with open(SSOT_FILE, 'r', encoding='utf-8') as f:
            ssot = json.load(f)
        
        return jsonify({
            "recent_inputs": ssot.get("recent_inputs", [])
        })
    except Exception as e:
        logger.error(f"最新指令取得エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/ssot/error', methods=['GET'])
def get_last_error():
    """直近エラー取得"""
    try:
        if not SSOT_FILE.exists():
            return jsonify({
                "status": "error",
                "error": "SSOT file not found"
            }), 404
        
        with open(SSOT_FILE, 'r', encoding='utf-8') as f:
            ssot = json.load(f)
        
        return jsonify({
            "last_error": ssot.get("last_error")
        })
    except Exception as e:
        logger.error(f"直近エラー取得エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5120))
    logger.info(f"📡 SSOT API起動中... (ポート: {port})")
    logger.info(f"SSOTファイル: {SSOT_FILE}")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

