"""
LLMルーティングMCPサーバー
Cursorから直接ManaOSのLLMルーティング機能を使用可能にする
"""

import os
import sys
import json
import logging
from typing import Any, Dict, List, Optional
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from manaos_logger import get_logger
except ImportError:
    from logging import getLogger as get_logger

# MCP SDKのインポート
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = get_logger(__name__)
if not MCP_AVAILABLE:
    logger.warning("MCP SDKがインストールされていません。pip install mcp を実行してください。")

# APIエンドポイント
UNIFIED_API_URL = os.getenv("MANAOS_INTEGRATION_API_URL", "http://localhost:9500")
ROUTING_API_URL = os.getenv("LLM_ROUTING_API_URL", "http://localhost:9501")

# ヘルスチェック用HTTPサーバー
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "llm-routing"}).encode())
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        # ログを抑制
        pass

def start_health_server(port: int = 5111):
    """ヘルスチェック用HTTPサーバーを起動"""
    try:
        server = HTTPServer(("127.0.0.1", port), HealthCheckHandler)
        logger.info(f"ヘルスチェックサーバー起動: ポート {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"ヘルスチェックサーバー起動エラー: {e}")

# MCPサーバーの初期化
if MCP_AVAILABLE:
    app = Server("llm-routing")
else:
    app = None


def analyze_difficulty(prompt: str, code_context: Optional[str] = None) -> Dict[str, Any]:
    """
    プロンプトの難易度を分析
    
    Args:
        prompt: ユーザーのプロンプト
        code_context: 関連コード（オプション）
    
    Returns:
        難易度分析結果
    """
    url = f"{UNIFIED_API_URL}/api/llm/analyze"
    
    data = {
        "prompt": prompt,
        "context": {}
    }
    
    if code_context:
        data["context"]["code_context"] = code_context
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"難易度分析エラー: {e}")
        return {
            "error": str(e),
            "difficulty_score": 0,
            "difficulty_level": "unknown",
            "recommended_model": "unknown"
        }


def route_llm(
    prompt: str,
    code_context: Optional[str] = None,
    prefer_speed: bool = True,
    prefer_quality: bool = False
) -> Dict[str, Any]:
    """
    LLMリクエストをルーティングして実行
    
    Args:
        prompt: ユーザーのプロンプト
        code_context: 関連コード（オプション）
        prefer_speed: 速度優先
        prefer_quality: 品質優先
    
    Returns:
        ルーティング結果
    """
    url = f"{UNIFIED_API_URL}/api/llm/route-enhanced"
    
    data = {
        "prompt": prompt,
        "context": {},
        "preferences": {
            "prefer_speed": prefer_speed,
            "prefer_quality": prefer_quality
        }
    }
    
    if code_context:
        data["context"]["code_context"] = code_context
    
    try:
        response = requests.post(url, json=data, timeout=300)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"ルーティングエラー: {e}")
        return {
            "error": str(e),
            "success": False
        }


def get_available_models() -> Dict[str, Any]:
    """利用可能なモデル一覧を取得"""
    url = f"{UNIFIED_API_URL}/api/llm/models-enhanced"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}")
        return {
            "error": str(e),
            "models": []
        }


if MCP_AVAILABLE:
    @app.list_tools()
    async def list_tools() -> List[Tool]:
        """利用可能なツール一覧を返す"""
        return [
            Tool(
                name="analyze_llm_difficulty",
                description="プロンプトの難易度を分析して、推奨モデルを返す（LLM呼び出しなし）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "ユーザーのプロンプト"
                        },
                        "code_context": {
                            "type": "string",
                            "description": "関連コード（オプション）"
                        }
                    },
                    "required": ["prompt"]
                }
            ),
            Tool(
                name="route_llm_request",
                description="LLMリクエストをルーティングして実行（難易度に応じて適切なモデルを自動選択）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "ユーザーのプロンプト"
                        },
                        "code_context": {
                            "type": "string",
                            "description": "関連コード（オプション）"
                        },
                        "prefer_speed": {
                            "type": "boolean",
                            "description": "速度優先（デフォルト: true）"
                        },
                        "prefer_quality": {
                            "type": "boolean",
                            "description": "品質優先（デフォルト: false）"
                        }
                    },
                    "required": ["prompt"]
                }
            ),
            Tool(
                name="get_available_models",
                description="利用可能なLLMモデル一覧を取得",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """ツールを呼び出す"""
        try:
            if name == "analyze_llm_difficulty":
                prompt = arguments.get("prompt", "")
                code_context = arguments.get("code_context")
                
                result = analyze_difficulty(prompt, code_context)
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False)
                )]
            
            elif name == "route_llm_request":
                prompt = arguments.get("prompt", "")
                code_context = arguments.get("code_context")
                prefer_speed = arguments.get("prefer_speed", True)
                prefer_quality = arguments.get("prefer_quality", False)
                
                result = route_llm(prompt, code_context, prefer_speed, prefer_quality)
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False)
                )]
            
            elif name == "get_available_models":
                result = get_available_models()
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False)
                )]
            
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"不明なツール: {name}"}, ensure_ascii=False)
                )]
        
        except Exception as e:
            logger.error(f"ツール呼び出しエラー: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, ensure_ascii=False)
            )]


async def main():
    """メイン関数"""
    if not MCP_AVAILABLE:
        logger.error("MCP SDKがインストールされていません。pip install mcp を実行してください。")
        sys.exit(1)
    
    # ヘルスチェックサーバーをバックグラウンドで起動
    health_port = int(os.getenv("PORT", "5111"))
    health_thread = threading.Thread(target=start_health_server, args=(health_port,), daemon=True)
    health_thread.start()
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())



















