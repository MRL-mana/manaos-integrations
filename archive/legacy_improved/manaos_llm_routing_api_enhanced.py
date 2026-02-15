"""
ManaOS統合LLMルーティングAPI（拡張版）
ログ記録とエラーハンドリングを強化
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from manaos_logger import get_logger
from typing import Dict, Any, Optional
from llm_router_enhanced import EnhancedLLMRouter
from llm_routing_logger import logger as routing_logger

logger = get_service_logger("manaos-llm-routing-api-enhanced")
app = Flask(__name__)
CORS(app)

# LLMルーターの初期化
router = EnhancedLLMRouter()


@app.route("/api/llm/route", methods=["POST"])
def route_llm_request():
    """
    LLMリクエストをルーティング（ログ記録付き）
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
        
        # リクエストをログ記録
        routing_logger.log_request(prompt, context, preferences)
        
        # ルーティング実行
        result = router.route(prompt, context, preferences)
        
        # レスポンスをログ記録
        routing_logger.log_response(
            prompt=prompt,
            model=result.get("model", "unknown"),
            difficulty_score=result.get("difficulty_score", 0),
            response_time_ms=result.get("response_time_ms", 0),
            success=result.get("success", False),
            response=result.get("response"),
            error=result.get("error")
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"ルーティングエラー: {e}", exc_info=True)
        routing_logger.log_response(
            prompt=data.get("prompt", "") if data else "",
            model="unknown",
            difficulty_score=0,
            response_time_ms=0,
            success=False,
            error=str(e)
        )
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@app.route("/api/llm/analyze", methods=["POST"])
def analyze_difficulty():
    """プロンプトの難易度を分析（LLM呼び出しなし）"""
    if not ENHANCED_LLM_ROUTING_AVAILABLE:
        return jsonify({"error": "拡張LLMルーティングが利用できません"}), 503
    
    router = integrations.get("enhanced_llm_routing")
    if not router:
        return jsonify({"error": "拡張LLMルーティングが初期化されていません"}), 503
    
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "リクエストボディが空です"}), 400
        
        prompt = data.get("prompt", "")
        context = data.get("context", {})
        
        if not prompt:
            return jsonify({"error": "promptが必要です"}), 400
        
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


@app.route("/api/llm/models", methods=["GET"])
def get_available_models():
    """利用可能なモデル一覧を取得"""
    try:
        models = router.get_available_models()
        return jsonify({"models": models})
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/health", methods=["GET"])
def health_check():
    """ヘルスチェック"""
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


@app.route("/api/llm/logs/statistics", methods=["GET"])
def get_log_statistics():
    """ログ統計情報を取得"""
    try:
        stats = routing_logger.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"ログ統計取得エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 開発用サーバー起動
    port = int(os.getenv("PORT", 5111))
    logger.info(f"ManaOS LLMルーティングAPI（拡張版）を起動: http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)



















