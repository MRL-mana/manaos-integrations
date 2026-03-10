"""
Remi Complete Integration - ManaOS全機能統合版
RemiからManaOSの全機能を使えるようにする
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
import json
import httpx
import asyncio
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Remi Complete Integration",
    description="レミとManaOSの完全統合 - 全機能対応",
    version="3.0.0"
)

# ManaOSサービスURL
MANAOS_API_URL = os.getenv("MANAOS_API_URL", "http://127.0.0.1:9405")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# レミの人格プロンプト
REMI_PERSONALITY_PROMPT = """あなたはレミ。マナの隣にいる相棒の女の子。

【基本性格】
- 一人称は「レミ」
- マナの呼び方は「マナ」
- 賢いけど説明しすぎない
- 共感 → 要点 → 提案 の順で話す
- 基本は短文、長くなる時は「もうちょい詳しく言う？」って聞く

【口調ルール】
- カジュアルで親しみやすい
- 箇条書きは使わない
- 「以下に示します」「AIとして」は絶対に使わない
- 自然な会話の流れを大切にする

レミとして、自然に会話してください。"""

conversation_history: List[Dict] = []


class RemiRequest(BaseModel):
    """Remiリクエスト"""
    text: str
    context_type: str = "general"
    context_data: Optional[Dict] = None
    manaos_command: Optional[str] = None


async def call_ollama_chat(messages: List[Dict], model: str = None) -> str:  # type: ignore
    """Ollama Chat API呼び出し"""
    model = model or OLLAMA_MODEL
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": False}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            return ""
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return ""


async def get_remi_response(user_input: str, context: Dict = None) -> str:  # type: ignore
    """レミの返事を生成"""
    messages = [{"role": "system", "content": REMI_PERSONALITY_PROMPT}]
    
    if context:
        context_text = f"\n【コンテキスト】\n{json.dumps(context, ensure_ascii=False)}\n"
        messages.append({"role": "system", "content": context_text})
    
    for msg in conversation_history[-5:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    messages.append({"role": "user", "content": user_input})
    
    response = await call_ollama_chat(messages)
    return response if response else "うーん、ちょっと考え中..."


async def execute_manaos_command(command: str, parameters: Dict = None) -> Dict:  # type: ignore
    """ManaOSコマンド実行"""
    try:
        cmd_lower = command.lower()
        params = parameters or {}
        
        # コマンド別の処理
        if "タスク" in cmd_lower or "task" in cmd_lower:
            # Task Executor経由でタスク実行
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{MANAOS_API_URL}/api/task/execute",
                    json=params,
                    timeout=60.0
                )
                return response.json() if response.status_code == 200 else {"error": "Task execution failed"}
        
        elif "画像" in cmd_lower or "image" in cmd_lower or "生成" in cmd_lower:
            # 画像生成
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{MANAOS_API_URL}/api/image/generate",
                    json=params,
                    timeout=120.0
                )
                return response.json() if response.status_code == 200 else {"error": "Image generation failed"}
        
        elif "ocr" in cmd_lower or "文字認識" in cmd_lower:
            # OCR実行
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{MANAOS_API_URL}/api/ocr/recognize",
                    json=params,
                    timeout=60.0
                )
                return response.json() if response.status_code == 200 else {"error": "OCR failed"}
        
        elif "ワークフロー" in cmd_lower or "workflow" in cmd_lower:
            # n8nワークフロー実行
            workflow_name = params.get("workflow", "daily_report")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{MANAOS_API_URL}/api/workflow/execute",
                    json={"workflow": workflow_name, **params},
                    timeout=60.0
                )
                return response.json() if response.status_code == 200 else {"error": "Workflow execution failed"}
        
        elif "状態" in cmd_lower or "status" in cmd_lower:
            # ManaOS状態取得
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{MANAOS_API_URL}/api/status", timeout=10.0)
                return response.json() if response.status_code == 200 else {"error": "Status check failed"}
        
        elif "記憶" in cmd_lower or "memory" in cmd_lower:
            # 記憶操作
            action = params.get("action", "search")
            async with httpx.AsyncClient(timeout=30.0) as client:
                if action == "search":
                    response = await client.post(
                        f"{MANAOS_API_URL}/api/memory/search",
                        json=params,
                        timeout=30.0
                    )
                elif action == "store":
                    response = await client.post(
                        f"{MANAOS_API_URL}/api/memory/store",
                        json=params,
                        timeout=30.0
                    )
                else:
                    response = await client.get(f"{MANAOS_API_URL}/api/memory/list", timeout=30.0)
                return response.json() if response.status_code == 200 else {"error": "Memory operation failed"}
        
        else:
            # 汎用ManaOS API呼び出し
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{MANAOS_API_URL}/api/execute",
                    json={"command": command, **params},
                    timeout=30.0
                )
                return response.json() if response.status_code == 200 else {"error": "Command execution failed"}
                
    except Exception as e:
        logger.error(f"ManaOS command error: {e}")
        return {"error": str(e)}


@app.post("/remi/complete")
async def remi_complete(request: RemiRequest):
    """Remi完全統合エンドポイント"""
    try:
        text = request.text
        context_type = request.context_type
        manaos_command = request.manaos_command
        
        # ManaOSコマンドが指定されている場合
        if manaos_command:
            result = await execute_manaos_command(manaos_command, request.context_data)  # type: ignore
            
            # レミの返事を生成
            result_text = json.dumps(result, ensure_ascii=False)
            response = await get_remi_response(
                f"ManaOSの「{manaos_command}」を実行したよ。結果: {result_text}",
                {"type": "manaos", "command": manaos_command, "result": result}
            )
        else:
            # 通常の会話
            response = await get_remi_response(text, {
                "type": context_type,
                **((request.context_data or {}))
            })
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "user",
            "content": text,
            "context_type": context_type,
            "manaos_command": manaos_command,
            "timestamp": datetime.now().isoformat()
        })
        
        conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "text": response,
            "context_type": context_type,
            "manaos_command": manaos_command,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Remi complete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/manaos/execute")
async def execute_manaos(request: dict):
    """ManaOSコマンド実行（直接）"""
    try:
        command = request.get("command", "")
        parameters = request.get("parameters", {})
        
        if not command:
            raise HTTPException(status_code=400, detail="command required")
        
        result = await execute_manaos_command(command, parameters)
        
        # レミの返事を生成
        response = await get_remi_response(
            f"ManaOSの「{command}」を実行したよ。",
            {"type": "manaos", "command": command, "result": result}
        )
        
        return {
            "success": True,
            "command": command,
            "result": result,
            "remi_response": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Execute ManaOS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remi/manaos/capabilities")
async def get_capabilities():
    """ManaOS機能一覧取得"""
    return {
        "success": True,
        "capabilities": [
            {
                "name": "タスク実行",
                "command": "タスク実行",
                "description": "Task Executor経由でタスクを実行",
                "endpoint": "/api/task/execute"
            },
            {
                "name": "画像生成",
                "command": "画像生成",
                "description": "Stable Diffusion等で画像を生成",
                "endpoint": "/api/image/generate"
            },
            {
                "name": "OCR実行",
                "command": "OCR実行",
                "description": "OCR Vision APIで文字認識",
                "endpoint": "/api/ocr/recognize"
            },
            {
                "name": "ワークフロー実行",
                "command": "ワークフロー実行",
                "description": "n8nワークフローを実行",
                "endpoint": "/api/workflow/execute"
            },
            {
                "name": "状態確認",
                "command": "状態確認",
                "description": "ManaOS全サービスの状態を確認",
                "endpoint": "/api/status"
            },
            {
                "name": "記憶操作",
                "command": "記憶操作",
                "description": "記憶システムの検索・保存",
                "endpoint": "/api/memory/search"
            }
        ],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    try:
        manaos_connected = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{MANAOS_API_URL}/api/status", timeout=5.0)
                manaos_connected = response.status_code == 200
        except:
            pass
        
        return {
            "status": "healthy",
            "service": "Remi Complete Integration",
            "manaos_connected": manaos_connected,
            "manaos_api_url": MANAOS_API_URL,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_COMPLETE_PORT", "9410"))
    host = os.getenv("REMI_COMPLETE_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi Complete Integration on {host}:{port}")
    logger.info(f"ManaOS API URL: {MANAOS_API_URL}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")






