#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ManaOS 統合状態ダッシュボード
システム間連携の可視化
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# 統合オーケストレーターのインポート
try:
    from manaos_integration_orchestrator import ManaOSIntegrationOrchestrator

    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    ManaOSIntegrationOrchestrator = None

app = Flask(__name__)
CORS(app)

orchestrator = None


def init_orchestrator():
    """オーケストレーターを初期化"""
    global orchestrator
    if orchestrator is None and ORCHESTRATOR_AVAILABLE:
        orchestrator = ManaOSIntegrationOrchestrator()
    return orchestrator


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS 統合状態ダッシュボード</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
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
            border-radius: 5px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .status-available {
            background: #4caf50;
            color: white;
        }
        .status-unavailable {
            background: #f44336;
            color: white;
        }
        .status-partial {
            background: #ff9800;
            color: white;
        }
        .integration-status {
            margin-top: 15px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 5px;
        }
        .integration-item {
            display: flex;
            align-items: center;
            margin: 10px 0;
        }
        .integration-icon {
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border-radius: 50%;
        }
        .integration-active {
            background: #4caf50;
        }
        .integration-inactive {
            background: #ccc;
        }
        .refresh-btn {
            display: block;
            margin: 20px auto;
            padding: 15px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 1.1em;
            cursor: pointer;
            transition: background 0.3s;
        }
        .refresh-btn:hover {
            background: #764ba2;
        }
        .timestamp {
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 ManaOS 統合状態ダッシュボード</h1>

        <div class="dashboard-grid" id="dashboard">
            <!-- ダッシュボードコンテンツはJavaScriptで動的に生成 -->
        </div>

        <button class="refresh-btn" onclick="refreshDashboard()">🔄 更新</button>
        <div class="timestamp" id="timestamp"></div>
    </div>

    <script>
        function refreshDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateDashboard(data);
                    document.getElementById('timestamp').textContent =
                        '最終更新: ' + new Date(data.timestamp).toLocaleString('ja-JP');
                })
                .catch(error => {
                    console.error('エラー:', error);
                    document.getElementById('dashboard').innerHTML =
                        '<div class="card"><h2>エラー</h2><p>データの取得に失敗しました</p></div>';
                });
        }

        function updateDashboard(data) {
            const dashboard = document.getElementById('dashboard');
            dashboard.innerHTML = '';

            // コアサービス
            const coreServices = createCard('コアサービス', data.services || {});
            dashboard.appendChild(coreServices);

            // 自己能力システム
            const selfCapabilities = createSelfCapabilitiesCard(data);
            dashboard.appendChild(selfCapabilities);

            // 統合システム
            const integrations = createIntegrationsCard(data);
            dashboard.appendChild(integrations);

            // システム間連携
            const systemIntegration = createSystemIntegrationCard(data);
            dashboard.appendChild(systemIntegration);

            // ask_orchestrator 集計（Portal から取得）
            fetch('/api/orchestrator/stats')
                .then(response => response.ok ? response.json() : null)
                .then(stats => {
                    if (stats && !stats.error) {
                        const card = createOrchestratorStatsCard(stats);
                        dashboard.appendChild(card);
                    }
                })
                .catch(() => {});
        }

        function createOrchestratorStatsCard(stats) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = '<h2>ask_orchestrator 集計</h2>';
            const s = stats.status || {};
            const wrap = document.createElement('div');
            wrap.innerHTML = `
                <div class="status-item"><span>ok</span><span class="status-badge status-available">${s.ok || 0}</span></div>
                <div class="status-item"><span>skill_not_found</span><span>${s.skill_not_found || 0}</span></div>
                <div class="status-item"><span>tool_error</span><span>${s.tool_error || 0}</span></div>
                <div class="status-item"><span>error</span><span class="status-badge status-unavailable">${s.error || 0}</span></div>
                <div class="status-item"><span>Portal タイムアウト（直近5分）</span><span>${stats.portal_timeout_last_5min != null ? stats.portal_timeout_last_5min : '-'}</span></div>
                <div class="status-item"><span>更新</span><span>${stats.updated_at || '-'}</span></div>
            `;
            card.appendChild(wrap);
            return card;
        }

        function createCard(title, data) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `<h2>${title}</h2>`;

            const summary = data.summary || {};
            const statusDiv = document.createElement('div');
            statusDiv.innerHTML = `
                <div class="status-item">
                    <span>総サービス数</span>
                    <span>${summary.total_services || 0}</span>
                </div>
                <div class="status-item">
                    <span>利用可能</span>
                    <span class="status-badge status-available">${summary.available_services || 0}</span>
                </div>
                <div class="status-item">
                    <span>利用不可</span>
                    <span class="status-badge status-unavailable">${summary.unavailable_services || 0}</span>
                </div>
                <div class="status-item">
                    <span>可用性</span>
                    <span>${((summary.availability_rate || 0) * 100).toFixed(1)}%</span>
                </div>
            `;
            card.appendChild(statusDiv);

            return card;
        }

        function createSelfCapabilitiesCard(data) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = '<h2>自己能力システム</h2>';

            const orchestrator = data.orchestrator || {};
            const statusDiv = document.createElement('div');

            const systems = [
                { name: '包括的自己能力', key: 'comprehensive_self_capabilities_available' },
                { name: '自己進化', key: 'self_evolution_available' },
                { name: '自己保護', key: 'self_protection_available' },
                { name: '自己管理', key: 'self_management_available' }
            ];

            systems.forEach(system => {
                const isAvailable = orchestrator[system.key] || false;
                const statusItem = document.createElement('div');
                statusItem.className = 'status-item';
                statusItem.innerHTML = `
                    <span>${system.name}</span>
                    <span class="status-badge ${isAvailable ? 'status-available' : 'status-unavailable'}">
                        ${isAvailable ? '利用可能' : '利用不可'}
                    </span>
                `;
                statusDiv.appendChild(statusItem);
            });

            card.appendChild(statusDiv);
            return card;
        }

        function createIntegrationsCard(data) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = '<h2>統合システム</h2>';

            const orchestrator = data.orchestrator || {};
            const statusDiv = document.createElement('div');

            const integrations = [
                { name: 'Service Bridge', key: 'service_bridge_available' },
                { name: 'Complete Integration', key: 'complete_integration_available' },
                { name: '分散処理', key: 'distributed_execution_available' },
                { name: 'コスト最適化', key: 'cost_optimization_available' },
                { name: '学習システム', key: 'learning_system_available' },
                { name: '予測的メンテナンス', key: 'predictive_maintenance_available' }
            ];

            integrations.forEach(integration => {
                const isAvailable = orchestrator[integration.key] || false;
                const statusItem = document.createElement('div');
                statusItem.className = 'status-item';
                statusItem.innerHTML = `
                    <span>${integration.name}</span>
                    <span class="status-badge ${isAvailable ? 'status-available' : 'status-unavailable'}">
                        ${isAvailable ? '利用可能' : '利用不可'}
                    </span>
                `;
                statusDiv.appendChild(statusItem);
            });

            card.appendChild(statusDiv);
            return card;
        }

        function createSystemIntegrationCard(data) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = '<h2>システム間連携</h2>';

            const integration = data.system_integration || {};
            const integrationDiv = document.createElement('div');
            integrationDiv.className = 'integration-status';

            const integrations = [
                { name: '自己修復 ↔ 自己進化', key: 'self_healing_to_evolution' },
                { name: '自己保護 ↔ 自己管理', key: 'self_protection_to_management' },
                { name: '自己進化 ↔ 自己管理', key: 'self_evolution_to_management' }
            ];

            integrations.forEach(item => {
                const isActive = integration[item.key] || false;
                const integrationItem = document.createElement('div');
                integrationItem.className = 'integration-item';
                integrationItem.innerHTML = `
                    <div class="integration-icon ${isActive ? 'integration-active' : 'integration-inactive'}"></div>
                    <span>${item.name}: ${isActive ? '連携中' : '未連携'}</span>
                `;
                integrationDiv.appendChild(integrationItem);
            });

            card.appendChild(integrationDiv);
            return card;
        }

        // 初回読み込み
        refreshDashboard();
        // 30秒ごとに自動更新
        setInterval(refreshDashboard, 30000);
    </script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    """ダッシュボードを表示"""
    return render_template_string(DASHBOARD_HTML)


PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:5108")


@app.route("/api/orchestrator/stats", methods=["GET"])
def get_orchestrator_stats():
    """ask_orchestrator 本格運用の集計を Portal から取得（プロキシ）。ダッシュボード用。"""
    if not HTTPX_AVAILABLE:
        return jsonify({"error": "httpx が利用できません"}), 503
    try:
        r = httpx.get(f"{PORTAL_URL.rstrip('/')}/api/orchestrator/stats", timeout=5)
        if r.status_code == 200:
            return jsonify(r.json())
        return jsonify({"error": f"Portal returned {r.status_code}"}), r.status_code
    except Exception as e:
        return jsonify({"error": str(e), "hint": "Portal が起動しているか確認してください"}), 503


@app.route("/api/status", methods=["GET"])
def get_status():
    """統合状態を取得"""
    orchestrator = init_orchestrator()
    if not orchestrator:
        return (
            jsonify(
                {
                    "error": "オーケストレーターが利用できません",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            503,
        )

    try:
        status = orchestrator.get_comprehensive_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e), "timestamp": datetime.now().isoformat()}), 500


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    return jsonify(
        {
            "status": "healthy",
            "service": "System Integration Dashboard",
            "timestamp": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 9400))
    print(f"📊 ManaOS 統合状態ダッシュボード起動中... (ポート: {port})")
    app.run(host="0.0.0.0", port=port, debug=False)
