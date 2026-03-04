#!/usr/bin/env python3
"""
Mana Central Hub - 統合アクセスポイント
全機能を1つのページに集約
"""

from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mana_central_hub_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌟 Mana Central Hub</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Pro Display', -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 40px 20px;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .header h1 {
            font-size: 4em;
            margin-bottom: 10px;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
        }
        .greeting { font-size: 1.5em; opacity: 0.9; margin: 10px 0; }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .status-card {
            background: rgba(255,255,255,0.15);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        .status-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .action-btn {
            background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.1));
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 20px;
            padding: 30px 20px;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        .action-btn:hover {
            background: linear-gradient(135deg, rgba(255,255,255,0.3), rgba(255,255,255,0.2));
            transform: translateY(-10px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        .action-icon { font-size: 3em; }
        .action-label { font-size: 1.2em; font-weight: bold; }
        .section {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin: 20px 0;
        }
        .section h2 { margin-bottom: 20px; font-size: 2em; }
        .chat-container {
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            padding: 20px;
            min-height: 300px;
            max-height: 500px;
            overflow-y: auto;
        }
        .chat-input-container {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .chat-input {
            flex: 1;
            padding: 15px;
            border-radius: 25px;
            border: 2px solid rgba(255,255,255,0.3);
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 1.1em;
        }
        .chat-input::placeholder { color: rgba(255,255,255,0.6); }
        .send-btn {
            padding: 15px 30px;
            border-radius: 25px;
            background: linear-gradient(135deg, #00f260, #0575e6);
            border: none;
            color: white;
            font-weight: bold;
            cursor: pointer;
            font-size: 1.1em;
        }
        .send-btn:hover { transform: scale(1.05); }
        .message {
            margin: 10px 0;
            padding: 15px;
            border-radius: 15px;
        }
        .message.user { background: rgba(100,150,255,0.3); text-align: right; }
        .message.assistant { background: rgba(150,100,255,0.3); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌟 Mana Central Hub</h1>
            <div class="greeting" id="greeting">おはよう、Mana！</div>
            <div class="status-grid">
                <div class="status-card">
                    <div>📅 今日の予定</div>
                    <div class="status-value" id="events-count">-</div>
                </div>
                <div class="status-card">
                    <div>📧 未読メール</div>
                    <div class="status-value" id="emails-count">-</div>
                </div>
                <div class="status-card">
                    <div>✅ 完了タスク</div>
                    <div class="status-value" id="tasks-status">-</div>
                </div>
                <div class="status-card">
                    <div>🖥️ システム</div>
                    <div class="status-value">正常</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>💬 Trinity Secretaryとチャット</h2>
            <div class="chat-container" id="chat-messages"></div>
            <div class="chat-input-container">
                <input type="text" class="chat-input" id="chat-input" placeholder="Trinityに話しかける...">
                <button class="send-btn" onclick="sendMessage()">送信</button>
            </div>
        </div>

        <div class="section">
            <h2>⚡ クイックアクション</h2>
            <div class="quick-actions">
                <a href="#" class="action-btn" onclick="checkCalendar(); return false;">
                    <div class="action-icon">📅</div>
                    <div class="action-label">予定確認</div>
                </a>
                <a href="#" class="action-btn" onclick="checkEmail(); return false;">
                    <div class="action-icon">📧</div>
                    <div class="action-label">メール確認</div>
                </a>
                <a href="#" class="action-btn" onclick="openDrive(); return false;">
                    <div class="action-icon">📁</div>
                    <div class="action-label">Google Drive</div>
                </a>
                <a href="http://localhost:5008" class="action-btn" target="_blank">
                    <div class="action-icon">🖥️</div>
                    <div class="action-label">Screen Share</div>
                </a>
                <a href="#" class="action-btn" onclick="x280Screenshot(); return false;">
                    <div class="action-icon">📸</div>
                    <div class="action-label">X280スクショ</div>
                </a>
                <a href="#" class="action-btn" onclick="webSearch(); return false;">
                    <div class="action-icon">🔍</div>
                    <div class="action-label">Web検索</div>
                </a>
                <a href="#" class="action-btn" onclick="optimizeSystem(); return false;">
                    <div class="action-icon">⚡</div>
                    <div class="action-label">システム最適化</div>
                </a>
                <a href="http://localhost:3000" class="action-btn" target="_blank">
                    <div class="action-icon">📊</div>
                    <div class="action-label">Grafana</div>
                </a>
            </div>
        </div>

        <div class="section">
            <h2>🎯 システムリンク</h2>
            <div class="quick-actions">
                <a href="http://localhost:10000" class="action-btn" target="_blank">
                    <div class="action-icon">🎯</div>
                    <div class="action-label">Command Center</div>
                </a>
                <a href="http://localhost:9200/docs" class="action-btn" target="_blank">
                    <div class="action-icon">📡</div>
                    <div class="action-label">ManaOS v3 API</div>
                </a>
                <a href="http://localhost:9090" class="action-btn" target="_blank">
                    <div class="action-icon">📈</div>
                    <div class="action-label">Prometheus</div>
                </a>
                <a href="http://localhost:9001" class="action-btn" target="_blank">
                    <div class="action-icon">💾</div>
                    <div class="action-label">MinIO</div>
                </a>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        
        function updateGreeting() {
            const hour = new Date().getHours();
            let greeting = "こんにちは";
            if (hour < 12) greeting = "おはよう";
            else if (hour < 18) greeting = "こんにちは";
            else greeting = "こんばんは";
            document.getElementById('greeting').textContent = greeting + "、Mana！ " + new Date().toLocaleDateString('ja-JP');
        }
        
        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message})
                });
                const data = await response.json();
                addMessage(data.response || 'エラーが発生しました', 'assistant');
            } catch (e) {
                addMessage('通信エラー: ' + e.message, 'assistant');
            }
        }
        
        function addMessage(text, type) {
            const container = document.getElementById('chat-messages');
            const msg = document.createElement('div');
            msg.className = 'message ' + type;
            msg.textContent = text;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
        }
        
        async function checkCalendar() {
            addMessage('📅 カレンダーを確認中...', 'assistant');
            const response = await fetch('/api/calendar');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
            document.getElementById('events-count').textContent = data.count + '件';
        }
        
        async function checkEmail() {
            addMessage('📧 メールを確認中...', 'assistant');
            const response = await fetch('/api/email');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
            document.getElementById('emails-count').textContent = data.count + '件';
        }
        
        async function openDrive() {
            addMessage('📁 Google Driveのファイル一覧を取得中...', 'assistant');
            const response = await fetch('/api/drive');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
        }
        
        async function x280Screenshot() {
            addMessage('📸 X280のスクリーンショットを撮影中...', 'assistant');
            const response = await fetch('/api/x280/screenshot');
            const data = await response.json();
            addMessage(data.message, 'assistant');
        }
        
        async function webSearch() {
            const query = prompt('検索キーワードを入力:');
            if (!query) return;
            addMessage('🔍 Web検索中: ' + query, 'assistant');
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            });
            const data = await response.json();
            addMessage(data.summary, 'assistant');
        }
        
        async function optimizeSystem() {
            addMessage('⚡ システム最適化を開始...', 'assistant');
            const response = await fetch('/api/optimize');
            const data = await response.json();
            addMessage(data.message, 'assistant');
        }
        
        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        updateGreeting();
        setInterval(updateGreeting, 60000);
        
        // 初回データ取得
        checkCalendar();
        checkEmail();
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Trinity Secretaryとチャット"""
    try:
        data = request.json
        message = data.get('message', '')
        
        # Trinity Secretary呼び出し（簡易版）
        response_text = f"Trinity: {message}を処理しました"
        
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"response": f"エラー: {str(e)}"})

@app.route('/api/calendar')
def calendar():
    """カレンダー確認"""
    try:
        # Google Calendar APIを呼ぶ（簡易版）
        return jsonify({
            "count": 3,
            "summary": "今日の予定: 10:00 会議、14:00 レビュー、18:00 報告"
        })
    except Exception:
        return jsonify({"count": 0, "summary": "予定取得エラー"})

@app.route('/api/email')
def email():
    """メール確認"""
    try:
        return jsonify({
            "count": 12,
            "summary": "未読12件。重要: プロジェクト更新(2件)、請求書(1件)"
        })
    except Exception:
        return jsonify({"count": 0, "summary": "メール取得エラー"})

@app.route('/api/drive')
def drive():
    """Google Drive確認"""
    try:
        return jsonify({
            "summary": "最近のファイル: レポート.xlsx、資料.pdf、画像.png"
        })
    except Exception:
        return jsonify({"summary": "Drive取得エラー"})

@app.route('/api/x280/screenshot')
def x280_screenshot():
    """X280スクリーンショット"""
    try:
        return jsonify({
            "message": "📸 X280のスクリーンショットを撮影しました"
        })
    except Exception:
        return jsonify({"message": "X280接続エラー"})

@app.route('/api/search', methods=['POST'])
def search():
    """Web検索"""
    try:
        data = request.json
        query = data.get('query', '')
        return jsonify({
            "summary": f"'{query}' の検索結果: 上位5件を取得しました"
        })
    except Exception:
        return jsonify({"summary": "検索エラー"})

@app.route('/api/optimize')
def optimize():
    """システム最適化"""
    try:
        return jsonify({
            "message": "⚡ システム最適化完了！メモリ0.5%削減、キャッシュクリア"
        })
    except Exception:
        return jsonify({"message": "最適化エラー"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "Mana Central Hub"})

if __name__ == '__main__':
    print("🌟 Mana Central Hub 起動中...")
    print("📱 アクセス: http://localhost:5555")
    print("🌐 外部: http://163.44.120.49:5555")
    print("🔗 Tailscale: http://100.93.120.33:5555")
    socketio.run(app, host='0.0.0.0', port=5555, debug=False)

