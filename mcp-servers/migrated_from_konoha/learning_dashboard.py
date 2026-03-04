#!/usr/bin/env python3
"""
🎨 ManaOS Learning Dashboard
リアルタイム学習状況を可視化
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import sys
import requests

sys.path.insert(0, str(Path("/root/trinity_workspace/stabilization")))

app = Flask(__name__)

WORKSPACE = Path("/root/trinity_workspace")
REFLECTION_DB = WORKSPACE / "shared" / "reflection_memory.db"
COGNITIVE_DB = WORKSPACE / "shared" / "cognitive_memory.db"
IMPROVEMENT_DB = WORKSPACE / "shared" / "auto_improvement.db"
DAILY_DB = WORKSPACE / "shared" / "daily_reflections.db"

# Trinity統合秘書API
SECRETARY_API_URL = "http://127.0.0.1:8888"

def get_reflection_stats():
    """Reflection Engineの統計"""
    try:
        conn = sqlite3.connect(REFLECTION_DB)
        cursor = conn.cursor()
        
        # 総アクション数
        cursor.execute("SELECT COUNT(*) FROM actions")
        total_actions = cursor.fetchone()[0]
        
        # エージェント別統計
        cursor.execute("""
            SELECT agent, COUNT(*) as count, AVG(confidence) as avg_conf
            FROM actions 
            GROUP BY agent 
            ORDER BY count DESC
        """)
        agent_stats = cursor.fetchall()
        
        # 最近のアクション
        cursor.execute("""
            SELECT timestamp, agent, action_type, confidence
            FROM actions 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        recent_actions = cursor.fetchall()
        
        # 時系列データ（学習曲線用）
        cursor.execute("""
            SELECT timestamp, confidence, agent
            FROM actions 
            ORDER BY timestamp ASC
        """)
        timeline_data = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_actions': total_actions,
            'agent_stats': agent_stats,
            'recent_actions': recent_actions,
            'timeline_data': timeline_data
        }
    except Exception as e:
        return {'error': str(e)}

def get_cognitive_stats():
    """Cognitive Bridgeの統計"""
    try:
        conn = sqlite3.connect(COGNITIVE_DB)
        cursor = conn.cursor()
        
        # テーブル存在確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        stats = {'tables': tables}
        
        # message_streamテーブルがあれば統計取得
        if 'message_stream' in tables:
            cursor.execute("SELECT COUNT(*) FROM message_stream")
            stats['total_messages'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT agent_id) FROM message_stream")
            stats['unique_agents'] = cursor.fetchone()[0]
            
            # 最近24時間
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor.execute(f"SELECT COUNT(*) FROM message_stream WHERE timestamp > '{yesterday}'")
            stats['messages_24h'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    except Exception as e:
        return {'error': str(e)}

def get_system_health():
    """システムヘルス"""
    import psutil
    
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu,
        'memory_percent': memory.percent,
        'memory_used': memory.used // (1024**3),  # GB
        'memory_total': memory.total // (1024**3),  # GB
        'disk_percent': disk.percent,
        'disk_used': disk.used // (1024**3),  # GB
        'disk_total': disk.total // (1024**3),  # GB
    }

def get_learning_summary():
    """学習サマリー"""
    reflection = get_reflection_stats()
    cognitive = get_cognitive_stats()
    health = get_system_health()
    
    # QSRスコア計算（簡易版）
    if reflection.get('agent_stats'):
        confidences = [stat[2] for stat in reflection['agent_stats'] if stat[2]]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        qsr_score = avg_confidence * 100
    else:
        qsr_score = 50.0
    
    return {
        'qsr_score': round(qsr_score, 1),
        'total_actions': reflection.get('total_actions', 0),
        'active_agents': len(reflection.get('agent_stats', [])),
        'cognitive_messages': cognitive.get('total_messages', 0),
        'system_health': health
    }

@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template('dashboard.html')

@app.route('/mobile')
def mobile():
    """モバイルダッシュボード"""
    return render_template('mobile.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """静的ファイル配信"""
    return send_from_directory('static', filename)

@app.route('/api/summary')
def api_summary():
    """サマリーAPI"""
    return jsonify(get_learning_summary())

@app.route('/api/reflection')
def api_reflection():
    """Reflection Engine統計API"""
    return jsonify(get_reflection_stats())

@app.route('/api/cognitive')
def api_cognitive():
    """Cognitive Bridge統計API"""
    return jsonify(get_cognitive_stats())

@app.route('/api/health')
def api_health():
    """システムヘルスAPI"""
    return jsonify(get_system_health())

@app.route('/api/communication')
def api_communication():
    """AI通信ネットワークAPI"""
    import sys
    sys.path.insert(0, str(WORKSPACE / 'tools'))
    from ai_communication_analyzer import AICommunicationAnalyzer
    
    analyzer = AICommunicationAnalyzer()
    data = analyzer.analyze_communication_patterns(hours=24)
    return jsonify(data)

@app.route('/network')
def network_page():
    """ネットワークグラフページ"""
    return render_template('network.html')

@app.route('/api/lightweight_monitor')
def api_lightweight_monitor():
    """Lightweight Monitor API"""
    try:
        from lightweight_monitor import get_monitor
        monitor = get_monitor()
        status = monitor.get_current_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/secretary')
def secretary():
    """Trinity統合秘書システム"""
    return render_template('secretary.html')

@app.route('/api/secretary/chat', methods=['POST'])
def secretary_chat():
    """秘書チャットAPI（プロキシ）"""
    try:
        data = request.get_json()
        response = requests.post(
            f"{SECRETARY_API_URL}/api/chat",
            json=data,
            timeout=30
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/secretary/tasks', methods=['GET'])
def secretary_tasks():
    """秘書タスク一覧API（プロキシ）"""
    try:
        response = requests.get(
            f"{SECRETARY_API_URL}/api/tasks/list",
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/secretary/tasks/create', methods=['POST'])
def secretary_create_task():
    """秘書タスク作成API（プロキシ）"""
    try:
        data = request.get_json()
        response = requests.post(
            f"{SECRETARY_API_URL}/api/tasks/create",
            json=data,
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/secretary/status', methods=['GET'])
def secretary_status():
    """秘書ステータスAPI（プロキシ）"""
    try:
        response = requests.get(
            f"{SECRETARY_API_URL}/api/status/all",
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🎨 ManaOS Learning Dashboard 起動中...")
    print("📊 アクセス: http://127.0.0.1:5100")
    
    # ポート競合チェック
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 5100))
    sock.close()
    
    if result == 0:
        print("⚠️  ポート5100は既に使用中です")
        print("既存プロセスを停止してから再起動してください")
        import sys
        sys.exit(1)
    
    app.run(host='0.0.0.0', port=5100, debug=False)

