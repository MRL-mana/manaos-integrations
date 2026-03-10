"""
ManaOS Pixel 7 Hub (簡易版)
Pixel 7をManaOSシステムに統合するためのサービス
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import subprocess
import logging
import os
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ManaOS Pixel 7 Hub", version="1.0.0")

# 設定
SCREENSHOT_DIR = os.getenv("PIXEL7_SCREENSHOT_DIR", "./screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# デバイスID（自動検出）
DEVICE_ID = None


def get_adb_path():
    """ADBのパスを取得"""
    # 環境変数から取得を試みる
    import shutil
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path
    # デフォルトのインストール場所
    default_paths = [
        r"C:\Users\mana4\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe",
        r"C:\platform-tools\adb.exe",
    ]
    for path in default_paths:
        if os.path.exists(path):
            return path
    return "adb"  # PATHに含まれている場合


def get_device_id():
    """デバイスIDを取得"""
    global DEVICE_ID
    if DEVICE_ID:
        return DEVICE_ID
    
    try:
        adb_path = get_adb_path()
        result = subprocess.run(
            [adb_path, "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        for line in result.stdout.split('\n'):
            if 'device' in line and 'unauthorized' not in line and 'offline' not in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    DEVICE_ID = parts[0]
                    return DEVICE_ID
    except Exception as e:
        logger.error(f"Failed to get device ID: {e}")
    
    return None


class NotificationRequest(BaseModel):
    title: str
    text: str


@app.get("/")
async def root():
    return {"service": "ManaOS Pixel 7 Hub", "status": "running"}


@app.get("/health")
async def health():
    device_id = get_device_id()
    return {
        "status": "healthy" if device_id else "degraded",
        "device_connected": device_id is not None,
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/pixel7/info")
async def get_device_info():
    device_id = get_device_id()
    if not device_id:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    try:
        info = {}
        
        adb_path = get_adb_path()
        
        # モデル名
        result = subprocess.run(
            [adb_path, "-s", device_id, "shell", "getprop", "ro.product.model"],
            capture_output=True,
            text=True,
            timeout=5
        )
        info["model"] = result.stdout.strip() if result.returncode == 0 else "unknown"
        
        # Android バージョン
        result = subprocess.run(
            [adb_path, "-s", device_id, "shell", "getprop", "ro.build.version.release"],
            capture_output=True,
            text=True,
            timeout=5
        )
        info["android_version"] = result.stdout.strip() if result.returncode == 0 else "unknown"
        
        # バッテリー情報
        result = subprocess.run(
            [adb_path, "-s", device_id, "shell", "dumpsys", "battery"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'level:' in line:
                    level = int(re.search(r'level:\s*(\d+)', line).group(1))  # type: ignore[union-attr]
                    info["battery_level"] = level
                    break
        
        return {"success": True, "info": info}
    except Exception as e:
        logger.error(f"Failed to get device info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/screenshot")
async def get_screenshot():
    device_id = get_device_id()
    if not device_id:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pixel7_screenshot_{timestamp}.png"
        output_path = os.path.join(SCREENSHOT_DIR, filename)
        
        adb_path = get_adb_path()
        
        # スクリーンショット取得
        remote_path = "/sdcard/screenshot.png"
        subprocess.run(
            [adb_path, "-s", device_id, "shell", "screencap", "-p", remote_path],
            capture_output=True,
            timeout=10
        )
        
        # PCにコピー
        subprocess.run(
            [adb_path, "-s", device_id, "pull", remote_path, output_path],
            capture_output=True,
            timeout=10
        )
        
        # デバイス上のファイルを削除
        subprocess.run(
            [adb_path, "-s", device_id, "shell", "rm", remote_path],
            capture_output=True,
            timeout=5
        )
        
        if os.path.exists(output_path):
            return FileResponse(output_path, media_type="image/png", filename=filename)
        else:
            raise HTTPException(status_code=500, detail="Failed to take screenshot")
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pixel7/notification")
async def send_notification(request: NotificationRequest):
    device_id = get_device_id()
    if not device_id:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    try:
        adb_path = get_adb_path()
        
        # 通知送信（簡易版）
        cmd = f'am broadcast -a android.intent.action.SHOW_ALERT -e title "{request.title}" -e text "{request.text}"'
        result = subprocess.run(
            [adb_path, "-s", device_id, "shell", cmd],
            capture_output=True,
            timeout=5
        )
        
        return {
            "success": result.returncode == 0,
            "message": "Notification sent",
            "title": request.title,
            "text": request.text
        }
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/battery")
async def get_battery():
    device_id = get_device_id()
    if not device_id:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    try:
        adb_path = get_adb_path()
        
        result = subprocess.run(
            [adb_path, "-s", device_id, "shell", "dumpsys", "battery"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        battery_info = {}
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'level:' in line:
                    battery_info["level"] = int(re.search(r'level:\s*(\d+)', line).group(1))  # type: ignore[union-attr]
                elif 'status:' in line:
                    battery_info["status"] = int(re.search(r'status:\s*(\d+)', line).group(1))  # type: ignore[union-attr]
        
        return {"success": True, "battery": battery_info}
    except Exception as e:
        logger.error(f"Failed to get battery info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PIXEL7_HUB_PORT", "9405"))
    host = os.getenv("PIXEL7_HUB_HOST", "0.0.0.0")
    
    logger.info(f"Starting ManaOS Pixel 7 Hub on {host}:{port}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

