"""
LLMメトリクスダッシュボード
メトリクスを可視化するWeb UI
"""

import json
import logging
from pathlib import Path
from flask import Flask, render_template_string, jsonify
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ダッシュボードHTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLMメトリクスダッシュボード</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
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
            color: #333;
            margin-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .chart-container h2 {
            color: #333;
            margin-bottom: 20px;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-left: 10px;
        }
        .refresh-btn:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 LLMメトリクスダッシュボード</h1>
            <p>ローカルLLMシステムのパフォーマンス監視</p>
            <button class="refresh-btn" onclick="loadMetrics()">🔄 更新</button>
        </div>
        
        <div class="stats-grid" id="stats-grid">
            <!-- 統計カードがここに動的に追加されます -->
        </div>
        
        <div class="chart-container">
            <h2>📈 応答時間の推移</h2>
            <canvas id="responseTimeChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h2>💾 キャッシュヒット率</h2>
            <canvas id="cacheHitRateChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h2>✨ プロンプト最適化率</h2>
            <canvas id="optimizationRateChart"></canvas>
        </div>
    </div>
    
    <script>
        let responseTimeChart, cacheHitRateChart, optimizationRateChart;
        
        async function loadMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                
                updateStats(data.stats);
                updateCharts(data.history);
            } catch (error) {
                console.error('メトリクス読み込みエラー:', error);
            }
        }
        
        function updateStats(stats) {
            const grid = document.getElementById('stats-grid');
            grid.innerHTML = `
                <div class="stat-card">
                    <h3>総クエリ数</h3>
                    <div class="value">${stats.total_queries || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>平均応答時間</h3>
                    <div class="value">${(stats.average_response_time || 0).toFixed(2)}秒</div>
                </div>
                <div class="stat-card">
                    <h3>キャッシュヒット率</h3>
                    <div class="value">${((stats.cache_hit_rate || 0) * 100).toFixed(1)}%</div>
                </div>
                <div class="stat-card">
                    <h3>プロンプト最適化率</h3>
                    <div class="value">${((stats.optimization_rate || 0) * 100).toFixed(1)}%</div>
                </div>
                <div class="stat-card">
                    <h3>平均プロンプト長</h3>
                    <div class="value">${Math.round(stats.average_prompt_length || 0)}文字</div>
                </div>
                <div class="stat-card">
                    <h3>平均回答長</h3>
                    <div class="value">${Math.round(stats.average_answer_length || 0)}文字</div>
                </div>
            `;
        }
        
        function updateCharts(history) {
            // 応答時間チャート
            const responseTimeCtx = document.getElementById('responseTimeChart').getContext('2d');
            if (responseTimeChart) {
                responseTimeChart.destroy();
            }
            responseTimeChart = new Chart(responseTimeCtx, {
                type: 'line',
                data: {
                    labels: history.map(h => new Date(h.timestamp).toLocaleTimeString()),
                    datasets: [{
                        label: '応答時間 (秒)',
                        data: history.map(h => h.response_time),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
            
            // キャッシュヒット率チャート
            const cacheHitRateCtx = document.getElementById('cacheHitRateChart').getContext('2d');
            if (cacheHitRateChart) {
                cacheHitRateChart.destroy();
            }
            const cacheHits = history.filter(h => h.cache_hit).length;
            const cacheMisses = history.length - cacheHits;
            cacheHitRateChart = new Chart(cacheHitRateCtx, {
                type: 'doughnut',
                data: {
                    labels: ['ヒット', 'ミス'],
                    datasets: [{
                        data: [cacheHits, cacheMisses],
                        backgroundColor: ['#22c55e', '#ef4444']
                    }]
                },
                options: {
                    responsive: true
                }
            });
            
            // プロンプト最適化率チャート
            const optimizationRateCtx = document.getElementById('optimizationRateChart').getContext('2d');
            if (optimizationRateChart) {
                optimizationRateChart.destroy();
            }
            const optimized = history.filter(h => h.optimized).length;
            const notOptimized = history.length - optimized;
            optimizationRateChart = new Chart(optimizationRateCtx, {
                type: 'doughnut',
                data: {
                    labels: ['最適化済み', '未最適化'],
                    datasets: [{
                        data: [optimized, notOptimized],
                        backgroundColor: ['#3b82f6', '#94a3b8']
                    }]
                },
                options: {
                    responsive: true
                }
            });
        }
        
        // 初期読み込み
        loadMetrics();
        
        // 30秒ごとに自動更新
        setInterval(loadMetrics, 30000);
    </script>
</body>
</html>
"""


class LLMDashboard:
    """LLMメトリクスダッシュボード"""
    
    def __init__(self, metrics_instance=None):
        """
        初期化
        
        Args:
            metrics_instance: LLMMetricsインスタンス
        """
        self.metrics = metrics_instance
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """ルートを設定"""
        
        @self.app.route('/')
        def index():
            """ダッシュボード表示"""
            return render_template_string(DASHBOARD_HTML)
        
        @self.app.route('/api/metrics')
        def get_metrics():
            """メトリクスAPI"""
            if not self.metrics:
                return jsonify({
                    'stats': {},
                    'history': []
                })
            
            stats = self.metrics.get_stats()
            recent_queries = self.metrics.get_recent_queries(limit=100)
            
            return jsonify({
                'stats': stats,
                'history': recent_queries
            })
    
    def run(self, host='0.0.0.0', port=5090, debug=False):
        """
        ダッシュボードを起動
        
        Args:
            host: ホスト
            port: ポート
            debug: デバッグモード
        """
        print("=" * 60)
        print("📊 LLMメトリクスダッシュボード")
        print("=" * 60)
        print(f"📍 http://127.0.0.1:{port}")
        print("=" * 60)
        
        self.app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    from llm_metrics import get_metrics
    
    metrics = get_metrics(enable=True)
    dashboard = LLMDashboard(metrics_instance=metrics)
    dashboard.run()



