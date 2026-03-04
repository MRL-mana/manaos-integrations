"""
Remi Pixel Client - レミの身体（Pixel側）
音声再生・表情表示を担当
"""

import subprocess
import requests
import logging
import os
from typing import Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定
REMI_BRAIN_URL = os.getenv("REMI_BRAIN_URL", "http://127.0.0.1:9407")
DEVICE_ID = None


def get_device_id():
    """デバイスIDを取得"""
    global DEVICE_ID
    if DEVICE_ID:
        return DEVICE_ID
    
    try:
        result = subprocess.run(
            ["adb", "devices"],
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


def set_face_expression(expression: str):
    """
    表情を変更
    idle / listen / talk / think
    """
    device_id = get_device_id()
    if not device_id:
        logger.warning("Device not connected")
        return False
    
    try:
        # 簡易版：通知で表情を表現
        # 実際の実装では専用UIアプリを使用
        expressions = {
            "idle": "😊",
            "listen": "👂",
            "talk": "💬",
            "think": "🤔"
        }
        
        emoji = expressions.get(expression, "😊")
        
        # 通知で表情を表示（簡易版）
        subprocess.run(
            ["adb", "-s", device_id, "shell", "am", "broadcast", "-a", "android.intent.action.SHOW_ALERT",
             "-e", "title", f"Remi {emoji}", "-e", "text", f"Expression: {expression}"],
            capture_output=True,
            timeout=5
        )
        
        logger.info(f"Face expression set to: {expression}")
        return True
    except Exception as e:
        logger.error(f"Failed to set face expression: {e}")
        return False


def speak_text(text: str, emotion: str = "normal"):
    """
    テキストを音声で再生
    """
    device_id = get_device_id()
    if not device_id:
        logger.warning("Device not connected")
        return False
    
    try:
        # 表情をtalkに変更
        set_face_expression("talk")
        
        # TTSで音声生成（簡易版：実際はStyle-Bert-VITS2を使用）
        # 今はadb経由でテキスト読み上げを使用
        # 実際の実装では母艦でTTS生成してPixelに送信
        
        # Androidのテキスト読み上げを使用（簡易版）
        # 実際は母艦で生成した音声ファイルを再生
        subprocess.run(
            ["adb", "-s", device_id, "shell", "am", "broadcast", "-a", "android.intent.action.TTS",
             "-e", "text", text],
            capture_output=True,
            timeout=10
        )
        
        # 実際の実装例（音声ファイルを生成して再生）
        # 1. 母艦でTTS生成
        # 2. 音声ファイルをPixelに転送
        # 3. Pixelで再生
        
        logger.info(f"Remi said: {text}")
        
        # 再生完了後、表情をidleに戻す
        set_face_expression("idle")
        
        # 出力を記録
        try:
            requests.post(
                f"{REMI_BRAIN_URL}/remi/speech/output",
                json={
                    "text": text,
                    "emotion": emotion,
                    "should_ask": False
                },
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to record speech output: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to speak: {e}")
        set_face_expression("idle")
        return False


def process_speech_input(text: str, source: str = "pixel"):
    """
    音声入力を処理してレミの返事を取得・再生
    """
    try:
        # 表情をlistenに変更
        set_face_expression("listen")
        
        # 母艦に送信
        response = requests.post(
            f"{REMI_BRAIN_URL}/remi/speech/input",
            json={
                "text": text,
                "source": source,
                "timestamp": datetime.now().timestamp()
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            remi_text = data.get("text", "")
            emotion = data.get("emotion", "normal")
            
            # レミの返事を再生
            if remi_text:
                speak_text(remi_text, emotion)
            
            return True
        else:
            logger.error(f"Failed to get response: {response.status_code}")
            set_face_expression("idle")
            return False
            
    except Exception as e:
        logger.error(f"Failed to process speech input: {e}")
        set_face_expression("idle")
        return False


def process_x_post(post_text: str, post_url: Optional[str] = None):
    """
    Xポストを処理してレミの反応を取得・再生
    """
    try:
        # 表情をthinkに変更
        set_face_expression("think")
        
        # 母艦に送信
        response = requests.post(
            f"{REMI_BRAIN_URL}/remi/x/analyze",
            json={
                "post_text": post_text,
                "post_url": post_url
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # 要約を再生
            summary = data.get("summary", "")
            if summary:
                speak_text(summary)
            
            # 論点を再生
            point = data.get("point", "")
            if point:
                speak_text(point)
            
            # 返信案を再生
            reply = data.get("reply_suggestion", "")
            if reply:
                speak_text(reply)
            
            return True
        else:
            logger.error(f"Failed to analyze X post: {response.status_code}")
            set_face_expression("idle")
            return False
            
    except Exception as e:
        logger.error(f"Failed to process X post: {e}")
        set_face_expression("idle")
        return False


if __name__ == "__main__":
    # テスト用
    print("Remi Pixel Client - Test Mode")
    print("=" * 60)
    
    device_id = get_device_id()
    if device_id:
        print(f"✅ Device connected: {device_id}")
        
        # テスト：表情変更
        print("\n[Test] Setting face expression...")
        set_face_expression("listen")
        
        # テスト：音声再生
        print("\n[Test] Speaking...")
        speak_text("テストです。レミです。")
        
    else:
        print("❌ Device not connected")
        print("Please connect Pixel 7 and enable USB debugging")






