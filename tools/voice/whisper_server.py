#!/usr/bin/env python3
"""
Whisper音声認識サーバー
OpenAI WhisperでリアルタイムNGな音声→テキスト変換 + ManaOS実行
"""

import whisper
import torch
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import requests

# Flask設定
app = Flask(__name__)
CORS(app)

# ディレクトリ設定
WORK_DIR = Path("/root/whisper_voice_system")
AUDIO_DIR = WORK_DIR / "audio"
RECORDINGS_DIR = WORK_DIR / "recordings"
TRANSCRIPTS_DIR = WORK_DIR / "transcripts"

# ディレクトリ作成
for dir_path in [AUDIO_DIR, RECORDINGS_DIR, TRANSCRIPTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Whisperモデルロード
print("🎤 Whisperモデルロード中...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"デバイス: {device}")

# モデルサイズ: tiny, base, small, medium, large
# tiny: 最速（74MB）、base: バランス（142MB）、small: 高精度（466MB）
MODEL_SIZE = "base"  # 変更可能
model = whisper.load_model(MODEL_SIZE, device=device)
print(f"✅ Whisper {MODEL_SIZE}モデルロード完了")

# ログ記録
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    log_file = WORK_DIR / "logs" / f"whisper_{datetime.now().strftime('%Y%m%d')}.log"
    log_file.parent.mkdir(exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


# ===== API エンドポイント =====

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Whisper Voice Recognition Server",
        "model": MODEL_SIZE,
        "device": device,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """音声ファイルをテキストに変換"""
    try:
        # ファイルアップロード確認
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "音声ファイルがありません"}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'ja')  # デフォルト: 日本語
        
        # 一時ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audio_{timestamp}.{audio_file.filename.split('.')[-1]}"
        temp_path = AUDIO_DIR / filename
        
        audio_file.save(temp_path)
        log(f"音声ファイル保存: {filename}")
        
        # Whisper実行
        log(f"Whisper認識開始: {filename}")
        result = model.transcribe(
            str(temp_path),
            language=language,
            task="transcribe"
        )
        
        text = result["text"].strip()
        log(f"認識完了: {text[:50]}...")
        
        # トランスクリプト保存
        transcript_filename = f"transcript_{timestamp}.json"
        transcript_path = TRANSCRIPTS_DIR / transcript_filename
        
        transcript_data = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "language": language,
            "text": text,
            "segments": result.get("segments", [])
        }
        
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "text": text,
            "language": language,
            "filename": filename,
            "transcript_file": transcript_filename
        })
    
    except Exception as e:
        log(f"❌ 認識エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/transcribe_and_execute', methods=['POST'])
def transcribe_and_execute():
    """音声認識 → ManaOS v3.0実行"""
    try:
        # まず音声認識
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "音声ファイルがありません"}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'ja')
        
        # 一時ファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audio_{timestamp}.{audio_file.filename.split('.')[-1]}"
        temp_path = AUDIO_DIR / filename
        
        audio_file.save(temp_path)
        log(f"音声ファイル保存: {filename}")
        
        # Whisper実行
        log(f"Whisper認識開始: {filename}")
        result = model.transcribe(
            str(temp_path),
            language=language,
            task="transcribe"
        )
        
        text = result["text"].strip()
        log(f"認識テキスト: {text}")
        
        # ManaOS v3.0 Orchestratorに送信
        log("ManaOS v3.0実行中...")
        manaos_response = requests.post(
            "http://localhost:9200/v3/orchestrator/run",
            json={"text": text, "actor": "remi"},
            timeout=30
        )
        
        manaos_result = manaos_response.json()
        log(f"ManaOS実行完了: {manaos_result.get('success')}")
        
        # トランスクリプト保存
        transcript_filename = f"transcript_{timestamp}.json"
        transcript_path = TRANSCRIPTS_DIR / transcript_filename
        
        transcript_data = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "language": language,
            "text": text,
            "manaos_result": manaos_result
        }
        
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "text": text,
            "language": language,
            "filename": filename,
            "manaos_result": manaos_result,
            "transcript_file": transcript_filename
        })
    
    except Exception as e:
        log(f"❌ 実行エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/record', methods=['GET'])
def show_recorder():
    """音声録音Webインターフェース"""
    html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 Whisper Voice Input</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 600px;
            width: 100%;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        h1 { text-align: center; font-size: 2.5em; margin-bottom: 30px; }
        .record-button {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: none;
            background: radial-gradient(circle, #ef4444 0%, #dc2626 100%);
            color: white;
            font-size: 3em;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            margin: 0 auto;
            display: block;
        }
        .record-button:hover { transform: scale(1.05); }
        .record-button.recording {
            background: radial-gradient(circle, #10b981 0%, #059669 100%);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .status {
            text-align: center;
            margin-top: 30px;
            font-size: 1.2em;
            min-height: 30px;
        }
        .result {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
            display: none;
        }
        .result.show { display: block; }
        .text-output {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 1.1em;
            line-height: 1.6;
        }
        .manaos-result {
            margin-top: 15px;
            padding: 15px;
            background: rgba(16, 185, 129, 0.2);
            border-radius: 8px;
            border-left: 4px solid #10b981;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 Whisper Voice Input</h1>
        
        <button id="recordButton" class="record-button" onclick="toggleRecording()">
            🎤
        </button>
        
        <div class="status" id="status">マイクボタンをクリックして録音開始</div>
        
        <div class="result" id="result">
            <h3>📝 認識結果:</h3>
            <div class="text-output" id="textOutput"></div>
            
            <div class="manaos-result" id="manaosResult" style="display: none;">
                <h4>🤖 ManaOS実行結果:</h4>
                <div id="manaosOutput"></div>
            </div>
        </div>
    </div>

    <script>
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;

        async function toggleRecording() {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        }

        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    await sendAudio(audioBlob);
                };

                mediaRecorder.start();
                isRecording = true;

                document.getElementById('recordButton').classList.add('recording');
                document.getElementById('status').textContent = '🔴 録音中...（クリックで停止）';
            } catch (error) {
                alert('マイクアクセスを許可してください: ' + error.message);
            }
        }

        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;

                document.getElementById('recordButton').classList.remove('recording');
                document.getElementById('status').textContent = '⏳ 音声認識中...';

                // ストリーム停止
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        }

        async function sendAudio(audioBlob) {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            formData.append('language', 'ja');

            try {
                const response = await fetch('/transcribe_and_execute', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    document.getElementById('textOutput').textContent = data.text;
                    document.getElementById('result').classList.add('show');
                    document.getElementById('status').textContent = '✅ 認識完了！';

                    // ManaOS結果表示
                    if (data.manaos_result) {
                        document.getElementById('manaosOutput').textContent = 
                            JSON.stringify(data.manaos_result, null, 2);
                        document.getElementById('manaosResult').style.display = 'block';
                    }
                } else {
                    document.getElementById('status').textContent = '❌ エラー: ' + data.error;
                }
            } catch (error) {
                document.getElementById('status').textContent = '❌ 通信エラー: ' + error.message;
            }
        }
    </script>
</body>
</html>
    """
    return render_template_string(html)


@app.route('/transcripts', methods=['GET'])
def list_transcripts():
    """トランスクリプト一覧取得"""
    transcripts = []
    for file_path in sorted(TRANSCRIPTS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            transcripts.append({
                "filename": file_path.name,
                "timestamp": data.get("timestamp"),
                "text": data.get("text", "")[:100]  # 最初の100文字
            })
    
    return jsonify({
        "success": True,
        "transcripts": transcripts[:50],  # 最新50件
        "total": len(transcripts)
    })


if __name__ == '__main__':
    log("=" * 60)
    log("🎤 Whisper音声認識サーバー起動")
    log("=" * 60)
    log(f"モデル: {MODEL_SIZE}")
    log(f"デバイス: {device}")
    log("API起動中... (http://0.0.0.0:5012)")
    log("Ctrl+C で停止")
    
    app.run(host='0.0.0.0', port=5012, debug=os.getenv("DEBUG", "False").lower() == "true")

