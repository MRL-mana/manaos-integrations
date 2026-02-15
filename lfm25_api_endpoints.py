"""
LFM 2.5専用APIエンドポイント
unified_api_server.pyに追加するエンドポイント
"""

from flask import request, jsonify
from manaos_logger import get_logger, get_service_logger
from typing import Dict, Any

logger = get_service_logger("lfm25-api-endpoints")

# LFM 2.5クライアントのインポート
LFM25_AVAILABLE = False
try:
    from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
    LFM25_AVAILABLE = True
except ImportError:
    logger.warning("LFM 2.5クライアントが利用できません")


def register_lfm25_endpoints(app):
    """LFM 2.5専用エンドポイントを登録"""
    
    @app.route("/api/lfm25/chat", methods=["POST"])
    def lfm25_chat():
        """LFM 2.5でチャット（超軽量・超高速）"""
        if not LFM25_AVAILABLE:
            return jsonify({"error": "LFM 2.5クライアントが利用できません"}), 503
        
        try:
            data = request.json or {}
            message = data.get("message", "")
            task_type = data.get("task_type", "conversation")
            use_cache = data.get("use_cache", True)
            temperature = data.get("temperature", 0.7)
            max_tokens = data.get("max_tokens")
            
            if not message:
                return jsonify({"error": "messageパラメータが必要です"}), 400
            
            # タスクタイプの変換
            if task_type == "lightweight_conversation":
                task_type_enum = TaskType.LIGHTWEIGHT_CONVERSATION
            elif task_type == "conversation":
                task_type_enum = TaskType.CONVERSATION
            else:
                task_type_enum = TaskType.CONVERSATION
            
            # LFM 2.5クライアントでチャット
            client = AlwaysReadyLLMClient()
            response = client.chat(
                message=message,
                model=ModelType.ULTRA_LIGHT,
                task_type=task_type_enum,
                use_cache=use_cache,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return jsonify({
                "success": True,
                "response": response.response,
                "model": response.model,
                "latency_ms": response.latency_ms,
                "cached": response.cached,
                "source": response.source,
                "tokens": response.tokens
            })
            
        except Exception as e:
            logger.error(f"LFM 2.5チャットエラー: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/lfm25/lightweight", methods=["POST"])
    def lfm25_lightweight():
        """LFM 2.5軽量会話（オフライン会話・下書き・整理専用）"""
        if not LFM25_AVAILABLE:
            return jsonify({"error": "LFM 2.5クライアントが利用できません"}), 503
        
        try:
            data = request.json or {}
            message = data.get("message", "")
            use_cache = data.get("use_cache", True)
            
            if not message:
                return jsonify({"error": "messageパラメータが必要です"}), 400
            
            # LFM 2.5クライアントで軽量会話
            client = AlwaysReadyLLMClient()
            response = client.chat(
                message=message,
                model=ModelType.ULTRA_LIGHT,
                task_type=TaskType.LIGHTWEIGHT_CONVERSATION,
                use_cache=use_cache
            )
            
            return jsonify({
                "success": True,
                "response": response.response,
                "model": response.model,
                "latency_ms": response.latency_ms,
                "cached": response.cached,
                "source": response.source,
                "task_type": "lightweight_conversation"
            })
            
        except Exception as e:
            logger.error(f"LFM 2.5軽量会話エラー: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/lfm25/batch", methods=["POST"])
    def lfm25_batch():
        """LFM 2.5バッチチャット（複数メッセージを順次処理）"""
        if not LFM25_AVAILABLE:
            return jsonify({"error": "LFM 2.5クライアントが利用できません"}), 503
        
        try:
            data = request.json or {}
            messages = data.get("messages", [])
            task_type = data.get("task_type", "conversation")
            
            if not messages or not isinstance(messages, list):
                return jsonify({"error": "messagesパラメータ（リスト）が必要です"}), 400
            
            # タスクタイプの変換
            if task_type == "lightweight_conversation":
                task_type_enum = TaskType.LIGHTWEIGHT_CONVERSATION
            else:
                task_type_enum = TaskType.CONVERSATION
            
            # LFM 2.5クライアントでバッチチャット
            client = AlwaysReadyLLMClient()
            results = client.batch_chat(
                messages=messages,
                model=ModelType.ULTRA_LIGHT,
                task_type=task_type_enum
            )
            
            # 結果を整形
            formatted_results = []
            for i, result in enumerate(results):
                formatted_results.append({
                    "index": i,
                    "message": messages[i] if i < len(messages) else "",
                    "response": result.response,
                    "model": result.model,
                    "latency_ms": result.latency_ms,
                    "cached": result.cached,
                    "source": result.source
                })
            
            return jsonify({
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results)
            })
            
        except Exception as e:
            logger.error(f"LFM 2.5バッチチャットエラー: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/lfm25/status", methods=["GET"])
    def lfm25_status():
        """LFM 2.5の状態を取得"""
        if not LFM25_AVAILABLE:
            return jsonify({
                "available": False,
                "error": "LFM 2.5クライアントが利用できません"
            }), 503
        
        try:
            # 簡単なテストリクエストで状態確認
            client = AlwaysReadyLLMClient()
            test_response = client.chat(
                "test",
                model=ModelType.ULTRA_LIGHT,
                task_type=TaskType.CONVERSATION
            )
            
            return jsonify({
                "available": True,
                "model": ModelType.ULTRA_LIGHT.value,
                "status": "operational",
                "test_latency_ms": test_response.latency_ms,
                "test_source": test_response.source
            })
            
        except Exception as e:
            return jsonify({
                "available": False,
                "error": str(e)
            }), 500
    
    logger.info("LFM 2.5専用エンドポイントを登録しました")
    return app
