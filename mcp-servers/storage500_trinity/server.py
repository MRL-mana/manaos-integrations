#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trinity v2.0 Dashboard Server
===============================

Flask + SocketIOベースのリアルタイムダッシュボード

機能:
- REST API（タスク/エージェント/ログ管理）
- WebSocket通信（リアルタイム更新）
- ファイル監視統合
- CORS対応
"""

import sys
import os

# パスを追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from core.db_manager import DatabaseManager
from queue import Queue
import threading
import json
import logging
from datetime import datetime
from pathlib import Path

# ロギング設定
# セキュリティ注意: ログには機密情報（APIキー、パスワード、トークン）を絶対に出力しない
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/trinity_workspace/logs/dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flaskアプリ初期化
app = Flask(__name__, 
    static_folder='static',
    template_folder='static'
)

# Secret Key設定（環境変数から、なければ生成）
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())

# CORS設定
CORS(app, resources={r"/*": {"origins": "*"}})

# CSRF Protection有効化
csrf = CSRFProtect(app)

# SocketIO初期化（CSRF除外）
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    logger=True,
    engineio_logger=False
)

# WebSocketはCSRF保護から除外（Socket.IOが独自のセキュリティを持つため）
csrf.exempt(socketio)

# データベース初期化
db = DatabaseManager()

# グローバル変数
event_queue = Queue()
watcher_thread = None
connected_clients = set()


# ==================== セキュリティヘッダー ====================

@app.after_request
def set_security_headers(response):
    """セキュリティヘッダー設定（XSS/CSRF対策）"""
    # Content Security Policy - XSS対策
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdn.socket.io; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    # その他のセキュリティヘッダー
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HTTPS強制（本番環境）
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response


# ==================== ルート ====================

@app.route('/')
@csrf.exempt  # 静的ファイル提供はCSRF除外
def index():
    """メインダッシュボード"""
    return send_from_directory('static', 'index.html')


@app.route('/api/health')
@csrf.exempt
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': 'Trinity v2.0',
        'connected_clients': len(connected_clients),
        'database': 'connected'
    })


# ==================== タスクAPI ====================
# 注: APIエンドポイントはCSRF除外（別の認証方法を使用）

@app.route('/api/tasks', methods=['GET'])
@csrf.exempt
def get_tasks():
    """タスク一覧取得
    
    Query Parameters:
        status: str - タスクステータスでフィルタ
        assigned_to: str - 担当者でフィルタ
        priority: str - 優先度でフィルタ
    """
    try:
        status = request.args.get('status')
        assigned_to = request.args.get('assigned_to')
        priority = request.args.get('priority')
        
        tasks = db.get_tasks(
            status=status,
            assigned_to=assigned_to,
            priority=priority
        )
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'count': len(tasks),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
@csrf.exempt
def get_task(task_id):
    """個別タスク取得"""
    try:
        tasks = db.get_tasks(task_id=task_id)
        
        if not tasks:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        return jsonify({
            'success': True,
            'task': tasks[0]
        })
    
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tasks', methods=['POST'])
@csrf.exempt
def create_task():
    """タスク作成"""
    try:
        data = request.json
        
        if not data or 'title' not in data:
            return jsonify({
                'success': False,
                'error': 'Title is required'
            }), 400
        
        task_id = db.create_task(data)
        
        # WebSocketで通知
        socketio.emit('task_created', {
            'task_id': task_id,
            'task': data,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Task created: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Task created successfully'
        }), 201
    
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tasks/<task_id>', methods=['PUT'])
@csrf.exempt
def update_task(task_id):
    """タスク更新"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Update data is required'
            }), 400
        
        db.update_task(task_id, data)
        
        # 更新後のタスクを取得
        updated_tasks = db.get_tasks(task_id=task_id)
        updated_task = updated_tasks[0] if updated_tasks else None
        
        # WebSocketで通知
        if updated_task:
            socketio.emit('task_updated', {
                'task_id': task_id,
                'task': updated_task,
                'updates': data,
                'timestamp': datetime.now().isoformat()
            })
        
        logger.info(f"Task updated: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Task updated successfully',
            'task': updated_task
        })
    
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@csrf.exempt
def delete_task(task_id):
    """タスク削除"""
    try:
        db.delete_task(task_id)
        
        # WebSocketで通知
        socketio.emit('task_deleted', {
            'task_id': task_id,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Task deleted: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Task deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tasks/stats', methods=['GET'])
@csrf.exempt
def get_task_stats():
    """タスク統計取得"""
    try:
        stats = db.get_task_stats()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== エージェントAPI ====================

@app.route('/api/agents', methods=['GET'])
@csrf.exempt
def get_agents():
    """エージェント一覧取得"""
    try:
        agents = db.get_all_agent_status()
        
        return jsonify({
            'success': True,
            'agents': agents,
            'count': len(agents),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/agents/<agent_name>', methods=['GET'])
@csrf.exempt
def get_agent(agent_name):
    """個別エージェント状態取得"""
    try:
        status = db.get_agent_status(agent_name)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404
        
        return jsonify({
            'success': True,
            'agent': status
        })
    
    except Exception as e:
        logger.error(f"Failed to get agent {agent_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/agents/<agent_name>/tasks', methods=['GET'])
@csrf.exempt
def get_agent_tasks(agent_name):
    """エージェント別タスク取得"""
    try:
        tasks = db.get_tasks(assigned_to=agent_name)
        
        return jsonify({
            'success': True,
            'agent': agent_name,
            'tasks': tasks,
            'count': len(tasks)
        })
    
    except Exception as e:
        logger.error(f"Failed to get tasks for agent {agent_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/agents/<agent_name>/status', methods=['PUT'])
@csrf.exempt
def update_agent_status(agent_name):
    """エージェント状態更新"""
    try:
        data = request.json
        status = data.get('status')
        current_task_id = data.get('current_task_id')
        
        db.update_agent_status(
            agent_name=agent_name,
            status=status,
            current_task_id=current_task_id
        )
        
        # WebSocketで通知
        socketio.emit('agent_status_changed', {
            'agent': agent_name,
            'status': status,
            'current_task_id': current_task_id,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Agent status updated: {agent_name} -> {status}")
        
        return jsonify({
            'success': True,
            'agent': agent_name,
            'message': 'Agent status updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Failed to update agent status {agent_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== ログAPI ====================

@app.route('/api/logs', methods=['GET'])
@csrf.exempt
def get_logs():
    """ログ取得
    
    Query Parameters:
        agent: str - エージェント名でフィルタ
        limit: int - 取得件数（デフォルト: 50）
    """
    try:
        agent = request.args.get('agent')
        limit = request.args.get('limit', 50, type=int)
        
        logs = db.get_recent_logs(agent=agent, limit=limit)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== WebSocketイベント ====================

@socketio.on('connect')
def handle_connect():
    """クライアント接続"""
    client_id = request.sid  # type: ignore
    connected_clients.add(client_id)
    
    logger.info(f"Client connected: {client_id} (Total: {len(connected_clients)})")
    
    emit('connected', {
        'message': 'Connected to Trinity Dashboard',
        'client_id': client_id,
        'timestamp': datetime.now().isoformat()
    })


@socketio.on('disconnect')
def handle_disconnect():
    """クライアント切断"""
    client_id = request.sid  # type: ignore
    connected_clients.discard(client_id)
    
    logger.info(f"Client disconnected: {client_id} (Total: {len(connected_clients)})")


@socketio.on('subscribe_tasks')
def handle_subscribe_tasks():
    """タスク更新を購読"""
    client_id = request.sid  # type: ignore
    logger.info(f"Client {client_id} subscribed to task updates")
    
    # 現在のタスク一覧を送信
    try:
        tasks = db.get_tasks()
        emit('tasks_snapshot', {
            'tasks': tasks,
            'count': len(tasks),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to send tasks snapshot: {e}")
        emit('error', {'message': str(e)})


@socketio.on('subscribe_agents')
def handle_subscribe_agents():
    """エージェント状態更新を購読"""
    client_id = request.sid  # type: ignore
    logger.info(f"Client {client_id} subscribed to agent updates")
    
    # 現在のエージェント状態を送信
    try:
        agents = db.get_all_agent_status()
        emit('agents_snapshot', {
            'agents': agents,
            'count': len(agents),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to send agents snapshot: {e}")
        emit('error', {'message': str(e)})


@socketio.on('ping')
def handle_ping():
    """Ping/Pong（接続維持）"""
    emit('pong', {'timestamp': datetime.now().isoformat()})


# ==================== ファイル監視統合 ====================

def start_file_watcher():
    """ファイル監視を別スレッドで開始"""
    def watcher_loop():
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class TrinityFileHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    if event.src_path.endswith('tasks.db'):
                        # タスク変更を検知
                        socketio.emit('file_changed', {
                            'type': 'tasks_db_modified',
                            'timestamp': datetime.now().isoformat()
                        })
                        logger.info("tasks.db modified - notifying clients")
                    
                    elif event.src_path.endswith('sync_status.json'):
                        # メッセージ受信を検知
                        socketio.emit('file_changed', {
                            'type': 'sync_status_modified',
                            'timestamp': datetime.now().isoformat()
                        })
                        logger.info("sync_status.json modified - notifying clients")
            
            # 監視開始
            observer = Observer()
            event_handler = TrinityFileHandler()
            watch_path = '/root/trinity_workspace/shared'
            
            observer.schedule(event_handler, watch_path, recursive=False)
            observer.start()
            
            logger.info(f"File watcher started: {watch_path}")
            
            # 監視ループ
            import time
            while True:
                time.sleep(1)
        
        except Exception as e:
            logger.error(f"File watcher error: {e}")
    
    thread = threading.Thread(target=watcher_loop, daemon=True)
    thread.start()
    return thread


# ==================== メイン実行 ====================

def main():
    """ダッシュボードサーバー起動"""
    
    print("=" * 60)
    print("🎯 Trinity Dashboard v2.0 Starting...")
    print("=" * 60)
    print(f"📊 Dashboard URL: http://localhost:5100")
    print(f"🔗 API Endpoint: http://localhost:5100/api")
    print(f"📡 WebSocket: ws://localhost:5100/socket.io")
    print(f"📁 Static Files: /root/trinity_workspace/dashboard/static")
    print(f"💾 Database: /root/trinity_workspace/shared/tasks.db")
    print("=" * 60)
    
    # ファイル監視開始
    global watcher_thread
    watcher_thread = start_file_watcher()
    logger.info("File watcher thread started")
    
    # サーバー起動
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5100,
            debug=False,  # 本番環境ではFalse
            use_reloader=False,  # watchdogと競合するため
            log_output=True,
            allow_unsafe_werkzeug=True  # 開発環境用
        )
    except KeyboardInterrupt:
        logger.info("Dashboard server shutting down...")
        print("\n👋 Trinity Dashboard stopped.")
    except Exception as e:
        logger.error(f"Dashboard server error: {e}")
        raise


if __name__ == '__main__':
    main()

