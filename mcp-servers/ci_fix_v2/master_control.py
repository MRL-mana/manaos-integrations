"""
ManaOSマスターコントロール
すべてのシステムを統合管理するマスターコントロールパネル
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import json
from datetime import datetime

# from ultimate_integration import UltimateIntegration

app = Flask(__name__)
CORS(app)

try:
    from ultimate_integration import UltimateIntegration
    system = UltimateIntegration()
except Exception as e:
    print(f"UltimateIntegration initialization failed: {e}")
    system = None

MASTER_CONTROL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ManaOS マスターコントロールパネル</title>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            text-align: center;
        }
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
            font-size: 1.2em;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.4em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .status-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-badge {
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .status-online {
            background: #10b981;
            color: white;
        }
        .status-offline {
            background: #ef4444;
            color: white;
        }
        .command-panel {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-top: 30px;
        }
        .command-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #667eea;
            border-radius: 10px;
            font-size: 1.1em;
            margin-bottom: 15px;
        }
        .command-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1.1em;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .command-button:hover {
            transform: scale(1.05);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .stat-value {
            font-size: 3em;
            font-weight: bold;
            margin: 15px 0;
        }
        .stat-label {
            font-size: 1.1em;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ManaOS マスターコントロールパネル</h1>
            <p>すべてのシステムを統合管理</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">統合システム</div>
                <div class="stat-value" id="total-systems">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">オンライン</div>
                <div class="stat-value" id="online-systems">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">タスク</div>
                <div class="stat-value" id="total-tasks">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">目標</div>
                <div class="stat-value" id="total-goals">0</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>基本統合システム</h2>
                <div class="status-grid" id="basic-integrations"></div>
            </div>
            
            <div class="card">
                <h2>高度機能</h2>
                <div class="status-grid" id="advanced-features"></div>
            </div>
            
            <div class="card">
                <h2>AIエージェント</h2>
                <div id="agent-status"></div>
            </div>
            
            <div class="card">
                <h2>セキュリティ</h2>
                <div id="security-status"></div>
            </div>
        </div>
        
        <div class="command-panel">
            <h2>インテリジェントコマンド</h2>
            <input type="text" class="command-input" id="command-input" placeholder="コマンドを入力してください（例: 画像を生成して）">
            <button class="command-button" onclick="executeCommand()">実行</button>
            <div id="command-result" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 10px; display: none;"></div>
        </div>
    </div>
    
    <script>
        function updateDashboard(data) {
            // 統計更新
            const basicCount = Object.keys(data.basic_integrations || {}).length;
            const advancedCount = Object.keys(data.advanced_features || {}).length;
            document.getElementById('total-systems').textContent = basicCount + advancedCount;
            document.getElementById('online-systems').textContent = 
                Object.values(data.basic_integrations || {}).filter(v => v).length;
            document.getElementById('total-tasks').textContent = 
                data.agent_status?.tasks_count || 0;
            document.getElementById('total-goals').textContent = 
                data.agent_status?.goals_count || 0;
            
            // 基本統合システム
            const basicDiv = document.getElementById('basic-integrations');
            basicDiv.innerHTML = '';
            for (const [name, status] of Object.entries(data.basic_integrations || {})) {
                const item = document.createElement('div');
                item.className = 'status-item';
                item.innerHTML = `
                    <span>${name}</span>
                    <span class="status-badge ${status ? 'status-online' : 'status-offline'}">
                        ${status ? 'オンライン' : 'オフライン'}
                    </span>
                `;
                basicDiv.appendChild(item);
            }
            
            // 高度機能
            const advancedDiv = document.getElementById('advanced-features');
            advancedDiv.innerHTML = '';
            for (const [name, status] of Object.entries(data.advanced_features || {})) {
                if (typeof status === 'boolean') {
                    const item = document.createElement('div');
                    item.className = 'status-item';
                    item.innerHTML = `
                        <span>${name}</span>
                        <span class="status-badge ${status ? 'status-online' : 'status-offline'}">
                            ${status ? '利用可能' : '利用不可'}
                        </span>
                    `;
                    advancedDiv.appendChild(item);
                }
            }
            
            // AIエージェント状態
            if (data.agent_status) {
                document.getElementById('agent-status').innerHTML = `
                    <div class="status-item">
                        <span>実行中タスク</span>
                        <span>${data.agent_status.running_tasks || 0}</span>
                    </div>
                    <div class="status-item">
                        <span>待機中タスク</span>
                        <span>${data.agent_status.pending_tasks || 0}</span>
                    </div>
                    <div class="status-item">
                        <span>完了タスク</span>
                        <span>${data.agent_status.completed_tasks || 0}</span>
                    </div>
                `;
            }
            
            // セキュリティ状態
            if (data.security_status) {
                document.getElementById('security-status').innerHTML = `
                    <div class="status-item">
                        <span>ブロックIP数</span>
                        <span>${data.security_status.blocked_ips_count || 0}</span>
                    </div>
                    <div class="status-item">
                        <span>失敗試行数</span>
                        <span>${data.security_status.failed_attempts_count || 0}</span>
                    </div>
                `;
            }
        }
        
        function executeCommand() {
            const input = document.getElementById('command-input');
            const command = input.value.trim();
            
            if (!command) {
                return;
            }
            
            const resultDiv = document.getElementById('command-result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>実行中...</p>';
            
            fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: command})
            })
            .then(response => response.json())
            .then(data => {
                resultDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            })
            .catch(error => {
                resultDiv.innerHTML = `<p style="color: red;">エラー: ${error}</p>`;
            });
        }
        
        // Enterキーで実行
        document.getElementById('command-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                executeCommand();
            }
        });
        
        // 初期データ取得
        fetch('/api/status')
            .then(response => response.json())
            .then(data => updateDashboard(data));
        
        // 5秒ごとに更新
        setInterval(() => {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => updateDashboard(data));
        }, 5000);
    </script>
</body>
</html>
"""


@app.route('/')
def master_control():
    """マスターコントロールパネル"""
    return render_template_string(MASTER_CONTROL_HTML)


@app.route('/api/status')
def get_status():
    """状態を取得"""
    if system:
        try:
            status = system.get_comprehensive_status()
        except Exception as e:
            status = {"error": str(e)}
    else:
        status = {"error": "System not initialized"}
    return jsonify(status)


@app.route('/api/execute', methods=['POST'])
def execute_command():
    """コマンドを実行"""
    data = request.json
    command = data.get('command', '')
    
    if system:
        try:
            result = system.execute_intelligent_workflow(command)
        except Exception as e:
            result = {"error": str(e)}
    else:
        result = {"error": "System not initialized"}
    return jsonify(result)


@app.route('/api/full-check', methods=['POST'])
def full_check():
    """フルシステムチェック"""
    if system:
        try:
            result = system.run_full_system_check()
        except Exception as e:
            result = {"error": str(e)}
    else:
        result = {"error": "System not initialized"}
    return jsonify(result)


if __name__ == '__main__':
    print("=" * 60)
    print("ManaOSマスターコントロールパネル")
    print("=" * 60)
    print("アクセス: http://127.0.0.1:9700")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=9700, debug=True)


















