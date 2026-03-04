#!/usr/bin/env python3
"""
ManaOS Jenkins風UI ダッシュボード
JenkinsライクなインターフェースでマナOSシステムを管理
"""

import logging
import subprocess
from datetime import datetime
from typing import Dict
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ManaOS Jenkins UI")

# ManaOSサービス一覧（システムdサービス + アプリケーションサービス）
MANAOS_SERVICES = {
    # Core Services
    "manaos-heal.service": {"name": "ManaOS Heal", "category": "core", "port": None},
    "manaos-learning-portal.service": {"name": "Learning Portal", "category": "core", "port": 5084},
    "manaos-learning-dashboard.service": {"name": "Learning Dashboard", "category": "core", "port": 5085},
    "manaos-lightweight-monitor.service": {"name": "Lightweight Monitor", "category": "core", "port": 5086},
    "manaos-sd-inference.service": {"name": "SD Inference", "category": "ai", "port": 5559},

    # Trinity Services
    "trinity-enhanced-secretary.service": {"name": "Trinity Secretary", "category": "trinity", "port": 5012},

    # Application Services
    "screen_sharing": {"name": "Screen Sharing", "category": "app", "port": 5008},
    "unified_api": {"name": "Unified API Gateway", "category": "app", "port": 8009},
    "realtime_dashboard": {"name": "Realtime Dashboard", "category": "app", "port": 5555},
    "api_bridge": {"name": "API Bridge", "category": "app", "port": 7000},
}

def get_service_status(service_name: str) -> Dict:
    """サービスステータスを取得"""
    try:
        # systemdサービスの場合
        if service_name.endswith('.service'):
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_active = result.stdout.strip() == 'active'

            result = subprocess.run(
                ['systemctl', 'is-enabled', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_enabled = result.stdout.strip() == 'enabled'

            # 起動時刻を取得
            result = subprocess.run(
                ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp', '--value'],
                capture_output=True,
                text=True,
                timeout=5
            )
            start_time = result.stdout.strip() if is_active else None

            return {
                "status": "running" if is_active else "stopped",
                "enabled": is_enabled,
                "start_time": start_time,
                "type": "systemd"
            }
        else:
            # アプリケーションサービスの場合（ポートチェック）
            service_info = MANAOS_SERVICES.get(service_name, {})
            port = service_info.get("port")

            if port:
                try:
                    result = subprocess.run(
                        ['netstat', '-tlnp'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    is_running = f':{port}' in result.stdout
                    return {
                        "status": "running" if is_running else "stopped",
                        "enabled": True,
                        "start_time": None,
                        "type": "application"
                    }
                except Exception:
                    return {
                        "status": "unknown",
                        "enabled": True,
                        "start_time": None,
                        "type": "application"
                    }
            return {
                "status": "unknown",
                "enabled": True,
                "start_time": None,
                "type": "application"
            }
    except Exception as e:
        logger.error(f"Error getting service status for {service_name}: {e}")
        return {
            "status": "error",
            "enabled": False,
            "start_time": None,
            "type": "unknown"
        }

def control_service(service_name: str, action: str) -> Dict:
    """サービスを制御（start/stop/restart）"""
    try:
        if service_name.endswith('.service'):
            result = subprocess.run(
                ['systemctl', action, service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Service {action}ed successfully"}
            else:
                return {"success": False, "message": result.stderr.strip()}
        else:
            # アプリケーションサービスの制御は未実装（個別のスクリプトが必要）
            return {"success": False, "message": "Application service control not implemented"}
    except Exception as e:
        logger.error(f"Error controlling service {service_name}: {e}")
        return {"success": False, "message": str(e)}

@app.get("/", response_class=HTMLResponse)
async def jenkins_ui():
    """Jenkins風UIのメイン画面"""
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f3f3f3;
            color: #333;
            font-size: 13px;
            line-height: 1.6;
        }

        /* Jenkins風ヘッダー */
        .header {
            background: #1a6091;
            color: white;
            padding: 15px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header h1 {
            font-size: 18px;
            font-weight: normal;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .header .logo {
            width: 32px;
            height: 32px;
            background: white;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #1a6091;
        }

        .header .actions {
            display: flex;
            gap: 10px;
        }

        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 13px;
            background: rgba(255,255,255,0.2);
            color: white;
            transition: background 0.2s;
        }

        .btn:hover {
            background: rgba(255,255,255,0.3);
        }

        /* メインコンテンツ */
        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }

        /* タブ */
        .tabs {
            display: flex;
            gap: 2px;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }

        .tab {
            padding: 10px 20px;
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            cursor: pointer;
            font-size: 13px;
        }

        .tab.active {
            background: white;
            border-color: #1a6091;
            border-bottom-color: white;
            color: #1a6091;
            font-weight: bold;
        }

        /* ジョブ一覧（Jenkins風） */
        .jobs-list {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        .job-item {
            padding: 12px 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: background 0.2s;
        }

        .job-item:hover {
            background: #f9f9f9;
        }

        .job-item:last-child {
            border-bottom: none;
        }

        .status-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .status-icon.running {
            background: #4CAF50;
        }

        .status-icon.stopped {
            background: #ccc;
        }

        .status-icon.building {
            background: #2196F3;
            animation: pulse 2s infinite;
        }

        .status-icon.error {
            background: #f44336;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .status-icon::after {
            content: '';
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: white;
        }

        .job-info {
            flex: 1;
            min-width: 0;
        }

        .job-name {
            font-weight: 500;
            font-size: 14px;
            color: #1a6091;
            margin-bottom: 4px;
        }

        .job-details {
            font-size: 12px;
            color: #666;
        }

        .job-actions {
            display: flex;
            gap: 5px;
        }

        .btn-small {
            padding: 4px 8px;
            font-size: 11px;
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 3px;
            cursor: pointer;
            color: #333;
        }

        .btn-small:hover {
            background: #e8e8e8;
        }

        .btn-small.primary {
            background: #1a6091;
            color: white;
            border-color: #1a6091;
        }

        .btn-small.primary:hover {
            background: #155080;
        }

        /* カテゴリヘッダー */
        .category-header {
            background: #f8f8f8;
            padding: 8px 20px;
            font-weight: bold;
            font-size: 12px;
            color: #666;
            border-bottom: 1px solid #eee;
        }

        /* 統計カード */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
        }

        .stat-number {
            font-size: 28px;
            font-weight: bold;
            color: #1a6091;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
        }

        /* ローディング */
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }

        /* 更新時刻 */
        .last-update {
            text-align: right;
            font-size: 11px;
            color: #999;
            padding: 10px 20px;
            background: #f8f8f8;
            border-top: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            <span class="logo">M</span>
            ManaOS Dashboard
        </h1>
        <div class="actions">
            <button class="btn" onclick="refreshAll()">🔄 更新</button>
        </div>
    </div>

    <div class="container">
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-number" id="stat-total">-</div>
                <div class="stat-label">総サービス数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="stat-running">-</div>
                <div class="stat-label">稼働中</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="stat-stopped">-</div>
                <div class="stat-label">停止中</div>
            </div>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('all')">すべて</div>
            <div class="tab" onclick="switchTab('core')">Core</div>
            <div class="tab" onclick="switchTab('ai')">AI</div>
            <div class="tab" onclick="switchTab('trinity')">Trinity</div>
            <div class="tab" onclick="switchTab('app')">App</div>
        </div>

        <div class="jobs-list" id="jobs-list">
            <div class="loading">読み込み中...</div>
        </div>
    </div>

    <script>
        let currentTab = 'all';
        let services = [];

        async function loadServices() {
            try {
                const response = await fetch('/api/services');
                const data = await response.json();
                services = data.services || [];
                updateStats(data);
                renderJobs();
            } catch (error) {
                console.error('Error loading services:', error);
                document.getElementById('jobs-list').innerHTML =
                    '<div class="loading">エラー: サービス情報の取得に失敗しました</div>';
            }
        }

        function updateStats(data) {
            document.getElementById('stat-total').textContent = data.stats.total || 0;
            document.getElementById('stat-running').textContent = data.stats.running || 0;
            document.getElementById('stat-stopped').textContent = data.stats.stopped || 0;
        }

        function renderJobs() {
            const filtered = currentTab === 'all'
                ? services
                : services.filter(s => s.category === currentTab);

            if (filtered.length === 0) {
                document.getElementById('jobs-list').innerHTML =
                    '<div class="loading">サービスが見つかりません</div>';
                return;
            }

            // カテゴリごとにグループ化
            const grouped = {};
            filtered.forEach(service => {
                const cat = service.category || 'other';
                if (!grouped[cat]) grouped[cat] = [];
                grouped[cat].push(service);
            });

            let html = '';
            const categoryNames = {
                'core': 'Core Services',
                'ai': 'AI Services',
                'trinity': 'Trinity Services',
                'app': 'Application Services',
                'other': 'Other'
            };

            Object.keys(grouped).sort().forEach(cat => {
                html += `<div class="category-header">${categoryNames[cat] || cat}</div>`;
                grouped[cat].forEach(service => {
                    const statusIcon = service.status === 'running' ? 'running' :
                                     service.status === 'building' ? 'building' :
                                     service.status === 'error' ? 'error' : 'stopped';

                    html += `
                        <div class="job-item">
                            <div class="status-icon ${statusIcon}"></div>
                            <div class="job-info">
                                <div class="job-name">${service.name}</div>
                                <div class="job-details">
                                    ${service.port ? `ポート: ${service.port} | ` : ''}
                                    ${service.start_time ? `起動: ${new Date(service.start_time).toLocaleString('ja-JP')} | ` : ''}
                                    タイプ: ${service.type}
                                </div>
                            </div>
                            <div class="job-actions">
                                ${service.status === 'running'
                                    ? `<button class="btn-small" onclick="controlService('${service.id}', 'stop')">停止</button>
                                       <button class="btn-small" onclick="controlService('${service.id}', 'restart')">再起動</button>`
                                    : `<button class="btn-small primary" onclick="controlService('${service.id}', 'start')">起動</button>`}
                            </div>
                        </div>
                    `;
                });
            });

            html += `<div class="last-update">最終更新: ${new Date().toLocaleString('ja-JP')}</div>`;

            document.getElementById('jobs-list').innerHTML = html;
        }

        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            renderJobs();
        }

        async function controlService(serviceId, action) {
            if (!confirm(`${action === 'start' ? '起動' : action === 'stop' ? '停止' : '再起動'}しますか？`)) {
                return;
            }

            try {
                const response = await fetch(`/api/services/${serviceId}/${action}`, {
                    method: 'POST'
                });
                const data = await response.json();

                if (data.success) {
                    alert('操作が完了しました');
                    setTimeout(loadServices, 1000);
                } else {
                    alert('エラー: ' + data.message);
                }
            } catch (error) {
                alert('エラー: ' + error.message);
            }
        }

        function refreshAll() {
            loadServices();
        }

        // 初回読み込み + 30秒ごと自動更新
        loadServices();
        setInterval(loadServices, 30000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/services")
async def get_services():
    """全サービスの状態を取得"""
    services_list = []
    stats = {"total": 0, "running": 0, "stopped": 0}

    for service_id, service_info in MANAOS_SERVICES.items():
        status = get_service_status(service_id)
        services_list.append({
            "id": service_id,
            "name": service_info["name"],
            "category": service_info["category"],
            "port": service_info.get("port"),
            "status": status["status"],
            "enabled": status["enabled"],
            "start_time": status["start_time"],
            "type": status["type"]
        })

        stats["total"] += 1
        if status["status"] == "running":
            stats["running"] += 1
        else:
            stats["stopped"] += 1

    return JSONResponse({
        "services": services_list,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    })

@app.post("/api/services/{service_id}/{action}")
async def control_service_api(service_id: str, action: str):
    """サービスを制御"""
    if action not in ["start", "stop", "restart"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    if service_id not in MANAOS_SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

    result = control_service(service_id, action)
    return JSONResponse(result)

if __name__ == "__main__":
    logger.info("🚀 ManaOS Jenkins UI 起動中...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9010,
        log_level="info"
    )
