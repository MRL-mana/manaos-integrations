#!/usr/bin/env python3
"""
FastAPI + WebSocket 音声ストリームサーバー
リアルタイム音声認識と応答の常時音声反応モード
"""
import asyncio
import base64
import io
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import whisper
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# ログ設定
log_dir = Path("/root/logs/voice_stream")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "voice_stream.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Voice Stream Server",
    version="2.0.0",
    description="リアルタイム音声ストリームサーバー"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 設定 =====
class Config:
    """設定"""
    PORT = int(os.getenv("VOICE_STREAM_PORT", "5014"))
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    CHUNK_DURATION = 1.0  # 秒（音声チャンクの長さ）
    SAMPLE_RATE = 16000  # Whisper推奨サンプルレート
    BUFFER_SIZE = 5.0  # 秒（バッファサイズ）


# ===== Whisperモデルロード =====
logger.info(f"🎤 Whisperモデルロード中... (モデル: {Config.WHISPER_MODEL}, デバイス: {Config.DEVICE})")
try:
    whisper_model = whisper.load_model(Config.WHISPER_MODEL, device=Config.DEVICE)
    logger.info(f"✅ Whisper {Config.WHISPER_MODEL}モデルロード完了")
except Exception as e:
    logger.error(f"❌ Whisperモデルロードエラー: {e}")
    whisper_model = None


# ===== データモデル =====
class TranscriptionRequest(BaseModel):
    """文字起こしリクエスト"""
    audio_data: str  # base64エンコードされた音声データ
    format: str = "wav"  # wav, mp3, etc.
    language: str = "ja"  # 言語コード


class TranscriptionResponse(BaseModel):
    """文字起こしレスポンス"""
    success: bool
    text: Optional[str] = None
    language: Optional[str] = None
    timestamp: str
    error: Optional[str] = None


# ===== 音声処理ユーティリティ =====
class AudioProcessor:
    """音声処理クラス"""

    @staticmethod
    def decode_base64_audio(base64_data: str) -> bytes:
        """base64エンコードされた音声データをデコード"""
        try:
            # data:audio/wav;base64, のプレフィックスを除去
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Base64デコードエラー: {e}")
            raise HTTPException(status_code=400, detail=f"音声データのデコードに失敗: {e}")

    @staticmethod
    def save_audio_to_temp(audio_bytes: bytes, format: str = "wav") -> str:
        """音声データを一時ファイルに保存"""
        suffix = f".{format}" if format else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            return temp_file.name

    @staticmethod
    async def transcribe_audio(audio_path: str, language: str = "ja") -> dict:
        """音声を文字起こし"""
        if whisper_model is None:
            raise HTTPException(status_code=500, detail="Whisperモデルがロードされていません")

        try:
            result = whisper_model.transcribe(
                audio_path,
                language=language,
                task="transcribe"
            )
            return {
                "text": result["text"].strip(),
                "language": result.get("language", language),
                "segments": result.get("segments", [])
            }
        except Exception as e:
            logger.error(f"文字起こしエラー: {e}")
            raise HTTPException(status_code=500, detail=f"文字起こしに失敗: {e}")


# ===== WebSocket接続管理 =====
class ConnectionManager:
    """WebSocket接続管理"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.audio_buffers: dict[str, list] = {}  # 接続IDごとの音声バッファ

    async def connect(self, websocket: WebSocket):
        """接続を追加"""
        await websocket.accept()
        connection_id = id(websocket)
        self.active_connections.append(websocket)
        self.audio_buffers[connection_id] = []
        logger.info(f"✅ WebSocket接続: {connection_id}")
        return connection_id

    def disconnect(self, websocket: WebSocket):
        """接続を削除"""
        connection_id = id(websocket)
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if connection_id in self.audio_buffers:
            del self.audio_buffers[connection_id]
        logger.info(f"❌ WebSocket切断: {connection_id}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """個人メッセージを送信"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """全接続にブロードキャスト"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"ブロードキャストエラー: {e}")
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


# ===== APIエンドポイント =====
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "Voice Stream Server",
        "version": "2.0.0",
        "description": "リアルタイム音声ストリームサーバー",
        "features": [
            "WebSocketリアルタイム音声認識",
            "Whisper音声認識",
            "常時音声反応モード"
        ],
        "endpoints": {
            "/health": "ヘルスチェック",
            "/ws": "WebSocket接続",
            "/transcribe": "音声文字起こし（HTTP）"
        }
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "whisper_model": Config.WHISPER_MODEL,
        "device": Config.DEVICE,
        "model_loaded": whisper_model is not None,
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest):
    """音声を文字起こし（HTTP）"""
    try:
        # 音声データをデコード
        audio_bytes = AudioProcessor.decode_base64_audio(request.audio_data)

        # 一時ファイルに保存
        temp_path = AudioProcessor.save_audio_to_temp(audio_bytes, request.format)

        try:
            # 文字起こし
            result = await AudioProcessor.transcribe_audio(temp_path, request.language)

            return TranscriptionResponse(
                success=True,
                text=result["text"],
                language=result["language"],
                timestamp=datetime.now().isoformat()
            )
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文字起こしエラー: {e}", exc_info=True)
        return TranscriptionResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


# ===== WebSocketエンドポイント =====
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続ハンドラー"""
    connection_id = await manager.connect(websocket)

    try:
        # 接続確認メッセージ
        await manager.send_personal_message({
            "type": "connected",
            "connection_id": connection_id,
            "message": "WebSocket接続が確立されました"
        }, websocket)

        while True:
            # メッセージ受信
            data = await websocket.receive()

            if "text" in data:
                # テキストメッセージ
                try:
                    message = json.loads(data["text"])
                    await handle_text_message(websocket, message, connection_id)
                except json.JSONDecodeError:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "無効なJSON形式"
                    }, websocket)

            elif "bytes" in data:
                # バイナリメッセージ（音声データ）
                await handle_audio_message(websocket, data["bytes"], connection_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket切断: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}", exc_info=True)
        manager.disconnect(websocket)


async def handle_text_message(websocket: WebSocket, message: dict, connection_id: int):
    """テキストメッセージを処理"""
    msg_type = message.get("type")

    if msg_type == "ping":
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)

    elif msg_type == "transcribe":
        # 音声データの文字起こしリクエスト
        audio_data = message.get("audio_data")
        language = message.get("language", "ja")

        if not audio_data:
            await manager.send_personal_message({
                "type": "error",
                "message": "音声データがありません"
            }, websocket)
            return

        try:
            # 音声データをデコード
            audio_bytes = AudioProcessor.decode_base64_audio(audio_data)

            # 一時ファイルに保存
            temp_path = AudioProcessor.save_audio_to_temp(audio_bytes, message.get("format", "wav"))

            try:
                # 文字起こし
                result = await AudioProcessor.transcribe_audio(temp_path, language)

                # 結果を送信
                await manager.send_personal_message({
                    "type": "transcription",
                    "text": result["text"],
                    "language": result["language"],
                    "timestamp": datetime.now().isoformat()
                }, websocket)
            finally:
                # 一時ファイルを削除
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"文字起こしエラー: {e}")
            await manager.send_personal_message({
                "type": "error",
                "message": f"文字起こしに失敗: {str(e)}"
            }, websocket)

    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"未知のメッセージタイプ: {msg_type}"
        }, websocket)


async def handle_audio_message(websocket: WebSocket, audio_bytes: bytes, connection_id: int):
    """音声メッセージを処理"""
    try:
        # 音声バッファに追加
        buffer = manager.audio_buffers.get(connection_id, [])
        buffer.append(audio_bytes)

        # バッファサイズをチェック（簡易実装）
        # 実際の実装では、音声チャンクを適切に処理する必要がある

        # 確認メッセージを送信
        await manager.send_personal_message({
            "type": "audio_received",
            "size": len(audio_bytes),
            "timestamp": datetime.now().isoformat()
        }, websocket)

    except Exception as e:
        logger.error(f"音声メッセージ処理エラー: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": f"音声処理に失敗: {str(e)}"
        }, websocket)


# ===== 起動 =====
@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Voice Stream Server 起動中...")
    logger.info(f"📊 ポート: {Config.PORT}")
    logger.info(f"🎤 Whisperモデル: {Config.WHISPER_MODEL}")
    logger.info(f"💻 デバイス: {Config.DEVICE}")
    logger.info(f"✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Voice Stream Server シャットダウン中...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )

