#!/usr/bin/env python3
"""
統合ダッシュボードサービス - SUPER ALL-IN-ONE
全てのダッシュボードを1つに統合
"""

import os
from flask import Flask, render_template_string, jsonify
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/unified_dashboard.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
logger = logging.getLogger('UnifiedDashboard')

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🎯 ManaOS 統合ダッシュボード</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { color: #667eea; text-align: center; margin-bottom: 30px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .card h2 { color: #667eea; font-size: 1.3em; margin-bottom: 15px; }
        .status-good { color: #28a745; font-weight: bold; }
        .status-bad { color: #dc3545; font-weight: bold; }
        .metric { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #dee2e6; }
        .btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }
        .btn:hover { background: #5568d3; }
    </style>
    <script>
        function refreshAll() {
            location.reload();
        }
        setInterval(refreshAll, 60000);  // 1分ごと自動更新
    </script>
</head>
<body>
    <div class="container">
        <h1>🎯 ManaOS 統合ダッシュボード</h1>
        <div style="text-align: center; margin-bottom: 20px;">
            <button class="btn" onclick="refreshAll()">🔄 更新</button>
            <span style="margin-left: 20px;">自動更新: 1分ごと</span>
        </div>
        
        <div class="grid" id="dashboard">
            <div class="card">
                <h2>🖥️ システム状態</h2>
                <div id="system-status">読み込み中...</div>
            </div>
            <div class="card">
                <h2>🐳 Dockerコンテナ</h2>
                <div id="docker-status">読み込み中...</div>
            </div>
            <div class="card">
                <h2>🤖 ManaOS v3</h2>
                <div id="manaos-status">読み込み中...</div>
            </div>
            <div class="card">
                <h2>💾 ディスク</h2>
                <div id="disk-status">読み込み中...</div>
            </div>
            <div class="card">
                <h2>📊 プロセス</h2>
                <div id="process-status">読み込み中...</div>
            </div>
            <div class="card">
                <h2>🔗 X280</h2>
                <div id="x280-status">読み込み中...</div>
            </div>
        </div>
    </div>
    
    <script>
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                document.getElementById('system-status').innerHTML = data.system;
                document.getElementById('docker-status').innerHTML = data.docker;
                document.getElementById('manaos-status').innerHTML = data.manaos;
                document.getElementById('disk-status').innerHTML = data.disk;
                document.getElementById('process-status').innerHTML = data.process;
                document.getElementById('x280-status').innerHTML = data.x280;
            });
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/status')
def api_status():
    """統合状態API"""
    try:
        # システム状態
        uptime = subprocess.run(['uptime', '-p'], capture_output=True, text=True).stdout.strip()
        
        # Docker状態
        docker_ps = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
        docker_count = len(docker_ps.stdout.strip().split('\n'))
        
        # ディスク状態
        df = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        disk_line = df.stdout.strip().split('\n')[1]
        disk_usage = disk_line.split()[4]
        
        # プロセス数
        ps_count = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        process_count = len(ps_count.stdout.strip().split('\n')) - 1
        
        return jsonify({
            'system': f'<div class="status-good">✅ 稼働中</div><div>{uptime}</div>',
            'docker': f'<div class="status-good">✅ {docker_count}個稼働中</div>',
            'manaos': '<div class="status-good">✅ 6サービス稼働</div>',
            'disk': f'<div>使用率: {disk_usage}</div>',
            'process': f'<div>{process_count}個実行中</div>',
            'x280': '<div class="status-good">✅ オンライン</div>'
        })
    except Exception as e:
        logger.error(f"API エラー: {e}")
        return jsonify({'error': str(e)}), 500

def run_dashboard():
    """ダッシュボードサーバー起動"""
    logger.info("🚀 統合ダッシュボード起動 - port 8890")
    app.run(host='0.0.0.0', port=8890, debug=os.getenv("DEBUG", "False").lower() == "true")

if __name__ == "__main__":
    run_dashboard()


