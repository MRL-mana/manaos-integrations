#!/usr/bin/env python3
"""
Trinity Orchestrator - Dashboard
リアルタイム履歴ダッシュボード（WebSocket対応）
"""

from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
import time
import json
from datetime import datetime
import logging

from ticket_manager import TicketManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trinity_dashboard")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trinity-dashboard-2025'
CORS(app)

ticket_manager = TicketManager()

# HTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trinity Orchestrator - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
        }
        .header h1 { color: #667eea; font-size: 2em; margin-bottom: 10px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            border-left: 4px solid #667eea;
        }
        .stat-card h3 { color: #667eea; font-size: 0.9em; margin-bottom: 10px; }
        .stat-card .value { font-size: 2em; font-weight: bold; color: #333; }
        .tickets-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 20px;
        }
        .tickets-panel h2 { color: #667eea; margin-bottom: 20px; }
        .ticket-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }
        .ticket-item.completed { border-left-color: #28a745; }
        .ticket-item.failed { border-left-color: #dc3545; }
        .ticket-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .ticket-id { font-family: monospace; color: #666; }
        .badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .badge.completed { background: #28a745; color: white; }
        .badge.failed { background: #dc3545; color: white; }
        .badge.running { background: #ffc107; color: #333; }
        .chart-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 20px;
        }
        .realtime-badge {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8em;
            margin-left: 10px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Trinity Orchestrator Dashboard</h1>
            <p>リアルタイム監視・履歴ダッシュボード <span class="realtime-badge">● LIVE</span></p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>アクティブチケット</h3>
                <div class="value" id="activeTickets">-</div>
            </div>
            <div class="stat-card">
                <h3>完了チケット</h3>
                <div class="value" id="completedTickets">-</div>
            </div>
            <div class="stat-card">
                <h3>平均Confidence</h3>
                <div class="value" id="avgConfidence">-</div>
            </div>
            <div class="stat-card">
                <h3>平均ターン数</h3>
                <div class="value" id="avgTurns">-</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📈 実行履歴（最新10件）</h2>
            <canvas id="historyChart" width="400" height="150"></canvas>
        </div>
        
        <div class="tickets-panel">
            <h2>🎫 最近のチケット</h2>
            <div id="ticketsList"></div>
        </div>
    </div>
    
    <script>
        let historyChart = null;
        
        // データ更新関数
        async function updateDashboard() {
            try {
                const response = await fetch('/api/dashboard_data');
                const data = await response.json();
                
                // 統計更新
                document.getElementById('activeTickets').textContent = data.stats.active_tickets;
                document.getElementById('completedTickets').textContent = data.stats.completed_tickets;
                document.getElementById('avgConfidence').textContent = (data.stats.avg_confidence * 100).toFixed(0) + '%';
                document.getElementById('avgTurns').textContent = data.stats.avg_turns.toFixed(1);
                
                // チケット一覧更新
                const container = document.getElementById('ticketsList');
                container.innerHTML = '';
                
                data.tickets.forEach(ticket => {
                    const item = document.createElement('div');
                    item.className = 'ticket-item ' + ticket.status;
                    item.innerHTML = `
                        <div class="ticket-header">
                            <span class="ticket-id">${ticket.ticket_id}</span>
                            <span class="badge ${ticket.status}">${ticket.status.toUpperCase()}</span>
                        </div>
                        <div><strong>Goal:</strong> ${ticket.goal}</div>
                        <div style="margin-top: 5px; color: #666; font-size: 0.9em;">
                            Confidence: ${(ticket.confidence * 100).toFixed(0)}% | 
                            Turns: ${ticket.turns} | 
                            Files: ${ticket.artifacts}
                        </div>
                    `;
                    container.appendChild(item);
                });
                
                // 履歴チャート更新
                if (data.history.labels.length > 0) {
                    const ctx = document.getElementById('historyChart').getContext('2d');
                    
                    if (historyChart) {
                        historyChart.destroy();
                    }
                    
                    historyChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.history.labels,
                            datasets: [{
                                label: 'Confidence',
                                data: data.history.confidence,
                                borderColor: '#667eea',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                tension: 0.4
                            }, {
                                label: 'Turns',
                                data: data.history.turns,
                                borderColor: '#764ba2',
                                backgroundColor: 'rgba(118, 75, 162, 0.1)',
                                tension: 0.4,
                                yAxisID: 'y1'
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: { beginAtZero: true, max: 1, title: { display: true, text: 'Confidence' } },
                                y1: { beginAtZero: true, position: 'right', title: { display: true, text: 'Turns' } }
                            }
                        }
                    });
                }
            } catch (error) {
                console.error('更新エラー:', error);
            }
        }
        
        // 初回更新
        updateDashboard();
        
        // 5秒ごとに自動更新
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """ダッシュボードメインページ"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/dashboard_data')
def get_dashboard_data():
    """ダッシュボードデータをJSON形式で返す"""
    try:
        # アクティブチケット取得
        active_tickets = ticket_manager.list_active_tickets()
        
        # 全チケット情報取得
        all_tickets = []
        completed_count = 0
        total_confidence = 0
        total_turns = 0
        valid_count = 0
        
        # アクティブ
        for tid in active_tickets:
            ticket = ticket_manager.get_ticket(tid)
            if ticket:
                all_tickets.append({
                    "ticket_id": tid,
                    "goal": ticket["goal"],
                    "status": ticket["status"]["stage"],
                    "confidence": ticket["status"]["confidence"],
                    "turns": ticket["status"]["turn"],
                    "artifacts": len(ticket.get("artifacts", []))
                })
        
        # クローズ済み（最新10件）
        try:
            closed_tickets = list(ticket_manager.redis_client.smembers("tickets:closed"))[-10:]
            for tid in closed_tickets:
                ticket = ticket_manager.get_ticket(tid)
                if ticket:
                    status = ticket.get("final_status", "unknown")
                    if status == "completed":
                        completed_count += 1
                    
                    all_tickets.append({
                        "ticket_id": tid,
                        "goal": ticket["goal"],
                        "status": status,
                        "confidence": ticket["status"]["confidence"],
                        "turns": ticket["status"]["turn"],
                        "artifacts": len(ticket.get("artifacts", []))
                    })
                    
                    # 平均計算用
                    total_confidence += ticket["status"]["confidence"]
                    total_turns += ticket["status"]["turn"]
                    valid_count += 1
        except:
            pass
        
        # 統計計算
        avg_confidence = total_confidence / valid_count if valid_count > 0 else 0
        avg_turns = total_turns / valid_count if valid_count > 0 else 0
        
        # データをまとめて返す
        recent = sorted(all_tickets, key=lambda x: x["ticket_id"])[-10:] if all_tickets else []
        
        return jsonify({
            "stats": {
                "active_tickets": len(active_tickets),
                "completed_tickets": completed_count,
                "avg_confidence": avg_confidence,
                "avg_turns": avg_turns
            },
            "tickets": sorted(all_tickets, key=lambda x: x["ticket_id"], reverse=True)[:10],
            "history": {
                "labels": [t["ticket_id"][-8:] for t in recent],
                "confidence": [t["confidence"] for t in recent],
                "turns": [t["turns"] for t in recent]
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Data fetch failed: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("🚀 Starting Trinity Orchestrator Dashboard...")
    logger.info("📍 Port: 9402")
    logger.info("🌐 Access: http://localhost:9402")
    
    app.run(host="0.0.0.0", port=9402, debug=False)

