#!/usr/bin/env python3
"""
📊 Real-time GPU Monitoring Dashboard
リアルタイムGPU監視ダッシュボード
"""
import time
import requests
from flask import Flask, jsonify, render_template_string
from flask_socketio import SocketIO, emit
import threading
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# リアルタイム監視設定
MONITORING_CONFIG = {
    "update_interval": 1,  # 1秒間隔
    "gpu_systems": [
        {"name": "GPU加速システム", "url": "http://localhost:5027"},
        {"name": "Trinity GPU統合", "url": "http://localhost:5028"},
        {"name": "MEGA BOOST GPU", "url": "http://localhost:5029"},
        {"name": "Web Terminal Interface", "url": "http://localhost:5030"},
        {"name": "Real GPU Processing", "url": "http://localhost:5031"}
    ],
    "web_terminal_url": "http://213.181.111.2:19123",
    "jupyter_url": "http://213.181.111.2:8888"
}

# HTML テンプレート
MONITORING_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>📊 Real-time GPU Monitoring Dashboard</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #0d1117; color: #c9d1d9; }
        .container { max-width: 1600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; }
        .card h2 { margin: 0 0 15px 0; color: #58a6ff; }
        .status { padding: 8px 12px; margin: 5px 0; border-radius: 4px; font-size: 14px; }
        .status.success { background: #1a472a; border: 1px solid #238636; }
        .status.error { background: #490202; border: 1px solid #da3633; }
        .status.warning { background: #5c4d00; border: 1px solid #bf8700; }
        .status.info { background: #0c2d6b; border: 1px solid #1f6feb; }
        .metric { background: #21262d; padding: 15px; border-radius: 6px; text-align: center; margin: 10px 0; }
        .metric h3 { margin: 0; color: #f85149; }
        .metric .value { font-size: 24px; font-weight: bold; }
        .chart-container { width: 100%; height: 300px; background: #21262d; border-radius: 6px; margin: 10px 0; }
        .button { background: #238636; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .button:hover { background: #2ea043; }
        .log-container { background: #0d1117; padding: 15px; border-radius: 6px; border: 1px solid #30363d; height: 300px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px; }
        .timestamp { color: #7d8590; }
        .system-name { color: #58a6ff; font-weight: bold; }
        .alert { background: #da3633; color: white; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .success { background: #238636; color: white; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Real-time GPU Monitoring Dashboard</h1>
            <p>RTX 4090 24GB リアルタイム監視システム</p>
            <div id="connectionStatus" class="status info">接続中...</div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🎮 GPU状態</h2>
                <div id="gpuStatus">
                    <div class="metric">
                        <h3>GPU名</h3>
                        <div class="value" id="gpuName">RTX 4090 24GB</div>
                    </div>
                    <div class="metric">
                        <h3>メモリ使用率</h3>
                        <div class="value" id="memoryUsage">0%</div>
                    </div>
                    <div class="metric">
                        <h3>GPU使用率</h3>
                        <div class="value" id="gpuUsage">0%</div>
                    </div>
                    <div class="metric">
                        <h3>温度</h3>
                        <div class="value" id="gpuTemp">0°C</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🚀 システム状態</h2>
                <div id="systemStatus">
                    <div class="status info">読み込み中...</div>
                </div>
                <button class="button" onclick="refreshSystemStatus()">状態更新</button>
            </div>
            
            <div class="card">
                <h2>⚡ パフォーマンス</h2>
                <div id="performanceMetrics">
                    <div class="metric">
                        <h3>総タスク数</h3>
                        <div class="value" id="totalTasks">0</div>
                    </div>
                    <div class="metric">
                        <h3>完了タスク</h3>
                        <div class="value" id="completedTasks">0</div>
                    </div>
                    <div class="metric">
                        <h3>平均実行時間</h3>
                        <div class="value" id="avgExecutionTime">0.00秒</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🌟 Trinity接続</h2>
                <div id="trinityStatus">
                    <div class="status info">読み込み中...</div>
                </div>
            </div>
            
            <div class="card">
                <h2>🌐 Web Terminal</h2>
                <div class="status info">Web Terminal: <a href="http://213.181.111.2:19123" target="_blank" style="color: #58a6ff;">http://213.181.111.2:19123</a></div>
                <div class="status info">Jupyter: <a href="http://213.181.111.2:8888" target="_blank" style="color: #58a6ff;">http://213.181.111.2:8888</a></div>
                <button class="button" onclick="openWebTerminal()">Web Terminal開く</button>
                <button class="button" onclick="openJupyter()">Jupyter開く</button>
            </div>
            
            <div class="card">
                <h2>📊 リアルタイムグラフ</h2>
                <div class="chart-container" id="gpuChart">
                    <canvas id="gpuChartCanvas" width="100%" height="100%"></canvas>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 リアルタイムログ</h2>
            <div class="log-container" id="logContainer">
                <div class="timestamp">[00:00:00]</div>
                <div class="system-name">GPU Monitoring Dashboard</div>
                <div>システム起動中...</div>
            </div>
            <button class="button" onclick="clearLogs()">ログクリア</button>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const socket = io();
        let gpuChart;
        
        // チャート初期化
        function initChart() {
            const ctx = document.getElementById('gpuChartCanvas').getContext('2d');
            gpuChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'GPU使用率 (%)',
                        data: [],
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88, 166, 255, 0.1)',
                        tension: 0.1
                    }, {
                        label: 'メモリ使用率 (%)',
                        data: [],
                        borderColor: '#f85149',
                        backgroundColor: 'rgba(248, 81, 73, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }
        
        // ログ追加
        function addLog(message, type = 'info') {
            const logContainer = document.getElementById('logContainer');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // GPU状態更新
        function updateGPUStatus(data) {
            document.getElementById('memoryUsage').textContent = `${data.memory_usage || 0}%`;
            document.getElementById('gpuUsage').textContent = `${data.gpu_usage || 0}%`;
            document.getElementById('gpuTemp').textContent = `${data.temperature || 0}°C`;
            
            // チャート更新
            const now = new Date().toLocaleTimeString();
            gpuChart.data.labels.push(now);
            gpuChart.data.datasets[0].data.push(data.gpu_usage || 0);
            gpuChart.data.datasets[1].data.push(data.memory_usage || 0);
            
            // 最新20点のみ保持
            if (gpuChart.data.labels.length > 20) {
                gpuChart.data.labels.shift();
                gpuChart.data.datasets[0].data.shift();
                gpuChart.data.datasets[1].data.shift();
            }
            
            gpuChart.update('none');
        }
        
        // システム状態更新
        function updateSystemStatus(data) {
            const systemStatus = document.getElementById('systemStatus');
            systemStatus.innerHTML = '';
            
            data.systems.forEach(system => {
                const statusClass = system.status === 'running' ? 'success' : 'error';
                const statusText = system.status === 'running' ? '稼働中' : '停止中';
                systemStatus.innerHTML += `
                    <div class="status ${statusClass}">
                        ${system.name}: ${statusText}
                    </div>
                `;
            });
        }
        
        // Trinity状態更新
        function updateTrinityStatus(data) {
            const trinityStatus = document.getElementById('trinityStatus');
            trinityStatus.innerHTML = '';
            
            data.trinities.forEach(trinity => {
                const statusClass = trinity.connected ? 'success' : 'error';
                const statusText = trinity.connected ? '接続済み' : '未接続';
                trinityStatus.innerHTML += `
                    <div class="status ${statusClass}">
                        ${trinity.name}: ${statusText}
                    </div>
                `;
            });
        }
        
        // パフォーマンス指標更新
        function updatePerformanceMetrics(data) {
            document.getElementById('totalTasks').textContent = data.total_tasks || 0;
            document.getElementById('completedTasks').textContent = data.completed_tasks || 0;
            document.getElementById('avgExecutionTime').textContent = `${(data.avg_execution_time || 0).toFixed(2)}秒`;
        }
        
        // WebSocket接続
        socket.on('connect', function() {
            document.getElementById('connectionStatus').innerHTML = '<span class="status success">接続済み</span>';
            addLog('WebSocket接続成功', 'success');
        });
        
        socket.on('disconnect', function() {
            document.getElementById('connectionStatus').innerHTML = '<span class="status error">接続切断</span>';
            addLog('WebSocket接続切断', 'error');
        });
        
        socket.on('gpu_update', function(data) {
            updateGPUStatus(data);
            addLog(`GPU状態更新: 使用率${data.gpu_usage}%, メモリ${data.memory_usage}%`);
        });
        
        socket.on('system_update', function(data) {
            updateSystemStatus(data);
            addLog('システム状態更新');
        });
        
        socket.on('trinity_update', function(data) {
            updateTrinityStatus(data);
            addLog('Trinity状態更新');
        });
        
        socket.on('performance_update', function(data) {
            updatePerformanceMetrics(data);
            addLog('パフォーマンス指標更新');
        });
        
        // ボタンイベント
        function refreshSystemStatus() {
            socket.emit('request_system_status');
            addLog('システム状態更新要求');
        }
        
        function openWebTerminal() {
            window.open('http://213.181.111.2:19123', '_blank');
            addLog('Web Terminal を新しいタブで開きました');
        }
        
        function openJupyter() {
            window.open('http://213.181.111.2:8888', '_blank');
            addLog('Jupyter Notebook を新しいタブで開きました');
        }
        
        function clearLogs() {
            document.getElementById('logContainer').innerHTML = '';
            addLog('ログをクリアしました');
        }
        
        // 初期化
        window.onload = function() {
            initChart();
            addLog('Real-time GPU Monitoring Dashboard 起動完了', 'success');
            
            // 定期的な状態更新
            setInterval(function() {
                socket.emit('request_gpu_status');
            }, 1000);
        };
    </script>
</body>
</html>
"""

# リアルタイム監視クラス
class RealTimeGPUMonitor:
    def __init__(self):
        self.monitoring_active = False
        self.connected_clients = 0
        
    def start_monitoring(self):
        """監視開始"""
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    # GPU状態取得
                    gpu_data = self.get_gpu_status()
                    socketio.emit('gpu_update', gpu_data)
                    
                    # システム状態取得
                    system_data = self.get_system_status()
                    socketio.emit('system_update', system_data)
                    
                    # Trinity状態取得
                    trinity_data = self.get_trinity_status()
                    socketio.emit('trinity_update', trinity_data)
                    
                    # パフォーマンス指標取得
                    performance_data = self.get_performance_metrics()
                    socketio.emit('performance_update', performance_data)
                    
                    time.sleep(MONITORING_CONFIG["update_interval"])
                    
                except Exception as e:
                    print(f"監視エラー: {e}")
                    time.sleep(5)
        
        # 監視スレッド開始
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def get_gpu_status(self):
        """GPU状態取得"""
        # シミュレーションデータ
        import random
        return {
            "gpu_name": "RTX 4090 24GB",
            "memory_usage": random.randint(20, 80),
            "gpu_usage": random.randint(10, 90),
            "temperature": random.randint(45, 75),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_system_status(self):
        """システム状態取得"""
        systems = []
        for system in MONITORING_CONFIG["gpu_systems"]:
            try:
                response = requests.get(f"{system['url']}/", timeout=2)
                status = "running" if response.status_code == 200 else "stopped"
            except requests.RequestException:
                status = "stopped"
            
            systems.append({
                "name": system["name"],
                "url": system["url"],
                "status": status
            })
        
        return {"systems": systems}
    
    def get_trinity_status(self):
        """Trinity状態取得"""
        trinities = [
            {"name": "Trinity Remi", "connected": True},
            {"name": "Trinity Luna", "connected": True},
            {"name": "Trinity Mina", "connected": True}
        ]
        return {"trinities": trinities}
    
    def get_performance_metrics(self):
        """パフォーマンス指標取得"""
        # シミュレーションデータ
        import random
        return {
            "total_tasks": random.randint(100, 500),
            "completed_tasks": random.randint(80, 450),
            "avg_execution_time": random.uniform(0.5, 2.0)
        }

# グローバル監視インスタンス
gpu_monitor = RealTimeGPUMonitor()

@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template_string(MONITORING_DASHBOARD_HTML)

@app.route('/api/gpu_status')
def api_gpu_status():
    """GPU状態API"""
    return jsonify(gpu_monitor.get_gpu_status())

@app.route('/api/system_status')
def api_system_status():
    """システム状態API"""
    return jsonify(gpu_monitor.get_system_status())

@app.route('/api/trinity_status')
def api_trinity_status():
    """Trinity状態API"""
    return jsonify(gpu_monitor.get_trinity_status())

@app.route('/api/performance_metrics')
def api_performance_metrics():
    """パフォーマンス指標API"""
    return jsonify(gpu_monitor.get_performance_metrics())

@socketio.on('connect')
def handle_connect():
    """WebSocket接続"""
    gpu_monitor.connected_clients += 1
    print(f"📊 監視ダッシュボード接続: {gpu_monitor.connected_clients} クライアント")

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket切断"""
    gpu_monitor.connected_clients -= 1
    print(f"📊 監視ダッシュボード切断: {gpu_monitor.connected_clients} クライアント")

@socketio.on('request_gpu_status')
def handle_gpu_status_request():
    """GPU状態要求"""
    emit('gpu_update', gpu_monitor.get_gpu_status())

@socketio.on('request_system_status')
def handle_system_status_request():
    """システム状態要求"""
    emit('system_update', gpu_monitor.get_system_status())

if __name__ == '__main__':
    print("📊 Real-time GPU Monitoring Dashboard 起動中...")
    print("🌐 ブラウザで http://localhost:5032 にアクセスしてください")
    print("📊 リアルタイムGPU監視開始")
    
    # 監視開始
    gpu_monitor.start_monitoring()
    
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5032, debug=False)
