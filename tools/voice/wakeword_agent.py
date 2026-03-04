#!/usr/bin/env python3
"""
レミ音声エージェント Always-ON
ウェイクワード対応 + 常時音声反応
"""
import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ログ設定
log_dir = Path("/root/logs/voice_always_on")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "wakeword_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Voice Always-ON Agent",
    version="1.0.0",
    description="レミ音声エージェント Always-ON"
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
    PORT = int(os.getenv("VOICE_ALWAYS_ON_PORT", "5019"))
    WAKE_WORD = os.getenv("WAKE_WORD", "レミ")  # ウェイクワード
    VOICE_STREAM_URL = os.getenv("VOICE_STREAM_URL", "ws://localhost:5014/ws")
    TRINITY_API_URL = os.getenv("TRINITY_API_URL", "http://localhost:5015")
    TTS_API_URL = os.getenv("TTS_API_URL", "http://localhost:5013")


# ===== 音声処理 =====
class WakeWordDetector:
    """ウェイクワード検出"""

    def __init__(self, wake_word: str = "レミ"):
        self.wake_word = wake_word
        self.is_listening = False

    def detect(self, text: str) -> bool:
        """ウェイクワードを検出"""
        return self.wake_word in text or self.wake_word.lower() in text.lower()

    def extract_command(self, text: str) -> Optional[str]:
        """ウェイクワード後のコマンドを抽出"""
        if self.wake_word in text:
            return text.split(self.wake_word, 1)[1].strip()
        return None


wake_detector = WakeWordDetector(Config.WAKE_WORD)


# ===== Intent検出 =====
async def detect_intent(text: str) -> dict:
    """意図を検出（Trinity API経由）"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.TRINITY_API_URL}/intent",
                json={"text": text},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Intent検出エラー: {e}")
        return {"intent": "unknown", "confidence": 0.0}


# ===== アクション実行 =====
async def execute_action(intent: dict) -> str:
    """アクションを実行"""
    intent_type = intent.get("intent", "unknown")

    try:
        if intent_type == "create_image":
            # 画像生成
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{Config.TRINITY_API_URL}/task",
                    json={
                        "description": intent.get("text", ""),
                        "use_langgraph": False
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return "画像生成を開始しました"

        elif intent_type == "create_task":
            # タスク作成
            return "タスクを作成しました"

        elif intent_type == "daily_report":
            # 日報生成
            return "日報を生成しました"

        else:
            # デフォルト: Trinity APIに送信
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{Config.TRINITY_API_URL}/task",
                    json={
                        "description": intent.get("text", ""),
                        "use_langgraph": False
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return "処理を開始しました"

    except Exception as e:
        logger.error(f"アクション実行エラー: {e}")
        return f"エラーが発生しました: {str(e)}"


# ===== TTS応答 =====
async def generate_tts_response(text: str) -> bytes:
    """TTSで音声応答を生成"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.TTS_API_URL}/tts/generate_and_play",
                json={"text": text, "language": "ja"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"TTS生成エラー: {e}")
        return b""


# ===== WebSocket接続管理 =====
class ConnectionManager:
    """WebSocket接続管理"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接続を追加"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✅ WebSocket接続: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """接続を削除"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"❌ WebSocket切断: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """個人メッセージを送信"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            self.disconnect(websocket)


manager = ConnectionManager()


# ===== APIエンドポイント =====
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "Voice Always-ON Agent",
        "version": "1.0.0",
        "wake_word": Config.WAKE_WORD,
        "description": "レミ音声エージェント Always-ON"
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "wake_word": Config.WAKE_WORD,
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }


# ===== WebSocketエンドポイント =====
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続ハンドラー"""
    await manager.connect(websocket)

    try:
        # 接続確認
        await manager.send_personal_message({
            "type": "connected",
            "wake_word": Config.WAKE_WORD,
            "message": "レミ音声エージェント接続完了"
        }, websocket)

        while True:
            # メッセージ受信
            data = await websocket.receive()

            if "text" in data:
                try:
                    message = await asyncio.wait_for(
                        asyncio.to_thread(lambda: __import__("json").loads(data["text"])),
                        timeout=5.0
                    )
                    await handle_message(websocket, message)
                except Exception as e:
                    logger.error(f"メッセージ処理エラー: {e}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": str(e)
                    }, websocket)

            elif "bytes" in data:
                # 音声データ（将来実装）
                await manager.send_personal_message({
                    "type": "audio_received",
                    "size": len(data["bytes"])
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}", exc_info=True)
        manager.disconnect(websocket)


async def handle_message(websocket: WebSocket, message: dict):
    """メッセージを処理"""
    msg_type = message.get("type")

    if msg_type == "transcription":
        # 音声認識結果
        text = message.get("text", "")

        # ウェイクワード検出
        if wake_detector.detect(text):
            command = wake_detector.extract_command(text)

            await manager.send_personal_message({
                "type": "wake_word_detected",
                "command": command,
                "message": "ウェイクワード検出"
            }, websocket)

            if command:
                # Intent検出
                intent = await detect_intent(command)

                await manager.send_personal_message({
                    "type": "intent_detected",
                    "intent": intent,
                    "message": "意図を検出しました"
                }, websocket)

                # アクション実行
                result = await execute_action(intent)

                await manager.send_personal_message({
                    "type": "action_completed",
                    "result": result,
                    "message": "アクション実行完了"
                }, websocket)

                # TTS応答（オプション）
                # tts_audio = await generate_tts_response(result)
                # await manager.send_personal_message({
                #     "type": "tts_response",
                #     "audio": tts_audio.hex()
                # }, websocket)

    elif msg_type == "ping":
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Voice Always-ON Agent 起動中...")
    logger.info(f"📊 ポート: {Config.PORT}")
    logger.info(f"🎤 ウェイクワード: {Config.WAKE_WORD}")
    logger.info("✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Voice Always-ON Agent シャットダウン中...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )

