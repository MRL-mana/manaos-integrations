#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 音声統合ダッシュボード
Flask + WebSocket + 音声フィードバック

機能:
- リアルタイムメトリクス表示
- 音声コマンド受付
- 音声フィードバック
- アラート履歴
- 統計グラフ
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
from datetime import datetime
from manaos_voice_monitoring import VoiceMonitoringEngine

app = Flask(__name__)
app.config['SECRET_KEY'] = 'manaos-voice-dashboard-2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# グローバル監視エンジン
monitoring_engine = None
background_thread = None


def background_monitoring():
    """バックグラウンド監視スレッド"""
    global monitoring_engine
    
    while True:
        try:
            # メトリクス収集
            metrics = monitoring_engine.collect_metrics()
            
            # 異常検知
            alerts = monitoring_engine.analyze_metrics(metrics)
            
            # WebSocket経由でクライアントに送信
            socketio.emit('metrics_update', {
                'metrics': metrics,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            })
            
            # アラート処理
            if alerts:
                monitoring_engine.handle_alerts(alerts)
            
            time.sleep(10)  # 10秒ごと
            
        except Exception as e:
            print(f"監視エラー: {e}")
            time.sleep(30)


@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template('voice_dashboard.html')


@app.route('/api/status')
def api_status():
    """現在のステータス取得"""
    if not monitoring_engine:
        return jsonify({'error': 'Engine not initialized'}), 500
    
    metrics = monitoring_engine.collect_metrics()
    alerts = monitoring_engine.analyze_metrics(metrics)
    
    return jsonify({
        'metrics': metrics,
        'alerts': alerts,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/statistics')
def api_statistics():
    """統計情報取得"""
    if not monitoring_engine:
        return jsonify({'error': 'Engine not initialized'}), 500
    
    hours = request.args.get('hours', default=24, type=int)
    stats = monitoring_engine.get_statistics(hours=hours)
    
    return jsonify(stats)


@app.route('/api/alerts')
def api_alerts():
    """最近のアラート取得"""
    if not monitoring_engine:
        return jsonify({'error': 'Engine not initialized'}), 500
    
    limit = request.args.get('limit', default=20, type=int)
    alerts = monitoring_engine.get_recent_alerts(limit=limit)
    
    return jsonify(alerts)


@app.route('/api/voice-query', methods=['POST'])
def api_voice_query():
    """音声クエリ処理"""
    if not monitoring_engine:
        return jsonify({'error': 'Engine not initialized'}), 500
    
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    result = monitoring_engine.voice_query(query)
    
    return jsonify(result)


@socketio.on('connect')
def handle_connect():
    """WebSocket接続"""
    print('クライアント接続')
    emit('connected', {'status': 'ok'})


@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket切断"""
    print('クライアント切断')


@socketio.on('voice_query')
def handle_voice_query(data):
    """音声クエリ（WebSocket）"""
    query = data.get('query', '')
    
    if monitoring_engine and query:
        result = monitoring_engine.voice_query(query)
        emit('voice_response', result)


def create_dashboard_html():
    """ダッシュボードHTML作成"""
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 ManaOS 音声統合ダッシュボード</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            padding: 30px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .card h2 {
            font-size: 1.5em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .metric-box {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        
        .metric-label {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
        }
        
        .metric-bar {
            height: 10px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 5px;
            margin-top: 10px;
            overflow: hidden;
        }
        
        .metric-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981, #3b82f6);
            transition: width 0.5s;
        }
        
        .metric-bar-fill.warning {
            background: linear-gradient(90deg, #f59e0b, #ef4444);
        }
        
        .metric-bar-fill.critical {
            background: linear-gradient(90deg, #ef4444, #dc2626);
        }
        
        .voice-control {
            text-align: center;
        }
        
        .voice-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 20px 40px;
            border-radius: 50px;
            font-size: 1.2em;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        
        .voice-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }
        
        .voice-btn:active {
            transform: scale(0.95);
        }
        
        .voice-input {
            width: 100%;
            padding: 15px;
            border-radius: 10px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 1.1em;
            margin: 10px 0;
        }
        
        .voice-response {
            background: rgba(16, 185, 129, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            border-left: 4px solid #10b981;
        }
        
        .alert-item {
            background: rgba(239, 68, 68, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid #ef4444;
        }
        
        .alert-item.warning {
            background: rgba(245, 158, 11, 0.2);
            border-left-color: #f59e0b;
        }
        
        .alert-item.critical {
            background: rgba(220, 38, 38, 0.3);
            border-left-color: #dc2626;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-indicator.online {
            background: #10b981;
            box-shadow: 0 0 10px #10b981;
        }
        
        .status-indicator.offline {
            background: #ef4444;
        }
        
        .chart-container {
            height: 300px;
            margin-top: 20px;
        }
        
        .timestamp {
            text-align: center;
            opacity: 0.7;
            margin-top: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 ManaOS 音声統合ダッシュボード</h1>
            <p>
                <span class="status-indicator online" id="wsStatus"></span>
                リアルタイム監視中
            </p>
        </div>
        
        <div class="grid">
            <!-- システムメトリクス -->
            <div class="card">
                <h2>📊 システムメトリクス</h2>
                
                <div class="metric-box">
                    <div class="metric-label">CPU使用率</div>
                    <div class="metric-value" id="cpu-value">0%</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" id="cpu-bar"></div>
                    </div>
                </div>
                
                <div class="metric-box">
                    <div class="metric-label">メモリ使用率</div>
                    <div class="metric-value" id="memory-value">0%</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" id="memory-bar"></div>
                    </div>
                </div>
                
                <div class="metric-box">
                    <div class="metric-label">ディスク使用率</div>
                    <div class="metric-value" id="disk-value">0%</div>
                    <div class="metric-bar">
                        <div class="metric-bar-fill" id="disk-bar"></div>
                    </div>
                </div>
                
                <div class="metric-box">
                    <div class="metric-label">プロセス数</div>
                    <div class="metric-value" id="process-value">0</div>
                </div>
            </div>
            
            <!-- 音声コントロール -->
            <div class="card">
                <h2>🎙️ 音声コントロール</h2>
                <div class="voice-control">
                    <input type="text" class="voice-input" id="voiceQuery" 
                           placeholder="質問を入力してください（例: システムの状態は？）">
                    <button class="voice-btn" onclick="sendVoiceQuery()">
                        🔊 音声で質問
                    </button>
                    
                    <div id="voiceResponse" style="display:none;" class="voice-response">
                        <strong>応答:</strong>
                        <p id="responseText"></p>
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <strong>使用例:</strong>
                    <ul style="margin-top: 10px; opacity: 0.8;">
                        <li>システムの状態は？</li>
                        <li>CPU使用率は？</li>
                        <li>メモリは大丈夫？</li>
                        <li>Dockerコンテナは？</li>
                        <li>ManaOSの状態は？</li>
                    </ul>
                </div>
            </div>
            
            <!-- アラート -->
            <div class="card">
                <h2>🚨 アラート履歴</h2>
                <div id="alerts-container">
                    <p style="opacity: 0.7;">アラートはありません</p>
                </div>
            </div>
            
            <!-- 統計 -->
            <div class="card">
                <h2>📈 24時間統計</h2>
                <div id="stats-container">
                    読み込み中...
                </div>
                <div class="chart-container">
                    <canvas id="statsChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="timestamp" id="lastUpdate">
            最終更新: -
        </div>
    </div>
    
    <script>
        // WebSocket接続
        const socket = io();
        
        socket.on('connect', () => {
            console.log('WebSocket接続完了');
            document.getElementById('wsStatus').className = 'status-indicator online';
        });
        
        socket.on('disconnect', () => {
            console.log('WebSocket切断');
            document.getElementById('wsStatus').className = 'status-indicator offline';
        });
        
        // メトリクス更新
        socket.on('metrics_update', (data) => {
            updateMetrics(data.metrics);
            updateAlerts(data.alerts);
            
            document.getElementById('lastUpdate').textContent = 
                '最終更新: ' + new Date().toLocaleTimeString('ja-JP');
        });
        
        // 音声応答
        socket.on('voice_response', (data) => {
            showVoiceResponse(data.response);
        });
        
        function updateMetrics(metrics) {
            // CPU
            updateMetric('cpu', metrics.cpu_percent);
            
            // メモリ
            updateMetric('memory', metrics.memory_percent);
            
            // ディスク
            updateMetric('disk', metrics.disk_percent);
            
            // プロセス
            document.getElementById('process-value').textContent = metrics.process_count;
        }
        
        function updateMetric(name, value) {
            const valueEl = document.getElementById(name + '-value');
            const barEl = document.getElementById(name + '-bar');
            
            valueEl.textContent = value.toFixed(1) + '%';
            barEl.style.width = value + '%';
            
            // 色変更
            if (value >= 95) {
                barEl.className = 'metric-bar-fill critical';
            } else if (value >= 85) {
                barEl.className = 'metric-bar-fill warning';
            } else {
                barEl.className = 'metric-bar-fill';
            }
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<p style="opacity: 0.7;">アラートはありません</p>';
                return;
            }
            
            let html = '';
            alerts.forEach(alert => {
                html += `
                    <div class="alert-item ${alert.level}">
                        <strong>[${alert.level.toUpperCase()}] ${alert.category}</strong>
                        <p>${alert.message}</p>
                        <small>値: ${alert.value.toFixed(1)}, 閾値: ${alert.threshold}</small>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        function sendVoiceQuery() {
            const query = document.getElementById('voiceQuery').value;
            if (!query) return;
            
            // WebSocket経由で送信
            socket.emit('voice_query', {query: query});
            
            // または REST API
            fetch('/api/voice-query', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            })
            .then(res => res.json())
            .then(data => {
                showVoiceResponse(data.response);
            });
        }
        
        function showVoiceResponse(response) {
            const responseDiv = document.getElementById('voiceResponse');
            const responseText = document.getElementById('responseText');
            
            responseText.textContent = response;
            responseDiv.style.display = 'block';
        }
        
        // Enterキーで送信
        document.getElementById('voiceQuery').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendVoiceQuery();
            }
        });
        
        // 統計取得
        function loadStatistics() {
            fetch('/api/statistics')
                .then(res => res.json())
                .then(data => {
                    const container = document.getElementById('stats-container');
                    container.innerHTML = `
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div>
                                <strong>CPU平均:</strong> ${data.metrics.cpu_avg.toFixed(1)}%<br>
                                <strong>CPU最大:</strong> ${data.metrics.cpu_max.toFixed(1)}%
                            </div>
                            <div>
                                <strong>メモリ平均:</strong> ${data.metrics.memory_avg.toFixed(1)}%<br>
                                <strong>メモリ最大:</strong> ${data.metrics.memory_max.toFixed(1)}%
                            </div>
                            <div>
                                <strong>ディスク平均:</strong> ${data.metrics.disk_avg.toFixed(1)}%<br>
                                <strong>ディスク最大:</strong> ${data.metrics.disk_max.toFixed(1)}%
                            </div>
                            <div>
                                <strong>総アラート:</strong> ${data.total_alerts}件<br>
                                <strong>測定回数:</strong> ${data.metrics.count}回
                            </div>
                        </div>
                    `;
                    
                    // グラフ更新
                    updateChart(data);
                });
        }
        
        let statsChart = null;
        
        function updateChart(data) {
            const ctx = document.getElementById('statsChart').getContext('2d');
            
            if (statsChart) {
                statsChart.destroy();
            }
            
            statsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['CPU', 'メモリ', 'ディスク'],
                    datasets: [{
                        label: '平均値',
                        data: [
                            data.metrics.cpu_avg,
                            data.metrics.memory_avg,
                            data.metrics.disk_avg
                        ],
                        backgroundColor: 'rgba(16, 185, 129, 0.5)'
                    }, {
                        label: '最大値',
                        data: [
                            data.metrics.cpu_max,
                            data.metrics.memory_max,
                            data.metrics.disk_max
                        ],
                        backgroundColor: 'rgba(239, 68, 68, 0.5)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {color: 'white'}
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {color: 'white'}
                        },
                        x: {
                            ticks: {color: 'white'}
                        }
                    }
                }
            });
        }
        
        // 初期ロード
        loadStatistics();
        
        // 定期更新
        setInterval(loadStatistics, 60000); // 1分ごと
    </script>
</body>
</html>"""
    
    # テンプレートディレクトリ作成
    import os
    os.makedirs('/root/templates', exist_ok=True)
    
    with open('/root/templates/voice_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html)


def main():
    """メイン関数"""
    global monitoring_engine, background_thread
    
    # HTMLテンプレート作成
    create_dashboard_html()
    
    # 監視エンジン初期化
    monitoring_engine = VoiceMonitoringEngine(enable_voice=True)
    
    # バックグラウンドスレッド開始
    background_thread = threading.Thread(target=background_monitoring, daemon=True)
    background_thread.start()
    
    print("""
╔══════════════════════════════════════════════════════╗
║  🎤 ManaOS 音声統合ダッシュボード                   ║
╚══════════════════════════════════════════════════════╝

起動中...

アクセス:
  http://localhost:6060
  http://163.44.120.49:6060 (外部)

""")
    
    # Flask起動
    socketio.run(app, host='0.0.0.0', port=6060, debug=False)


if __name__ == '__main__':
    main()

