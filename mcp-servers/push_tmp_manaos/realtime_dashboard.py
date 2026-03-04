"""
リアルタイムダッシュボード
統合システムの状態を可視化
"""

from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO, emit
import json
from typing import Dict, Any
from datetime import datetime
import threading
import time

from unified_api_server import initialize_integrations, integrations
# from manaos_service_bridge import ManaOSServiceBridge
# from ai_agent_autonomous import AutonomousAgent


app = Flask(__name__)
app.config['SECRET_KEY'] = 'manaos-dashboard-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

try:
    from manaos_service_bridge import ManaOSServiceBridge
    bridge = ManaOSServiceBridge()
except Exception as e:
    print(f"ManaOSServiceBridge initialization failed: {e}")
    bridge = None

try:
    from ai_agent_autonomous import AutonomousAgent
    agent = AutonomousAgent()
except Exception as e:
    print(f"AutonomousAgent initialization failed: {e}")
    agent = None


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ManaOS統合システムダッシュボード</title>
    <meta charset="utf-8">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
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
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .status-item:last-child {
            border-bottom: none;
        }
        .status-badge {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-online {
            background: #10b981;
            color: white;
        }
        .status-offline {
            background: #ef4444;
            color: white;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ManaOS統合システムダッシュボード</h1>
            <p>リアルタイム監視と制御</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">統合システム</div>
                <div class="stat-value" id="total-integrations">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">オンライン</div>
                <div class="stat-value" id="online-count">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">タスク</div>
                <div class="stat-value" id="task-count">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">目標</div>
                <div class="stat-value" id="goal-count">0</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>統合システム状態</h2>
                <div id="integrations-status"></div>
            </div>

            <div class="card">
                <h2>ManaOSサービス状態</h2>
                <div id="manaos-services-status"></div>
            </div>

            <div class="card">
                <h2>AIエージェント状態</h2>
                <div id="agent-status"></div>
            </div>
        </div>

        <div class="card">
            <h2>パフォーマンスメトリクス</h2>
            <div class="chart-container">
                <canvas id="performance-chart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let performanceChart;

        // パフォーマンスチャートの初期化
        const ctx = document.getElementById('performance-chart').getContext('2d');
        performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'オンラインシステム数',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10
                    }
                }
            }
        });

        // ステータス更新
        socket.on('status_update', function(data) {
            updateDashboard(data);
        });

        function updateDashboard(data) {
            // 統計更新
            document.getElementById('total-integrations').textContent =
                Object.keys(data.integrations || {}).length;
            document.getElementById('online-count').textContent =
                Object.values(data.integrations || {}).filter(v => v).length;
            document.getElementById('task-count').textContent =
                data.agent?.tasks_count || 0;
            document.getElementById('goal-count').textContent =
                data.agent?.goals_count || 0;

            // 統合システム状態
            const integrationsDiv = document.getElementById('integrations-status');
            integrationsDiv.innerHTML = '';
            for (const [name, status] of Object.entries(data.integrations || {})) {
                const item = document.createElement('div');
                item.className = 'status-item';
                item.innerHTML = `
                    <span>${name}</span>
                    <span class="status-badge ${status ? 'status-online' : 'status-offline'}">
                        ${status ? 'オンライン' : 'オフライン'}
                    </span>
                `;
                integrationsDiv.appendChild(item);
            }

            // ManaOSサービス状態
            const servicesDiv = document.getElementById('manaos-services-status');
            servicesDiv.innerHTML = '';
            for (const [name, status] of Object.entries(data.manaos_services || {})) {
                const item = document.createElement('div');
                item.className = 'status-item';
                item.innerHTML = `
                    <span>${name}</span>
                    <span class="status-badge ${status ? 'status-online' : 'status-offline'}">
                        ${status ? 'オンライン' : 'オフライン'}
                    </span>
                `;
                servicesDiv.appendChild(item);
            }

            // AIエージェント状態
            const agentDiv = document.getElementById('agent-status');
            if (data.agent) {
                agentDiv.innerHTML = `
                    <div class="status-item">
                        <span>実行中タスク</span>
                        <span>${data.agent.running_tasks || 0}</span>
                    </div>
                    <div class="status-item">
                        <span>待機中タスク</span>
                        <span>${data.agent.pending_tasks || 0}</span>
                    </div>
                    <div class="status-item">
                        <span>完了タスク</span>
                        <span>${data.agent.completed_tasks || 0}</span>
                    </div>
                    <div class="status-item">
                        <span>失敗タスク</span>
                        <span>${data.agent.failed_tasks || 0}</span>
                    </div>
                `;
            }

            // パフォーマンスチャート更新
            const now = new Date().toLocaleTimeString();
            performanceChart.data.labels.push(now);
            performanceChart.data.datasets[0].data.push(
                Object.values(data.integrations || {}).filter(v => v).length
            );

            if (performanceChart.data.labels.length > 20) {
                performanceChart.data.labels.shift();
                performanceChart.data.datasets[0].data.shift();
            }

            performanceChart.update();
        }

        // 初期データ取得
        fetch('/api/dashboard/status')
            .then(response => response.json())
            .then(data => updateDashboard(data));
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """ダッシュボードページ"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/dashboard/status')
def get_status():
    """ダッシュボード状態を取得"""
    integration_status = {}
    for name, integration in integrations.items():
        if hasattr(integration, "is_available"):
            integration_status[name] = integration.is_available()
        else:
            integration_status[name] = False

    manaos_status = {}
    if bridge:
        try:
            manaos_status = bridge.check_manaos_services()
        except Exception as e:
            print(f"Error checking manaos services: {e}")

    agent_status = {}
    if agent:
        try:
            agent_status = agent.get_status()
        except Exception as e:
            print(f"Error checking agent status: {e}")

    return jsonify({
        "integrations": integration_status,
        "manaos_services": manaos_status,
        "agent": agent_status,
        "timestamp": datetime.now().isoformat()
    })


def background_task():
    """バックグラウンドタスク"""
    while True:
        try:
            manaos_services = {}
            if bridge:
                try:
                    manaos_services = bridge.check_manaos_services()
                except Exception:
                    pass

            agent_status = {}
            if agent:
                try:
                    agent_status = agent.get_status()
                except Exception:
                    pass

            status = {
                "integrations": {},
                "manaos_services": manaos_services,
                "agent": agent_status,
                "timestamp": datetime.now().isoformat()
            }

            for name, integration in integrations.items():
                if hasattr(integration, "is_available"):
                    status["integrations"][name] = integration.is_available()
                else:
                    status["integrations"][name] = False

            socketio.emit('status_update', status)
            time.sleep(5)  # 5秒ごとに更新

        except Exception as e:
            print(f"バックグラウンドタスクエラー: {e}")
            time.sleep(5)


if __name__ == '__main__':
    print("ManaOSリアルタイムダッシュボードを起動中...")
    initialize_integrations()

    # バックグラウンドタスクを開始
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()

    print("ダッシュボード: http://127.0.0.1:9600")
    # Flask-SocketIO は debug=True の際に Werkzeug を弾くことがあるため、
    # 開発/ローカル用途では allow_unsafe_werkzeug=True で明示的に許可する。
    # （本番運用は eventlet/gevent 等の本番用サーバー推奨）
    socketio.run(app, host='0.0.0.0', port=9600, debug=True, allow_unsafe_werkzeug=True)
