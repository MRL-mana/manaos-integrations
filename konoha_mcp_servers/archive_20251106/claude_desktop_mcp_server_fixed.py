#!/usr/bin/env python3
"""
Claude Desktop MCP Server - 修正版
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション
app = FastAPI(
    title="Claude Desktop MCP Server",
    description="Claude Desktop用のMCPサーバー",
    version="1.0.0"
)

# ルート追加
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"status": "ok", "service": "claude_desktop_mcp_server_fixed"}

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "healthy"}

@app.get("/api/status")
async def api_status():
    """APIステータス"""
    return {"status": "running", "service": "claude_desktop_mcp_server_fixed"}



# データモデル
class ClaudeInstance(BaseModel):
    name: str
    port: int
    status: str = "running"
    started_at: str

class MessageRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ConversationRequest(BaseModel):
    instances: List[str]
    messages: List[str]

# MCPサーバークラス
class ClaudeDesktopMCPServer:
    def __init__(self):
        self.claude_instances = {}
        self.websocket_port=int(os.getenv("PORT", "9000"))
    
    def start_claude_instance(self, instance_name: str, port_offset: int = 0):
        port = self.websocket_port + port_offset
        instance_info = {
            "name": instance_name,
            "port": port,
            "status": "running",
            "started_at": datetime.now().isoformat()
        }
        self.claude_instances[instance_name] = instance_info
        return {"success": True, "message": f"Claude instance '{instance_name}' started on port {port}"}
    
    def send_message_to_claude(self, instance_name: str, message: str, context: Optional[Dict] = None):
        if instance_name not in self.claude_instances:
            return {"success": False, "error": f"Instance '{instance_name}' not found"}
        
        response = {
            "message": f"Claude response to: {message}",
            "instance": instance_name,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }
        return {"success": True, "response": response}
    
    def create_conversation_chain(self, instances: List[str], messages: List[str]):
        results = []
        current_context = None
        
        for instance_name, message in zip(instances, messages):
            result = self.send_message_to_claude(instance_name, message, context=current_context)
            if result["success"]:
                results.append(result["response"])
                current_context = result["response"]
            else:
                results.append({"error": result["error"]})
        
        return {"success": True, "conversation_chain": results}
    
    def list_claude_instances(self):
        return {"success": True, "instances": self.claude_instances}

# サーバーインスタンス
mcp_server = ClaudeDesktopMCPServer()

# API エンドポイント
@app.get("/")
async def root():
    return {
        "message": "Claude Desktop MCP Server",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "instances": len(mcp_server.claude_instances),
        "server": "Claude Desktop MCP"
    }

@app.post("/start_instance")
async def start_instance(instance_name: str, port_offset: int = 0):
    try:
        result = mcp_server.start_claude_instance(instance_name, port_offset)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send_message")
async def send_message(instance_name: str, request: MessageRequest):
    try:
        result = mcp_server.send_message_to_claude(
            instance_name, 
            request.message, 
            request.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation_chain")
async def create_conversation_chain(request: ConversationRequest):
    try:
        result = mcp_server.create_conversation_chain(
            request.instances, 
            request.messages
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instances")
async def list_instances():
    return mcp_server.list_claude_instances()

if __name__ == "__main__":
    print("🚀 Claude Desktop MCP Server を起動中...")
    print("🌐 アクセスURL: http://localhost:9000")
    print("📋 インスタンス一覧: http://localhost:9000/instances")
    print("❤️ ヘルスチェック: http://localhost:9000/health")
    
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9000")), log_level="info")
