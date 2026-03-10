#!/usr/bin/env python3
"""
Trinity Orchestrator v1.0 - API Server
FastAPI経由でOrchestratorを公開
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

# カレントディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

from core import TrinityOrchestrator
from ticket_manager import TicketManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger("orchestrator_api")

# FastAPI アプリ
app = FastAPI(
    title="Trinity Orchestrator v1.0 API",
    description="Multi-Agent Control Engine with PACTS Loop",
    version="1.0.0"
)

# CORS設定（ManaOSダッシュボードからのアクセス許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIキー確認
if not os.getenv("OPENAI_API_KEY"):
    logger.error("❌ OPENAI_API_KEY not set")
    print("❌ Error: OPENAI_API_KEY not set")
    print("Set it with: export OPENAI_API_KEY='your-api-key'")
    sys.exit(1)

# Orchestrator初期化
try:
    orchestrator = TrinityOrchestrator()
    ticket_manager = TicketManager()
    logger.info("✅ Trinity Orchestrator initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Orchestrator: {e}")
    sys.exit(1)


# リクエストモデル
class OrchestrateRequest(BaseModel):
    goal: str
    context: Optional[List[str]] = []
    budget_turns: Optional[int] = 12


class TicketResponse(BaseModel):
    ticket_id: str
    goal: str
    status: str
    confidence: float
    turns: int
    artifacts: List[Dict]


# ヘルスチェック
@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {
        "status": "ok",
        "service": "Trinity Orchestrator v1.0",
        "version": "1.0.0",
        "redis_connected": True
    }


# Orchestrator実行
@app.post("/api/orchestrate", response_model=TicketResponse)
async def orchestrate(request: OrchestrateRequest):
    """
    Orchestratorを実行
    
    Args:
        goal: 達成目標
        context: 前提条件・制約
        budget_turns: 最大ターン数
        
    Returns:
        実行結果
    """
    try:
        logger.info(f"🚀 Orchestrate request: {request.goal}")
        
        result = orchestrator.run(
            goal=request.goal,
            context=request.context,  # type: ignore
            budget_turns=request.budget_turns  # type: ignore
        )
        
        logger.info(f"✅ Orchestrate complete: {result['ticket_id']}")
        
        return TicketResponse(
            ticket_id=result["ticket_id"],
            goal=result["goal"],
            status=result["final_status"],
            confidence=result["confidence"],
            turns=result["turns"],
            artifacts=result["artifacts"]
        )
    except Exception as e:
        logger.error(f"❌ Orchestrate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# チケット一覧取得
@app.get("/api/tickets")
async def list_tickets():
    """アクティブなチケット一覧を取得"""
    try:
        tickets = ticket_manager.list_active_tickets()
        return {
            "tickets": tickets,
            "count": len(tickets)
        }
    except Exception as e:
        logger.error(f"❌ List tickets failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 特定チケットの詳細取得
@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """特定チケットの詳細を取得"""
    try:
        ticket = ticket_manager.get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get ticket failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# チケットサマリー取得
@app.get("/api/tickets/{ticket_id}/summary")
async def get_ticket_summary(ticket_id: str):
    """チケットのサマリーを取得"""
    try:
        summary = ticket_manager.get_summary(ticket_id)
        if "not found" in summary.lower():
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return {"summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get ticket summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 統計情報
@app.get("/api/stats")
async def get_stats():
    """統計情報を取得"""
    try:
        active_tickets = ticket_manager.list_active_tickets()
        
        return {
            "active_tickets": len(active_tickets),
            "orchestrator_version": "1.0.0",
            "api_version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"❌ Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ルート
@app.get("/")
async def root():
    """API情報"""
    return {
        "service": "Trinity Orchestrator v1.0 API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "orchestrate": "POST /api/orchestrate",
            "list_tickets": "GET /api/tickets",
            "get_ticket": "GET /api/tickets/{ticket_id}",
            "stats": "GET /api/stats"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Trinity Orchestrator API Server...")
    logger.info("📍 Port: 9400")
    logger.info("📖 Docs: http://localhost:9400/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9400,
        log_level="info"
    )

