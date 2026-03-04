#!/usr/bin/env python3
"""
LINE Notify送信サービス
ManaOSの各種イベント・通知をLINEに送信
"""

import requests
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ディレクトリ設定
WORK_DIR = Path("/root/line_notify_system")
LOGS_DIR = WORK_DIR / "logs"
CONFIG_DIR = WORK_DIR / "config"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# LINE Notify設定
LINE_NOTIFY_API = "https://notify-api.line.me/api/notify"

# トークン取得（優先度: 環境変数 > ファイル）
LINE_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN')
if not LINE_TOKEN:
    token_file = CONFIG_DIR / "token.txt"
    if token_file.exists():
        LINE_TOKEN = token_file.read_text().strip()

if not LINE_TOKEN:
    print("⚠️ LINE_NOTIFY_TOKENが設定されていません")
    print("セットアップガイドを参照: /root/line_notify_system/LINE_SETUP_GUIDE.md")


# ログ記録
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    log_file = LOGS_DIR / f"line_notify_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


def send_line_notify(message, image_path=None):
    """
    LINE Notify送信
    
    Args:
        message: メッセージ本文
        image_path: 画像パス（オプション）
    """
    if not LINE_TOKEN:
        log("❌ トークン未設定のため送信スキップ")
        return {"success": False, "error": "トークン未設定"}
    
    try:
        headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
        data = {"message": message}
        files = {}
        
        if image_path and Path(image_path).exists():
            files = {"imageFile": open(image_path, "rb")}
        
        response = requests.post(
            LINE_NOTIFY_API,
            headers=headers,
            data=data,
            files=files,
            timeout=10
        )
        
        if response.status_code == 200:
            log(f"✅ LINE送信成功: {message[:50]}...")
            return {"success": True, "message": "送信完了"}
        else:
            log(f"❌ LINE送信失敗: {response.status_code} - {response.text}")
            return {"success": False, "error": f"HTTPエラー {response.status_code}"}
    
    except Exception as e:
        log(f"❌ LINE送信エラー: {e}")
        return {"success": False, "error": str(e)}


# ===== API エンドポイント =====

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "LINE Notify Service",
        "token_configured": LINE_TOKEN is not None,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/send', methods=['POST'])
def send_message():
    """メッセージ送信"""
    try:
        data = request.json
        message = data.get('message', '')
        image_path = data.get('image_path')
        
        if not message:
            return jsonify({"success": False, "error": "メッセージが空です"}), 400
        
        result = send_line_notify(message, image_path)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 500
    
    except Exception as e:
        log(f"❌ 送信エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/system_status', methods=['POST'])
def send_system_status():
    """システム状態通知"""
    try:
        data = request.json
        
        message = f"""
🤖 ManaOS System Status

📊 CPU: {data.get('cpu', 0):.1f}%
💾 メモリ: {data.get('memory', 0):.1f}%
💿 ディスク: {data.get('disk', 0):.1f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        result = send_line_notify(message.strip())
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/manaos_event', methods=['POST'])
def send_manaos_event():
    """ManaOSイベント通知"""
    try:
        data = request.json
        event_type = data.get('type', 'event')
        title = data.get('title', 'ManaOS Event')
        content = data.get('content', '')
        
        icon_map = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'task': '📋',
            'schedule': '📅',
            'email': '📧',
            'file': '📁'
        }
        
        icon = icon_map.get(event_type, '🤖')
        
        message = f"""
{icon} {title}

{content}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        result = send_line_notify(message.strip())
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/voice_recognition', methods=['POST'])
def send_voice_recognition():
    """音声認識結果通知"""
    try:
        data = request.json
        text = data.get('text', '')
        manaos_result = data.get('manaos_result', {})
        
        message = f"""
🎤 Whisper音声認識

📝 認識結果:
{text}

🤖 ManaOS実行:
{manaos_result.get('success', False) and '✅ 成功' or '❌ 失敗'}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        
        result = send_line_notify(message.strip())
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/x280_screenshot', methods=['POST'])
def send_x280_screenshot():
    """X280スクリーンショット通知"""
    try:
        data = request.json
        filename = data.get('filename', '')
        ocr_text = data.get('ocr_text', '')
        image_path = data.get('image_path')
        
        message = f"""
🖥️ X280スクリーンショット

📸 ファイル: {filename}

"""
        
        if ocr_text:
            message += f"📝 OCR結果:\n{ocr_text[:100]}...\n\n"
        
        message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        result = send_line_notify(message.strip(), image_path)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/alert', methods=['POST'])
def send_alert():
    """アラート通知"""
    try:
        data = request.json
        level = data.get('level', 'info')  # info, warning, error, critical
        title = data.get('title', 'Alert')
        message_text = data.get('message', '')
        
        icon_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        
        icon = icon_map.get(level, 'ℹ️')
        
        message = f"""
{icon} {level.upper()}: {title}

{message_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        result = send_line_notify(message.strip())
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    log("=" * 60)
    log("📱 LINE Notifyサービス起動")
    log("=" * 60)
    log(f"トークン設定: {'✅ 済' if LINE_TOKEN else '❌ 未設定'}")
    _port = int(os.getenv("PORT", "5591"))
    log(f"API起動中... (http://0.0.0.0:{_port})")
    log("Ctrl+C で停止")
    
    app.run(host='0.0.0.0', port=_port, debug=os.getenv("DEBUG", "False").lower() == "true")

