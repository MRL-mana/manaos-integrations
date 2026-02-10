"""
ローカルLLM統合API
取り込んだ全ローカルLLMシステムを統合APIで提供
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from typing import Dict, Any, Optional
import httpx
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 既存の統合APIサーバーを拡張（オプション）
try:
    from unified_api_server import app as base_app
    UNIFIED_API_AVAILABLE = True
except ImportError:
    UNIFIED_API_AVAILABLE = False
    logger.warning("統合APIサーバーが見つかりません")

# ローカルLLM統合用のエンドポイントを追加
app = Flask(__name__)
CORS(app)

# ローカルLLMシステムURL
FREE_ASSISTANT_URL = "http://localhost:8501"
SARA_API_URL = "http://localhost:8000"
N8N_URL = "http://localhost:5678"

# 統合システム管理
local_llm_systems = {
    "free_assistant": {
        "name": "Free-personal-AI-Assistant",
        "url": FREE_ASSISTANT_URL,
        "enabled": True,
        "features": ["plugins", "web_search", "pdf", "youtube"]
    },
    "sara": {
        "name": "Sara-AI-Platform",
        "url": SARA_API_URL,
        "enabled": True,
        "features": ["memory", "persona", "tts", "multi_model"]
    },
    "n8n": {
        "name": "n8n",
        "url": N8N_URL,
        "enabled": True,
        "features": ["workflow", "automation"]
    }
}


@app.route("/api/local-llm/status", methods=["GET"])
def get_local_llm_status():
    """ローカルLLMシステムの状態を取得"""
    status = {}
    
    for system_id, system_info in local_llm_systems.items():
        try:
            response = httpx.get(f"{system_info['url']}/healthz", timeout=2.0)
            status[system_id] = {
                "available": response.status_code == 200,
                "url": system_info["url"],
                "features": system_info["features"]
            }
        except Exception:
            status[system_id] = {
                "available": False,
                "url": system_info["url"],
                "features": system_info["features"]
            }
    
    return jsonify({
        "status": "ok",
        "systems": status
    })


@app.route("/api/local-llm/chat", methods=["POST"])
def chat_with_local_llm():
    """ローカルLLMとチャット"""
    data = request.json
    message = data.get("message", "")
    system = data.get("system", "free_assistant")
    
    if system not in local_llm_systems:
        return jsonify({"error": f"不明なシステム: {system}"}), 400
    
    system_info = local_llm_systems[system]
    
    try:
        # Sara-AI-Platform経由
        if system == "sara":
            response = httpx.post(
                f"{system_info['url']}/api/chat",
                json={"message": message},
                timeout=30.0
            )
            return jsonify(response.json())
        
        # その他のシステムは個別実装
        return jsonify({
            "error": "未実装",
            "system": system,
            "message": "このシステムは直接API未対応です"
        })
    except Exception as e:
        logger.error(f"チャットエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/local-llm/systems", methods=["GET"])
def list_systems():
    """利用可能なローカルLLMシステム一覧"""
    return jsonify({
        "systems": [
            {
                "id": system_id,
                "name": info["name"],
                "url": info["url"],
                "features": info["features"]
            }
            for system_id, info in local_llm_systems.items()
        ]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9406, debug=True)

