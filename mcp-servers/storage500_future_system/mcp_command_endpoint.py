# MCP定型指令受信エンドポイント
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import datetime
import os
import json
import logging
from typing import Optional, Dict, Any

# 指令処理エンジンをインポート
import sys
sys.path.append(os.path.expanduser("~/mrl-mcp/commands"))
from command_processor import CommandProcessor

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser('~/mrl-mcp/logs/mcp_command_server.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Command Server", version="1.0.0")

# 指令処理エンジンを初期化
command_processor = CommandProcessor()

@app.post("/receive/command")
async def receive_command(request: Request):
    """定型指令を受信・処理"""
    try:
        # リクエストボディを取得
        body = await request.body()
        
        # JSONとしてパース
        try:
            data = json.loads(body.decode('utf-8'))
            text = data.get('text', '')
            source = data.get('source', 'unknown')
            metadata = data.get('metadata', {})
        except json.JSONDecodeError:
            # プレーンテキストとして処理
            text = body.decode('utf-8')
            source = 'unknown'
            metadata = {}
        
        logger.info(f"Received command from {source}: {text}")
        
        # 定型指令を検出
        matches = command_processor.detect_commands(text)
        
        if not matches:
            return {
                "status": "no_command_detected",
                "message": "No command patterns detected in text",
                "text": text,
                "source": source,
                "timestamp": datetime.datetime.now().isoformat()
            }
        
        # 検出された指令を実行
        results = []
        for match in matches:
            result = command_processor.execute_command(match, text)
            results.append({
                "pattern": match.pattern,
                "target": match.target,
                "action": match.action,
                "confidence": match.confidence,
                "result": result
            })
        
        # レスポンスを構築
        response = {
            "status": "commands_executed",
            "text": text,
            "source": source,
            "matches": len(matches),
            "results": results,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        logger.info(f"Executed {len(matches)} commands for text: {text}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy", 
        "source": "command_server", 
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/commands/stats")
async def get_command_stats():
    """指令統計を取得"""
    try:
        stats = command_processor.get_command_stats()
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting command stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/commands/patterns")
async def get_command_patterns():
    """登録されている指令パターンを取得"""
    try:
        patterns = command_processor.patterns
        return {
            "status": "success",
            "patterns": patterns,
            "total_patterns": len(patterns),
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting pattern