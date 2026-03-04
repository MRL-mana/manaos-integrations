#!/usr/bin/env python3
"""
🎯 まなOS統一ダッシュボード - 全機能統合管理
ポート: 5050
既存のUnified Portalを拡張して、全機能にアクセス可能な統一UIを提供
"""

import os
import sys
import json
import sqlite3
import re
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from io import StringIO

from flask import Flask, jsonify, render_template, render_template_string, request, session, send_file, Response
from flask_cors import CORS
import psutil
import requests
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "manaos-dashboard-secret-key-2025")
CORS(app)

# データベースパス
DB_PATH = Path("/root/.mana_vault/manaos_dashboard.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_database():
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

    # 実績管理テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            work_time INTEGER DEFAULT 0,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    conn.commit()
    conn.close()


# データベース初期化
init_database()

# 監視対象サービス一覧
SERVICES = {
    "5008": {"name": "Mana Screen Sharing", "url": "http://localhost:5008"},
    "5050": {"name": "Unified Portal", "url": "http://localhost:5050"},
    "5054": {"name": "AI Predictive", "url": "http://localhost:5054"},
    "5062": {"name": "Security Monitor", "url": "http://localhost:5062"},
    "5063": {"name": "Cost Optimizer", "url": "http://localhost:5063"},
    "5176": {"name": "Task Executor", "url": "http://localhost:5176"},
    "5080": {"name": "AI Model Hub", "url": "http://localhost:5080"},
    "8001": {"name": "Trinity API Server", "url": "http://localhost:8001"},
    "8002": {"name": "Trinity Web UI", "url": "http://localhost:8002"},
    "11434": {"name": "Ollama", "url": "http://localhost:11434"},
}

def check_port_status(port):
    """ポートが開いているかチェック"""
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == int(port) and conn.status == 'LISTEN':
            return True
    return False

def get_service_health(port):
    """サービスのヘルスチェック"""
    if not check_port_status(port):
        return {"status": "stopped", "message": "Port not listening"}

    service = SERVICES.get(port)
    if not service:
        return {"status": "unknown", "message": "Service not registered"}

    try:
        # ヘルスチェックエンドポイントを試行
        for endpoint in ["/health", "/api/health", "/"]:
            try:
                response = requests.get(f"{service['url']}{endpoint}", timeout=2)
                if response.status_code == 200:
                    return {"status": "healthy", "message": "Service responding", "code": 200}
            except:
                continue

        return {"status": "running", "message": "Port open but health check failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.route('/')
def index():
    """メインダッシュボード"""
    # 新しい統一ダッシュボードを表示
    try:
        return render_template('dashboard_template.html')
    except:
        # フォールバック: インラインHTML
        return render_template_string(DASHBOARD_HTML)

@app.route('/api/services')
def list_services():
    """全サービス一覧"""
    services_status = []

    for port, info in SERVICES.items():
        health = get_service_health(port)
        services_status.append({
            "port": port,
            "name": info["name"],
            "url": info["url"],
            "status": health["status"],
            "message": health["message"]
        })

    return jsonify({
        "services": services_status,
        "total": len(services_status),
        "healthy": len([s for s in services_status if s["status"] == "healthy"]),
        "running": len([s for s in services_status if s["status"] in ["healthy", "running"]]),
        "stopped": len([s for s in services_status if s["status"] == "stopped"]),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/service/<port>')
def service_detail(port):
    """個別サービス詳細"""
    if port not in SERVICES:
        return jsonify({"error": "Service not found"}), 404

    health = get_service_health(port)
    service = SERVICES[port]

    return jsonify({
        "port": port,
        "name": service["name"],
        "url": service["url"],
        "health": health,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/system')
def system_status():
    """システムステータス"""
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

@app.route('/api/logs/<port>')
def get_service_logs(port):
    """サービスログ取得"""
    if port not in SERVICES:
        return jsonify({"error": "Service not found"}), 404

    service_name = SERVICES[port]["name"].lower().replace(" ", "_")
    log_paths = [
        f"/root/logs/{service_name}.log",
        f"/root/services/{service_name}/app.log",
        f"/var/log/{service_name}.log"
    ]

    for log_path in log_paths:
        if Path(log_path).exists():
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    return jsonify({
                        "log_file": log_path,
                        "lines": lines[-100:],  # 最新100行
                        "total_lines": len(lines)
                    })
            except Exception:
                continue

    return jsonify({
        "log_file": None,
        "lines": [],
        "message": "Log file not found"
    })

@app.route('/api/restart/<port>', methods=['POST'])
def restart_service(port):
    """サービス再起動"""
    if port not in SERVICES:
        return jsonify({"error": "Service not found"}), 404

    service_name = SERVICES[port]["name"].lower().replace(" ", "_")

    try:
        # systemctl restart 試行
        result = subprocess.run(
            ['systemctl', 'restart', service_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": f"Service {service_name} restarted",
                "port": port
            })
        else:
            return jsonify({
                "success": False,
                "message": result.stderr,
                "port": port
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e),
            "port": port
        }), 500

@app.route('/api/tasks', methods=['GET', 'POST'])
def tasks():
    """タスク管理API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        status = request.args.get('status', 'all')
        search = request.args.get('search', '')
        priority = request.args.get('priority', 'all')

        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status != 'all':
            query += " AND status = ?"
            params.append(status)

        if priority != 'all':
            query += " AND priority = ?"
            params.append(priority)

        if search:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)

        tasks_list = []
        for row in cursor.fetchall():
            tasks_list.append({
                "id": row[0], "title": row[1], "description": row[2],
                "status": row[3], "priority": row[4],
                "created_at": row[5], "updated_at": row[6], "due_date": row[7]
            })
        conn.close()
        return jsonify({"tasks": tasks_list, "count": len(tasks_list)})

    elif request.method == 'POST':
        data = request.get_json()
        cursor.execute("""
            INSERT INTO tasks (title, description, status, priority, due_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title"), data.get("description"),
            data.get("status", "todo"), data.get("priority", "normal"),
            data.get("due_date")
        ))
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "task_id": task_id}), 201


@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def task_detail(task_id):
    """タスク詳細API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            task = {
                "id": row[0], "title": row[1], "description": row[2],
                "status": row[3], "priority": row[4],
                "created_at": row[5], "updated_at": row[6], "due_date": row[7]
            }
            conn.close()
            return jsonify(task)
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    elif request.method == 'PUT':
        data = request.get_json()
        old_status = None

        # 現在のステータスを取得
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        old_row = cursor.fetchone()
        if old_row:
            old_status = old_row[0]

        # タスクを更新
        cursor.execute("""
            UPDATE tasks
            SET title = ?, description = ?, status = ?, priority = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data.get("title"), data.get("description"), data.get("status"),
            data.get("priority"), data.get("due_date"), task_id
        ))
        conn.commit()

        # タスクが完了した場合、実績を自動登録
        new_status = data.get("status")
        if old_status != 'done' and new_status == 'done':
            # タスク情報を取得
            cursor.execute("SELECT title, description FROM tasks WHERE id = ?", (task_id,))
            task_row = cursor.fetchone()
            if task_row:
                task_title = task_row[0]
                task_description = task_row[1]

                # 実績を自動登録
                cursor.execute("""
                    INSERT INTO achievements (task_id, title, description, work_time, completed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    task_id,
                    task_title,
                    task_description,
                    0,  # 作業時間は0分（後で編集可能）
                    datetime.now().isoformat()
                ))
                conn.commit()
                logger.info(f"✅ タスク完了時に実績を自動登録: task_id={task_id}, title={task_title}")

                # 通知を送信
                try:
                    # 通知テーブルが存在するか確認
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='notifications'
                    """)
                    if cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO notifications (title, message, type, user_id)
                            VALUES (?, ?, ?, ?)
                        """, (f"タスク完了: {task_title}", "タスクが完了しました", "success", "default"))
                        conn.commit()
                        logger.info(f"📬 通知を送信: タスク完了 - {task_title}")
                except Exception as e:
                    logger.error(f"通知作成エラー: {e}")

        conn.close()
        return jsonify({"success": True})

    elif request.method == 'DELETE':
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})


@app.route('/api/inventory', methods=['GET', 'POST'])
def inventory():
    """在庫管理API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        search = request.args.get('search', '')
        category = request.args.get('category', 'all')
        location = request.args.get('location', 'all')

        query = "SELECT * FROM inventory WHERE 1=1"
        params = []

        if category != 'all':
            query += " AND category = ?"
            params.append(category)

        if location != 'all':
            query += " AND location = ?"
            params.append(location)

        if search:
            query += " AND (name LIKE ? OR notes LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)

        items = []
        for row in cursor.fetchall():
            items.append({
                "id": row[0], "name": row[1], "category": row[2],
                "quantity": row[3], "location": row[4], "notes": row[5],
                "created_at": row[6], "updated_at": row[7]
            })
        conn.close()
        return jsonify({"inventory": items, "count": len(items)})

    elif request.method == 'POST':
        data = request.get_json()
        cursor.execute("""
            INSERT INTO inventory (name, category, quantity, location, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("name"), data.get("category"), data.get("quantity", 0),
            data.get("location"), data.get("notes")
        ))
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "item_id": item_id}), 201


@app.route('/api/schedule', methods=['GET', 'POST'])
def schedule():
    """スケジュール管理API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        search = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        query = "SELECT * FROM schedule WHERE 1=1"
        params = []

        if date_from:
            query += " AND start_time >= ?"
            params.append(date_from)

        if date_to:
            query += " AND start_time <= ?"
            params.append(date_to)

        if search:
            query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

        query += " ORDER BY start_time ASC"
        cursor.execute(query, params)

        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0], "title": row[1], "description": row[2],
                "start_time": row[3], "end_time": row[4], "location": row[5],
                "created_at": row[6], "updated_at": row[7]
            })
        conn.close()
        return jsonify({"schedule": events, "count": len(events)})

    elif request.method == 'POST':
        data = request.get_json()
        cursor.execute("""
            INSERT INTO schedule (title, description, start_time, end_time, location)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title"), data.get("description"),
            data.get("start_time"), data.get("end_time"), data.get("location")
        ))
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "event_id": event_id}), 201


@app.route('/api/image/generate', methods=['POST'])
def image_generate():
    """画像生成API"""
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        style = data.get("style", "clear_beautiful")
        model_name = data.get("model_name")
        size = data.get("size", "portrait")

        if not prompt:
            return jsonify({"error": "プロンプトが指定されていません"}), 400

        # 既存の画像生成APIにリクエストを転送
        try:
            api_url = "http://localhost:8001/api/image/generate"

            # サイズを幅・高さに変換
            size_map = {
                "portrait": {"width": 512, "height": 768},
                "landscape": {"width": 768, "height": 512},
                "square": {"width": 512, "height": 512}
            }
            dimensions = size_map.get(size, size_map["portrait"])

            response = requests.post(api_url, json={
                "prompt": prompt,
                "width": dimensions["width"],
                "height": dimensions["height"],
                "steps": 20
            }, timeout=300)

            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    "success": True,
                    "filepath": result.get("filepath"),
                    "image_path": result.get("filepath"),
                    "generation_time": result.get("generation_time"),
                    "message": "画像生成が完了しました"
                })
            else:
                error_text = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
                return jsonify({"error": "画像生成に失敗しました", "details": error_text}), 500
        except requests.exceptions.RequestException as e:
            logger.error(f"画像生成API接続エラー: {e}")
            return jsonify({"error": "画像生成APIに接続できませんでした", "details": str(e)}), 503
        except Exception as e:
            logger.error(f"画像生成エラー: {e}")
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"画像生成APIエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/image/history', methods=['GET'])
def image_history():
    """画像生成履歴API"""
    try:
        # 画像生成履歴を取得（生成された画像ファイルから）
        import os
        from pathlib import Path

        image_dirs = [
            Path("/root/generated_images"),
            Path("/root/ai_outputs"),
            Path("/root/trinity_workspace/generated"),
        ]

        images = []
        for img_dir in image_dirs:
            if img_dir.exists():
                for img_file in img_dir.glob("*.png"):
                    stat = img_file.stat()
                    images.append({
                        "filename": img_file.name,
                        "path": str(img_file),
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

        # 作成日時でソート
        images.sort(key=lambda x: x["created_at"], reverse=True)

        return jsonify({
            "images": images[:50],  # 最新50件
            "count": len(images)
        })
    except Exception as e:
        logger.error(f"画像履歴取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/pdf_excel/convert', methods=['POST'])
def pdf_excel_convert():
    """PDF→Excel変換API"""
    try:
        # 既存のPDF→Excel変換APIにリクエストを転送
        api_url = "http://localhost:8001/api/pdf_excel/convert"

        # ファイルアップロードの処理
        if 'file' in request.files:
            file = request.files['file']
            files = {'file': (file.filename, file.stream, file.content_type)}
            response = requests.post(api_url, files=files, timeout=300)
        else:
            data = request.get_json()
            response = requests.post(api_url, json=data, timeout=300)

        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "success": True,
                "filepath": result.get("filepath"),
                "message": "PDF→Excel変換が完了しました"
            })
        else:
            error_text = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
            return jsonify({"error": "PDF→Excel変換に失敗しました", "details": error_text}), 500
    except requests.exceptions.RequestException as e:
        logger.error(f"PDF→Excel変換API接続エラー: {e}")
        return jsonify({"error": "PDF→Excel変換APIに接続できませんでした", "details": str(e)}), 503
    except Exception as e:
        logger.error(f"PDF→Excel変換エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/pdf_excel/status', methods=['GET'])
def pdf_excel_status():
    """PDF→Excel変換ステータスAPI"""
    try:
        api_url = "http://localhost:8001/api/pdf_excel/status"
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "ステータス取得に失敗しました"}), 500
    except Exception as e:
        logger.error(f"PDF→Excel変換ステータス取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


def _parse_intent(message: str) -> Dict[str, Any]:
    """メッセージから意図を解析"""
    message_lower = message.lower()

    # タスク関連
    if any(word in message_lower for word in ['タスク', 'task', 'やること', 'todo']):
        if any(word in message_lower for word in ['追加', 'add', '作る', '作成']):
            return {"type": "task_create", "confidence": 0.9}
        elif any(word in message_lower for word in ['一覧', "list", '見る', '確認']):
            return {"type": "task_list", "confidence": 0.9}
        elif any(word in message_lower for word in ['完了', 'done', '終了']):
            return {"type": "task_complete", "confidence": 0.9}

    # 在庫関連
    elif any(word in message_lower for word in ['在庫', 'inventory', 'ストック', 'stock']):
        if any(word in message_lower for word in ['追加', 'add', '作る', '作成']):
            return {"type": "inventory_create", "confidence": 0.9}
        elif any(word in message_lower for word in ['一覧', 'list', '見る', '確認']):
            return {"type": "inventory_list", "confidence": 0.9}
        elif any(word in message_lower for word in ['検索', 'search', '探す']):
            return {"type": "inventory_search", "confidence": 0.9}

    # スケジュール関連
    elif any(word in message_lower for word in ['予定', 'schedule', 'カレンダー', 'calendar']):
        if any(word in message_lower for word in ['追加', 'add', '作る', '作成']):
            return {"type": "schedule_create", "confidence": 0.9}
        elif any(word in message_lower for word in ['一覧', 'list', '見る', '確認', '明日', '来週']):
            return {"type": "schedule_list", "confidence": 0.9}

    # 画像生成関連
    elif any(word in message_lower for word in ['画像', 'image', '生成', 'generate', '絵', '作って']):
        return {"type": "image_generate", "confidence": 0.9}

    # 情報収集関連
    elif any(word in message_lower for word in ['調べて', '検索', 'search', '情報', 'info']):
        return {"type": "info_search", "confidence": 0.8}

    # デフォルト
    return {"type": "unknown", "confidence": 0.5}


def _extract_task_from_message(message: str) -> Dict[str, Any]:
    """メッセージからタスク情報を抽出"""
    title = message
    description = ""
    priority = "normal"

    # 「：」や「:」で区切られている場合、後半をタイトルにする
    if '：' in message:
        parts = message.split('：', 1)
        title = parts[1].strip() if len(parts) > 1 else message
    elif ':' in message and not message.startswith('http'):
        parts = message.split(':', 1)
        title = parts[1].strip() if len(parts) > 1 else message

    # 「タスクを追加して」などの前置詞を削除
    remove_patterns = [
        r'タスク[を]?追加して?',
        r'タスク[を]?作成して?',
        r'タスク[を]?作って?',
        r'task[を]?add',
        r'task[を]?create',
        r'^タスク',
        r'^task'
    ]
    import re
    for pattern in remove_patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()

    # 余分な空白や記号を削除
    title = title.strip(' ：:、,')

    if not title:
        title = "新しいタスク"

    return {
        "title": title,
        "description": description,
        "priority": priority,
        "status": "todo"
    }


def _extract_inventory_from_message(message: str) -> Dict[str, Any]:
    """メッセージから在庫情報を抽出"""
    words = message.split()
    name = message
    quantity = 1
    category = ""

    # 「在庫を追加して」などの前置詞を削除
    remove_words = ['在庫', 'を', '追加', 'して', '作成', '作って', 'inventory', 'add', 'create']
    for word in remove_words:
        name = name.replace(word, "").strip()

    if not name:
        name = "新しい在庫"

    return {
        "name": name,
        "quantity": quantity,
        "category": category,
        "location": ""
    }


def _extract_schedule_from_message(message: str) -> Dict[str, Any]:
    """メッセージからスケジュール情報を抽出"""
    title = message
    description = ""

    # 「予定を追加して」などの前置詞を削除
    remove_words = ['予定', 'を', '追加', 'して', '作成', '作って', 'schedule', 'add', 'create']
    for word in remove_words:
        title = title.replace(word, "").strip()

    if not title:
        title = "新しい予定"

    return {
        "title": title,
        "description": description,
        "start_time": None,
        "end_time": None,
        "location": ""
    }


def _extract_image_prompt_from_message(message: str) -> str:
    """メッセージから画像生成プロンプトを抽出"""
    # 「画像を生成して」などの前置詞を削除
    remove_words = ['画像', 'を', '生成', 'して', '作って', '絵', 'image', 'generate', 'create']
    prompt = message
    for word in remove_words:
        prompt = prompt.replace(word, "").strip()

    if not prompt:
        prompt = "a beautiful clear girl, innocent expression, soft smile"

    return prompt


def _execute_intent(intent: Dict[str, Any], message: str, user_id: str) -> Dict[str, Any]:
    """意図に応じて処理を実行"""
    intent_type = intent.get('type')

    try:
        if intent_type == "task_create":
            # タスク作成
            task_data = _extract_task_from_message(message)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, status, priority)
                VALUES (?, ?, ?, ?)
            """, (task_data['title'], task_data['description'], task_data['status'], task_data['priority']))
            conn.commit()
            task_id = cursor.lastrowid
            conn.close()
            return {
                "message": f"タスク「{task_data['title']}」を作成しました",
                "task_id": task_id,
                "task": task_data
            }

        elif intent_type == "task_list":
            # タスク一覧取得
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10")
            tasks = cursor.fetchall()
            conn.close()
            task_list = [{"id": t[0], "title": t[1], "status": t[3]} for t in tasks]
            return {
                "message": f"{len(task_list)}件のタスクが見つかりました",
                "tasks": task_list
            }

        elif intent_type == "inventory_create":
            # 在庫作成
            inventory_data = _extract_inventory_from_message(message)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (name, category, quantity, location)
                VALUES (?, ?, ?, ?)
            """, (inventory_data['name'], inventory_data['category'], inventory_data['quantity'], inventory_data['location']))
            conn.commit()
            inventory_id = cursor.lastrowid
            conn.close()
            return {
                "message": f"在庫「{inventory_data['name']}」を追加しました",
                "inventory_id": inventory_id,
                "inventory": inventory_data
            }

        elif intent_type == "inventory_list":
            # 在庫一覧取得
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory ORDER BY created_at DESC LIMIT 10")
            inventory_items = cursor.fetchall()
            conn.close()
            inventory_list = [{"id": i[0], "name": i[1], "quantity": i[3]} for i in inventory_items]
            return {
                "message": f"{len(inventory_list)}件の在庫が見つかりました",
                "inventory": inventory_list
            }

        elif intent_type == "schedule_create":
            # スケジュール作成
            schedule_data = _extract_schedule_from_message(message)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule (title, description, start_time, end_time, location)
                VALUES (?, ?, ?, ?, ?)
            """, (schedule_data['title'], schedule_data['description'], schedule_data['start_time'], schedule_data['end_time'], schedule_data['location']))
            conn.commit()
            schedule_id = cursor.lastrowid
            conn.close()
            return {
                "message": f"予定「{schedule_data['title']}」を追加しました",
                "schedule_id": schedule_id,
                "schedule": schedule_data
            }

        elif intent_type == "schedule_list":
            # スケジュール一覧取得
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedule ORDER BY start_time ASC LIMIT 10")
            schedules = cursor.fetchall()
            conn.close()
            schedule_list = [{"id": s[0], "title": s[1], "start_time": s[3]} for s in schedules]
            return {
                "message": f"{len(schedule_list)}件の予定が見つかりました",
                "schedules": schedule_list
            }

        elif intent_type == "image_generate":
            # 画像生成
            prompt = _extract_image_prompt_from_message(message)
            try:
                api_url = "http://localhost:8001/api/image/generate"
                response = requests.post(api_url, json={
                    "prompt": prompt,
                    "width": 512,
                    "height": 768,
                    "steps": 20
                }, timeout=300)
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "message": f"画像を生成しました: {prompt}",
                        "filepath": result.get("filepath"),
                        "prompt": prompt
                    }
                else:
                    return {
                        "message": f"画像生成に失敗しました: {prompt}",
                        "error": "API接続エラー"
                    }
            except Exception as e:
                return {
                    "message": f"画像生成に失敗しました: {prompt}",
                    "error": str(e)
                }

        else:
            return {
                "message": f"メッセージを理解しました: {message}",
                "intent": intent_type,
                "note": "対応する機能を実行できませんでした"
            }
    except Exception as e:
        logger.error(f"意図実行エラー: {e}")
        return {
            "message": f"処理中にエラーが発生しました: {message}",
            "error": str(e)
        }


@app.route('/api/achievements', methods=['GET', 'POST'])
def achievements():
    """実績管理API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == 'GET':
        task_id = request.args.get('task_id', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        query = "SELECT * FROM achievements WHERE 1=1"
        params = []

        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)

        if date_from:
            query += " AND completed_at >= ?"
            params.append(date_from)

        if date_to:
            query += " AND completed_at <= ?"
            params.append(date_to)

        query += " ORDER BY completed_at DESC"
        cursor.execute(query, params)

        achievements_list = []
        for row in cursor.fetchall():
            achievements_list.append({
                "id": row[0], "task_id": row[1], "title": row[2],
                "description": row[3], "work_time": row[4],
                "completed_at": row[5], "created_at": row[6], "updated_at": row[7]
            })
        conn.close()
        return jsonify({"achievements": achievements_list, "count": len(achievements_list)})

    elif request.method == 'POST':
        data = request.get_json()
        cursor.execute("""
            INSERT INTO achievements (task_id, title, description, work_time, completed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("task_id"), data.get("title"),
            data.get("description", ""), data.get("work_time", 0),
            data.get("completed_at", datetime.now().isoformat())
        ))
        conn.commit()
        achievement_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "achievement_id": achievement_id}), 201


@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """ダッシュボード統計API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 今日の日付
        today = datetime.now().date().isoformat()

        # 今日のタスク数
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE DATE(created_at) = ?", (today,))
        today_tasks = cursor.fetchone()[0]

        # 未完了のタスク数
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != 'done'")
        pending_tasks = cursor.fetchone()[0]

        # 完了したタスク数
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'")
        completed_tasks = cursor.fetchone()[0]

        # 今週の実績数
        cursor.execute("""
            SELECT COUNT(*) FROM achievements
            WHERE DATE(completed_at) >= DATE('now', '-7 days')
        """)
        week_achievements = cursor.fetchone()[0]

        # 今週の作業時間（分）
        cursor.execute("""
            SELECT COALESCE(SUM(work_time), 0) FROM achievements
            WHERE DATE(completed_at) >= DATE('now', '-7 days')
        """)
        week_work_time = cursor.fetchone()[0]

        # 今週の予定数
        cursor.execute("""
            SELECT COUNT(*) FROM schedule
            WHERE DATE(start_time) >= DATE('now', '-7 days')
            AND DATE(start_time) <= DATE('now', '+7 days')
        """)
        week_schedule = cursor.fetchone()[0]

        # 在庫数
        cursor.execute("SELECT COUNT(*) FROM inventory")
        inventory_count = cursor.fetchone()[0]

        # 最近のタスク（5件）
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 5")
        recent_tasks = []
        for row in cursor.fetchall():
            recent_tasks.append({
                "id": row[0], "title": row[1], "description": row[2],
                "status": row[3], "priority": row[4],
                "created_at": row[5], "updated_at": row[6], "due_date": row[7]
            })

        # 最近の実績（過去7日間）
        cursor.execute("""
            SELECT * FROM achievements
            WHERE DATE(completed_at) >= DATE('now', '-7 days')
            ORDER BY completed_at DESC
        """)
        recent_achievements = []
        for row in cursor.fetchall():
            recent_achievements.append({
                "id": row[0], "task_id": row[1], "title": row[2],
                "description": row[3], "work_time": row[4],
                "completed_at": row[5], "created_at": row[6], "updated_at": row[7]
            })

        conn.close()

        return jsonify({
            "success": True,
            "stats": {
                "today_tasks": today_tasks,
                "pending_tasks": pending_tasks,
                "completed_tasks": completed_tasks,
                "week_achievements": week_achievements,
                "week_work_time": week_work_time,
                "week_schedule": week_schedule,
                "inventory_count": inventory_count
            },
            "recent_tasks": recent_tasks,
            "recent_achievements": recent_achievements
        })
    except Exception as e:
        logger.error(f"ダッシュボード統計エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/tasks', methods=['GET'])
def export_tasks():
    """タスクエクスポートAPI"""
    try:
        format_type = request.args.get('format', 'json')  # json or csv

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0], "title": row[1], "description": row[2] or "",
                "status": row[3], "priority": row[4],
                "created_at": row[5], "updated_at": row[6], "due_date": row[7] or ""
            })
        conn.close()

        if format_type == 'csv':
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=['id', 'title', 'description', 'status', 'priority', 'created_at', 'updated_at', 'due_date'])
            writer.writeheader()
            writer.writerows(tasks)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=tasks.csv'}
            )
        else:
            return jsonify({"success": True, "tasks": tasks, "count": len(tasks)})
    except Exception as e:
        logger.error(f"タスクエクスポートエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/inventory', methods=['GET'])
def export_inventory():
    """在庫エクスポートAPI"""
    try:
        format_type = request.args.get('format', 'json')  # json or csv

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory ORDER BY created_at DESC")
        items = []
        for row in cursor.fetchall():
            items.append({
                "id": row[0], "name": row[1], "category": row[2] or "",
                "quantity": row[3], "location": row[4] or "", "notes": row[5] or "",
                "created_at": row[6], "updated_at": row[7]
            })
        conn.close()

        if format_type == 'csv':
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=['id', 'name', 'category', 'quantity', 'location', 'notes', 'created_at', 'updated_at'])
            writer.writeheader()
            writer.writerows(items)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=inventory.csv'}
            )
        else:
            return jsonify({"success": True, "inventory": items, "count": len(items)})
    except Exception as e:
        logger.error(f"在庫エクスポートエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/schedule', methods=['GET'])
def export_schedule():
    """スケジュールエクスポートAPI"""
    try:
        format_type = request.args.get('format', 'json')  # json or csv

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedule ORDER BY start_time ASC")
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0], "title": row[1], "description": row[2] or "",
                "start_time": row[3] or "", "end_time": row[4] or "", "location": row[5] or "",
                "created_at": row[6], "updated_at": row[7]
            })
        conn.close()

        if format_type == 'csv':
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=['id', 'title', 'description', 'start_time', 'end_time', 'location', 'created_at', 'updated_at'])
            writer.writeheader()
            writer.writerows(events)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=schedule.csv'}
            )
        else:
            return jsonify({"success": True, "schedule": events, "count": len(events)})
    except Exception as e:
        logger.error(f"スケジュールエクスポートエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/achievements', methods=['GET'])
def export_achievements():
    """実績エクスポートAPI"""
    try:
        format_type = request.args.get('format', 'json')  # json or csv

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM achievements ORDER BY completed_at DESC")
        achievements = []
        for row in cursor.fetchall():
            achievements.append({
                "id": row[0], "task_id": row[1] or "", "title": row[2],
                "description": row[3] or "", "work_time": row[4],
                "completed_at": row[5] or "", "created_at": row[6], "updated_at": row[7]
            })
        conn.close()

        if format_type == 'csv':
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=['id', 'task_id', 'title', 'description', 'work_time', 'completed_at', 'created_at', 'updated_at'])
            writer.writeheader()
            writer.writerows(achievements)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=achievements.csv'}
            )
        else:
            return jsonify({"success": True, "achievements": achievements, "count": len(achievements)})
    except Exception as e:
        logger.error(f"実績エクスポートエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/notifications', methods=['GET', 'POST'])
def notifications():
    """通知管理API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 通知テーブルを作成（存在しない場合）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT,
                type TEXT DEFAULT 'info',
                read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT DEFAULT 'default'
            )
        """)
        conn.commit()

        if request.method == 'GET':
            # 未読通知を取得
            read_filter = request.args.get('read', 'all')  # all, unread, read
            limit = request.args.get('limit', 50, type=int)

            query = "SELECT * FROM notifications WHERE 1=1"
            params = []

            if read_filter == 'unread':
                query += " AND read = 0"
            elif read_filter == 'read':
                query += " AND read = 1"

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            notifications_list = []
            for row in cursor.fetchall():
                notifications_list.append({
                    "id": row[0], "title": row[1], "message": row[2],
                    "type": row[3], "read": bool(row[4]),
                    "created_at": row[5], "user_id": row[6]
                })

            # 未読数
            cursor.execute("SELECT COUNT(*) FROM notifications WHERE read = 0")
            unread_count = cursor.fetchone()[0]

            conn.close()
            return jsonify({
                "success": True,
                "notifications": notifications_list,
                "unread_count": unread_count,
                "count": len(notifications_list)
            })

        elif request.method == 'POST':
            # 通知を作成
            data = request.get_json()
            title = data.get('title', '')
            message = data.get('message', '')
            notification_type = data.get('type', 'info')  # info, success, warning, error
            user_id = data.get('user_id', 'default')

            if not title:
                return jsonify({"error": "タイトルが指定されていません"}), 400

            cursor.execute("""
                INSERT INTO notifications (title, message, type, user_id)
                VALUES (?, ?, ?, ?)
            """, (title, message, notification_type, user_id))
            conn.commit()
            notification_id = cursor.lastrowid
            conn.close()

            return jsonify({
                "success": True,
                "notification_id": notification_id
            }), 201

    except Exception as e:
        logger.error(f"通知管理エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/notifications/<int:notification_id>', methods=['PUT', 'DELETE'])
def notification_detail(notification_id):
    """通知詳細API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if request.method == 'PUT':
            # 通知を既読にする
            data = request.get_json()
            read = data.get('read', True)

            cursor.execute("""
                UPDATE notifications SET read = ? WHERE id = ?
            """, (1 if read else 0, notification_id))
            conn.commit()
            conn.close()

            return jsonify({"success": True})

        elif request.method == 'DELETE':
            # 通知を削除
            cursor.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
            conn.commit()
            conn.close()

            return jsonify({"success": True})

    except Exception as e:
        logger.error(f"通知詳細エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/notifications/read-all', methods=['POST'])
def read_all_notifications():
    """すべての通知を既読にするAPI"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("UPDATE notifications SET read = 1 WHERE read = 0")
        conn.commit()
        conn.close()

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"通知既読エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/search', methods=['GET'])
def global_search():
    """グローバル検索API"""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 50, type=int)

        if not query:
            return jsonify({"error": "検索クエリが指定されていません"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        results = {
            "tasks": [],
            "inventory": [],
            "schedule": [],
            "achievements": [],
            "total": 0
        }

        # タスクを検索
        cursor.execute("""
            SELECT * FROM tasks
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f'%{query}%', f'%{query}%', limit))
        for row in cursor.fetchall():
            results["tasks"].append({
                "id": row[0], "title": row[1], "description": row[2] or "",
                "status": row[3], "priority": row[4],
                "created_at": row[5], "updated_at": row[6], "due_date": row[7] or ""
            })

        # 在庫を検索
        cursor.execute("""
            SELECT * FROM inventory
            WHERE name LIKE ? OR category LIKE ? OR notes LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        for row in cursor.fetchall():
            results["inventory"].append({
                "id": row[0], "name": row[1], "category": row[2] or "",
                "quantity": row[3], "location": row[4] or "", "notes": row[5] or "",
                "created_at": row[6], "updated_at": row[7]
            })

        # スケジュールを検索
        cursor.execute("""
            SELECT * FROM schedule
            WHERE title LIKE ? OR description LIKE ? OR location LIKE ?
            ORDER BY start_time ASC LIMIT ?
        """, (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        for row in cursor.fetchall():
            results["schedule"].append({
                "id": row[0], "title": row[1], "description": row[2] or "",
                "start_time": row[3] or "", "end_time": row[4] or "", "location": row[5] or "",
                "created_at": row[6], "updated_at": row[7]
            })

        # 実績を検索
        cursor.execute("""
            SELECT * FROM achievements
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY completed_at DESC LIMIT ?
        """, (f'%{query}%', f'%{query}%', limit))
        for row in cursor.fetchall():
            results["achievements"].append({
                "id": row[0], "task_id": row[1] or "", "title": row[2],
                "description": row[3] or "", "work_time": row[4],
                "completed_at": row[5] or "", "created_at": row[6], "updated_at": row[7]
            })

        results["total"] = len(results["tasks"]) + len(results["inventory"]) + len(results["schedule"]) + len(results["achievements"])

        conn.close()

        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "total": results["total"]
        })
    except Exception as e:
        logger.error(f"グローバル検索エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/backup', methods=['GET', 'POST'])
def backup_data():
    """データバックアップAPI"""
    try:
        import shutil
        import json
        from datetime import datetime
        from pathlib import Path

        backup_dir = Path("/root/.mana_vault/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        if request.method == 'GET':
            # バックアップ一覧を取得
            backups = []
            for backup_file in backup_dir.glob("manaos_dashboard_*.db"):
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(backup_file)
                })
            backups.sort(key=lambda x: x["created_at"], reverse=True)

            return jsonify({
                "success": True,
                "backups": backups,
                "count": len(backups)
            })

        elif request.method == 'POST':
            # バックアップを作成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"manaos_dashboard_{timestamp}.db"
            backup_path = backup_dir / backup_filename

            # データベースをコピー
            shutil.copy2(DB_PATH, backup_path)

            logger.info(f"✅ データバックアップ作成: {backup_path}")

            return jsonify({
                "success": True,
                "backup_path": str(backup_path),
                "filename": backup_filename,
                "message": "バックアップが作成されました"
            }), 201

    except Exception as e:
        logger.error(f"バックアップエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/backup/<filename>', methods=['GET', 'DELETE'])
def backup_detail(filename):
    """バックアップ詳細API"""
    try:
        import shutil
        from pathlib import Path

        backup_dir = Path("/root/.mana_vault/backups")
        backup_path = backup_dir / filename

        if not backup_path.exists():
            return jsonify({"error": "バックアップが見つかりません"}), 404

        if request.method == 'GET':
            # バックアップをダウンロード
            return send_file(str(backup_path), as_attachment=True, download_name=filename)

        elif request.method == 'DELETE':
            # バックアップを削除
            backup_path.unlink()
            logger.info(f"✅ バックアップ削除: {backup_path}")

            return jsonify({"success": True, "message": "バックアップが削除されました"})

    except Exception as e:
        logger.error(f"バックアップ詳細エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/restore', methods=['POST'])
def restore_data():
    """データ復元API"""
    try:
        import shutil
        from pathlib import Path
        from datetime import datetime

        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({"error": "ファイル名が指定されていません"}), 400

        backup_dir = Path("/root/.mana_vault/backups")
        backup_path = backup_dir / filename

        if not backup_path.exists():
            return jsonify({"error": "バックアップが見つかりません"}), 404

        # 現在のデータベースをバックアップ（復元前の安全対策）
        restore_backup_dir = Path("/root/.mana_vault/restore_backups")
        restore_backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        restore_backup_filename = f"manaos_dashboard_before_restore_{timestamp}.db"
        restore_backup_path = restore_backup_dir / restore_backup_filename

        # データベースファイルが存在する場合のみバックアップ
        db_exists = DB_PATH.exists()
        if db_exists:
            shutil.copy2(DB_PATH, restore_backup_path)
            logger.info(f"✅ 復元前バックアップ: {restore_backup_path}")

        # バックアップから復元
        shutil.copy2(backup_path, DB_PATH)

        logger.info(f"✅ データ復元: {backup_path} -> {DB_PATH}")

        return jsonify({
            "success": True,
            "message": "データが復元されました。ページを再読み込みしてください。",
            "restore_backup": str(restore_backup_path) if db_exists else None
        })

    except Exception as e:
        logger.error(f"データ復元エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/nlp', methods=['POST'])
def nlp_process():
    """自然言語処理API（Slack/Telegramからの入力に対応）"""
    try:
        data = request.get_json()
        message = data.get("message", "")
        user_id = data.get("user_id", "default")
        source = data.get("source", "web")  # web, slack, telegram

        if not message:
            return jsonify({"error": "メッセージが指定されていません"}), 400

        logger.info(f"📝 自然言語処理: {message} (user: {user_id}, source: {source})")

        # 意図を解析
        intent = _parse_intent(message)

        # 意図に応じて処理
        result = _execute_intent(intent, message, user_id)

        return jsonify({
            "success": True,
            "intent": intent,
            "result": result,
            "message": message
        })
    except Exception as e:
        logger.error(f"自然言語処理エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Unified Portal",
        "port": 5050,
        "timestamp": datetime.now().isoformat()
    })


# HTMLテンプレート（フォールバック用）
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>まなOS 統一ダッシュボード</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 30px;
        }
        h1 { color: #667eea; font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { color: #666; font-size: 1.1em; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            flex-wrap: wrap;
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
        .tab:hover { background: #d1d5db; }
        .tab.active { background: #667eea; color: white; }
        .content {
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            min-height: 500px;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
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
            <div id="tasks" class="tab-content active"><h2>タスク管理</h2><div class="loading">読み込み中...</div></div>
            <div id="inventory" class="tab-content"><h2>在庫管理</h2><div class="loading">読み込み中...</div></div>
            <div id="schedule" class="tab-content"><h2>スケジュール管理</h2><div class="loading">読み込み中...</div></div>
            <div id="services" class="tab-content"><h2>サービス一覧</h2><div class="loading">読み込み中...</div></div>
            <div id="system" class="tab-content"><h2>システムステータス</h2><div class="loading">読み込み中...</div></div>
        </div>
    </div>
    <script>
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
            loadTabData(tabName);
        }
        function loadTabData(tabName) {
            if (tabName === 'tasks') loadTasks();
            else if (tabName === 'inventory') loadInventory();
            else if (tabName === 'schedule') loadSchedule();
            else if (tabName === 'services') loadServices();
            else if (tabName === 'system') loadSystem();
        }
        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                const content = document.getElementById('tasks');
                if (data.tasks && data.tasks.length > 0) {
                    content.innerHTML = '<h2>タスク管理</h2><p>タスク数: ' + data.count + '</p><pre>' + JSON.stringify(data.tasks, null, 2) + '</pre>';
                } else {
                    content.innerHTML = '<h2>タスク管理</h2><p>タスクがありません</p>';
                }
            } catch (error) {
                console.error('Failed to load tasks:', error);
                document.getElementById('tasks').innerHTML = '<h2>タスク管理</h2><p>エラーが発生しました</p>';
            }
        }
        async function loadInventory() {
            try {
                const response = await fetch('/api/inventory');
                const data = await response.json();
                const content = document.getElementById('inventory');
                if (data.inventory && data.inventory.length > 0) {
                    content.innerHTML = '<h2>在庫管理</h2><p>在庫数: ' + data.count + '</p><pre>' + JSON.stringify(data.inventory, null, 2) + '</pre>';
                } else {
                    content.innerHTML = '<h2>在庫管理</h2><p>在庫がありません</p>';
                }
            } catch (error) {
                console.error('Failed to load inventory:', error);
                document.getElementById('inventory').innerHTML = '<h2>在庫管理</h2><p>エラーが発生しました</p>';
            }
        }
        async function loadSchedule() {
            try {
                const response = await fetch('/api/schedule');
                const data = await response.json();
                const content = document.getElementById('schedule');
                if (data.schedule && data.schedule.length > 0) {
                    content.innerHTML = '<h2>スケジュール管理</h2><p>予定数: ' + data.count + '</p><pre>' + JSON.stringify(data.schedule, null, 2) + '</pre>';
                } else {
                    content.innerHTML = '<h2>スケジュール管理</h2><p>予定がありません</p>';
                }
            } catch (error) {
                console.error('Failed to load schedule:', error);
                document.getElementById('schedule').innerHTML = '<h2>スケジュール管理</h2><p>エラーが発生しました</p>';
            }
        }
        async function loadServices() {
            try {
                const response = await fetch('/api/services');
                const data = await response.json();
                const content = document.getElementById('services');
                let html = '<h2>サービス一覧</h2><p>総数: ' + data.total + ', 稼働中: ' + data.running + ', 停止中: ' + data.stopped + '</p><pre>' + JSON.stringify(data.services, null, 2) + '</pre>';
                content.innerHTML = html;
            } catch (error) {
                console.error('Failed to load services:', error);
                document.getElementById('services').innerHTML = '<h2>サービス一覧</h2><p>エラーが発生しました</p>';
            }
        }
        async function loadSystem() {
            try {
                const response = await fetch('/api/system');
                const data = await response.json();
                const content = document.getElementById('system');
                content.innerHTML = '<h2>システムステータス</h2><p>CPU: ' + data.cpu.percent.toFixed(1) + '%, メモリ: ' + data.memory.percent.toFixed(1) + '%, ディスク: ' + data.disk.percent.toFixed(1) + '%</p><pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                console.error('Failed to load system:', error);
                document.getElementById('system').innerHTML = '<h2>システムステータス</h2><p>エラーが発生しました</p>';
            }
        }
        loadTabData('tasks');
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("🎯 まなOS統一ダッシュボード起動中...")
    print("📊 アクセス: http://localhost:5050")
    app.run(host='0.0.0.0', port=5050, debug=os.getenv("DEBUG", "False").lower() == "true")

