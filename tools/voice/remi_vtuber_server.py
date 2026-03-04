#!/usr/bin/env python3
"""
VTuberレミV1: Live2D + 口パク + AI音声 + 常駐
"""
import asyncio
import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ログ設定
log_dir = Path("/root/logs/vtuber_remi")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "vtuber_remi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="VTuber Remi V1",
    version="1.0.0",
    description="Live2D + 口パク + AI音声 + 常駐"
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
    PORT = int(os.getenv("VTUBER_REMI_PORT", "5020"))
    TTS_API_URL = os.getenv("TTS_API_URL", "http://localhost:5013")
    VOICE_STREAM_URL = os.getenv("VOICE_STREAM_URL", "ws://localhost:5014/ws")
    TRINITY_API_URL = os.getenv("TRINITY_API_URL", "http://localhost:5015")

    # Live2D設定
    LIVE2D_MODEL_PATH = os.getenv("LIVE2D_MODEL_PATH", "/root/vtuber_remi/models/remi")
    LIVE2D_EXPRESSION_DEFAULT = "default"
    LIVE2D_EXPRESSION_HAPPY = "happy"
    LIVE2D_EXPRESSION_SAD = "sad"
    LIVE2D_EXPRESSION_SURPRISED = "surprised"


# ===== 表情管理 =====
class ExpressionManager:
    """表情管理"""

    def __init__(self):
        self.current_expression = Config.LIVE2D_EXPRESSION_DEFAULT
        self.expression_history: List[Dict] = []

    def set_expression(self, expression: str, duration: float = 1.0):
        """表情を設定"""
        self.current_expression = expression
        self.expression_history.append({
            "expression": expression,
            "timestamp": datetime.now().isoformat(),
            "duration": duration
        })
        logger.info(f"表情変更: {expression}")

    def get_expression(self) -> str:
        """現在の表情を取得"""
        return self.current_expression


expression_manager = ExpressionManager()


# ===== 口パク管理 =====
class LipSyncManager:
    """口パク管理"""

    def __init__(self):
        self.is_speaking = False
        self.current_phoneme: Optional[str] = None

    def start_speaking(self):
        """話し始め"""
        self.is_speaking = True
        logger.info("口パク開始")

    def stop_speaking(self):
        """話し終わり"""
        self.is_speaking = False
        self.current_phoneme = None
        logger.info("口パク終了")

    def update_phoneme(self, phoneme: str):
        """音素を更新"""
        self.current_phoneme = phoneme

    def get_lip_sync_data(self) -> Dict:
        """口パクデータを取得"""
        return {
            "is_speaking": self.is_speaking,
            "phoneme": self.current_phoneme,
            "timestamp": datetime.now().isoformat()
        }


lip_sync_manager = LipSyncManager()


# ===== TTS統合 =====
async def generate_tts(text: str) -> Optional[bytes]:
    """TTSで音声を生成"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.TTS_API_URL}/tts/generate",
                json={"text": text, "language": "ja"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.content
    except Exception as e:
        logger.error(f"TTS生成エラー: {e}")
        return None


# ===== 音声認識統合 =====
async def process_voice_input(audio_data: bytes) -> Optional[str]:
    """音声入力を処理"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.VOICE_STREAM_URL.replace('ws://', 'http://').replace('/ws', '/transcribe')}",
                files={"audio": audio_data},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("text")
    except Exception as e:
        logger.error(f"音声認識エラー: {e}")
        return None


# ===== AI応答生成 =====
async def generate_ai_response(text: str) -> str:
    """AI応答を生成"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.TRINITY_API_URL}/task",
                json={
                    "description": text,
                    "use_langgraph": False
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("result", "了解しました")
    except Exception as e:
        logger.error(f"AI応答生成エラー: {e}")
        return "すみません、よく聞こえませんでした"


# ===== WebSocket接続管理 =====
class ConnectionManager:
    """WebSocket接続管理"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

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
        "name": "VTuber Remi V1",
        "version": "1.0.0",
        "description": "Live2D + 口パク + AI音声 + 常駐",
        "endpoints": {
            "/ui": "VTuber UI",
            "/ws": "WebSocket接続",
            "/speak": "音声合成",
            "/expression": "表情変更"
        }
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "active_connections": len(manager.active_connections),
        "current_expression": expression_manager.get_expression(),
        "is_speaking": lip_sync_manager.is_speaking,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/speak")
async def speak(text: str):
    """音声合成と口パク"""
    # 表情変更（話している時）
    expression_manager.set_expression(Config.LIVE2D_EXPRESSION_HAPPY, duration=len(text) * 0.1)

    # 口パク開始
    lip_sync_manager.start_speaking()
    await manager.broadcast({
        "type": "speak_start",
        "text": text,
        "expression": expression_manager.get_expression()
    })

    # TTS生成
    audio_data = await generate_tts(text)

    if audio_data:
        # 音声データをブロードキャスト
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        await manager.broadcast({
            "type": "audio",
            "data": audio_base64,
            "format": "wav"
        })

    # 口パク終了
    lip_sync_manager.stop_speaking()
    expression_manager.set_expression(Config.LIVE2D_EXPRESSION_DEFAULT)
    await manager.broadcast({
        "type": "speak_end",
        "expression": expression_manager.get_expression()
    })

    return {
        "success": True,
        "text": text,
        "audio_length": len(audio_data) if audio_data else 0
    }


@app.post("/expression")
async def set_expression(expression: str, duration: float = 1.0):
    """表情を変更"""
    expression_manager.set_expression(expression, duration)
    await manager.broadcast({
        "type": "expression",
        "expression": expression,
        "duration": duration
    })
    return {
        "success": True,
        "expression": expression,
        "duration": duration
    }


@app.post("/interact")
async def interact(text: str):
    """対話（音声認識→AI応答→TTS）"""
    # 表情変更（聞いている時）
    expression_manager.set_expression(Config.LIVE2D_EXPRESSION_SURPRISED, duration=2.0)
    await manager.broadcast({
        "type": "listening",
        "expression": expression_manager.get_expression()
    })

    # AI応答生成
    response_text = await generate_ai_response(text)

    # 音声合成
    await speak(response_text)

    return {
        "success": True,
        "input": text,
        "response": response_text
    }


# ===== WebSocketエンドポイント =====
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket接続ハンドラー"""
    await manager.connect(websocket)

    try:
        # 接続確認
        await websocket.send_json({
            "type": "connected",
            "message": "VTuber Remi接続完了",
            "current_expression": expression_manager.get_expression()
        })

        while True:
            # メッセージ受信
            data = await websocket.receive()

            if "text" in data:
                try:
                    message = json.loads(data["text"])
                    await handle_websocket_message(websocket, message)
                except Exception as e:
                    logger.error(f"メッセージ処理エラー: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

            elif "bytes" in data:
                # 音声データ（将来実装）
                await websocket.send_json({
                    "type": "audio_received",
                    "size": len(data["bytes"])
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}", exc_info=True)
        manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, message: dict):
    """WebSocketメッセージを処理"""
    msg_type = message.get("type")

    if msg_type == "speak":
        text = message.get("text", "")
        await speak(text)

    elif msg_type == "expression":
        expression = message.get("expression", Config.LIVE2D_EXPRESSION_DEFAULT)
        duration = message.get("duration", 1.0)
        await set_expression(expression, duration)

    elif msg_type == "interact":
        text = message.get("text", "")
        await interact(text)

    elif msg_type == "ping":
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })


# ===== UI =====
@app.get("/ui", response_class=HTMLResponse)
async def vtuber_ui():
    """VTuber UI"""
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎭 VTuber Remi V1</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 1200px;
            width: 100%;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        h1 { text-align: center; font-size: 2.5em; margin-bottom: 30px; }
        .vtuber-display {
            width: 100%;
            height: 500px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 30px;
            position: relative;
        }
        .live2d-container {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .controls {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        button {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .speak-btn { background: #4285F4; color: white; }
        .expression-btn { background: #34A853; color: white; }
        .interact-btn { background: #EA4335; color: white; }
        button:hover { transform: scale(1.05); }
        input[type="text"] {
            flex: 1;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
        }
        .status {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎭 VTuber Remi V1</h1>

        <div class="vtuber-display">
            <div class="live2d-container">
                <div id="live2d-canvas">Live2Dモデル読み込み中...</div>
            </div>
        </div>

        <div class="controls">
            <input type="text" id="textInput" placeholder="話す内容を入力...">
            <button class="speak-btn" onclick="speak()">💬 話す</button>
            <button class="interact-btn" onclick="interact()">🤖 対話</button>
        </div>

        <div class="controls">
            <button class="expression-btn" onclick="setExpression('happy')">😊 嬉しい</button>
            <button class="expression-btn" onclick="setExpression('sad')">😢 悲しい</button>
            <button class="expression-btn" onclick="setExpression('surprised')">😲 驚き</button>
            <button class="expression-btn" onclick="setExpression('default')">😐 通常</button>
        </div>

        <div class="status" id="status">
            接続中...
        </div>
    </div>

    <script>
        const API_URL = 'http://localhost:5020';
        let ws = null;

        // WebSocket接続
        function connectWebSocket() {
            ws = new WebSocket(`ws://localhost:5020/ws`);

            ws.onopen = () => {
                updateStatus('✅ 接続完了');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };

            ws.onerror = (error) => {
                updateStatus('❌ 接続エラー');
            };

            ws.onclose = () => {
                updateStatus('❌ 接続切断');
                setTimeout(connectWebSocket, 3000);
            };
        }

        function handleWebSocketMessage(data) {
            if (data.type === 'speak_start') {
                updateStatus(`💬 話しています: ${data.text}`);
            } else if (data.type === 'speak_end') {
                updateStatus('✅ 話し終わり');
            } else if (data.type === 'expression') {
                updateStatus(`😊 表情変更: ${data.expression}`);
            } else if (data.type === 'audio') {
                // 音声再生（将来実装）
                updateStatus('🔊 音声再生中...');
            }
        }

        async function speak() {
            const text = document.getElementById('textInput').value;
            if (!text) return;

            try {
                const response = await fetch(`${API_URL}/speak`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                const data = await response.json();
                updateStatus(`✅ 話しました: ${data.text}`);
            } catch (error) {
                updateStatus(`❌ エラー: ${error.message}`);
            }
        }

        async function interact() {
            const text = document.getElementById('textInput').value;
            if (!text) return;

            try {
                const response = await fetch(`${API_URL}/interact`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                const data = await response.json();
                updateStatus(`✅ 対話完了: ${data.response}`);
            } catch (error) {
                updateStatus(`❌ エラー: ${error.message}`);
            }
        }

        async function setExpression(expression) {
            try {
                const response = await fetch(`${API_URL}/expression`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({expression: expression, duration: 1.0})
                });
                const data = await response.json();
                updateStatus(`✅ 表情変更: ${data.expression}`);
            } catch (error) {
                updateStatus(`❌ エラー: ${error.message}`);
            }
        }

        function updateStatus(message) {
            document.getElementById('status').textContent = message;
        }

        // 初期化
        connectWebSocket();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 VTuber Remi V1 起動中...")
    logger.info(f"📊 ポート: {Config.PORT}")
    logger.info("✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 VTuber Remi V1 シャットダウン中...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )

