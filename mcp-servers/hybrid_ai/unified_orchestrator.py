#!/usr/bin/env python3
"""
🌟 統合オーケストレーター
GeminiとChatGPTの両方からアクセス可能
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# リクエストモデル
class UnifiedRequest(BaseModel):
    message: str
    user_id: str = "mana"
    ai_type: str = "auto"  # "gemini", "chatgpt", "auto"
    context: Optional[Dict] = None

class UnifiedResponse(BaseModel):
    success: bool
    message: str
    ai_used: str
    data: Optional[Dict] = None

class UnifiedOrchestrator:
    def __init__(self):
        self.app = FastAPI(
            title="🌟 Unified AI Orchestrator",
            description="GeminiとChatGPTの統合オーケストレーター",
            version="1.0.0"
        )
        
        # 各AIサーバーのURL
        self.gemini_url = "http://localhost:9110"
        self.chatgpt_url = "http://localhost:9101"
        self.trinity_url = "http://localhost:8097"
        self.manaos_url = "http://localhost:9200"
        
        # 🎯 ManaSpec統合
        self.manaspec_api_url = "http://localhost:9301"
        self.manaspec_ui_url = "http://localhost:9302"
        
        # 認証設定
        self.security = HTTPBearer()
        self.api_key = os.getenv("MANAOS_API_KEY", "manaos-2024-secure-key")
        
        logger.info("🌟 Unified Orchestrator 初期化")
        
        self.setup_middleware()
        self.setup_routes()
    
    def verify_api_key(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """APIキー認証"""
        if credentials.credentials != self.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return credentials.credentials
    
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
                "name": "🌟 Unified AI Orchestrator",
                "version": "1.0.0",
                "status": "active",
                "ai_services": {
                    "gemini": {
                        "url": self.gemini_url,
                        "status": "active",
                        "features": ["Googleサービス統合", "自然言語理解"]
                    },
                    "chatgpt": {
                        "url": self.chatgpt_url,
                        "status": "active",
                        "features": ["複雑なタスク", "分析"]
                    }
                },
                "capabilities": [
                    "自動AI選択",
                    "冗長性",
                    "高可用性",
                    "全システム統合"
                ]
            }
        
        @self.app.post("/api/unified/chat")
        async def unified_chat(request: UnifiedRequest):
            """統合チャット"""
            try:
                # AI選択
                ai_type = self._select_ai(request.message, request.ai_type)
                
                # 選択したAIにリクエスト送信
                result = await self._forward_to_ai(ai_type, request)
                
                return UnifiedResponse(
                    success=True,
                    message=result.get("message", "処理完了"),
                    ai_used=ai_type,
                    data=result
                )
                
            except Exception as e:
                logger.error(f"❌ Unified Chat Error: {e}")
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
        
        # 🎯 =====  ManaSpec統合エンドポイント =====
        
        @self.app.post("/api/manaspec/propose")
        async def manaspec_propose(feature: dict):
            """🎯 ManaSpec: Remi が Proposal作成"""
            try:
                import subprocess
                
                feature_desc = feature.get("description", "")
                logger.info(f"📋 Remi: Proposal作成開始 - {feature_desc}")
                
                # Remi APIを呼び出して提案生成
                remi_response = await self._call_remi_for_proposal(feature_desc)
                
                # ManaSpec CLIで実際にProposal作成
                result = subprocess.run(
                    ["/root/bin/manaspec", "propose", feature_desc],
                    capture_output=True,
                    text=True
                )
                
                return {
                    "success": True,
                    "remi_guidance": remi_response,
                    "cli_output": result.stdout,
                    "message": "Proposal作成完了 by Remi"
                }
            except Exception as e:
                logger.error(f"❌ ManaSpec Propose Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/manaspec/apply/{change_id}")
        async def manaspec_apply(change_id: str):
            """⚙️ ManaSpec: Luna が Apply実行"""
            try:
                import subprocess
                
                logger.info(f"⚙️ Luna: Apply実行開始 - {change_id}")
                
                # ManaSpec CLIでApply実行
                result = subprocess.run(
                    ["/root/bin/manaspec", "apply", change_id],
                    capture_output=True,
                    text=True
                )
                
                return {
                    "success": result.returncode == 0,
                    "change_id": change_id,
                    "output": result.stdout,
                    "message": "Apply実行完了 by Luna"
                }
            except Exception as e:
                logger.error(f"❌ ManaSpec Apply Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/manaspec/archive/{change_id}")
        async def manaspec_archive(change_id: str):
            """📦 ManaSpec: Mina が Archive実行"""
            try:
                import subprocess
                
                logger.info(f"📦 Mina: Archive実行開始 - {change_id}")
                
                # ManaSpec CLIでArchive実行
                result = subprocess.run(
                    ["/root/bin/manaspec", "archive", change_id, "--yes"],
                    capture_output=True,
                    text=True
                )
                
                # AI Learning Systemに保存
                await self._save_to_ai_learning(change_id)
                
                return {
                    "success": result.returncode == 0,
                    "change_id": change_id,
                    "output": result.stdout,
                    "message": "Archive完了 & 学習保存 by Mina"
                }
            except Exception as e:
                logger.error(f"❌ ManaSpec Archive Error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/manaspec/status")
        async def manaspec_status():
            """📊 ManaSpec: ステータス取得"""
            try:
                import requests
                
                # ManaSpec API経由でステータス取得
                response = requests.get(f"{self.manaspec_api_url}/api/manaspec/status", timeout=5)
                return response.json()
            except Exception as e:
                logger.error(f"❌ ManaSpec Status Error: {e}")
                return {"error": str(e), "manaspec": "offline"}
        
        @self.app.get("/api/manaspec/dashboard")
        async def manaspec_dashboard():
            """🎨 ManaSpec: Dashboard URL取得"""
            return {
                "api_url": self.manaspec_api_url,
                "ui_url": self.manaspec_ui_url,
                "status": "active",
                "message": "ManaSpec Dashboard統合完了"
            }
        
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
            """全システム状態確認"""
            try:
                import requests
                
                systems = {}
                
                # Gemini
                try:
                    gemini_response = requests.get(
                        f"{self.gemini_url}/health",
                        timeout=5
                    )
                    systems["gemini"] = gemini_response.json()
                except requests.RequestException:
                    systems["gemini"] = {"status": "unknown"}
                
                # ChatGPT
                try:
                    chatgpt_response = requests.get(
                        f"{self.chatgpt_url}/health",
                        timeout=5
                    )
                    systems["chatgpt"] = chatgpt_response.json()
                except requests.RequestException:
                    systems["chatgpt"] = {"status": "unknown"}
                
                # Trinity
                try:
                    trinity_response = requests.get(
                        f"{self.trinity_url}/api/status",
                        timeout=5
                    )
                    systems["trinity"] = trinity_response.json()
                except requests.RequestException:
                    systems["trinity"] = {"status": "unknown"}
                
                # ManaOS
                try:
                    manaos_response = requests.get(
                        f"{self.manaos_url}/health",
                        timeout=5
                    )
                    systems["manaos"] = manaos_response.json()
                except requests.RequestException:
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
        
        # テスト用エンドポイント（認証なし）
        @self.app.get("/api/test/system_status")
        async def test_system_status():
            """システム状態確認（認証なし・テスト用）"""
            try:
                result = await system_status()
                return {
                    "success": True,
                    "message": "システム状態を確認しました（認証なし）",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Test System Status Error: {e}")
                return {
                    "success": False,
                    "message": f"システム状態確認に失敗: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
        
        # ChatGPT Actions用エンドポイント
        @self.app.get("/api/actions/system_status")
        async def actions_system_status(api_key: str = Depends(self.verify_api_key)):
            """システム状態確認（Actions用）"""
            try:
                result = await system_status()
                return {
                    "success": True,
                    "message": "システム状態を確認しました",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Actions System Status Error: {e}")
                return {
                    "success": False,
                    "message": f"システム状態確認に失敗: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.app.get("/api/actions/today_schedule")
        async def actions_today_schedule(api_key: str = Depends(self.verify_api_key)):
            """今日の予定取得（Actions用）"""
            try:
                result = await get_calendar_events()
                return {
                    "success": True,
                    "message": "今日の予定を取得しました",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Actions Today Schedule Error: {e}")
                return {
                    "success": False,
                    "message": f"予定取得に失敗: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.app.post("/api/actions/create_event")
        async def actions_create_event(event_data: dict, api_key: str = Depends(self.verify_api_key)):
            """予定作成（Actions用）"""
            try:
                result = await create_calendar_event(event_data)
                return {
                    "success": True,
                    "message": "予定を作成しました",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Actions Create Event Error: {e}")
                return {
                    "success": False,
                    "message": f"予定作成に失敗: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.app.get("/api/actions/drive_search")
        async def actions_drive_search(api_key: str = Depends(self.verify_api_key)):
            """Drive検索（Actions用）"""
            try:
                result = await get_drive_files()
                return {
                    "success": True,
                    "message": "Driveファイルを検索しました",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Actions Drive Search Error: {e}")
                return {
                    "success": False,
                    "message": f"Drive検索に失敗: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.app.get("/api/actions/x280_screenshot")
        async def actions_x280_screenshot(api_key: str = Depends(self.verify_api_key)):
            """X280スクリーンショット（Actions用）"""
            try:
                result = await x280_screenshot()
                return {
                    "success": True,
                    "message": "X280スクリーンショットを取得しました",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Actions X280 Screenshot Error: {e}")
                return {
                    "success": False,
                    "message": f"スクリーンショット取得に失敗: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
    
    def _select_ai(self, message: str, ai_type: str) -> str:
        """最適なAIを選択"""
        if ai_type in ["gemini", "chatgpt"]:
            return ai_type
        
        # 自動選択ロジック
        message_lower = message.lower()
        
        # Googleサービス関連はGemini
        if any(word in message_lower for word in [
            "予定", "calendar", "スケジュール",
            "ファイル", "drive", "ドライブ",
            "メール", "gmail", "email"
        ]):
            return "gemini"
        
        # 複雑なタスクや分析はChatGPT
        if any(word in message_lower for word in [
            "分析", "analyze", "比較", "compare",
            "レポート", "report", "統計", "statistics"
        ]):
            return "chatgpt"
        
        # デフォルトはGemini
        return "gemini"
    
    async def _forward_to_ai(self, ai_type: str, request: UnifiedRequest) -> Dict:
        """選択したAIにリクエストを転送"""
        try:
            import requests
            
            url = f"{self.gemini_url}/api/chat" if ai_type == "gemini" else f"{self.chatgpt_url}/api/chat"
            
            response = requests.post(
                url,
                json={
                    "message": request.message,
                    "user_id": request.user_id,
                    "context": request.context
                },
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ AI Forward Error: {e}")
            raise
    
    async def _call_remi_for_proposal(self, feature_desc: str) -> str:
        """Remi（戦略指令AI）にProposal提案を依頼"""
        try:
            import requests
            
            response = requests.post(
                f"{self.manaos_url}/api/execute",
                json={
                    "text": f"OpenSpec Proposalを作成: {feature_desc}",
                    "actor": "remi",
                    "source": "manaspec"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result", "")
            else:
                return "Remi offline - using default template"
        except Exception:
            return "Remi offline - using default template"
    
    async def _save_to_ai_learning(self, change_id: str):
        """Mina（洞察記録AI）にArchiveデータを保存"""
        try:
            import requests
            
            response = requests.post(
                f"{self.manaos_url}/api/execute",
                json={
                    "text": f"ManaSpec Archive保存: {change_id}",
                    "actor": "mina",
                    "source": "manaspec"
                },
                timeout=10
            )
            
            logger.info(f"📦 Mina: Archive saved - {change_id}")
        except Exception as e:
            logger.warning(f"⚠️ Mina save failed: {e}")
    
    def run(self, host: str = "0.0.0.0", port: int = 9102):
        """サーバー起動"""
        logger.info("🚀 Unified Orchestrator 起動中...")
        logger.info(f"🌐 アクセス: http://{host}:{port}")
        logger.info(f"📱 Gemini: http://{host}:9100")
        logger.info(f"📱 ChatGPT: http://{host}:9101")
        logger.info(f"🌟 統合: http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    orchestrator = UnifiedOrchestrator()
    orchestrator.run()

