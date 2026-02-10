#!/usr/bin/env python3
"""
📚 Learning System API Server
学習システムのRESTful APIサーバー
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("LearningSystemAPI")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# Learning Systemのインポート
from learning_system import LearningSystem

app = Flask(__name__)
CORS(app)

# グローバル学習システムインスタンス
learning_system = None

def init_learning_system() -> LearningSystem:
    """学習システムを初期化"""
    global learning_system
    if learning_system is None:
        learning_system = LearningSystem()
    return learning_system

@app.route('/health', methods=['GET'])
def health() -> tuple:
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Learning System API"})

@app.route('/api/record', methods=['POST'])
def record_usage() -> tuple:
    """使用パターンを記録"""
    try:
        data = request.get_json() or {}
        action = data.get("action")
        context = data.get("context", {})
        result = data.get("result", {})
        
        if not action:
            error = error_handler.handle_exception(
                ValueError("action is required"),
                context={"endpoint": "/api/record"},
                user_message="アクションが必要です"
            )
            return jsonify(error.to_json_response()), 400
        
        system = init_learning_system()
        system.record_usage(action, context, result)
        
        return jsonify({"status": "recorded", "action": action})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/record"},
            user_message="使用パターンの記録に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/analyze', methods=['GET'])
def analyze_patterns() -> tuple:
    """パターンを分析"""
    try:
        system = init_learning_system()
        analysis = system.analyze_patterns()
        return jsonify(analysis)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/analyze"},
            user_message="パターン分析に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/preferences', methods=['GET'])
def get_preferences() -> tuple:
    """学習された好みを取得"""
    try:
        system = init_learning_system()
        preferences = system.learn_preferences()
        return jsonify(preferences)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/preferences"},
            user_message="好みの取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/optimizations', methods=['GET'])
def get_optimizations() -> tuple:
    """最適化提案を取得"""
    try:
        system = init_learning_system()
        optimizations = system.suggest_optimizations()
        return jsonify({"optimizations": optimizations, "count": len(optimizations)})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/optimizations"},
            user_message="最適化提案の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/status', methods=['GET'])
def get_status() -> tuple:
    """状態を取得"""
    try:
        system = init_learning_system()
        status = system.get_status()
        return jsonify(status)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/status"},
            user_message="状態の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/apply-preferences', methods=['POST'])
def apply_preferences() -> tuple:
    """学習された好みを適用"""
    try:
        data = request.get_json() or {}
        action = data.get("action")
        params = data.get("params", {})
        
        if not action:
            error = error_handler.handle_exception(
                ValueError("action is required"),
                context={"endpoint": "/api/apply-preferences"},
                user_message="アクションが必要です"
            )
            return jsonify(error.to_json_response()), 400
        
        system = init_learning_system()
        optimized_params = system.apply_learned_preferences(action, params)
        
        return jsonify({"optimized_params": optimized_params})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/apply-preferences"},
            user_message="好みの適用に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5126))
    logger.info(f"📚 Learning System API起動中... (ポート: {port})")
    init_learning_system()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

