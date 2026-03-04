#!/usr/bin/env python3
"""
TTS (Text-to-Speech) サービス
Google TTS / gTTS を使用して音声応答
"""

from gtts import gTTS
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile

app = Flask(__name__)
CORS(app)

# ディレクトリ設定
WORK_DIR = Path("/root/whisper_voice_system")
AUDIO_OUTPUT_DIR = WORK_DIR / "audio_output"
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "TTS Service",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/tts', methods=['POST'])
def text_to_speech():
    """テキストを音声に変換"""
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'ja')
        
        if not text:
            return jsonify({"success": False, "error": "テキストが空です"}), 400
        
        log(f"TTS生成: {text[:50]}...")
        
        # gTTSで音声生成
        tts = gTTS(text=text, lang=language, slow=False)
        
        # ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tts_{timestamp}.mp3"
        output_path = AUDIO_OUTPUT_DIR / filename
        
        tts.save(str(output_path))
        log(f"✅ TTS生成完了: {filename}")
        
        return jsonify({
            "success": True,
            "filename": filename,
            "text": text,
            "language": language,
            "path": str(output_path)
        })
    
    except Exception as e:
        log(f"❌ TTS生成エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/tts/play/<filename>', methods=['GET'])
def play_audio(filename):
    """音声ファイルを再生（ダウンロード）"""
    file_path = AUDIO_OUTPUT_DIR / filename
    if file_path.exists():
        return send_file(file_path, mimetype='audio/mp3')
    else:
        return jsonify({"error": "File not found"}), 404


@app.route('/tts/generate_and_play', methods=['POST'])
def generate_and_play():
    """テキストから音声生成して即座に再生"""
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'ja')
        
        if not text:
            return jsonify({"success": False, "error": "テキストが空です"}), 400
        
        log(f"TTS生成＋再生: {text[:50]}...")
        
        # gTTSで音声生成
        tts = gTTS(text=text, lang=language, slow=False)
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            tts.save(temp_file.name)
            temp_path = temp_file.name
        
        # ファイルを返す
        return send_file(
            temp_path,
            mimetype='audio/mp3',
            as_attachment=False,
            download_name='response.mp3'
        )
    
    except Exception as e:
        log(f"❌ TTS生成エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    log("=" * 60)
    log("🔊 TTSサービス起動")
    log("=" * 60)
    log("API起動中... (http://0.0.0.0:5013)")
    log("Ctrl+C で停止")
    
    app.run(host='0.0.0.0', port=5013, debug=os.getenv("DEBUG", "False").lower() == "true")

