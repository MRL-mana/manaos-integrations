#!/usr/bin/env python3
"""
Trinity Orchestrator v1.0 - Standalone Web UI
シンプルで美しいWebインターフェース
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Orchestrator API
ORCHESTRATOR_API = "http://127.0.0.1:9400"

# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trinity Orchestrator v1.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container { max-width: 1200px; margin: 0 auto; }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p { color: #666; font-size: 1.1em; }
        
        .main-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 30px;
        }
        
        .form-group { margin-bottom: 25px; }
        
        .form-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
            font-size: 1.1em;
        }
        
        .form-group input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1em;
            transition: all 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .context-input-area {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .context-input-area input {
            flex: 1;
        }
        
        .context-input-area button {
            padding: 15px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .context-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }
        
        .context-tag {
            background: #667eea;
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .context-tag button {
            background: rgba(255, 255, 255, 0.3);
            border: none;
            color: white;
            cursor: pointer;
            font-size: 1.2em;
            padding: 0 8px;
            border-radius: 50%;
            width: 25px;
            height: 25px;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 30px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .loading.show { display: block; }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .result-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-top: 30px;
            display: none;
        }
        
        .result-panel.show {
            display: block;
            animation: slideIn 0.5s ease-out;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .status-badge {
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
        }
        
        .status-completed { background: #28a745; color: white; }
        .status-failed { background: #dc3545; color: white; }
        
        .result-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .info-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            border-left: 4px solid #667eea;
        }
        
        .info-card h3 { color: #667eea; font-size: 0.9em; margin-bottom: 8px; }
        .info-card p { font-size: 1.5em; font-weight: bold; color: #333; }
        
        .artifacts h3 { color: #333; margin-bottom: 15px; margin-top: 20px; }
        
        .artifact-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        
        .artifact-item code {
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Trinity Orchestrator v1.0</h1>
            <p>Multi-Agent Control Engine - Remi → Luna → Mina 自動連鎖</p>
        </div>
        
        <div class="main-panel">
            <h2 style="margin-bottom: 30px;">新しいタスクを実行</h2>
            
            <form id="orchestratorForm" onsubmit="runOrchestrator(event)">
                <div class="form-group">
                    <label for="goal">🎯 目標（Goal）</label>
                    <input type="text" id="goal" name="goal" placeholder="例: TODOアプリを作成" required>
                </div>
                
                <div class="form-group">
                    <label>📋 前提条件・制約（Context）</label>
                    <div class="context-input-area">
                        <input type="text" id="contextInput" placeholder="例: Python, Flask, シンプル">
                        <button type="button" onclick="addContext()">追加</button>
                    </div>
                    <div class="context-tags" id="contextTags"></div>
                </div>
                
                <div class="form-group">
                    <label for="budget">🔄 最大ターン数</label>
                    <input type="number" id="budget" name="budget" value="12" min="1" max="30">
                </div>
                
                <button type="submit" class="btn" id="submitBtn">🚀 実行開始</button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Orchestrator を実行中...</p>
                <p style="color: #666; font-size: 0.9em;">Remi → Luna → Mina が自動連鎖します</p>
            </div>
        </div>
        
        <div class="result-panel" id="resultPanel">
            <div class="result-header">
                <h2>📊 実行結果</h2>
                <span class="status-badge" id="statusBadge"></span>
            </div>
            
            <div class="result-info">
                <div class="info-card">
                    <h3>チケットID</h3>
                    <p id="ticketId">-</p>
                </div>
                <div class="info-card">
                    <h3>信頼度</h3>
                    <p id="confidence">-</p>
                </div>
                <div class="info-card">
                    <h3>実行ターン数</h3>
                    <p id="turns">-</p>
                </div>
                <div class="info-card">
                    <h3>生成ファイル数</h3>
                    <p id="artifactCount">-</p>
                </div>
            </div>
            
            <div class="artifacts" id="artifactsSection" style="display: none;">
                <h3>📦 生成されたファイル</h3>
                <div id="artifactsList"></div>
            </div>
        </div>
    </div>
    
    <script>
        const contextItems = [];
        
        function addContext() {
            const input = document.getElementById('contextInput');
            const value = input.value.trim();
            if (value && !contextItems.includes(value)) {
                contextItems.push(value);
                updateContextTags();
                input.value = '';
            }
        }
        
        document.getElementById('contextInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addContext();
            }
        });
        
        function updateContextTags() {
            const container = document.getElementById('contextTags');
            container.innerHTML = '';
            
            contextItems.forEach((item, index) => {
                const tag = document.createElement('div');
                tag.className = 'context-tag';
                tag.innerHTML = `<span>${item}</span><button onclick="removeContext(${index})">×</button>`;
                container.appendChild(tag);
            });
        }
        
        function removeContext(index) {
            contextItems.splice(index, 1);
            updateContextTags();
        }
        
        async function runOrchestrator(e) {
            e.preventDefault();
            
            const goal = document.getElementById('goal').value;
            const budget = parseInt(document.getElementById('budget').value);
            
            document.getElementById('loading').classList.add('show');
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('resultPanel').classList.remove('show');
            
            try {
                const response = await fetch('http://127.0.0.1:9400/api/orchestrate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        goal: goal,
                        context: contextItems,
                        budget_turns: budget
                    })
                });
                
                const result = await response.json();
                displayResult(result);
            } catch (error) {
                alert('エラー: ' + error.message);
            } finally {
                document.getElementById('loading').classList.remove('show');
                document.getElementById('submitBtn').disabled = false;
            }
        }
        
        function displayResult(result) {
            document.getElementById('statusBadge').textContent = result.status.toUpperCase();
            document.getElementById('statusBadge').className = 'status-badge status-' + result.status;
            
            document.getElementById('ticketId').textContent = result.ticket_id;
            document.getElementById('confidence').textContent = (result.confidence * 100).toFixed(0) + '%';
            document.getElementById('turns').textContent = result.turns;
            document.getElementById('artifactCount').textContent = result.artifacts.length;
            
            if (result.artifacts.length > 0) {
                const list = document.getElementById('artifactsList');
                list.innerHTML = '';
                
                result.artifacts.forEach(artifact => {
                    const item = document.createElement('div');
                    item.className = 'artifact-item';
                    item.innerHTML = `
                        <code>${artifact.path}</code>
                        <p style="margin-top: 5px; color: #666; font-size: 0.9em;">${artifact.description || ''}</p>
                    `;
                    list.appendChild(item);
                });
                
                document.getElementById('artifactsSection').style.display = 'block';
            }
            
            document.getElementById('resultPanel').classList.add('show');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """メインページ"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    """ヘルスチェック"""
    try:
        # Orchestrator APIの状態確認
        response = requests.get(f"{ORCHESTRATOR_API}/health", timeout=2)
        orchestrator_status = response.status_code == 200
    except:
        orchestrator_status = False
    
    return jsonify({
        "status": "ok",
        "web_ui": "running",
        "orchestrator_api": "online" if orchestrator_status else "offline"
    })

if __name__ == "__main__":
    logger.info("🚀 Starting Trinity Orchestrator Web UI...")
    logger.info("📍 Port: 9401")
    logger.info("🌐 Access: http://127.0.0.1:9401")
    
    app.run(host="0.0.0.0", port=9401, debug=False)



