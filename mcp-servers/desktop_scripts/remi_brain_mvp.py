"""
Remi Brain MVP - 最小構成版
母艦でTTS生成 → Pixelで再生
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
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

app = FastAPI(title="Remi Brain MVP", version="1.0.0")

# 設定
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:5001")
TTS_URL = os.getenv("TTS_URL", "http://127.0.0.1:5000")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

# WebSocket接続管理
active_connections: List[WebSocket] = []

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
conversation_state = {
    "mode": "idle",
    "mana_state": "normal",
    "last_interaction": None
}


class SpeechInput(BaseModel):
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    source: str = "pixel"


async def call_ollama_chat(messages: List[Dict], model: str = None) -> str:
    """Ollama Chat API呼び出し"""
    model = model or OLLAMA_MODEL
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            return ""
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return ""


async def transcribe_audio(audio_data: bytes) -> str:
    """Whisper APIで音声→テキスト"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": ("audio.wav", audio_data, "audio/wav")}
            response = await client.post(
                f"{WHISPER_URL}/whisper/transcribe",
                files=files
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("text", "")
            return ""
    except Exception as e:
        logger.error(f"Whisper error: {e}")
        return ""


async def generate_speech(text: str, emotion: str = "normal") -> bytes:
    """TTS APIでテキスト→音声"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TTS_URL}/tts/generate",
                json={"text": text, "emotion": emotion}
            )
            
            if response.status_code == 200:
                return response.content
            return b""
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return b""


async def get_remi_response(user_input: str) -> str:
    """レミの返事を生成"""
    messages = [
        {"role": "system", "content": REMI_PERSONALITY_PROMPT}
    ]
    
    # 会話履歴（直近5件）
    for msg in conversation_history[-5:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    # 現在の入力
    messages.append({"role": "user", "content": user_input})
    
    response = await call_ollama_chat(messages)
    return response if response else "うーん、ちょっと考え中..."


async def broadcast_message(message: dict):
    """全WebSocket接続にメッセージを送信"""
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            disconnected.append(connection)
    
    # 切断された接続を削除
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


@app.post("/remi/speech/input")
async def speech_input(input_data: SpeechInput):
    """音声入力処理"""
    try:
        text = input_data.text
        
        # 音声データが提供された場合、Whisperでテキスト化
        if not text and input_data.audio_base64:
            audio_data = base64.b64decode(input_data.audio_base64)
            text = await transcribe_audio(audio_data)
        
        if not text:
            raise HTTPException(status_code=400, detail="Text or audio required")
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now().isoformat()
        })
        
        # レミの返事を生成
        remi_response = await get_remi_response(text)
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "assistant",
            "content": remi_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # TTS生成
        audio_data = await generate_speech(remi_response)
        
        # WebSocketでブロードキャスト
        await broadcast_message({
            "type": "remi_response",
            "text": remi_response,
            "audio_base64": base64.b64encode(audio_data).decode() if audio_data else None,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "text": remi_response,
            "audio_base64": base64.b64encode(audio_data).decode() if audio_data else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Speech input error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/speech/output")
async def speech_output(text: str, emotion: str = "normal"):
    """音声出力（TTS生成）"""
    try:
        audio_data = await generate_speech(text, emotion)
        
        if audio_data:
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/wav"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
    except Exception as e:
        logger.error(f"Speech output error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/x/analyze")
async def x_analyze(request: dict):
    """Xポスト解析"""
    try:
        post_text = request.get("post_text", "")
        if not post_text:
            raise HTTPException(status_code=400, detail="post_text required")
        
        conversation_state["mode"] = "x_companion"
        
        # 要約
        summary_prompt = f"{REMI_PERSONALITY_PROMPT}\n\n以下のXポストを要約して、レミの口調で「これさ、要するに〇〇って話だね」の形式で返してください。\n\nポスト: {post_text}"
        summary = await get_remi_response(summary_prompt)
        
        # 論点
        point_prompt = f"{REMI_PERSONALITY_PROMPT}\n\n以下のXポストで一番揉めそうな論点を、レミの口調で「ここが一番揉めそう」の形式で返してください。\n\nポスト: {post_text}"
        point = await get_remi_response(point_prompt)
        
        # 返信案
        reply_prompt = f"{REMI_PERSONALITY_PROMPT}\n\n以下のXポストに対する返信案を、マナっぽい言い方で提案してください。レミの口調で「返すならこの言い方が一番マナっぽいと思う」の形式で返してください。\n\nポスト: {post_text}"
        reply = await get_remi_response(reply_prompt)
        
        return {
            "success": True,
            "summary": summary,
            "point": point,
            "reply_suggestion": reply
        }
    except Exception as e:
        logger.error(f"X analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/remi/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # 音声入力
            if data.get("type") == "speech_input":
                text = data.get("text")
                audio_base64 = data.get("audio_base64")
                
                if audio_base64:
                    audio_data = base64.b64decode(audio_base64)
                    text = await transcribe_audio(audio_data)
                
                if text:
                    remi_response = await get_remi_response(text)
                    audio_data = await generate_speech(remi_response)
                    
                    await websocket.send_json({
                        "type": "remi_response",
                        "text": remi_response,
                        "audio_base64": base64.b64encode(audio_data).decode() if audio_data else None
                    })
            
            # 状態更新
            elif data.get("type") == "state_update":
                conversation_state.update(data.get("state", {}))
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.get("/remi/panel")
async def remi_panel():
    """Pixel用PWAパネル"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Remi</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #1a1a1a;
            color: #fff;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .remi-face {
            font-size: 80px;
            margin-bottom: 20px;
            transition: transform 0.3s;
        }
        .remi-face.talking { animation: talk 0.5s infinite; }
        @keyframes talk {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .status {
            color: #888;
            margin-bottom: 30px;
        }
        .controls {
            display: flex;
            gap: 20px;
        }
        button {
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            background: #4a9eff;
            color: #fff;
            font-size: 16px;
            cursor: pointer;
        }
        button:active { background: #3a8eef; }
        .response {
            margin-top: 30px;
            padding: 20px;
            background: #2a2a2a;
            border-radius: 8px;
            max-width: 400px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="remi-face" id="face">😊</div>
    <div class="status" id="status">待機中</div>
    <div class="controls">
        <button id="talkBtn">話す</button>
        <button id="muteBtn">ミュート</button>
    </div>
    <div class="response" id="response" style="display: none;"></div>
    
    <script>
        const ws = new WebSocket(`ws://${window.location.host}/remi/ws`);
        const face = document.getElementById('face');
        const status = document.getElementById('status');
        const response = document.getElementById('response');
        let isRecording = false;
        let mediaRecorder;
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'remi_response') {
                face.textContent = '💬';
                face.classList.add('talking');
                status.textContent = '話してる...';
                
                if (data.audio_base64) {
                    const audio = new Audio('data:audio/wav;base64,' + data.audio_base64);
                    audio.play();
                    audio.onended = () => {
                        face.textContent = '😊';
                        face.classList.remove('talking');
                        status.textContent = '待機中';
                    };
                }
                
                response.textContent = data.text;
                response.style.display = 'block';
            }
        };
        
        document.getElementById('talkBtn').addEventListener('mousedown', async () => {
            isRecording = true;
            status.textContent = '聞いてる...';
            face.textContent = '👂';
            
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            const chunks = [];
            
            mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, { type: 'audio/wav' });
                const reader = new FileReader();
                reader.onload = () => {
                    const base64 = reader.result.split(',')[1];
                    ws.send(JSON.stringify({
                        type: 'speech_input',
                        audio_base64: base64
                    }));
                };
                reader.readAsDataURL(blob);
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
        });
        
        document.getElementById('talkBtn').addEventListener('mouseup', () => {
            if (isRecording && mediaRecorder) {
                mediaRecorder.stop();
                isRecording = false;
            }
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"service": "Remi Brain MVP", "status": "running"}

@app.get("/health")
async def health():
    """ヘルスチェック"""
    try:
        services = {
            "ollama": await check_service(OLLAMA_URL),
            "whisper": await check_service(WHISPER_URL),
            "tts": await check_service(TTS_URL)
        }
    except:
        services = {"ollama": False, "whisper": False, "tts": False}
    
    return {
        "status": "healthy",
        "services": services,
        "connections": len(active_connections)
    }


async def check_service(url: str) -> bool:
    """サービス確認"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(f"{url}/health", timeout=5.0)
            return True
    except:
        return False


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_BRAIN_PORT", "9407"))
    host = os.getenv("REMI_BRAIN_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi Brain MVP on {host}:{port}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

