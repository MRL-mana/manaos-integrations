"""
ManaOS統合LLMルーティングAPI
難易度判定とルーティングを提供するFlask API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from manaos_logger import get_logger
from typing import Dict, Any, Optional
from llm_router_enhanced import EnhancedLLMRouter

logger = get_logger(__name__)
app = Flask(__name__)
CORS(app)

# LLMルーターの初期化
router = EnhancedLLMRouter()


@app.route("/api/llm/route", methods=["POST"])
def route_llm_request():
    """
    LLMリクエストをルーティング
    
    リクエスト例:
    {
        "prompt": "ユーザーのプロンプト",
        "context": {
            "file_path": "path/to/file.py",
            "code_context": "関連コード",
            "task_type": "implementation|review|refactor"
        },
        "preferences": {
            "prefer_speed": true,
            "prefer_quality": false,
            "force_model": null
        }
    }
    
    レスポンス例:
    {
        "model": "Qwen2.5-Coder-7B-Instruct",
        "difficulty_score": 5.0,
        "difficulty_level": "low",
        "reasoning": "プロンプトが短く、単純なタスクのため軽量モデルを選択",
        "response": "モデルの応答",
        "response_time_ms": 250,
        "success": true
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "リクエストボディが空です"}), 400
        
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"error": "promptが指定されていません"}), 400
        
        context = data.get("context", {})
        preferences = data.get("preferences", {})
        
        # ルーティング実行
        result = router.route(prompt, context, preferences)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"ルーティングエラー: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@app.route("/api/llm/models", methods=["GET"])
def get_available_models():
    """
    利用可能なモデル一覧を取得
    
    レスポンス例:
    {
        "models": [
            "Qwen2.5-Coder-7B-Instruct",
            "Qwen2.5-Coder-14B-Instruct",
            "Qwen2.5-Coder-32B-Instruct"
        ]
    }
    """
    try:
        models = router.get_available_models()
        return jsonify({"models": models})
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/analyze", methods=["POST"])
def analyze_difficulty():
    """
    プロンプトの難易度を分析（LLM呼び出しなし）
    
    リクエスト例:
    {
        "prompt": "ユーザーのプロンプト",
        "context": {
            "code_context": "関連コード"
        }
    }
    
    レスポンス例:
    {
        "difficulty_score": 5.0,
        "difficulty_level": "low",
        "recommended_model": "Qwen2.5-Coder-7B-Instruct"
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "リクエストボディが空です"}), 400
        
        prompt = data.get("prompt", "")
        context = data.get("context", {})
        
        # 難易度分析
        analyzer = router.analyzer
        score = analyzer.calculate_difficulty(prompt, context)
        level = analyzer.get_difficulty_level(score)
        recommended_model = analyzer.get_recommended_model(score)
        
        return jsonify({
            "difficulty_score": score,
            "difficulty_level": level,
            "recommended_model": recommended_model
        })
    
    except Exception as e:
        logger.error(f"難易度分析エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/health", methods=["GET"])
def health_check():
    """
    ヘルスチェック
    
    レスポンス例:
    {
        "status": "ok",
        "llm_server": "lm_studio",
        "available_models": 3
    }
    """
    try:
        models = router.get_available_models()
        return jsonify({
            "status": "ok",
            "llm_server": router.llm_server,
            "available_models": len(models)
        })
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    # 開発用サーバー起動
    port = int(os.getenv("PORT", 5111))
    logger.info(f"ManaOS LLMルーティングAPIを起動: http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)

