"""
ManaOS Pixel 7 Hub
Pixel 7をManaOSシステムに統合するためのサービス
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging
import os
from datetime import datetime
from pixel7_adb_helper import Pixel7ADBHelper

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ManaOS Pixel 7 Hub",
    description="Pixel 7統合サービス",
    version="1.0.0"
)

# ADBヘルパーのインスタンス
adb_helper = Pixel7ADBHelper()

# 設定
SCREENSHOT_DIR = os.getenv("PIXEL7_SCREENSHOT_DIR", "./screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class NotificationRequest(BaseModel):
    """通知リクエスト"""
    title: str
    text: str
    package: Optional[str] = "com.android.systemui"


class CommandRequest(BaseModel):
    """コマンドリクエスト"""
    command: str
    timeout: Optional[int] = 10


@app.on_event("startup")
async def startup_event():
    """起動時の処理"""
    logger.info("ManaOS Pixel 7 Hub starting...")
    
    # ADB確認
    if not adb_helper.check_adb_available():
        logger.warning("ADB is not available. Some features may not work.")
    else:
        logger.info("ADB is available")
        
        # Pixel 7検索
        device_id = adb_helper.find_pixel7()
        if device_id:
            logger.info(f"Pixel 7 found: {device_id}")
        else:
            logger.warning("Pixel 7 not found. Please connect the device.")


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "service": "ManaOS Pixel 7 Hub",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    adb_available = adb_helper.check_adb_available()
    device_id = adb_helper.find_pixel7()
    
    return {
        "status": "healthy" if adb_available else "degraded",
        "adb_available": adb_available,
        "device_connected": device_id is not None,
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/pixel7/status")
async def get_status():
    """デバイス状態を取得"""
    try:
        devices = adb_helper.get_devices()
        device_id = adb_helper.find_pixel7()
        
        return {
            "connected": device_id is not None,
            "device_id": device_id,
            "devices": devices,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/info")
async def get_device_info():
    """デバイス情報を取得"""
    try:
        info = adb_helper.get_device_info()
        if not info:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return {
            "success": True,
            "info": info,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get device info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/screenshot")
async def get_screenshot():
    """スクリーンショットを取得"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pixel7_screenshot_{timestamp}.png"
        output_path = os.path.join(SCREENSHOT_DIR, filename)
        
        screenshot_path = adb_helper.take_screenshot(output_path)
        if not screenshot_path or not os.path.exists(screenshot_path):
            raise HTTPException(status_code=500, detail="Failed to take screenshot")
        
        return FileResponse(
            screenshot_path,
            media_type="image/png",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/logs")
async def get_logs(
    lines: int = Query(100, ge=1, le=1000),
    filter_tag: Optional[str] = None
):
    """ログを取得"""
    try:
        logs = adb_helper.get_logcat(lines=lines, filter_tag=filter_tag)
        if logs is None:
            raise HTTPException(status_code=500, detail="Failed to get logs")
        
        return {
            "success": True,
            "lines": lines,
            "filter_tag": filter_tag,
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pixel7/notification")
async def send_notification(request: NotificationRequest):
    """通知を送信"""
    try:
        success = adb_helper.send_notification(
            title=request.title,
            text=request.text,
            package=request.package
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send notification")
        
        return {
            "success": True,
            "message": "Notification sent",
            "title": request.title,
            "text": request.text,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pixel7/command")
async def execute_command(request: CommandRequest):
    """コマンドを実行"""
    try:
        result = adb_helper.execute_command(request.command)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to execute command")
        
        return {
            "success": True,
            "command": request.command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/battery")
async def get_battery():
    """バッテリー情報を取得"""
    try:
        battery_info = adb_helper.get_battery_info()
        if not battery_info:
            raise HTTPException(status_code=404, detail="Battery info not available")
        
        return {
            "success": True,
            "battery": battery_info,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get battery info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/storage")
async def get_storage():
    """ストレージ情報を取得"""
    try:
        storage_info = adb_helper.get_storage_info()
        if not storage_info:
            raise HTTPException(status_code=404, detail="Storage info not available")
        
        return {
            "success": True,
            "storage": storage_info,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get storage info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PIXEL7_HUB_PORT", "9405"))
    host = os.getenv("PIXEL7_HUB_HOST", "0.0.0.0")
    
    logger.info(f"Starting ManaOS Pixel 7 Hub on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )







