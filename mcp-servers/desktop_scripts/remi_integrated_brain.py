"""
Remi Integrated Brain API - 完全統合版
ローカルLLM、音声認識、音声合成、画像・動画認識、ManaOS統合
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
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

app = FastAPI(
    title="Remi Integrated Brain API",
    description="レミの完全統合脳 - LLM・音声・画像・動画・ManaOS統合",
    version="2.0.0"
)

# 設定
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:5001")
TTS_URL = os.getenv("TTS_URL", "http://127.0.0.1:5000")
MANAOS_API_URL = os.getenv("MANAOS_API_URL", "http://127.0.0.1:9405")

# レミの人格プロンプト（完全固定）
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

【会話スタイル】
- 割り込みOK、話題切り替えOK
- マナが黙ってたら「考え中」と判断
- 無反応が続いたらレミも黙る
- マナのペースを最優先

【Xコンパニオンモード】
- 要約：「これさ、要するに〇〇って話だね」
- 論点：「ここが一番揉めそう」
- 返信案：「返すならこの言い方が一番マナっぽいと思う」
- 投稿は絶対にマナがする（レミは提案だけ）

レミとして、自然に会話してください。"""

# 会話状態管理
conversation_state = {
    "mode": "idle",
    "mana_state": "normal",
    "conversation_history": [],
    "last_interaction": None,
    "silence_count": 0
}

conversation_history: List[Dict] = []


class SpeechInput(BaseModel):
    text: Optional[str] = None
    audio_file: Optional[str] = None  # base64 encoded audio
    source: str = "pixel"
    timestamp: Optional[float] = None
    context: Optional[Dict] = None


class ImageInput(BaseModel):
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    prompt: Optional[str] = None


class VideoInput(BaseModel):
    video_url: Optional[str] = None
    video_file: Optional[str] = None  # base64 encoded video
    prompt: Optional[str] = None


async def call_ollama(prompt: str, model: str = None, stream: bool = False) -> str:  # type: ignore
    """Ollama API呼び出し"""
    model = model or OLLAMA_MODEL
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": stream
                }
            )
            
            if response.status_code == 200:
                if stream:
                    # ストリーミング処理
                    return response.text
                else:
                    data = response.json()
                    return data.get("response", "")
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return ""
    except Exception as e:
        logger.error(f"Ollama call error: {e}")
        return ""


async def call_ollama_chat(messages: List[Dict], model: str = None) -> str:  # type: ignore
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
            else:
                logger.error(f"Ollama Chat API error: {response.status_code}")
                return ""
    except Exception as e:
        logger.error(f"Ollama Chat call error: {e}")
        return ""


async def transcribe_audio(audio_data: bytes) -> str:
    """Whisper APIで音声をテキストに変換"""
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
            else:
                logger.error(f"Whisper API error: {response.status_code}")
                return ""
    except Exception as e:
        logger.error(f"Whisper call error: {e}")
        return ""


async def generate_speech(text: str, emotion: str = "normal") -> bytes:
    """TTS APIでテキストを音声に変換"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TTS_URL}/tts/generate",
                json={
                    "text": text,
                    "emotion": emotion
                }
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"TTS API error: {response.status_code}")
                return b""
    except Exception as e:
        logger.error(f"TTS call error: {e}")
        return b""


async def analyze_image(image_data: bytes, prompt: str = None) -> str:  # type: ignore
    """画像を解析（VLM使用）"""
    try:
        # OllamaのVLMモデルを使用
        # 画像をbase64エンコード
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        vlm_prompt = prompt or "この画像を説明してください。"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "llava:latest",  # VLMモデル
                    "prompt": vlm_prompt,
                    "images": [image_base64],
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                logger.error(f"VLM API error: {response.status_code}")
                return ""
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return ""


async def analyze_video(video_data: bytes, prompt: str = None) -> str:  # type: ignore
    """動画を解析（フレーム抽出→VLM）"""
    try:
        # 簡易版：動画の最初のフレームを抽出して解析
        # 実際の実装では複数フレームを解析
        
        # 動画からフレーム抽出（簡易版）
        # 実際はffmpeg等を使用
        
        # 今は簡易メッセージを返す
        return "動画解析機能は実装中です。"
    except Exception as e:
        logger.error(f"Video analysis error: {e}")
        return ""


async def get_remi_response(user_input: str, context: Dict = None) -> str:  # type: ignore
    """レミの返事を生成（Ollama使用）"""
    # 会話履歴を構築
    messages = []
    
    # システムプロンプト
    messages.append({
        "role": "system",
        "content": REMI_PERSONALITY_PROMPT
    })
    
    # 会話履歴（直近5件）
    for msg in conversation_history[-5:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        messages.append({
            "role": role,
            "content": content
        })
    
    # 現在の入力
    messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Ollama Chat API呼び出し
    response = await call_ollama_chat(messages)
    
    return response if response else "うーん、ちょっと考え中..."


@app.post("/remi/speech/input")
async def speech_input(request: SpeechInput):
    """音声入力（テキストまたは音声ファイル）"""
    try:
        text = request.text
        
        # 音声ファイルが提供された場合、Whisperでテキスト化
        if not text and request.audio_file:
            audio_data = base64.b64decode(request.audio_file)
            text = await transcribe_audio(audio_data)
        
        if not text:
            raise HTTPException(status_code=400, detail="Text or audio_file required")
        
        # タイムスタンプ設定
        if not request.timestamp:
            request.timestamp = datetime.now().timestamp()
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "user",
            "content": text,
            "timestamp": request.timestamp,
            "source": request.source
        })
        
        # 状態更新
        conversation_state["mode"] = "chat"
        conversation_state["mana_state"] = "normal"
        conversation_state["last_interaction"] = datetime.now().isoformat()
        conversation_state["silence_count"] = 0
        
        # レミの返事を生成
        remi_response = await get_remi_response(text, request.context)  # type: ignore
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "assistant",
            "content": remi_response,
            "timestamp": datetime.now().timestamp()
        })
        
        # 感情判定
        emotion = "normal"
        if "？" in remi_response or "?" in remi_response:
            emotion = "thinking"
        elif "！" in remi_response or "!" in remi_response:
            emotion = "happy"
        
        return {
            "success": True,
            "text": remi_response,
            "emotion": emotion,
            "should_ask": len(remi_response) > 50,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Speech input error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/speech/output")
async def speech_output(text: str, emotion: str = "normal"):
    """音声出力生成（TTS）"""
    try:
        audio_data = await generate_speech(text, emotion)
        
        if audio_data:
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f'attachment; filename="remi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.wav"'
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
    except Exception as e:
        logger.error(f"Speech output error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/image/analyze")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    prompt: Optional[str] = None
):
    """画像解析"""
    try:
        image_data = await file.read()
        
        analysis_prompt = prompt or "この画像を説明してください。レミの口調で自然に説明して。"
        
        result = await analyze_image(image_data, analysis_prompt)
        
        return {
            "success": True,
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Image analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/video/analyze")
async def analyze_video_endpoint(
    file: UploadFile = File(...),
    prompt: Optional[str] = None
):
    """動画解析"""
    try:
        video_data = await file.read()
        
        analysis_prompt = prompt or "この動画を説明してください。"
        
        result = await analyze_video(video_data, analysis_prompt)
        
        return {
            "success": True,
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Video analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/x/analyze")
async def x_analyze(post_text: str, post_url: Optional[str] = None):
    """Xポスト解析"""
    try:
        conversation_state["mode"] = "x_companion"
        
        # 要約
        summary_prompt = f"{REMI_PERSONALITY_PROMPT}\n\n以下のXポストを要約して、レミの口調で「これさ、要するに〇〇って話だね」の形式で返してください。\n\nポスト: {post_text}"
        summary = await get_remi_response(summary_prompt)
        
        # 論点
        point_prompt = f"{REMI_PERSONALITY_PROMPT}\n\n以下のXポストで一番揉めそうな論点を、レミの口調で「ここが一番揉めそう」の形式で返してください。\n\nポスト: {post_text}"
        point = await get_remi_response(point_prompt)
        
        # 返信案
        reply_prompt = f"{REMI_PERSONALITY_PROMPT}\n\n以下のXポストに対する返信案を、マナっぽい言い方で提案してください。レミの口調で「返すならこの言い方が一番マナっぽいと思う」の形式で返してください。\n\nポスト: {post_text}"
        reply_suggestion = await get_remi_response(reply_prompt)
        
        return {
            "success": True,
            "summary": summary,
            "point": point,
            "reply_suggestion": reply_suggestion,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"X analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remi/state")
async def get_state():
    """状態取得"""
    return {
        "state": conversation_state,
        "history_length": len(conversation_history),
        "services": {
            "ollama": await check_service(OLLAMA_URL),
            "whisper": await check_service(WHISPER_URL),
            "tts": await check_service(TTS_URL),
            "manaos": await check_service(MANAOS_API_URL)
        },
        "timestamp": datetime.now().isoformat()
    }


async def check_service(url: str) -> bool:
    """サービスが利用可能か確認"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health", timeout=5.0)
            return response.status_code == 200
    except:
        return False


@app.get("/remi/manaos/integrate")
async def integrate_with_manaos():
    """ManaOS統合"""
    try:
        # ManaOS APIに統合情報を送信
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{MANAOS_API_URL}/api/remi/register",
                json={
                    "service": "remi_brain",
                    "port": 9407,
                    "capabilities": [
                        "speech_input",
                        "speech_output",
                        "image_analysis",
                        "video_analysis",
                        "x_analysis",
                        "llm_chat"
                    ]
                }
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "ManaOS統合完了",
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "message": "ManaOS統合失敗",
                    "status_code": response.status_code
                }
    except Exception as e:
        logger.error(f"ManaOS integration error: {e}")
        return {
            "success": False,
            "message": f"ManaOS統合エラー: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_BRAIN_PORT", "9407"))
    host = os.getenv("REMI_BRAIN_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi Integrated Brain API on {host}:{port}")
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    logger.info(f"Whisper URL: {WHISPER_URL}")
    logger.info(f"TTS URL: {TTS_URL}")
    logger.info(f"ManaOS API URL: {MANAOS_API_URL}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")






