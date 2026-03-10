"""
Remi ManaOS完全統合
ManaOSの全機能をRemiから使えるようにする
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import json
import httpx
import asyncio
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Remi ManaOS Integration",
    description="レミとManaOSの完全統合",
    version="3.0.0"
)

# ManaOSサービスURL
MANAOS_API_URL = os.getenv("MANAOS_API_URL", "http://127.0.0.1:9405")
TASK_EXECUTOR_URL = os.getenv("TASK_EXECUTOR_URL", "http://127.0.0.1:5176")
COMMAND_HUB_URL = os.getenv("COMMAND_HUB_URL", "http://127.0.0.1:9404")
OCR_API_URL = os.getenv("OCR_API_URL", "http://127.0.0.1:5002")
GALLERY_URL = os.getenv("GALLERY_URL", "http://127.0.0.1:5003")
SCREEN_SHARING_URL = os.getenv("SCREEN_SHARING_URL", "http://127.0.0.1:5008")
N8N_URL = os.getenv("N8N_URL", "http://127.0.0.1:5678")

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


class ManaOSCommand(BaseModel):
    """ManaOSコマンド"""
    command: str
    service: Optional[str] = None
    parameters: Optional[Dict] = None


class TaskRequest(BaseModel):
    """タスクリクエスト"""
    task_name: str
    parameters: Optional[Dict] = None
    timeout: Optional[int] = 300


async def call_manaos_api(endpoint: str, method: str = "GET", data: Dict = None):  # type: ignore
    """ManaOS API呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(f"{MANAOS_API_URL}{endpoint}")
            elif method == "POST":
                response = await client.post(f"{MANAOS_API_URL}{endpoint}", json=data)
            else:
                response = await client.request(method, f"{MANAOS_API_URL}{endpoint}", json=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ManaOS API error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"ManaOS API call error: {e}")
        return None


async def call_ollama_chat(messages: List[Dict], model: str = "qwen2.5:7b") -> str:
    """Ollama Chat API呼び出し"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"http://127.0.0.1:11434/api/chat",
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


@app.post("/remi/manaos/command")
async def manaos_command(command: ManaOSCommand):
    """ManaOSコマンド実行"""
    try:
        # コマンドを解析
        cmd = command.command.lower()
        
        # サービス別の処理
        if cmd.startswith("タスク") or cmd.startswith("task"):
            # タスク実行
            result = await execute_task(command.parameters or {})
            response = await get_remi_response(
                f"ManaOSのタスクを実行したよ。結果: {json.dumps(result, ensure_ascii=False)}",
                {"type": "manaos_task", "result": result}
            )
            
        elif cmd.startswith("画像") or cmd.startswith("image"):
            # 画像生成
            result = await generate_image(command.parameters or {})
            response = await get_remi_response(
                f"画像を生成したよ。結果: {json.dumps(result, ensure_ascii=False)}",
                {"type": "manaos_image", "result": result}
            )
            
        elif cmd.startswith("ocr") or cmd.startswith("文字認識"):
            # OCR実行
            result = await run_ocr(command.parameters or {})
            response = await get_remi_response(
                f"OCRを実行したよ。結果: {json.dumps(result, ensure_ascii=False)}",
                {"type": "manaos_ocr", "result": result}
            )
            
        elif cmd.startswith("ワークフロー") or cmd.startswith("workflow"):
            # n8nワークフロー実行
            result = await run_workflow(command.parameters or {})
            response = await get_remi_response(
                f"ワークフローを実行したよ。結果: {json.dumps(result, ensure_ascii=False)}",
                {"type": "manaos_workflow", "result": result}
            )
            
        elif cmd.startswith("状態") or cmd.startswith("status"):
            # ManaOS状態取得
            result = await get_manaos_status()
            response = await get_remi_response(
                f"ManaOSの状態を確認したよ。結果: {json.dumps(result, ensure_ascii=False)}",
                {"type": "manaos_status", "result": result}
            )
            
        else:
            # 汎用コマンド
            response = await get_remi_response(
                f"ManaOSコマンド「{command.command}」を実行するね。",
                {"type": "manaos_command", "command": command.command}
            )
        
        return {
            "success": True,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"ManaOS command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_task(parameters: Dict):
    """タスク実行"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{TASK_EXECUTOR_URL}/execute",
                json=parameters
            )
            return response.json() if response.status_code == 200 else {"error": "Task execution failed"}
    except Exception as e:
        logger.error(f"Task execution error: {e}")
        return {"error": str(e)}


async def generate_image(parameters: Dict):
    """画像生成"""
    try:
        result = await call_manaos_api("/api/image/generate", "POST", parameters)
        return result if result else {"error": "Image generation failed"}
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        return {"error": str(e)}


async def run_ocr(parameters: Dict):
    """OCR実行"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OCR_API_URL}/ocr/recognize",
                json=parameters
            )
            return response.json() if response.status_code == 200 else {"error": "OCR failed"}
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return {"error": str(e)}


async def run_workflow(parameters: Dict):
    """n8nワークフロー実行"""
    try:
        workflow_name = parameters.get("workflow", "daily_report")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{N8N_URL}/webhook/{workflow_name}",
                json=parameters
            )
            return response.json() if response.status_code == 200 else {"error": "Workflow execution failed"}
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        return {"error": str(e)}


async def get_manaos_status():
    """ManaOS状態取得"""
    try:
        status = {}
        
        # 各サービスの状態を確認
        services = {
            "manaos_api": MANAOS_API_URL,
            "task_executor": TASK_EXECUTOR_URL,
            "command_hub": COMMAND_HUB_URL,
            "ocr_api": OCR_API_URL,
            "gallery": GALLERY_URL,
            "screen_sharing": SCREEN_SHARING_URL,
            "n8n": N8N_URL
        }
        
        for name, url in services.items():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    health_response = await client.get(f"{url}/health", timeout=5.0)
                    status[name] = "healthy" if health_response.status_code == 200 else "unhealthy"
            except:
                status[name] = "unavailable"
        
        return status
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {"error": str(e)}


@app.post("/remi/manaos/chat")
async def manaos_chat(text: str, context_type: str = "manaos"):
    """ManaOS機能を使った会話"""
    try:
        # テキストからManaOSコマンドを抽出
        text_lower = text.lower()
        
        # コマンド判定
        if "タスク" in text_lower or "実行" in text_lower:
            # タスク実行
            result = await execute_task({})
            response_text = await get_remi_response(
                f"タスクを実行したよ。{text}",
                {"type": "manaos_task", "result": result}
            )
            
        elif "画像" in text_lower or "生成" in text_lower:
            # 画像生成
            result = await generate_image({})
            response_text = await get_remi_response(
                f"画像を生成したよ。{text}",
                {"type": "manaos_image", "result": result}
            )
            
        elif "状態" in text_lower or "確認" in text_lower:
            # 状態確認
            result = await get_manaos_status()
            response_text = await get_remi_response(
                f"ManaOSの状態を確認したよ。{text}",
                {"type": "manaos_status", "result": result}
            )
            
        else:
            # 通常の会話
            response_text = await get_remi_response(text, {"type": context_type})
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now().isoformat()
        })
        
        conversation_history.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "text": response_text,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"ManaOS chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remi/manaos/services")
async def get_manaos_services():
    """ManaOSサービス一覧取得"""
    try:
        status = await get_manaos_status()
        
        return {
            "success": True,
            "services": status,
            "available_commands": [
                "タスク実行",
                "画像生成",
                "OCR実行",
                "ワークフロー実行",
                "状態確認"
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get services error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "Remi ManaOS Integration",
        "manaos_connected": await check_service(MANAOS_API_URL),
        "timestamp": datetime.now().isoformat()
    }


async def check_service(url: str) -> bool:
    """サービス確認"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 複数のエンドポイントを試す
            endpoints = ["/health", "/", "/api/health"]
            for endpoint in endpoints:
                try:
                    response = await client.get(f"{url}{endpoint}", timeout=5.0)
                    if response.status_code == 200:
                        return True
                except:
                    continue
            return False
    except:
        return False


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_MANAOS_PORT", "9409"))
    host = os.getenv("REMI_MANAOS_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi ManaOS Integration on {host}:{port}")
    logger.info(f"ManaOS API URL: {MANAOS_API_URL}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

