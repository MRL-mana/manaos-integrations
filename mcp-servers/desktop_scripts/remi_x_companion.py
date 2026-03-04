"""
Remi X Companion - PC側のXコンパニオンパネル
Xを見ながらレミと会話する
"""

from flask import Flask, render_template_string, request, jsonify
import requests
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 設定
REMI_BRAIN_URL = os.getenv("REMI_BRAIN_URL", "http://127.0.0.1:9407")
REMI_PIXEL_URL = os.getenv("REMI_PIXEL_URL", "http://127.0.0.1:9408")

# HTMLテンプレート
COMPANION_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Remi X Companion</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        .remi-panel {
            background: #2a2a2a;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .remi-face {
            font-size: 48px;
            text-align: center;
            margin-bottom: 10px;
        }
        .remi-status {
            text-align: center;
            color: #888;
            margin-bottom: 20px;
        }
        .input-area {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 1px solid #444;
            border-radius: 6px;
            background: #333;
            color: #fff;
            font-size: 14px;
        }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            background: #4a9eff;
            color: #fff;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
        }
        button:hover {
            background: #5aaeff;
        }
        .remi-response {
            background: #333;
            border-radius: 8px;
            padding: 15px;
            margin-top: 10px;
            min-height: 50px;
        }
        .x-post-input {
            width: 100%;
            min-height: 100px;
            padding: 12px;
            border: 1px solid #444;
            border-radius: 6px;
            background: #333;
            color: #fff;
            font-size: 14px;
            resize: vertical;
            margin-bottom: 10px;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-connected { background: #4caf50; }
        .status-disconnected { background: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Remi X Companion</h1>
        
        <div class="remi-panel">
            <div class="remi-face" id="remiFace">😊</div>
            <div class="remi-status">
                <span class="status-indicator status-connected" id="statusIndicator"></span>
                <span id="remiStatus">待機中</span>
            </div>
            
            <div class="input-area">
                <input type="text" id="speechInput" placeholder="レミに話しかける..." />
                <button onclick="sendSpeech()">話す</button>
            </div>
            
            <div class="remi-response" id="remiResponse">
                レミがここに返事を表示します
            </div>
        </div>
        
        <div class="remi-panel">
            <h2>Xポスト解析</h2>
            <textarea class="x-post-input" id="xPostInput" placeholder="Xのポストを貼り付けて「レミに聞く」をクリック"></textarea>
            <button onclick="analyzeXPost()" style="width: 100%;">レミに聞く</button>
            
            <div id="xResponse" style="margin-top: 20px;">
                <div class="remi-response" id="xSummary" style="display: none;">
                    <strong>要約:</strong> <span id="summaryText"></span>
                </div>
                <div class="remi-response" id="xPoint" style="display: none;">
                    <strong>論点:</strong> <span id="pointText"></span>
                </div>
                <div class="remi-response" id="xReply" style="display: none;">
                    <strong>返信案:</strong> <span id="replyText"></span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const REMI_BRAIN_URL = '{{ REMI_BRAIN_URL }}';
        
        function updateFace(expression) {
            const faces = {
                'idle': '😊',
                'listen': '👂',
                'talk': '💬',
                'think': '🤔'
            };
            document.getElementById('remiFace').textContent = faces[expression] || '😊';
        }
        
        async function sendSpeech() {
            const input = document.getElementById('speechInput');
            const text = input.value.trim();
            if (!text) return;
            
            updateFace('listen');
            document.getElementById('remiStatus').textContent = '聞いてる...';
            
            try {
                const response = await fetch(REMI_BRAIN_URL + '/remi/speech/input', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, source: 'x_companion' })
                });
                
                const data = await response.json();
                const remiText = data.text || '...';
                
                document.getElementById('remiResponse').textContent = remiText;
                updateFace('talk');
                document.getElementById('remiStatus').textContent = '話してる...';
                
                // Pixel側で再生（オプション）
                // await fetch(REMI_PIXEL_URL + '/speak', { ... });
                
                setTimeout(() => {
                    updateFace('idle');
                    document.getElementById('remiStatus').textContent = '待機中';
                }, 2000);
                
                input.value = '';
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('remiResponse').textContent = 'エラーが発生しました';
                updateFace('idle');
            }
        }
        
        async function analyzeXPost() {
            const input = document.getElementById('xPostInput');
            const text = input.value.trim();
            if (!text) return;
            
            updateFace('think');
            document.getElementById('remiStatus').textContent = '考えてる...';
            
            try {
                const response = await fetch(REMI_BRAIN_URL + '/remi/x/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ post_text: text })
                });
                
                const data = await response.json();
                
                if (data.summary) {
                    document.getElementById('summaryText').textContent = data.summary;
                    document.getElementById('xSummary').style.display = 'block';
                }
                if (data.point) {
                    document.getElementById('pointText').textContent = data.point;
                    document.getElementById('xPoint').style.display = 'block';
                }
                if (data.reply_suggestion) {
                    document.getElementById('replyText').textContent = data.reply_suggestion;
                    document.getElementById('xReply').style.display = 'block';
                }
                
                updateFace('idle');
                document.getElementById('remiStatus').textContent = '待機中';
            } catch (error) {
                console.error('Error:', error);
                updateFace('idle');
            }
        }
        
        // Enterキーで送信
        document.getElementById('speechInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendSpeech();
        });
        
        // 定期的に状態確認
        setInterval(async () => {
            try {
                const response = await fetch(REMI_BRAIN_URL + '/remi/state');
                const data = await response.json();
                const mode = data.state?.mode || 'idle';
                updateFace(mode === 'x_companion' ? 'think' : mode === 'chat' ? 'talk' : 'idle');
            } catch (error) {
                document.getElementById('statusIndicator').className = 'status-indicator status-disconnected';
            }
        }, 2000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """メインページ"""
    return render_template_string(COMPANION_HTML, REMI_BRAIN_URL=REMI_BRAIN_URL)


@app.route("/api/send", methods=["POST"])
def api_send():
    """API経由でレミに送信"""
    try:
        data = request.json
        text = data.get("text", "")
        source = data.get("source", "x_companion")
        
        # 母艦に送信
        response = requests.post(
            f"{REMI_BRAIN_URL}/remi/speech/input",
            json={
                "text": text,
                "source": source,
                "timestamp": None
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to get response"}), 500
            
    except Exception as e:
        logger.error(f"API send error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("REMI_X_COMPANION_PORT", "9409"))
    host = os.getenv("REMI_X_COMPANION_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi X Companion on {host}:{port}")
    logger.info(f"Remi Brain URL: {REMI_BRAIN_URL}")
    
    app.run(host=host, port=port, debug=True)






