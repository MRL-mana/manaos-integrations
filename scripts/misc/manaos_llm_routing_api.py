"""
ManaOS統合LLMルーティングAPI
難易度判定とルーティングを提供するFlask API
"""

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS
import os
import json
import time
import uuid
import re
import sys
from pathlib import Path
from manaos_logger import get_logger, get_service_logger
from typing import Dict, Any, Optional, List

_CURRENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CURRENT_DIR.parents[1]
_LLM_DIR = _REPO_ROOT / "llm"
for _path in (_REPO_ROOT, _LLM_DIR):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

try:
    from llm.llm_router_enhanced import EnhancedLLMRouter
except ModuleNotFoundError:
    from llm_router_enhanced import EnhancedLLMRouter

logger = get_service_logger("manaos-llm-routing-api")
app = Flask(__name__)
CORS(app)

# LLMルーターの初期化
router = EnhancedLLMRouter()


AUTO_MODEL_ALIASES = {"auto", "auto-local", "manaos-auto"}
AUTO_MODEL_DEFAULT = os.getenv("MANAOS_AUTO_MODEL_DEFAULT", "llama3-uncensored:latest").strip()


_SAFE_MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def _build_openai_model_list(raw_models: List[Any]) -> List[Dict[str, Any]]:
    created = int(time.time())
    seen = set()
    ordered_ids = ["auto", "auto-local"]

    for item in raw_models:
        model_id = str(item or "").strip()
        if not model_id:
            continue
        if not _SAFE_MODEL_ID_PATTERN.match(model_id):
            continue
        ordered_ids.append(model_id)

    result = []
    for model_id in ordered_ids:
        if model_id in seen:
            continue
        seen.add(model_id)
        result.append(
            {
                "id": model_id,
                "object": "model",
                "created": created,
                "owned_by": "manaos",
                "root": model_id,
            }
        )
    return result


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
        return "\n".join([chunk for chunk in chunks if chunk]).strip()
    return ""


def _build_prompt_from_messages(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""

    lines = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role", "user")
        content = _extract_text_from_content(message.get("content", ""))
        if not content:
            continue
        lines.append(f"[{role}] {content}")
    return "\n\n".join(lines).strip()


def _make_openai_chat_response(content: str, model: str, completion_id: str) -> Dict[str, Any]:
    created = int(time.time())
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": max(1, len(content) // 4),
            "total_tokens": max(1, len(content) // 4),
        },
    }


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


@app.route("/v1/models", methods=["GET"])
def openai_models():
    try:
        models = router.get_available_models()
        safe_models = _build_openai_model_list(models)
        logger.info(f"Models requested={len(models)}, exported={len(safe_models)}")
        return jsonify(
            {
                "object": "list",
                "data": safe_models,
            }
        )
    except Exception as e:
        logger.error(f"OpenAIモデル一覧取得エラー: {e}", exc_info=True)
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500


@app.route("/openapi.json", methods=["GET"])
def openapi_schema():
    """OpenAPI スキーマを返す"""
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "ManaOS LLM Router",
            "version": "1.0.0",
            "description": "OpenAI互換LLMルータAPI"
        },
        "paths": {
            "/v1/models": {
                "get": {
                    "summary": "利用可能なモデル一覧",
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/v1/chat/completions": {
                "post": {
                    "summary": "チャット完了リクエスト",
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    })


@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions():
    try:
        data = request.get_json(silent=True) or {}
        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            return jsonify({"error": {"message": "messages は必須です", "type": "invalid_request_error"}}), 400

        requested_model = str(data.get("model") or "auto-local")
        stream = bool(data.get("stream", False))
        prompt = _build_prompt_from_messages(messages)
        if not prompt:
            return jsonify({"error": {"message": "messages からテキストを抽出できません", "type": "invalid_request_error"}}), 400

        context = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        generation: Dict[str, Any] = {}
        for key in ["temperature", "max_tokens", "top_p", "stop", "timeout_sec"]:
            if key in data:
                generation[key] = data.get(key)
        if generation:
            context = dict(context)
            context["_generation"] = generation

        preferences: Dict[str, Any] = {}
        if requested_model in AUTO_MODEL_ALIASES and AUTO_MODEL_DEFAULT:
            preferences["force_model"] = AUTO_MODEL_DEFAULT
        elif requested_model not in AUTO_MODEL_ALIASES:
            preferences["force_model"] = requested_model

        if "temperature" in data:
            try:
                temperature = float(data.get("temperature"))
                preferences["prefer_speed"] = temperature <= 0.4
                preferences["prefer_quality"] = temperature <= 0.2
            except (TypeError, ValueError):
                pass

        result = router.route(prompt, context, preferences)
        if not result.get("success"):
            error_message = result.get("error") or "LLMルーティングに失敗しました"
            return jsonify({"error": {"message": error_message, "type": "server_error"}}), 500

        content = result.get("response") or ""
        if "max_tokens" in data:
            try:
                requested_max_tokens = max(1, min(4096, int(data.get("max_tokens"))))
                max_chars = requested_max_tokens * 6
                if len(content) > max_chars:
                    content = content[:max_chars].rstrip()
            except (TypeError, ValueError):
                pass

        resolved_model = str(result.get("model") or requested_model)
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

        if stream:
            def event_stream():
                created = int(time.time())
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": resolved_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

            return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

        response_payload = _make_openai_chat_response(content, resolved_model, completion_id)
        return jsonify(response_payload)

    except Exception as e:
        logger.error(f"OpenAI互換チャットエラー: {e}", exc_info=True)
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500


if __name__ == "__main__":
    # 開発用サーバー起動
    port = int(os.getenv("PORT", "5211"))
    debug_mode = os.getenv("MANAOS_LLM_ROUTER_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    logger.info(f"ManaOS LLMルーティングAPIを起動: http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)

