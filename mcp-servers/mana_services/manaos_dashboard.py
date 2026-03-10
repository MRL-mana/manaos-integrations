#!/usr/bin/env python3
"""
🎯 まなOS統一ダッシュボード
全機能にアクセス可能な統一UI
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from flask import Flask, render_template_string, request, jsonify, session
from flask_cors import CORS
import psutil
import requests
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "manaos-dashboard-secret-key-2025")
CORS(app)

# データベースパス
DB_PATH = Path("/root/.mana_vault/manaos_dashboard.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# API Gateway URL
API_GATEWAY_URL = "http://localhost:8001"
UNIFIED_API_URL = "http://localhost:5050"


class ManaOSDashboard:
    def __init__(self):
        self.init_database()
        self.services = self.load_services()

    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # タスク管理テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'normal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP
            )
        """)

        # 在庫管理テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER DEFAULT 0,
                location TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # スケジュール管理テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def load_services(self) -> Dict[str, Dict[str, Any]]:
        """サービス一覧を読み込み"""
        return {
            "5008": {"name": "Mana Screen Sharing", "url": "http://localhost:5008", "category": "システム"},
            "5050": {"name": "Unified Portal", "url": "http://localhost:5050", "category": "システム"},
            "5054": {"name": "AI Predictive", "url": "http://localhost:5054", "category": "AI"},
            "5062": {"name": "Security Monitor", "url": "http://localhost:5062", "category": "セキュリティ"},
            "5063": {"name": "Cost Optimizer", "url": "http://localhost:5063", "category": "システム"},
            "5176": {"name": "Task Executor", "url": "http://localhost:5176", "category": "タスク"},
            "5080": {"name": "AI Model Hub", "url": "http://localhost:5080", "category": "AI"},
            "8001": {"name": "Trinity API Server", "url": "http://localhost:8001", "category": "API"},
            "8002": {"name": "Trinity Web UI", "url": "http://localhost:8002", "category": "UI"},
            "11434": {"name": "Ollama", "url": "http://localhost:11434", "category": "AI"},
        }

    def get_service_status(self, port: str) -> Dict[str, Any]:
        """サービスステータスを取得"""
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == int(port) and conn.status == 'LISTEN':  # type: ignore
                    service = self.services.get(port, {})
                    url = service.get("url", f"http://localhost:{port}")

                    # ヘルスチェック
                    try:
                        response = requests.get(f"{url}/health", timeout=2)
                        if response.status_code == 200:
                            return {"status": "healthy", "message": "Service responding"}
                    except:
                        pass

                    return {"status": "running", "message": "Port open"}

            return {"status": "stopped", "message": "Port not listening"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


dashboard = ManaOSDashboard()


@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/tasks', methods=['GET', 'POST'])  # type: ignore
def tasks():
    """タスク管理API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        # タスク一覧取得
        status = request.args.get('status', 'all')
        if status == 'all':
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))

        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "status": row[3],
                "priority": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "due_date": row[7]
            })

        conn.close()
        return jsonify({"tasks": tasks, "count": len(tasks)})

    elif request.method == 'POST':
        # タスク追加
        data = request.get_json()
        cursor.execute("""
            INSERT INTO tasks (title, description, status, priority, due_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title"),
            data.get("description"),
            data.get("status", "todo"),
            data.get("priority", "normal"),
            data.get("due_date")
        ))
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "task_id": task_id}), 201


@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])  # type: ignore
def task_detail(task_id):
    """タスク詳細API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            task = {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "status": row[3],
                "priority": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "due_date": row[7]
            }
            conn.close()
            return jsonify(task)
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    elif request.method == 'PUT':
        data = request.get_json()
        cursor.execute("""
            UPDATE tasks
            SET title = ?, description = ?, status = ?, priority = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data.get("title"),
            data.get("description"),
            data.get("status"),
            data.get("priority"),
            data.get("due_date"),
            task_id
        ))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    elif request.method == 'DELETE':
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})


@app.route('/api/inventory', methods=['GET', 'POST'])  # type: ignore
def inventory():
    """在庫管理API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM inventory ORDER BY created_at DESC")
        items = []
        for row in cursor.fetchall():
            items.append({
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "quantity": row[3],
                "location": row[4],
                "notes": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            })
        conn.close()
        return jsonify({"inventory": items, "count": len(items)})

    elif request.method == 'POST':
        data = request.get_json()
        cursor.execute("""
            INSERT INTO inventory (name, category, quantity, location, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("name"),
            data.get("category"),
            data.get("quantity", 0),
            data.get("location"),
            data.get("notes")
        ))
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "item_id": item_id}), 201


@app.route('/api/schedule', methods=['GET', 'POST'])  # type: ignore
def schedule():
    """スケジュール管理API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM schedule ORDER BY start_time DESC")
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "start_time": row[3],
                "end_time": row[4],
                "location": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            })
        conn.close()
        return jsonify({"schedule": events, "count": len(events)})

    elif request.method == 'POST':
        data = request.get_json()
        cursor.execute("""
            INSERT INTO schedule (title, description, start_time, end_time, location)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title"),
            data.get("description"),
            data.get("start_time"),
            data.get("end_time"),
            data.get("location")
        ))
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "event_id": event_id}), 201


@app.route('/api/services', methods=['GET'])
def services():
    """サービス一覧API"""
    services_status = []
    for port, info in dashboard.services.items():
        status = dashboard.get_service_status(port)
        services_status.append({
            "port": port,
            "name": info["name"],
            "url": info["url"],
            "category": info["category"],
            "status": status["status"],
            "message": status["message"]
        })

    return jsonify({
        "services": services_status,
        "total": len(services_status),
        "healthy": len([s for s in services_status if s["status"] == "healthy"]),
        "running": len([s for s in services_status if s["status"] in ["healthy", "running"]]),
        "stopped": len([s for s in services_status if s["status"] == "stopped"]),
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/system', methods=['GET'])
def system_status():
    """システムステータスAPI"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return jsonify({
        "cpu": {
            "percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used_gb": round(memory.used / (1024**3), 2),
            "total_gb": round(memory.total / (1024**3), 2)
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2)
        },
        "timestamp": datetime.now().isoformat()
    })


@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "ManaOS Dashboard",
        "port": 5050,
        "timestamp": datetime.now().isoformat()
    })


# HTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>まなOS 統一ダッシュボード</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 30px;
        }

        h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 1.1em;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }

        .tab {
            padding: 10px 20px;
            border: none;
            background: #e5e7eb;
            color: #333;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }

        .tab:hover {
            background: #d1d5db;
        }

        .tab.active {
            background: #667eea;
            color: white;
        }

        .content {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            min-height: 500px;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            opacity: 0.9;
        }

        .loading {
            text-align: center;
            padding: 50px;
            color: #666;
            font-size: 1.5em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 まなOS 統一ダッシュボード</h1>
            <p class="subtitle">全機能にアクセス可能な統一UI</p>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('tasks')">📋 タスク</button>
            <button class="tab" onclick="showTab('inventory')">📦 在庫</button>
            <button class="tab" onclick="showTab('schedule')">📅 スケジュール</button>
            <button class="tab" onclick="showTab('services')">🔧 サービス</button>
            <button class="tab" onclick="showTab('system')">💻 システム</button>
        </div>

        <div class="content">
            <div id="tasks" class="tab-content active">
                <h2>タスク管理</h2>
                <div class="loading">読み込み中...</div>
            </div>

            <div id="inventory" class="tab-content">
                <h2>在庫管理</h2>
                <div class="loading">読み込み中...</div>
            </div>

            <div id="schedule" class="tab-content">
                <h2>スケジュール管理</h2>
                <div class="loading">読み込み中...</div>
            </div>

            <div id="services" class="tab-content">
                <h2>サービス一覧</h2>
                <div class="loading">読み込み中...</div>
            </div>

            <div id="system" class="tab-content">
                <h2>システムステータス</h2>
                <div class="loading">読み込み中...</div>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // タブ切り替え
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');

            // データ読み込み
            loadTabData(tabName);
        }

        function loadTabData(tabName) {
            const content = document.getElementById(tabName);

            if (tabName === 'tasks') {
                loadTasks();
            } else if (tabName === 'inventory') {
                loadInventory();
            } else if (tabName === 'schedule') {
                loadSchedule();
            } else if (tabName === 'services') {
                loadServices();
            } else if (tabName === 'system') {
                loadSystem();
            }
        }

        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                const content = document.getElementById('tasks');
                content.innerHTML = `
                    <h2>タスク管理</h2>
                    <p>タスク数: ${data.count}</p>
                    <pre>${JSON.stringify(data.tasks, null, 2)}</pre>
                `;
            } catch (error) {
                console.error('Failed to load tasks:', error);
            }
        }

        async function loadInventory() {
            try {
                const response = await fetch('/api/inventory');
                const data = await response.json();
                const content = document.getElementById('inventory');
                content.innerHTML = `
                    <h2>在庫管理</h2>
                    <p>在庫数: ${data.count}</p>
                    <pre>${JSON.stringify(data.inventory, null, 2)}</pre>
                `;
            } catch (error) {
                console.error('Failed to load inventory:', error);
            }
        }

        async function loadSchedule() {
            try {
                const response = await fetch('/api/schedule');
                const data = await response.json();
                const content = document.getElementById('schedule');
                content.innerHTML = `
                    <h2>スケジュール管理</h2>
                    <p>予定数: ${data.count}</p>
                    <pre>${JSON.stringify(data.schedule, null, 2)}</pre>
                `;
            } catch (error) {
                console.error('Failed to load schedule:', error);
            }
        }

        async function loadServices() {
            try {
                const response = await fetch('/api/services');
                const data = await response.json();
                const content = document.getElementById('services');
                content.innerHTML = `
                    <h2>サービス一覧</h2>
                    <p>総数: ${data.total}, 稼働中: ${data.running}, 停止中: ${data.stopped}</p>
                    <pre>${JSON.stringify(data.services, null, 2)}</pre>
                `;
            } catch (error) {
                console.error('Failed to load services:', error);
            }
        }

        async function loadSystem() {
            try {
                const response = await fetch('/api/system');
                const data = await response.json();
                const content = document.getElementById('system');
                content.innerHTML = `
                    <h2>システムステータス</h2>
                    <p>CPU: ${data.cpu.percent}%, メモリ: ${data.memory.percent}%, ディスク: ${data.disk.percent}%</p>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            } catch (error) {
                console.error('Failed to load system:', error);
            }
        }

        // 初期読み込み
        loadTabData('tasks');
    </script>
</body>
</html>
"""


if __name__ == '__main__':
    print("🎯 まなOS統一ダッシュボード起動中...")
    print("📊 アクセス: http://localhost:5050")
    app.run(host='0.0.0.0', port=5050, debug=os.getenv("DEBUG", "False").lower() == "true")

