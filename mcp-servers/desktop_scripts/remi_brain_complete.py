"""
Remi Brain Complete - ManaOS全機能統合版
Remi Brain MVP + ManaOS Complete Integration
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import os
import json
import httpx
import asyncio
from datetime import datetime
import base64
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Remi Brain Complete",
    description="レミの脳 - ManaOS全機能統合版",
    version="3.0.0"
)

# サービスURL
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
MANAOS_API_URL = os.getenv("MANAOS_API_URL", "http://127.0.0.1:9405")
REMI_COMPLETE_URL = os.getenv("REMI_COMPLETE_URL", "http://127.0.0.1:9410")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://127.0.0.1:5001")
TTS_API_URL = os.getenv("TTS_API_URL", "http://127.0.0.1:5002")

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

# 状態管理
conversation_state = {
    "mode": "idle",  # idle, listen, talk, think
    "mana_state": "normal",  # normal, focused, busy
    "conversation_history": []
}

active_connections: List[WebSocket] = []


class SpeechInput(BaseModel):
    """音声入力"""
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    source: str = "pixel"


class SpeechOutput(BaseModel):
    """音声出力"""
    text: str
    audio_base64: Optional[str] = None
    emotion: str = "normal"


class XAnalyzeRequest(BaseModel):
    """X解析リクエスト"""
    post_text: str
    image_url: Optional[str] = None


class StateEvent(BaseModel):
    """状態イベント"""
    event_type: str
    data: Dict


async def call_ollama_chat(messages: List[Dict], model: str = None) -> str:
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


async def transcribe_audio(audio_data: bytes) -> str:
    """Whisper APIで音声をテキストに変換"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{WHISPER_API_URL}/whisper/transcribe",
                files={"audio_file": ("audio.wav", audio_data, "audio/wav")},
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json().get("text", "")
            return ""
    except Exception as e:
        logger.warning(f"Whisper API error: {e}")
        return ""


async def generate_speech(text: str, emotion: str = "normal") -> Optional[bytes]:
    """TTS APIでテキストを音声に変換"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TTS_API_URL}/tts/generate",
                json={"text": text, "emotion": emotion},
                timeout=30.0
            )
            if response.status_code == 200:
                return response.content
            return None
    except Exception as e:
        logger.warning(f"TTS API error: {e}")
        return None


async def execute_manaos_command(command: str, parameters: Dict = None) -> Dict:
    """ManaOSコマンド実行（Remi Complete Integration経由）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{REMI_COMPLETE_URL}/remi/manaos/execute",
                json={"command": command, "parameters": parameters or {}},
                timeout=60.0
            )
            if response.status_code == 200:
                return response.json()
            return {"error": "ManaOS command failed"}
    except Exception as e:
        logger.error(f"ManaOS command error: {e}")
        return {"error": str(e)}


async def get_remi_response(user_input: str, context: Dict = None) -> str:
    """レミの返事を生成"""
    messages = [{"role": "system", "content": REMI_PERSONALITY_PROMPT}]
    
    if context:
        context_text = f"\n【コンテキスト】\n{json.dumps(context, ensure_ascii=False)}\n"
        messages.append({"role": "system", "content": context_text})
    
    history = conversation_state["conversation_history"]
    for msg in history[-5:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    messages.append({"role": "user", "content": user_input})
    
    response = await call_ollama_chat(messages)
    return response if response else "うーん、ちょっと考え中..."


async def analyze_manaos_command(text: str) -> tuple:
    """テキストからManaOSコマンドを抽出"""
    text_lower = text.lower()
    
    if "タスク" in text_lower or "task" in text_lower:
        return "タスク実行", {}
    elif "画像" in text_lower or "image" in text_lower or "生成" in text_lower:
        return "画像生成", {}
    elif "ocr" in text_lower or "文字認識" in text_lower:
        return "OCR実行", {}
    elif "ワークフロー" in text_lower or "workflow" in text_lower:
        return "ワークフロー実行", {}
    elif "状態" in text_lower or "status" in text_lower:
        return "状態確認", {}
    elif "記憶" in text_lower or "memory" in text_lower:
        return "記憶操作", {}
    
    return None, {}


@app.post("/remi/speech/input")
async def speech_input(input_data: SpeechInput):
    """音声入力処理"""
    try:
        # 音声データがある場合はテキストに変換
        if input_data.audio_base64:
            audio_data = base64.b64decode(input_data.audio_base64)
            text = await transcribe_audio(audio_data)
        else:
            text = input_data.text or ""
        
        if not text:
            raise HTTPException(status_code=400, detail="No text or audio provided")
        
        # ManaOSコマンドをチェック
        manaos_command, params = await analyze_manaos_command(text)
        
        if manaos_command:
            # ManaOSコマンド実行
            result = await execute_manaos_command(manaos_command, params)
            response_text = await get_remi_response(
                f"{text}（ManaOSコマンド: {manaos_command}を実行したよ）",
                {"type": "manaos", "command": manaos_command, "result": result}
            )
        else:
            # 通常の会話
            response_text = await get_remi_response(text)
        
        # 音声生成
        audio_data = await generate_speech(response_text)
        audio_base64 = base64.b64encode(audio_data).decode() if audio_data else None
        
        # 状態更新
        conversation_state["mode"] = "talk"
        conversation_state["conversation_history"].append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now().isoformat()
        })
        conversation_state["conversation_history"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        # WebSocketでブロードキャスト
        await broadcast_message({
            "event_type": "remi.speech.output",
            "data": {
                "text": response_text,
                "audio_base64": audio_base64
            }
        })
        
        await broadcast_message({
            "event_type": "remi.state.update",
            "data": conversation_state
        })
        
        return {
            "success": True,
            "text": response_text,
            "audio_base64": audio_base64,
            "state": conversation_state,
            "manaos_command": manaos_command
        }
        
    except Exception as e:
        logger.error(f"Speech input error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/x/analyze")
async def x_analyze(request: XAnalyzeRequest):
    """Xポスト解析"""
    try:
        post_text = request.post_text
        
        # レミの解析
        analysis_prompt = f"""以下のXポストを解析して、要約・論点・返信案を出してね。

ポスト: {post_text}

形式:
- 要約: [1-2文で要約]
- 論点: [重要な論点を1-2文で]
- 返信案: [返信の提案を1-2文で]
"""
        
        analysis = await get_remi_response(analysis_prompt, {"type": "x_analysis"})
        
        # 画像がある場合はVLMで解析
        if request.image_url:
            vlm_prompt = f"この画像について説明して: {request.image_url}"
            image_description = await call_ollama_chat([
                {"role": "user", "content": vlm_prompt}
            ], model="llava:latest")
            analysis += f"\n\n画像の説明: {image_description}"
        
        return {
            "success": True,
            "summary": analysis.split("要約:")[1].split("論点:")[0].strip() if "要約:" in analysis else analysis,
            "point": analysis.split("論点:")[1].split("返信案:")[0].strip() if "論点:" in analysis else "",
            "reply_suggestion": analysis.split("返信案:")[1].strip() if "返信案:" in analysis else "",
            "full_analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"X analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remi/state")
async def get_state():
    """状態取得"""
    return {
        "success": True,
        "state": conversation_state
    }


@app.post("/remi/event")
async def post_event(event: StateEvent):
    """状態イベント送信"""
    try:
        if event.event_type == "remi.mode.change":
            conversation_state["mode"] = event.data.get("mode", "idle")
        elif event.event_type == "remi.mana_state.change":
            conversation_state["mana_state"] = event.data.get("mana_state", "normal")
        
        await broadcast_message({
            "event_type": "remi.state.update",
            "data": conversation_state
        })
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/remi")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocketエンドポイント"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def broadcast_message(message: Dict):
    """全接続済みWebSocketクライアントにメッセージをブロードキャスト"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket client: {e}")


@app.get("/remi/manaos/capabilities")
async def get_manaos_capabilities():
    """ManaOS機能一覧取得"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{REMI_COMPLETE_URL}/remi/manaos/capabilities", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            # フォールバック: 直接機能一覧を返す
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
    except Exception as e:
        logger.error(f"Get capabilities error: {e}")
        return {
            "success": True,
            "capabilities": [
                {"name": "タスク実行", "command": "タスク実行"},
                {"name": "画像生成", "command": "画像生成"},
                {"name": "OCR実行", "command": "OCR実行"},
                {"name": "ワークフロー実行", "command": "ワークフロー実行"},
                {"name": "状態確認", "command": "状態確認"},
                {"name": "記憶操作", "command": "記憶操作"}
            ],
            "timestamp": datetime.now().isoformat()
        }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    ollama_status = False
    manaos_status = False
    whisper_status = False
    tts_status = False
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            ollama_status = response.status_code == 200
    except:
        pass
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{REMI_COMPLETE_URL}/health", timeout=5.0)
            manaos_status = response.status_code == 200
    except:
        pass
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{WHISPER_API_URL}/health", timeout=5.0)
            whisper_status = response.status_code == 200
    except:
        pass
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{TTS_API_URL}/health", timeout=5.0)
            tts_status = response.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy",
        "services": {
            "ollama": ollama_status,
            "manaos": manaos_status,
            "whisper": whisper_status,
            "tts": tts_status
        },
        "connections": len(active_connections)
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_BRAIN_PORT", "9407"))
    host = os.getenv("REMI_BRAIN_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi Brain Complete on {host}:{port}")
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    logger.info(f"ManaOS Complete URL: {REMI_COMPLETE_URL}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

