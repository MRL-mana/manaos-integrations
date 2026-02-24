#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ManaOS統一ダッシュボード
全システムの状態を統合表示
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from manaos_async_client import AsyncUnifiedAPIClient
from unified_test_system import UnifiedTestSystem
from personality_autonomy_secretary_integration import PersonalityAutonomySecretaryIntegration
from learning_memory_integration import LearningMemoryIntegration
from manaos_performance_optimizer import PerformanceOptimizer

# ロガーの初期化
logger = get_service_logger("unified-dashboard")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedDashboard")

app = Flask(__name__)
CORS(app)

# システムインスタンス
test_system = UnifiedTestSystem()
pas_integration = PersonalityAutonomySecretaryIntegration()
learning_memory = LearningMemoryIntegration()
performance_optimizer = PerformanceOptimizer()


@app.route('/')
def dashboard():
    """ダッシュボードページ"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/dashboard-data', methods=['GET'])
async def get_dashboard_data():
    """ダッシュボードデータを取得"""
    try:
        # 並列でデータを取得
        async with AsyncUnifiedAPIClient() as client:
            services_health, test_results, pas_status, learning_stats, perf_stats = await asyncio.gather(
                client.check_all_services(),
                test_system.run_all_tests(),
                pas_integration.get_integrated_status(),
                learning_memory.get_integrated_stats(),
                performance_optimizer.get_all_stats(),
                return_exceptions=True
            )
        
        # 例外を処理
        if isinstance(services_health, Exception):
            services_health = {}
        if isinstance(test_results, Exception):
            test_results = {}
        if isinstance(pas_status, Exception):
            pas_status = {}
        if isinstance(learning_stats, Exception):
            learning_stats = {}
        if isinstance(perf_stats, Exception):
            perf_stats = {}
        
        return jsonify({
            "services": services_health,
            "tests": test_results,
            "personality_autonomy_secretary": pas_status,
            "learning_memory": learning_stats,
            "performance": perf_stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/dashboard-data"},
            user_message="ダッシュボードデータの取得に失敗しました"
        )
        return jsonify({"error": error.user_message or error.message}), 500


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ManaOS統一ダッシュボード</title>
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
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ManaOS統一ダッシュボード</h1>
            <p>全システムの統合監視</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>サービス状態</h2>
                <div id="services-status"></div>
            </div>
            <div class="card">
                <h2>テスト結果</h2>
                <div id="test-results"></div>
            </div>
            <div class="card">
                <h2>パフォーマンス</h2>
                <div id="performance-stats"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/dashboard-data');
                const data = await response.json();
                
                // サービス状態を更新
                const servicesDiv = document.getElementById('services-status');
                if (data.services) {
                    let html = '';
                    for (const [name, status] of Object.entries(data.services)) {
                        const isHealthy = status.status === 'healthy';
                        html += `<div style="padding: 10px; border-bottom: 1px solid #eee;">
                            <strong>${name}</strong>: 
                            <span style="color: ${isHealthy ? 'green' : 'red'}">
                                ${isHealthy ? '✅ 正常' : '❌ 異常'}
                            </span>
                        </div>`;
                    }
                    servicesDiv.innerHTML = html;
                }
                
                // テスト結果を更新
                const testDiv = document.getElementById('test-results');
                if (data.tests && data.tests.summary) {
                    const summary = data.tests.summary;
                    testDiv.innerHTML = `
                        <div class="stat-value">${summary.passed_tests}/${summary.total_tests}</div>
                        <p>成功率: ${summary.success_rate.toFixed(1)}%</p>
                    `;
                }
                
                // パフォーマンス統計を更新
                const perfDiv = document.getElementById('performance-stats');
                if (data.performance) {
                    perfDiv.innerHTML = `
                        <div class="stat-value">${data.performance.cache?.hit_rate?.toFixed(1) || 0}%</div>
                        <p>キャッシュヒット率</p>
                    `;
                }
            } catch (error) {
                console.error('ダッシュボード更新エラー:', error);
            }
        }
        
        // 初期読み込み
        updateDashboard();
        
        // 10秒ごとに更新
        setInterval(updateDashboard, 10000);
    </script>
</body>
</html>
"""


def main():
    """メイン関数"""
    port = int(os.getenv("PORT", 5130))
    logger.info(f"🚀 Unified Dashboard起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")


if __name__ == '__main__':
    main()






















