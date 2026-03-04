#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ManaOS リアルタイム監視ダッシュボード
WebUIでサービスの状態をリアルタイム監視
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import random
import requests

try:
    from flask import Flask, render_template_string, jsonify
    from flask_cors import CORS
except ImportError:
    print("[NG] 必要なライブラリがインストールされていません")
    print("実行: pip install flask flask-cors")
    sys.exit(1)

app = Flask(__name__)
CORS(app)


def _resolve_port(service_name: str, default: int, category: str) -> int:
    env_map = {
        "unified_api": "UNIFIED_API_PORT",
        "mrl_memory": "MRL_MEMORY_PORT",
    }
    env_key = env_map.get(service_name)
    if env_key and os.getenv(env_key):
        try:
            return int(os.getenv(env_key, str(default)))
        except ValueError:
            pass

    integrations_dir = Path(__file__).resolve().parent.parent / "manaos_integrations"
    if integrations_dir.exists() and str(integrations_dir) not in sys.path:
        sys.path.insert(0, str(integrations_dir))
        try:
            from config_loader import get_port

            return int(get_port(service_name, category))
        except Exception:
            pass

    return default


_UNIFIED_API_PORT = _resolve_port("unified_api", 9502, "integration_services")
_MRL_MEMORY_PORT = _resolve_port("mrl_memory", 5105, "manaos_services")

# サービス定義
SERVICES = {
    "unified_api": {
        "name": "統合API",
        "url": f"http://localhost:{_UNIFIED_API_PORT}/health",
        "port": _UNIFIED_API_PORT,
        "description": "ManaOS 統合APIサーバー",
    },
    "mrl_memory": {
        "name": "MRL Memory統合",
        "url": f"http://localhost:{_MRL_MEMORY_PORT}/health",
        "port": _MRL_MEMORY_PORT,
        "description": "メモリと学習統合システム",
    },
    "watchdog": {
        "name": "ウォッチドッグ",
        "url": None,  # ローカルプロセス
        "port": None,
        "description": "自動再起動監視サービス",
    },
}

class DashboardManager:
    """ダッシュボード管理クラス"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.service_history = {k: [] for k in SERVICES.keys()}
    
    def _setup_logger(self):
        """ロギング設定"""
        logger = logging.getLogger("Dashboard")
        logger.setLevel(logging.INFO)
        
        log_file = Path("logs") / "dashboard.log"
        log_file.parent.mkdir(exist_ok=True)
        
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)
        return logger
    
    def check_service_health(self, service_key):
        """サービスのヘルスチェック"""
        service = SERVICES[service_key]
        
        if service_key == "watchdog":
            # ウォッチドッグのプロセスチェック
            return self._check_watchdog_process()
        
        # HTTPヘルスチェック
        try:
            response = requests.get(service["url"], timeout=5)
            is_healthy = response.status_code == 200
            response_time = response.elapsed.total_seconds() * 1000  # ミリ秒
            
            return {
                "healthy": is_healthy,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "message": "OK" if is_healthy else f"Status {response.status_code}",
            }
        except requests.exceptions.Timeout:
            return {
                "healthy": False,
                "status_code": 0,
                "response_time_ms": 5000,
                "message": "Timeout",
            }
        except requests.exceptions.ConnectionError:
            return {
                "healthy": False,
                "status_code": 0,
                "response_time_ms": 0,
                "message": "Connection refused",
            }
        except Exception as e:
            return {
                "healthy": False,
                "status_code": 0,
                "response_time_ms": 0,
                "message": str(e)[:50],
            }
    
    def _check_watchdog_process(self):
        """ウォッチドッグプロセスの確認"""
        try:
            import psutil
            
            # "watchdog" プロセスを検索
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'watchdog' in cmdline and 'python' in cmdline:
                        return {
                            "healthy": True,
                            "status_code": 200,
                            "response_time_ms": 0,
                            "message": f"Running (PID: {proc.info['pid']})",
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "healthy": False,
                "status_code": 0,
                "response_time_ms": 0,
                "message": "Process not found",
            }
        except ImportError:
            # psutilがない場合はダミー値を返す
            return {
                "healthy": True,
                "status_code": 200,
                "response_time_ms": 0,
                "message": "Unable to verify",
            }
    
    def get_all_services_status(self):
        """全サービスの状態を取得"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "overall_health": "OK",
        }
        
        healthy_count = 0
        
        for service_key, service_info in SERVICES.items():
            health = self.check_service_health(service_key)
            
            status["services"][service_key] = {
                "name": service_info["name"],
                "description": service_info["description"],
                "port": service_info["port"],
                "healthy": health["healthy"],
                "status_code": health["status_code"],
                "response_time_ms": health["response_time_ms"],
                "message": health["message"],
            }
            
            if health["healthy"]:
                healthy_count += 1
            
            # 履歴に追加
            self.service_history[service_key].append({
                "timestamp": datetime.now().isoformat(),
                "healthy": health["healthy"],
            })
            
            # 履歴を最新100件に制限
            if len(self.service_history[service_key]) > 100:
                self.service_history[service_key] = self.service_history[service_key][-100:]
        
        # 全体のヘルス判定
        if healthy_count == len(SERVICES):
            status["overall_health"] = "OK"
        elif healthy_count >= len(SERVICES) // 2:
            status["overall_health"] = "PARTIAL"
        else:
            status["overall_health"] = "CRITICAL"
        
        return status
    
    def generate_dashboard_html(self):
        """ダッシュボードHTMLを生成"""
        html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS 監視ダッシュボード</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .timestamp {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .service-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .service-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.2);
        }
        
        .service-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .service-name {
            font-size: 1.2em;
            font-weight: bold;
            color: #1e3c72;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.85em;
        }
        
        .status-badge.ok {
            background-color: #4caf50;
            color: white;
        }
        
        .status-badge.critical {
            background-color: #f44336;
            color: white;
        }
        
        .status-badge.warning {
            background-color: #ff9800;
            color: white;
        }
        
        .service-details {
            font-size: 0.9em;
            color: #555;
            line-height: 1.6;
        }
        
        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }
        
        .detail-label {
            font-weight: 600;
            color: #333;
        }
        
        .detail-value {
            color: #666;
        }
        
        .overall-status {
            background: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .overall-status h2 {
            color: #1e3c72;
            margin-bottom: 15px;
        }
        
        .overall-badge {
            display: inline-block;
            padding: 10px 30px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .overall-badge.ok {
            background-color: #4caf50;
            color: white;
        }
        
        .overall-badge.partial {
            background-color: #ff9800;
            color: white;
        }
        
        .overall-badge.critical {
            background-color: #f44336;
            color: white;
        }
        
        .refresh-info {
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 0.9em;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .refreshing {
            animation: pulse 1s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ManaOS リアルタイム監視ダッシュボード</h1>
            <div class="timestamp">
                更新: <span id="update-time">-</span>
            </div>
        </header>
        
        <div class="overall-status" id="overall-status">
            <h2>全体の状態</h2>
            <div class="overall-badge ok" id="overall-badge">
                取得中...
            </div>
        </div>
        
        <div class="status-grid" id="services-container">
            <p style="color: white; text-align: center;">ロード中...</p>
        </div>
        
        <div class="refresh-info">
            <p>自動更新: 5秒ごと</p>
        </div>
    </div>
    
    <script>
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // タイムスタンプ更新
                document.getElementById('update-time').textContent = 
                    new Date(data.timestamp).toLocaleString('ja-JP');
                
                // 全体ステータス更新
                const overallBadge = document.getElementById('overall-badge');
                overallBadge.textContent = data.overall_health === 'OK' ? 
                    '正常[OK]' : 
                    data.overall_health === 'PARTIAL' ? 
                    '部分的[注意]' : 
                    '異常[Critical]';
                overallBadge.className = 
                    'overall-badge ' + data.overall_health.toLowerCase();
                
                // サービスカード更新
                const container = document.getElementById('services-container');
                container.innerHTML = '';
                
                for (const [key, service] of Object.entries(data.services)) {
                    const statusClass = service.healthy ? 'ok' : 'critical';
                    const statusText = service.healthy ? '[稼働中]' : '[停止]';
                    
                    const card = document.createElement('div');
                    card.className = 'service-card';
                    card.innerHTML = `
                        <div class="service-header">
                            <div class="service-name">${service.name}</div>
                            <div class="status-badge ${statusClass}">${statusText}</div>
                        </div>
                        <div class="service-details">
                            <div class="detail-row">
                                <span class="detail-label">説明:</span>
                                <span class="detail-value">${service.description}</span>
                            </div>
                            ${service.port ? `
                            <div class="detail-row">
                                <span class="detail-label">ポート:</span>
                                <span class="detail-value">${service.port}</span>
                            </div>
                            ` : ''}
                            <div class="detail-row">
                                <span class="detail-label">ステータス:</span>
                                <span class="detail-value">${service.status_code || 'N/A'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">応答時間:</span>
                                <span class="detail-value">${service.response_time_ms.toFixed(0)}ms</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">メッセージ:</span>
                                <span class="detail-value">${service.message}</span>
                            </div>
                        </div>
                    `;
                    container.appendChild(card);
                }
            } catch (error) {
                console.error('ステータス取得エラー:', error);
                document.getElementById('overall-badge').textContent = 'エラー';
                document.getElementById('overall-badge').className = 
                    'overall-badge critical';
            }
        }
        
        // 初期ロード
        updateStatus();
        
        // 5秒ごとに更新
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
        """
        return html

# グローバルマネージャー
manager = DashboardManager()

@app.route('/')
def dashboard():
    """ダッシュボードHTMLを返す"""
    return render_template_string(manager.generate_dashboard_html())

@app.route('/api/status')
def api_status():
    """API: サービスステータスを返す"""
    status = manager.get_all_services_status()
    return jsonify(status)

@app.route('/api/health')
def api_health():
    """API: API自体のヘルスチェック"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
    })

def main():
    print("\n" + "="*60)
    print("ManaOS リアルタイム監視ダッシュボード")
    print("="*60)
    print(f"WebUI: http://localhost:8888")
    print(f"API: http://localhost:8888/api/status")
    print("="*60 + "\n")
    
    manager.logger.info("ダッシュボードを起動しました")
    
    # Flask起動
    app.run(
        host='0.0.0.0',
        port=8888,
        debug=False,
        use_reloader=False,
    )

if __name__ == "__main__":
    main()
