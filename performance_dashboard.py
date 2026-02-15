#!/usr/bin/env python3
"""
📊 ManaOS パフォーマンスダッシュボード
リアルタイムメトリクス表示・グラフ・アラート
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

try:
    from manaos_integrations._paths import METRICS_COLLECTOR_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import METRICS_COLLECTOR_PORT  # type: ignore
    except Exception:  # pragma: no cover
        METRICS_COLLECTOR_PORT = int(os.getenv("METRICS_COLLECTOR_PORT", "5127"))

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PerformanceDashboard")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# Metrics Collector URL
METRICS_COLLECTOR_URL = os.getenv(
    "METRICS_COLLECTOR_URL",
    f"http://127.0.0.1:{METRICS_COLLECTOR_PORT}",
)


# HTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS パフォーマンスダッシュボード</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h2 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #666; }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status.ok { background: #d4edda; color: #155724; }
        .status.warn { background: #fff3cd; color: #856404; }
        .status.error { background: #f8d7da; color: #721c24; }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            margin-top: 20px;
        }
        .refresh-btn:hover { background: #5568d3; }
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 ManaOS パフォーマンスダッシュボード</h1>
        <p>リアルタイムメトリクス監視</p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>サービスステータス</h2>
            <div id="service-status"></div>
        </div>

        <div class="card">
            <h2>レスポンス時間</h2>
            <div id="response-time"></div>
        </div>

        <div class="card">
            <h2>エラー率</h2>
            <div id="error-rate"></div>
        </div>

        <div class="card">
            <h2>成功率</h2>
            <div id="success-rate"></div>
        </div>
    </div>

    <div class="card">
        <h2>レスポンス時間推移</h2>
        <div class="chart-container">
            <canvas id="response-time-chart"></canvas>
        </div>
    </div>

    <div class="card">
        <h2>エラー率推移</h2>
        <div class="chart-container">
            <canvas id="error-rate-chart"></canvas>
        </div>
    </div>

    <div class="auto-refresh">
        <button class="refresh-btn" onclick="refreshData()">更新</button>
        <label>
            <input type="checkbox" id="auto-refresh" checked>
            自動更新（10秒間隔）
        </label>
    </div>

    <script>
        let responseTimeChart, errorRateChart;
        let autoRefreshInterval;

        // チャート初期化
        function initCharts() {
            const ctx1 = document.getElementById('response-time-chart').getContext('2d');
            responseTimeChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

            const ctx2 = document.getElementById('error-rate-chart').getContext('2d');
            errorRateChart = new Chart(ctx2, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 1 }
                    }
                }
            });
        }

        // データ更新
        async function refreshData() {
            try {
                const response = await fetch('/api/dashboard-data');
                const data = await response.json();

                // サービスステータス
                updateServiceStatus(data.services);

                // メトリクス表示
                updateMetrics(data.metrics);

                // チャート更新
                updateCharts(data.charts);
            } catch (error) {
                console.error('データ取得エラー:', error);
            }
        }

        function updateServiceStatus(services) {
            const container = document.getElementById('service-status');
            container.innerHTML = '';
            for (const [name, status] of Object.entries(services)) {
                const div = document.createElement('div');
                div.className = 'metric';
                div.innerHTML = `
                    <span class="metric-label">${name}</span>
                    <span class="status ${status === 'ok' ? 'ok' : 'error'}">${status === 'ok' ? '正常' : '異常'}</span>
                `;
                container.appendChild(div);
            }
        }

        function updateMetrics(metrics) {
            // レスポンス時間
            const rtContainer = document.getElementById('response-time');
            rtContainer.innerHTML = '';
            for (const [service, value] of Object.entries(metrics.response_time || {})) {
                const div = document.createElement('div');
                div.className = 'metric';
                div.innerHTML = `
                    <span class="metric-label">${service}</span>
                    <span class="metric-value">${value.toFixed(2)}s</span>
                `;
                rtContainer.appendChild(div);
            }

            // エラー率
            const erContainer = document.getElementById('error-rate');
            erContainer.innerHTML = '';
            for (const [service, value] of Object.entries(metrics.error_rate || {})) {
                const div = document.createElement('div');
                div.className = 'metric';
                div.innerHTML = `
                    <span class="metric-label">${service}</span>
                    <span class="metric-value">${(value * 100).toFixed(2)}%</span>
                `;
                erContainer.appendChild(div);
            }

            // 成功率
            const srContainer = document.getElementById('success-rate');
            srContainer.innerHTML = '';
            for (const [service, value] of Object.entries(metrics.success_rate || {})) {
                const div = document.createElement('div');
                div.className = 'metric';
                div.innerHTML = `
                    <span class="metric-label">${service}</span>
                    <span class="metric-value">${(value * 100).toFixed(2)}%</span>
                `;
                srContainer.appendChild(div);
            }
        }

        function updateCharts(chartData) {
            // レスポンス時間チャート
            responseTimeChart.data.labels = chartData.labels || [];
            responseTimeChart.data.datasets = chartData.response_time_datasets || [];
            responseTimeChart.update();

            // エラー率チャート
            errorRateChart.data.labels = chartData.labels || [];
            errorRateChart.data.datasets = chartData.error_rate_datasets || [];
            errorRateChart.update();
        }

        // 自動更新
        document.getElementById('auto-refresh').addEventListener('change', function(e) {
            if (e.target.checked) {
                autoRefreshInterval = setInterval(refreshData, 10000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        });

        // 初期化
        initCharts();
        refreshData();
        if (document.getElementById('auto-refresh').checked) {
            autoRefreshInterval = setInterval(refreshData, 10000);
        }
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """ダッシュボード表示"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """ダッシュボードデータを取得"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        # Metrics Collectorからデータを取得
        async def fetch_metrics():
            async with httpx.AsyncClient(timeout=timeout_config.get("api_call", 10.0)) as client:
                # サービス一覧を取得
                services = ["UnifiedOrchestrator", "IntentRouter", "TaskPlanner", "TaskCritic"]
                
                metrics_data = {
                    "response_time": {},
                    "error_rate": {},
                    "success_rate": {}
                }
                
                charts_data = {
                    "labels": [],
                    "response_time_datasets": [],
                    "error_rate_datasets": []
                }
                
                # 各サービスの統計情報を取得
                for service in services:
                    try:
                        # レスポンス時間
                        rt_response = await client.get(
                            f"{METRICS_COLLECTOR_URL}/api/statistics",
                            params={
                                "service_name": service,
                                "metric_type": "response_time",
                                "hours": hours
                            }
                        )
                        if rt_response.status_code == 200:
                            rt_stats = rt_response.json()
                            metrics_data["response_time"][service] = rt_stats.get("avg", 0)
                        
                        # エラー率
                        er_response = await client.get(
                            f"{METRICS_COLLECTOR_URL}/api/statistics",
                            params={
                                "service_name": service,
                                "metric_type": "error_rate",
                                "hours": hours
                            }
                        )
                        if er_response.status_code == 200:
                            er_stats = er_response.json()
                            metrics_data["error_rate"][service] = er_stats.get("avg", 0)
                        
                        # 成功率
                        sr_response = await client.get(
                            f"{METRICS_COLLECTOR_URL}/api/statistics",
                            params={
                                "service_name": service,
                                "metric_type": "success_rate",
                                "hours": hours
                            }
                        )
                        if sr_response.status_code == 200:
                            sr_stats = sr_response.json()
                            metrics_data["success_rate"][service] = sr_stats.get("avg", 0)
                    except Exception as e:
                        logger.warning(f"メトリクス取得エラー ({service}): {e}")
                
                # サービスステータス（簡易版）
                services_status = {}
                for service in services:
                    # メトリクスが取得できれば正常とみなす
                    if service in metrics_data["response_time"]:
                        services_status[service] = "ok"
                    else:
                        services_status[service] = "error"
                
                return {
                    "services": services_status,
                    "metrics": metrics_data,
                    "charts": charts_data
                }
        
        # 同期的に実行（簡易版）
        import asyncio
        data = asyncio.run(fetch_metrics())
        
        return jsonify(data)
    
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/dashboard-data"},
            user_message="ダッシュボードデータの取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Performance Dashboard"})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5128))
    logger.info(f"📊 Performance Dashboard起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

