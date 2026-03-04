#!/usr/bin/env python3
"""
ManaOS Unified Portal
全サービスを統合した中央ポータル
"""

import os
from flask import Flask, render_template_string, jsonify
import requests
from datetime import datetime
import psutil

app = Flask(__name__)

TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 ManaOS Unified Portal</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            color: white;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding: 40px 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.15);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .service-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: all 0.3s;
            cursor: pointer;
        }
        .service-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }
        .service-card h3 {
            font-size: 1.5em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .status-online { background: #10b981; }
        .status-offline { background: #ef4444; }
        .status-degraded { background: #f59e0b; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .service-info {
            margin: 10px 0;
            font-size: 0.9em;
            opacity: 0.9;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            text-decoration: none;
            color: white;
            margin: 5px;
            transition: all 0.3s;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: scale(1.05);
        }
        .footer {
            text-align: center;
            padding: 20px;
            opacity: 0.8;
            margin-top: 30px;
        }
        .timestamp {
            font-size: 0.9em;
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 ManaOS Unified Portal</h1>
            <p>中央統合ポータル - 全サービスへのアクセス</p>
            <p class="timestamp">最終更新: <span id="timestamp">Loading...</span></p>
        </div>

        <div class="stats" id="stats">
            <div class="stat-card">
                <div>CPU使用率</div>
                <div class="stat-value" id="cpu">-</div>
            </div>
            <div class="stat-card">
                <div>メモリ使用率</div>
                <div class="stat-value" id="memory">-</div>
            </div>
            <div class="stat-card">
                <div>ディスク使用率</div>
                <div class="stat-value" id="disk">-</div>
            </div>
            <div class="stat-card">
                <div>オンラインサービス</div>
                <div class="stat-value" id="services-online">-</div>
            </div>
        </div>

        <h2 style="margin: 30px 0 20px; text-align: center;">🌐 サービス一覧</h2>
        <div class="services-grid" id="services-grid"></div>

        <div class="footer">
            <p>🚀 ManaOS v3.0 with Trinity Integration</p>
            <p>Powered by レミ（戦略指令AI）・ルナ（実務遂行AI）・ミナ（洞察記録AI）</p>
        </div>
    </div>

    <script>
        const services = [
            {
                name: 'ManaOS v3 Orchestrator',
                icon: '🎯',
                url: 'http://localhost:9200',
                description: 'レミ - 戦略指令AI',
                port: 9200
            },
            {
                name: 'Command Center',
                icon: '🎛️',
                url: 'http://localhost:10000',
                description: '統合管理ダッシュボード',
                port: 10000
            },
            {
                name: 'Trinity Secretary',
                icon: '🤖',
                url: 'http://localhost:8087',
                description: 'AI秘書システム',
                port: 8087
            },
            {
                name: 'Trinity Google Services',
                icon: '📧',
                url: 'http://localhost:8097',
                description: 'Gmail/Drive/Calendar統合',
                port: 8097
            },
            {
                name: 'Screen Sharing',
                icon: '🖥️',
                url: 'http://localhost:5008',
                description: '画面共有システム',
                port: 5008
            },
            {
                name: 'Intention Detector',
                icon: '🔍',
                url: 'http://localhost:9201',
                description: '意図検出システム',
                port: 9201
            },
            {
                name: 'Policy Manager',
                icon: '🔒',
                url: 'http://localhost:9202',
                description: 'ポリシー判定',
                port: 9202
            },
            {
                name: 'Actuator (Luna)',
                icon: '⚙️',
                url: 'http://localhost:9203',
                description: 'ルナ - 実務遂行AI',
                port: 9203
            },
            {
                name: 'Data Ingestor',
                icon: '📝',
                url: 'http://localhost:9204',
                description: 'データ取込システム',
                port: 9204
            },
            {
                name: 'Insight (Mina)',
                icon: '📊',
                url: 'http://localhost:9205',
                description: 'ミナ - 洞察記録AI',
                port: 9205
            }
        ];

        async function checkServiceStatus(url) {
            try {
                const response = await fetch(url, { timeout: 3000 });
                return response.ok ? 'online' : 'degraded';
            } catch {
                return 'offline';
            }
        }

        async function loadServices() {
            const grid = document.getElementById('services-grid');
            grid.innerHTML = '';
            
            let onlineCount = 0;

            for (const service of services) {
                const status = await checkServiceStatus(service.url);
                if (status === 'online') onlineCount++;

                const card = document.createElement('div');
                card.className = 'service-card';
                card.onclick = () => window.open(service.url, '_blank');
                
                card.innerHTML = `
                    <h3>
                        ${service.icon} ${service.name}
                        <span class="status-indicator status-${status}"></span>
                    </h3>
                    <div class="service-info">${service.description}</div>
                    <div class="service-info">ポート: ${service.port}</div>
                    <div class="service-info">ステータス: ${status.toUpperCase()}</div>
                    <a href="${service.url}" target="_blank" class="btn">開く →</a>
                `;
                
                grid.appendChild(card);
            }

            document.getElementById('services-online').textContent = 
                onlineCount + '/' + services.length;
        }

        async function loadSystemStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('cpu').textContent = data.cpu + '%';
                document.getElementById('memory').textContent = data.memory + '%';
                document.getElementById('disk').textContent = data.disk + '%';
                document.getElementById('timestamp').textContent = 
                    new Date().toLocaleString('ja-JP');
            } catch (error) {
                console.error('Stats load error:', error);
            }
        }

        // 初期ロード
        loadServices();
        loadSystemStats();

        // 30秒ごとに更新
        setInterval(() => {
            loadServices();
            loadSystemStats();
        }, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

@app.route('/api/stats')
def get_stats():
    cpu = round(psutil.cpu_percent(interval=1), 1)
    memory = round(psutil.virtual_memory().percent, 1)
    disk = round(psutil.disk_usage('/').percent, 1)
    
    return jsonify({
        'cpu': cpu,
        'memory': memory,
        'disk': disk,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/services')
def get_services():
    services = [
        {'name': 'ManaOS Orchestrator', 'url': 'http://localhost:9200', 'port': 9200},
        {'name': 'Command Center', 'url': 'http://localhost:10000', 'port': 10000},
        {'name': 'Trinity Secretary', 'url': 'http://localhost:8087', 'port': 8087},
        {'name': 'Trinity Google', 'url': 'http://localhost:8097', 'port': 8097},
        {'name': 'Screen Sharing', 'url': 'http://localhost:5008', 'port': 5008},
    ]
    
    for service in services:
        try:
            response = requests.get(service['url'], timeout=2)
            service['status'] = 'online' if response.status_code == 200 else 'degraded'
        except requests.RequestException:
            service['status'] = 'offline'
    
    return jsonify({'services': services})

if __name__ == '__main__':
    print("🚀 ManaOS Unified Portal 起動中...")
    print("📍 アクセス: http://localhost:8000")
    print("🌐 外部: http://100.93.120.33:8000 (Tailscale)")
    app.run(host='0.0.0.0', port=8000, debug=os.getenv("DEBUG", "False").lower() == "true")

