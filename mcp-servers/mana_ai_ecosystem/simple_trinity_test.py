#!/usr/bin/env python3
"""
Simple Trinity Secretary Test - 簡単なテスト用サーバー
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime

# FastAPIアプリケーション
app = FastAPI(title="Simple Trinity Secretary Test", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydanticモデル
class SecretaryMessage(BaseModel):
    message: str
    user_id: str = "default_user"
    secretary_id: str = "trinity"
    context: dict = {}

# ルート
@app.get("/")
async def root():
    return {
        "message": "Trinity Secretary Test - 統合AI秘書システム",
        "version": "1.0.0",
        "status": "active",
        "features": [
            "タスク管理",
            "スケジュール管理", 
            "コミュニケーション管理",
            "情報検索",
            "個人的アシスタンス"
        ]
    }

@app.post("/chat")
async def chat_endpoint(secretary_message: SecretaryMessage):
    """チャットエンドポイント"""
    try:
        # 簡単な応答生成
        message = secretary_message.message.lower()
        
        if "こんにちは" in message or "hello" in message:
            response = "こんにちは！Trinity秘書です。お疲れ様です。何かお手伝いできることはありますか？"
            intent = "greeting"
        elif "タスク" in message or "task" in message:
            response = "タスク管理についてお手伝いします！新しいタスクの作成、一覧表示、更新、完了などが可能です。どのようなタスクを作成しますか？"
            intent = "task_management"
        elif "スケジュール" in message or "schedule" in message:
            response = "スケジュール管理についてお手伝いします！会議の予定、アポイントメント、リマインダーなどが管理できます。どのような予定を作成しますか？"
            intent = "schedule_management"
        elif "メール" in message or "email" in message:
            response = "コミュニケーション管理についてお手伝いします！メールの作成、送信、管理などが可能です。誰にメールを送りますか？"
            intent = "communication"
        elif "情報" in message or "info" in message:
            response = "情報検索についてお手伝いします！最新の情報、データ分析、調査などが可能です。どのような情報をお探しですか？"
            intent = "information_request"
        elif "助けて" in message or "help" in message:
            response = "個人的なアシスタンスについてお手伝いします！お疲れ様です。一緒に解決していきましょう。どのようなことでお困りですか？"
            intent = "personal_assistance"
        else:
            response = f"承知いたしました。「{secretary_message.message}」についてお手伝いします。もう少し詳しく教えていただけますか？"
            intent = "general_conversation"
        
        return {
            "response": response,
            "type": intent,
            "secretary": "Trinity",
            "personality": "professional",
            "timestamp": datetime.utcnow().isoformat(),
            "suggestions": [
                "タスクを作成する",
                "スケジュールを確認する", 
                "メールを送信する",
                "情報を検索する"
            ]
        }
        
    except Exception:
        return {
            "response": "申し訳ございません。エラーが発生しました。",
            "type": "error",
            "secretary": "Trinity",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Trinity Secretary Test"
    }

if __name__ == "__main__":
    print("🚀 Trinity Secretary Test Server を起動中...")
    print("📱 アクセスURL: http://localhost:8087")
    print("🔧 API エンドポイント: http://localhost:8087/chat")
    print("❤️ ヘルスチェック: http://localhost:8087/health")
    uvicorn.run(app, host="0.0.0.0", port=8087)
