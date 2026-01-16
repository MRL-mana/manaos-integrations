#!/usr/bin/env python3
"""
🤖 ChatGPT MCP統合サーバー
携帯のChatGPTアプリからManaOSシステムを操作
OpenAI Connector / MCP Protocol対応
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ MCPライブラリが見つかりません。stdio機能は無効です")
    MCP_AVAILABLE = False

# リクエストモデル
class ChatGPTRequest(BaseModel):
    message: str
    user_id: str = "mana"
    context: Optional[Dict] = None

class ChatGPTResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

class ChatGPTMCPIntegrationServer:
    def __init__(self):
        self.app = FastAPI(
            title="🤖 ChatGPT MCP Integration Server",
            description="携帯のChatGPTアプリからManaOSシステムを操作",
            version="1.0.0"
        )

        self.trinity_url = "http://localhost:8097"
        self.manaos_url = "http://localhost:9200"

        logger.info("🤖 ChatGPT MCP Integration Server 初期化")

        self.setup_middleware()
        self.setup_routes()

# グローバルインスタンス
server = ChatGPTMCPIntegrationServer()
app = server.app

# ルート追加
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"status": "ok", "service": "chatgpt_mcp_server"}

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "healthy"}

@app.get("/api/status")
async def api_status():
    """APIステータス"""
    return {"status": "running", "service": "chatgpt_mcp_server"}

# クラスメソッドを追加（既存のクラスに追加）
def add_methods_to_class():
    """クラスメソッドを追加"""
    def _get_tools_list(self):
        """ツール一覧を返すヘルパーメソッド"""
        return {
            "tools": [
                {"name": "get_calendar_events", "description": "Google Calendarの予定を取得"},
                {"name": "create_calendar_event", "description": "Google Calendarに予定を作成"},
                {"name": "get_drive_files", "description": "Google Driveのファイル一覧を取得"},
                {"name": "get_gmail_messages", "description": "Gmailのメッセージを取得"},
                {"name": "get_system_status", "description": "システムの状態を確認"},
                {"name": "x280_screenshot", "description": "X280のスクリーンショットを取得"}
            ]
        }

    ChatGPTMCPIntegrationServer._get_tools_list = _get_tools_list

add_methods_to_class()

# サーバーインスタンスのメソッドを直接追加
if hasattr(server, 'app'):
    def setup_middleware(self):
        """CORS設定"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """ルート設定"""

        @self.app.get("/")
        async def root():
            """トップページ"""
            return {
                "name": "🤖 ChatGPT MCP Integration Server",
                "version": "1.0.0",
                "status": "active",
                "features": [
                    "Google Calendar操作",
                    "Google Drive操作",
                    "Gmail操作",
                    "ManaOS v3.0操作",
                    "X280リモート操作",
                    "Obsidian操作",
                    "システム状態確認"
                ],
                "mcp_protocol": "1.0",
                "mcp_endpoints": {
                    "tools": "/mcp/tools",
                    "execute": "/mcp/execute"
                }
            }

        @self.app.get("/mcp")
        async def mcp_root():
            """MCPルートエンドポイント（ChatGPT Connector用）"""
            return self._get_tools_list()

        @self.app.post("/api/chat")
        async def chat(request: ChatGPTRequest):
            """ChatGPTとのチャット"""
            try:
                # メッセージ解析
                intent = self._parse_intent(request.message)

                # 適切なアクションを実行
                result = await self._execute_action(intent, request)

                # 💾 ManaOSに会話を記録（自動記憶機能）
                await self._record_to_manaos(request, result)

                return ChatGPTResponse(
                    success=True,
                    message=result.get("message", "処理完了"),
                    data=result
                )

            except Exception as e:
                logger.error(f"❌ ChatGPT API Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/calendar/events")
        async def get_calendar_events():
            """Google Calendar予定取得"""
            try:
                import requests
                response = requests.get(
                    f"{self.trinity_url}/api/calendar/events",
                    timeout=10
                )
                return response.json()
            except Exception as e:
                logger.error(f"❌ Calendar Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/calendar/create")
        async def create_calendar_event(event_data: dict):
            """Google Calendar予定作成"""
            try:
                import requests
                response = requests.post(
                    f"{self.trinity_url}/calendar/create",
                    json=event_data,
                    timeout=10
                )
                return response.json()
            except Exception as e:
                logger.error(f"❌ Calendar Create Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/drive/files")
        async def get_drive_files():
            """Google Driveファイル取得"""
            try:
                import requests
                response = requests.get(
                    f"{self.trinity_url}/api/drive/files",
                    timeout=10
                )
                return response.json()
            except Exception as e:
                logger.error(f"❌ Drive Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/gmail/messages")
        async def get_gmail_messages():
            """Gmailメッセージ取得"""
            try:
                import requests
                response = requests.get(
                    f"{self.trinity_url}/api/gmail/messages",
                    timeout=10
                )
                return response.json()
            except Exception as e:
                logger.error(f"❌ Gmail Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/manaos/execute")
        async def execute_manaos(command: dict):
            """ManaOS v3.0実行"""
            try:
                import requests
                response = requests.post(
                    f"{self.manaos_url}/api/execute",
                    json=command,
                    timeout=30
                )
                return response.json()
            except Exception as e:
                logger.error(f"❌ ManaOS Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/x280/screenshot")
        async def x280_screenshot():
            """X280スクリーンショット"""
            try:
                import requests
                response = requests.get(
                    "http://localhost:8097/api/x280/screenshot",
                    timeout=10
                )
                return response.json()
            except Exception as e:
                logger.error(f"❌ X280 Screenshot Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/system/status")
        async def system_status():
            """システム状態確認"""
            try:
                import requests

                # 各システムの状態を確認
                systems = {}

                # Trinity
                try:
                    trinity_response = requests.get(
                        f"{self.trinity_url}/api/status",
                        timeout=5
                    )
                    systems["trinity"] = trinity_response.json()
                except:
                    systems["trinity"] = {"status": "unknown"}

                # ManaOS
                try:
                    manaos_response = requests.get(
                        f"{self.manaos_url}/health",
                        timeout=5
                    )
                    systems["manaos"] = manaos_response.json()
                except:
                    systems["manaos"] = {"status": "unknown"}

                return {
                    "success": True,
                    "systems": systems,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"❌ System Status Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/health")
        async def health():
            """ヘルスチェック"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }

        # MCP Protocol エンドポイント（OpenAI Connector用）
        @self.app.get("/mcp/tools")
        async def mcp_tools():
            """MCPツール一覧（OpenAI Connector準拠）"""
            return self._get_tools_list()

        @self.app.post("/mcp/execute")
        async def mcp_execute(tool_name: str, parameters: dict):
            """MCPツール実行"""
            try:
                if tool_name == "get_calendar_events":
                    result = await get_calendar_events()
                elif tool_name == "create_calendar_event":
                    result = await create_calendar_event(parameters)
                elif tool_name == "get_drive_files":
                    result = await get_drive_files()
                elif tool_name == "get_gmail_messages":
                    result = await get_gmail_messages()
                elif tool_name == "get_system_status":
                    result = await system_status()
                elif tool_name == "x280_screenshot":
                    result = await x280_screenshot()
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

                return {
                    "success": True,
                    "tool": tool_name,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"❌ MCP Execute Error: {e}")
                return {
                    "success": False,
                    "tool": tool_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

    def _parse_intent(self, message: str) -> Dict:
        """メッセージから意図を解析"""
        intent = {
            "action": "chat",
            "target": None,
            "parameters": {}
        }

        message_lower = message.lower()

        # カレンダー関連
        if any(word in message_lower for word in ["予定", "calendar", "スケジュール"]):
            intent["action"] = "calendar"
            if any(word in message_lower for word in ["作成", "create", "追加"]):
                intent["target"] = "create_event"
            elif any(word in message_lower for word in ["確認", "get", "表示"]):
                intent["target"] = "get_events"

        # ドライブ関連
        elif any(word in message_lower for word in ["ファイル", "drive", "ドライブ"]):
            intent["action"] = "drive"
            if any(word in message_lower for word in ["一覧", "list", "表示"]):
                intent["target"] = "list_files"

        # Gmail関連
        elif any(word in message_lower for word in ["メール", "gmail", "email"]):
            intent["action"] = "gmail"
            if any(word in message_lower for word in ["確認", "get", "表示"]):
                intent["target"] = "get_messages"

        # ManaOS関連
        elif any(word in message_lower for word in ["manaos", "システム", "system"]):
            intent["action"] = "manaos"
            if any(word in message_lower for word in ["状態", "status", "確認"]):
                intent["target"] = "get_status"

        # X280関連
        elif any(word in message_lower for word in ["x280", "スクリーン", "screenshot"]):
            intent["action"] = "x280"
            intent["target"] = "screenshot"

        return intent

    async def _execute_action(self, intent: Dict, request: ChatGPTRequest) -> Dict:
        """アクションを実行"""
        action = intent.get("action")
        target = intent.get("target")

        result = {
            "action": action,
            "target": target,
            "timestamp": datetime.now().isoformat()
        }

        try:
            import requests

            if action == "calendar":
                if target == "get_events":
                    response = requests.get(
                        f"{self.trinity_url}/api/calendar/events",
                        timeout=10
                    )
                    result["data"] = response.json()
                    result["message"] = "カレンダーの予定を取得しました"

            elif action == "drive":
                if target == "list_files":
                    response = requests.get(
                        f"{self.trinity_url}/api/drive/files",
                        timeout=10
                    )
                    result["data"] = response.json()
                    result["message"] = "Google Driveのファイル一覧を取得しました"

            elif action == "gmail":
                if target == "get_messages":
                    response = requests.get(
                        f"{self.trinity_url}/api/gmail/messages",
                        timeout=10
                    )
                    result["data"] = response.json()
                    result["message"] = "Gmailのメッセージを取得しました"

            elif action == "manaos":
                if target == "get_status":
                    response = requests.get(
                        f"{self.manaos_url}/health",
                        timeout=10
                    )
                    result["data"] = response.json()
                    result["message"] = "ManaOSの状態を確認しました"

            elif action == "x280":
                if target == "screenshot":
                    response = requests.get(
                        "http://localhost:8097/api/x280/screenshot",
                        timeout=10
                    )
                    result["data"] = response.json()
                    result["message"] = "X280のスクリーンショットを取得しました"

            else:
                result["message"] = "処理完了"

        except Exception as e:
            logger.error(f"❌ Action Execution Error: {e}")
            result["error"] = str(e)

        return result

    async def _record_to_manaos(self, request: ChatGPTRequest, result: Dict):
        """ChatGPTの会話をManaOSに記録"""
        try:
            from pathlib import Path

            # dev_qa.mdに追記
            dev_qa_path = Path("/root/docs/guides/dev_qa.md")
            timestamp = datetime.now().strftime("%H:%M")

            # 重要な会話のみ記録（システム関連、知識関連など）
            important_keywords = [
                "システム", "setup", "設定", "config", "エラー", "error",
                "実装", "implement", "設計", "design", "コード", "code"
            ]

            is_important = any(keyword in request.message.lower() for keyword in important_keywords)

            if is_important or len(request.message) > 100:
                # dev_qa.mdに追記
                entry = f"""
---
### [{timestamp}] ChatGPT会話記録
**質問**: {request.message[:200]}...
**回答**: {result.get('message', '処理完了')[:200]}...
**タグ**: #chatgpt #auto-record
---
"""

                with open(dev_qa_path, "a", encoding="utf-8") as f:
                    f.write(entry)

                logger.info(f"💾 ChatGPT会話をManaOSに記録: {len(request.message)}文字")

                # AI Learning Systemにも記録（存在する場合）
                learning_system_path = Path("/root/ai_learning_system/data/knowledge_base.json")
                if learning_system_path.exists():
                    try:
                        with open(learning_system_path, "r", encoding="utf-8") as f:
                            knowledge_base = json.load(f)
                    except:
                        knowledge_base = []

                    # 新しい知識を追加
                    new_knowledge = {
                        "title": f"ChatGPT会話: {request.message[:50]}",
                        "content": request.message,
                        "category": "ChatGPT記録",
                        "tags": ["chatgpt", "auto-record"],
                        "created_at": datetime.now().isoformat(),
                        "importance": 6 if is_important else 4
                    }
                    knowledge_base.append(new_knowledge)

                    with open(learning_system_path, "w", encoding="utf-8") as f:
                        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)

                    logger.info("💾 AI Learning Systemにも記録完了")

        except Exception as e:
            logger.error(f"⚠️ ManaOS記録エラー: {e}")
            # 記録失敗しても処理は続行
            pass

    def run(self, host: str = "0.0.0.0", port: int = 9101):
        """サーバー起動"""
        logger.info("🚀 ChatGPT MCP Integration Server 起動中...")
        logger.info(f"🌐 アクセス: http://{host}:{port}")
        logger.info("📱 携帯のChatGPTアプリからアクセス可能")
        logger.info("💾 自動記憶機能: 有効")
        uvicorn.run(self.app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    server = ChatGPTMCPIntegrationServer()
    server.run()

