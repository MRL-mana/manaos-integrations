#!/usr/bin/env python3
"""
📊 Turbo Dashboard - リアルタイムWebダッシュボード
システム監視、タスク実行状況を可視化
"""

from flask import Flask, render_template, jsonify, request
import psutil
import json
import os
from datetime import datetime
from pathlib import Path
import threading
import time

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# グローバル状態
system_status = {
    "cpu": 0,
    "memory": 0,
    "disk": 0,
    "load": 0,
    "processes": 0,
    "gpu_available": False
}

running_tasks = []
task_history = []

def update_system_status():
    """システム状態更新（バックグラウンド）"""
    import requests
    
    while True:
        try:
            # CPU/メモリ/ディスク
            system_status["cpu"] = psutil.cpu_percent(interval=1)
            system_status["memory"] = psutil.virtual_memory().percent
            system_status["disk"] = psutil.disk_usage('/').percent
            system_status["load"] = psutil.getloadavg()[0]
            system_status["processes"] = len(list(psutil.process_iter()))
            
            # GPU状態
            try:
                resp = requests.get("http://localhost:5009/trinity/gpu/status", timeout=2)
                if resp.status_code == 200:
                    data = resp.json()
                    system_status["gpu_available"] = data.get("gpu_info", {}).get("gpu", False)
                    system_status["gpu_name"] = data.get("gpu_info", {}).get("name", "")
                    system_status["gpu_vram"] = data.get("gpu_info", {}).get("memory", 0)
            except requests.RequestException:
                system_status["gpu_available"] = False
            
            time.sleep(2)
        except requests.RequestException:
            time.sleep(5)

# バックグラウンドスレッド開始
monitor_thread = threading.Thread(target=update_system_status, daemon=True)
monitor_thread.start()

@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """システム状態API"""
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "system": system_status,
        "running_tasks": len(running_tasks),
        "completed_tasks": len(task_history)
    })

@app.route('/api/tasks')
def api_tasks():
    """タスク一覧API"""
    return jsonify({
        "running": running_tasks,
        "history": task_history[-50:]  # 最新50件
    })

@app.route('/api/logs')
def api_logs():
    """ログAPI"""
    log_files = {
        "mega_boost": "/root/logs/mega_boost.log",
        "system_optimizer": "/root/logs/system_optimizer.log",
        "system_monitor": "/root/logs/system_monitor.log"
    }
    
    log_type = request.args.get('type', 'mega_boost')
    lines = int(request.args.get('lines', 50))
    
    log_file = log_files.get(log_type)
    if log_file and Path(log_file).exists():
        with open(log_file) as f:
            all_lines = f.readlines()
            return jsonify({"logs": all_lines[-lines:]})
    
    return jsonify({"logs": []})

@app.route('/api/reports')
def api_reports():
    """レポート一覧API"""
    reports_dir = Path("/root/logs")
    reports = []
    
    for report_file in sorted(reports_dir.glob("*_report_*.json"), reverse=True)[:20]:
        try:
            with open(report_file) as f:
                data = json.load(f)
                reports.append({
                    "filename": report_file.name,
                    "timestamp": data.get("timestamp", ""),
                    "stats": data.get("stats", {})
                })
        except IOError:
            pass
    
    return jsonify({"reports": reports})

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    """システム最適化実行"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["python3", "/root/system_optimizer.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# HTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Turbo Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2.5em; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .card h2 {
            font-size: 1.2em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .metric {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00f260, #0575e6);
            transition: width 0.3s;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-online { background: #00f260; color: #000; }
        .status-offline { background: #ff6b6b; }
        .btn {
            background: rgba(255,255,255,0.2);
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
        }
        .btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .log-box {
            background: rgba(0,0,0,0.5);
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            max-height: 400px;
            overflow-y: auto;
        }
        .timestamp { color: #aaa; font-size: 0.8em; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .pulse { animation: pulse 2s infinite; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Turbo Dashboard</h1>
        
        <div class="grid">
            <!-- CPU -->
            <div class="card">
                <h2>💻 CPU</h2>
                <div class="metric" id="cpu">0%</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" style="width:0%"></div>
                </div>
                <div>負荷: <span id="load">0.00</span></div>
            </div>
            
            <!-- メモリ -->
            <div class="card">
                <h2>💾 メモリ</h2>
                <div class="metric" id="memory">0%</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar" style="width:0%"></div>
                </div>
            </div>
            
            <!-- ディスク -->
            <div class="card">
                <h2>💿 ディスク</h2>
                <div class="metric" id="disk">0%</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="disk-bar" style="width:0%"></div>
                </div>
            </div>
            
            <!-- GPU -->
            <div class="card">
                <h2>🎮 GPU</h2>
                <div class="status-badge" id="gpu-status">オフライン</div>
                <div id="gpu-name" style="margin-top:10px; font-size:0.9em;"></div>
                <div id="gpu-vram" style="font-size:0.9em; color:#aaa;"></div>
            </div>
            
            <!-- タスク -->
            <div class="card">
                <h2>⚙️ タスク</h2>
                <div>実行中: <span class="metric" id="running-tasks">0</span></div>
                <div>完了: <span id="completed-tasks">0</span></div>
                <div>プロセス: <span id="processes">0</span></div>
            </div>
            
            <!-- クイックアクション -->
            <div class="card">
                <h2>🔧 クイックアクション</h2>
                <button class="btn" onclick="optimize()">システム最適化</button>
                <button class="btn" onclick="location.reload()">リロード</button>
            </div>
        </div>
        
        <!-- ログ -->
        <div class="card">
            <h2>📄 ログ（最新50行）</h2>
            <div class="log-box" id="logs">読み込み中...</div>
        </div>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    const sys = data.system;
                    
                    // CPU
                    document.getElementById('cpu').textContent = sys.cpu.toFixed(1) + '%';
                    document.getElementById('cpu-bar').style.width = sys.cpu + '%';
                    document.getElementById('load').textContent = sys.load.toFixed(2);
                    
                    // メモリ
                    document.getElementById('memory').textContent = sys.memory.toFixed(1) + '%';
                    document.getElementById('memory-bar').style.width = sys.memory + '%';
                    
                    // ディスク
                    document.getElementById('disk').textContent = sys.disk.toFixed(1) + '%';
                    document.getElementById('disk-bar').style.width = sys.disk + '%';
                    
                    // GPU
                    const gpuStatus = document.getElementById('gpu-status');
                    if (sys.gpu_available) {
                        gpuStatus.textContent = 'オンライン';
                        gpuStatus.className = 'status-badge status-online pulse';
                        document.getElementById('gpu-name').textContent = sys.gpu_name || '';
                        document.getElementById('gpu-vram').textContent = sys.gpu_vram ? 
                            `VRAM: ${sys.gpu_vram.toFixed(1)}GB` : '';
                    } else {
                        gpuStatus.textContent = 'オフライン';
                        gpuStatus.className = 'status-badge status-offline';
                    }
                    
                    // タスク
                    document.getElementById('running-tasks').textContent = data.running_tasks;
                    document.getElementById('completed-tasks').textContent = data.completed_tasks;
                    document.getElementById('processes').textContent = sys.processes;
                });
        }
        
        function updateLogs() {
            fetch('/api/logs?type=mega_boost&lines=50')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('logs').innerHTML = 
                        data.logs.map(line => line.replace(/</g, '&lt;').replace(/>/g, '&gt;')).join('');
                });
        }
        
        function optimize() {
            if (confirm('システム最適化を実行しますか？')) {
                fetch('/api/optimize', {method: 'POST'})
                    .then(r => r.json())
                    .then(data => {
                        alert(data.success ? '✅ 最適化完了' : '❌ エラー: ' + data.error);
                    });
            }
        }
        
        // 初回実行
        updateStatus();
        updateLogs();
        
        // 定期更新
        setInterval(updateStatus, 2000);  // 2秒ごと
        setInterval(updateLogs, 5000);    // 5秒ごと
    </script>
</body>
</html>
"""

# テンプレートディレクトリ作成＆HTML保存
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
with open(templates_dir / "dashboard.html", "w", encoding="utf-8") as f:
    f.write(DASHBOARD_HTML)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Turbo Dashboard 起動")
    print("=" * 60)
    print()
    print("📊 ダッシュボード: http://localhost:8888")
    print("📊 外部アクセス: http://163.44.120.49:8888")
    print("📊 Tailscale: http://100.93.120.33:8888")
    print()
    print("Ctrl+C で停止")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8888, debug=os.getenv("DEBUG", "False").lower() == "true")

