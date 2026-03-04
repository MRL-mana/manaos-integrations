"""
Remi Pixel Enhanced - Pixel 7専用強化版
PWAパネル + 音声機能 + 表情アニメーション + ADB統合
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import json
import httpx
import asyncio
from datetime import datetime
import base64
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Remi Pixel Enhanced",
    description="レミのPixel 7専用強化版",
    version="2.0.0"
)

# サービスURL
REMI_BRAIN_URL = os.getenv("REMI_BRAIN_URL", "http://127.0.0.1:9407")
ADB_PATH = os.getenv("ADB_PATH", "adb")

# Pixel 7接続状態
pixel_connected = False
pixel_device_id = None

active_connections: List[WebSocket] = []


class PixelCommand(BaseModel):
    """Pixel 7コマンド"""
    command: str
    parameters: Optional[Dict] = None


async def check_pixel_connection() -> bool:
    """Pixel 7接続確認"""
    try:
        result = subprocess.run(
            [ADB_PATH, "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        devices = result.stdout.strip().split('\n')[1:]
        connected_devices = [d for d in devices if 'device' in d]
        return len(connected_devices) > 0
    except Exception as e:
        logger.error(f"ADB check error: {e}")
        return False


async def send_pixel_notification(title: str, message: str):
    """Pixel 7に通知を送信"""
    try:
        if not await check_pixel_connection():
            return {"success": False, "error": "Pixel 7 not connected"}
        
        # ADB経由で通知送信
        cmd = [
            ADB_PATH, "shell", "am", "broadcast",
            "-a", "com.remi.NOTIFICATION",
            "--es", "title", title,
            "--es", "message", message
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return {"success": True, "output": result.stdout}
    except Exception as e:
        logger.error(f"Notification error: {e}")
        return {"success": False, "error": str(e)}


async def get_pixel_battery():
    """Pixel 7のバッテリー情報取得"""
    try:
        if not await check_pixel_connection():
            return {"success": False, "error": "Pixel 7 not connected"}
        
        result = subprocess.run(
            [ADB_PATH, "shell", "dumpsys", "battery"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        battery_info = {}
        for line in result.stdout.split('\n'):
            if 'level' in line.lower():
                battery_info['level'] = int(line.split(':')[1].strip())
            if 'status' in line.lower():
                battery_info['status'] = line.split(':')[1].strip()
        
        return {"success": True, "battery": battery_info}
    except Exception as e:
        logger.error(f"Battery check error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/remi/pixel/panel")
async def pixel_panel():
    """Pixel 7用PWAパネル（強化版）"""
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#4a9eff">
    <title>Remi Companion</title>
    <link rel="manifest" href="/remi/pixel/manifest.json">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            color: #fff;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .remi-container {
            text-align: center;
            padding: 20px;
        }
        .remi-face {
            font-size: 120px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .remi-face.idle { transform: scale(1); }
        .remi-face.listen { 
            animation: listen 1s ease-in-out infinite;
        }
        .remi-face.talk { 
            animation: talk 0.5s ease-in-out infinite;
        }
        .remi-face.think { 
            animation: think 2s ease-in-out infinite;
        }
        @keyframes listen {
            0%, 100% { transform: scale(1) rotate(0deg); }
            50% { transform: scale(1.1) rotate(5deg); }
        }
        @keyframes talk {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
        @keyframes think {
            0%, 100% { transform: rotate(0deg); }
            25% { transform: rotate(-10deg); }
            75% { transform: rotate(10deg); }
        }
        .status {
            color: #888;
            margin-bottom: 30px;
            font-size: 18px;
        }
        .text-input-container {
            width: 100%;
            max-width: 400px;
            margin-bottom: 20px;
        }
        .text-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #4a9eff;
            border-radius: 25px;
            background: rgba(42, 42, 42, 0.8);
            color: #fff;
            font-size: 16px;
            outline: none;
            transition: all 0.3s;
        }
        .text-input:focus {
            border-color: #6ab4ff;
            box-shadow: 0 0 20px rgba(74, 158, 255, 0.5);
        }
        .text-input::placeholder {
            color: #888;
        }
        .controls {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }
        button {
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            background: #4a9eff;
            color: #fff;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(74, 158, 255, 0.3);
        }
        button:active { 
            transform: scale(0.95);
            box-shadow: 0 2px 8px rgba(74, 158, 255, 0.5);
        }
        button.recording {
            background: #ff4444;
            animation: pulse 1s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .response {
            margin-top: 30px;
            padding: 20px;
            background: rgba(42, 42, 42, 0.8);
            border-radius: 15px;
            max-width: 400px;
            text-align: center;
            backdrop-filter: blur(10px);
            display: none;
        }
        .response.show {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .battery-info {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 10px;
            background: rgba(42, 42, 42, 0.8);
            border-radius: 10px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="battery-info" id="batteryInfo">🔋 確認中...</div>
    <div class="remi-container">
        <div class="remi-face idle" id="face">😊</div>
        <div class="status" id="status">待機中</div>
        <div class="text-input-container">
            <input type="text" class="text-input" id="textInput" placeholder="レミに話しかけてね..." />
        </div>
        <div class="controls">
            <button id="sendBtn">送信</button>
            <button id="talkBtn">話す</button>
            <button id="muteBtn">ミュート</button>
            <button id="manaosBtn">ManaOS</button>
        </div>
        <div class="response" id="response"></div>
    </div>
    
    <script>
        const REMI_BRAIN_URL = '""" + REMI_BRAIN_URL + """';
        const ws = new WebSocket(`ws://${window.location.hostname}:9407/ws/remi`);
        const face = document.getElementById('face');
        const status = document.getElementById('status');
        const response = document.getElementById('response');
        const textInput = document.getElementById('textInput');
        const sendBtn = document.getElementById('sendBtn');
        const talkBtn = document.getElementById('talkBtn');
        const muteBtn = document.getElementById('muteBtn');
        const manaosBtn = document.getElementById('manaosBtn');
        const batteryInfo = document.getElementById('batteryInfo');
        
        let isRecording = false;
        let mediaRecorder;
        let audioContext;
        
        const expressions = {
            idle: { emoji: '😊', class: 'idle' },
            listen: { emoji: '👂', class: 'listen' },
            talk: { emoji: '💬', class: 'talk' },
            think: { emoji: '🤔', class: 'think' },
            happy: { emoji: '😄', class: 'idle' },
            sad: { emoji: '😢', class: 'idle' }
        };
        
        function updateExpression(state) {
            const expr = expressions[state] || expressions.idle;
            face.textContent = expr.emoji;
            face.className = `remi-face ${expr.class}`;
        }
        
        ws.onopen = () => {
            status.textContent = '接続完了';
            updateExpression('idle');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event_type === 'remi.speech.output') {
                updateExpression('talk');
                status.textContent = '話してる...';
                
                if (data.data.audio_base64) {
                    const audio = new Audio('data:audio/wav;base64,' + data.data.audio_base64);
                    audio.play();
                    audio.onended = () => {
                        updateExpression('idle');
                        status.textContent = '待機中';
                    };
                }
                
                response.textContent = data.data.text;
                response.classList.add('show');
                setTimeout(() => response.classList.remove('show'), 5000);
            } else if (data.event_type === 'remi.state.update') {
                const mode = data.data.mode || 'idle';
                updateExpression(mode);
                status.textContent = `モード: ${mode}`;
            }
        };
        
        ws.onerror = (error) => {
            status.textContent = '接続エラー';
            updateExpression('sad');
        };
        
        talkBtn.onclick = async () => {
            if (isRecording) {
                stopRecording();
                return;
            }
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                const chunks = [];
                
                mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const blob = new Blob(chunks, { type: 'audio/wav' });
                    const reader = new FileReader();
                    reader.onloadend = async () => {
                        const base64 = reader.result.split(',')[1];
                        updateExpression('think');
                        status.textContent = '考え中...';
                        
                        const res = await fetch(REMI_BRAIN_URL + '/remi/speech/input', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                audio_base64: base64,
                                source: 'pixel'
                            })
                        });
                        
                        const data = await res.json();
                        if (data.success) {
                            updateExpression('talk');
                        }
                    };
                    reader.readAsDataURL(blob);
                };
                
                mediaRecorder.start();
                isRecording = true;
                talkBtn.textContent = '停止';
                talkBtn.classList.add('recording');
                updateExpression('listen');
                status.textContent = '聞いてる...';
            } catch (error) {
                console.error('Recording error:', error);
                status.textContent = 'マイクエラー';
            }
        };
        
        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                isRecording = false;
                talkBtn.textContent = '話す';
                talkBtn.classList.remove('recording');
            }
        }
        
        sendBtn.onclick = async () => {
            const text = textInput.value.trim();
            if (!text) return;
            
            updateExpression('think');
            status.textContent = '考え中...';
            textInput.value = '';
            
            try {
                const res = await fetch(REMI_BRAIN_URL + '/remi/speech/input', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        source: 'pixel'
                    })
                });
                
                const data = await res.json();
                if (data.success) {
                    response.textContent = data.text;
                    response.classList.add('show');
                    updateExpression('talk');
                    
                    // 音声再生（もしあれば）
                    if (data.audio_base64) {
                        const audio = new Audio('data:audio/wav;base64,' + data.audio_base64);
                        audio.play();
                        audio.onended = () => {
                            updateExpression('idle');
                            status.textContent = '待機中';
                        };
                    } else {
                        setTimeout(() => {
                            updateExpression('idle');
                            status.textContent = '待機中';
                        }, 2000);
                    }
                } else {
                    updateExpression('sad');
                    status.textContent = 'エラー';
                    response.textContent = 'エラーが発生しました';
                    response.classList.add('show');
                }
            } catch (error) {
                console.error('Send error:', error);
                updateExpression('sad');
                status.textContent = 'エラー';
                response.textContent = '接続エラー: ' + error.message;
                response.classList.add('show');
            }
        };
        
        // Enterキーで送信
        textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendBtn.click();
            }
        });
        
        muteBtn.onclick = () => {
            // ミュート機能
            status.textContent = 'ミュート中';
        };
        
        manaosBtn.onclick = async () => {
            updateExpression('think');
            status.textContent = 'ManaOS機能を確認中...';
            
            const res = await fetch(REMI_BRAIN_URL + '/remi/manaos/capabilities');
            const data = await res.json();
            
            if (data.success) {
                const capabilities = data.capabilities.map(c => c.name).join(', ');
                response.textContent = `利用可能な機能: ${capabilities}`;
                response.classList.add('show');
            }
            
            updateExpression('idle');
            status.textContent = '待機中';
        };
        
        // バッテリー情報取得
        async function updateBattery() {
            try {
                const res = await fetch('/remi/pixel/battery');
                const data = await res.json();
                if (data.success) {
                    batteryInfo.textContent = `🔋 ${data.battery.level}%`;
                }
            } catch (error) {
                console.error('Battery check error:', error);
            }
        }
        
        updateBattery();
        setInterval(updateBattery, 60000); // 1分ごと
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/remi/pixel/manifest.json")
async def pixel_manifest():
    """PWAマニフェスト"""
    return {
        "name": "Remi Companion",
        "short_name": "Remi",
        "start_url": "/remi/pixel/panel",
        "display": "standalone",
        "background_color": "#1a1a1a",
        "theme_color": "#4a9eff",
        "icons": [
            {
                "src": "/remi/pixel/icon.png",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }


@app.get("/remi/pixel/battery")
async def get_battery():
    """Pixel 7バッテリー情報取得"""
    return await get_pixel_battery()


@app.post("/remi/pixel/notification")
async def send_notification(command: PixelCommand):
    """Pixel 7に通知送信"""
    title = command.parameters.get("title", "Remi") if command.parameters else "Remi"
    message = command.parameters.get("message", "") if command.parameters else ""
    return await send_pixel_notification(title, message)


@app.get("/remi/pixel/status")
async def pixel_status():
    """Pixel 7接続状態"""
    connected = await check_pixel_connection()
    return {
        "connected": connected,
        "device_id": pixel_device_id if connected else None,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    pixel_ok = await check_pixel_connection()
    return {
        "status": "healthy",
        "pixel_connected": pixel_ok,
        "connections": len(active_connections)
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_PIXEL_PORT", "9408"))
    host = os.getenv("REMI_PIXEL_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi Pixel Enhanced on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

