#!/usr/bin/env python3
"""
🚀 ManaOS ULTIMATE System - Phase 2完全版
WebSocket + Redis + Prometheus統合システム

機能:
- WebSocketリアルタイム通信
- Redisキャッシング
- Prometheus メトリクス収集
- 全システム統合
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
import psutil

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
import redis

# =============================================================================
# アプリケーション初期化
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'manaos-ultimate-secret-2025'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Redis接続（ローカル）
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✅ Redis接続成功")
except Exception as e:
    REDIS_AVAILABLE = False
    redis_client = None
    print(f"⚠️  Redis接続失敗（キャッシュ無効）: {e}")

# =============================================================================
# Prometheusメトリクス
# =============================================================================

# カウンター
requests_total = Counter('manaos_requests_total', 'Total requests', ['endpoint'])
websocket_connections = Gauge('manaos_websocket_connections', 'Active WebSocket connections')
cache_hits = Counter('manaos_cache_hits_total', 'Cache hits')
cache_misses = Counter('manaos_cache_misses_total', 'Cache misses')

# ゲージ
cpu_usage = Gauge('manaos_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('manaos_memory_usage_percent', 'Memory usage percentage')
active_services = Gauge('manaos_active_services', 'Number of active services')

# ヒストグラム
request_latency = Histogram('manaos_request_latency_seconds', 'Request latency', ['endpoint'])

# =============================================================================
# Redisキャッシング
# =============================================================================

def cache_get(key: str) -> Optional[str]:
    """キャッシュ取得"""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        value = redis_client.get(key)
        if value:
            cache_hits.inc()
            return value
        cache_misses.inc()
        return None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None

def cache_set(key: str, value: str, ttl: int = 60):
    """キャッシュ設定"""
    if not REDIS_AVAILABLE:
        return False
    
    try:
        redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        print(f"Cache set error: {e}")
        return False

def cache_delete(key: str):
    """キャッシュ削除"""
    if not REDIS_AVAILABLE:
        return False
    
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Cache delete error: {e}")
        return False

# =============================================================================
# システムメトリクス収集
# =============================================================================

def collect_system_metrics() -> Dict[str, Any]:
    """システムメトリクス収集"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Prometheusメトリクス更新
    cpu_usage.set(cpu_percent)
    memory_usage.set(memory.percent)
    
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_gb": round(memory.available / (1024**3), 2),
        "timestamp": datetime.now().isoformat(),
    }

# =============================================================================
# WebSocketリアルタイム通信
# =============================================================================

connected_clients = 0

@socketio.on('connect')
def handle_connect():
    """WebSocket接続"""
    global connected_clients
    connected_clients += 1
    websocket_connections.set(connected_clients)
    print(f'✅ Client connected. Total: {connected_clients}')
    emit('connection_response', {'status': 'connected', 'client_id': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket切断"""
    global connected_clients
    connected_clients -= 1
    websocket_connections.set(connected_clients)
    print(f'❌ Client disconnected. Total: {connected_clients}')

@socketio.on('request_metrics')
def handle_request_metrics():
    """メトリクスリクエスト（クライアントから）"""
    metrics = collect_system_metrics()
    emit('metrics_update', metrics)

# バックグラウンドでメトリクスをブロードキャスト
def broadcast_metrics():
    """メトリクスを全クライアントに配信"""
    while True:
        if connected_clients > 0:
            metrics = collect_system_metrics()
            socketio.emit('metrics_update', metrics)
        socketio.sleep(2)  # 2秒ごと

# =============================================================================
# REST API
# =============================================================================

@app.route('/')
def index():
    """システム情報"""
    requests_total.labels(endpoint='/').inc()
    
    return jsonify({
        "system": "ManaOS ULTIMATE System",
        "version": "2.0.0",
        "features": [
            "WebSocketリアルタイム通信",
            "Redisキャッシング",
            "Prometheusメトリクス",
            "完全統合API",
        ],
        "redis_available": REDIS_AVAILABLE,
        "websocket_connections": connected_clients,
        "timestamp": datetime.now().isoformat(),
    })

@app.route('/metrics')
def metrics():
    """Prometheusメトリクス"""
    return generate_latest(REGISTRY)

@app.route('/api/system/status')
def system_status():
    """システムステータス（キャッシュ付き）"""
    requests_total.labels(endpoint='/api/system/status').inc()
    
    # キャッシュチェック
    cache_key = "system:status"
    cached = cache_get(cache_key)
    
    if cached:
        return jsonify(json.loads(cached))
    
    # キャッシュミス - データ取得
    metrics = collect_system_metrics()
    
    status = {
        "metrics": metrics,
        "redis_available": REDIS_AVAILABLE,
        "websocket_connections": connected_clients,
        "cache_used": False,
    }
    
    # キャッシュに保存（5秒TTL）
    cache_set(cache_key, json.dumps(status), ttl=5)
    
    return jsonify(status)

@app.route('/api/cache/stats')
def cache_stats():
    """キャッシュ統計"""
    requests_total.labels(endpoint='/api/cache/stats').inc()
    
    if not REDIS_AVAILABLE:
        return jsonify({"error": "Redis not available"}), 503
    
    try:
        info = redis_client.info('stats')
        return jsonify({
            "redis_available": True,
            "total_connections": info.get('total_connections_received', 0),
            "total_commands": info.get('total_commands_processed', 0),
            "hits": int(cache_hits._value.get()),
            "misses": int(cache_misses._value.get()),
            "hit_rate": round(int(cache_hits._value.get()) / max(int(cache_hits._value.get()) + int(cache_misses._value.get()), 1) * 100, 2),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
def cache_clear():
    """キャッシュクリア"""
    if not REDIS_AVAILABLE:
        return jsonify({"error": "Redis not available"}), 503
    
    try:
        redis_client.flushdb()
        return jsonify({"success": True, "message": "Cache cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "redis": REDIS_AVAILABLE,
        "websocket": True,
        "prometheus": True,
    })

# =============================================================================
# WebSocketダッシュボード
# =============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🚀 ManaOS ULTIMATE Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2.5em; }
        .status { text-align: center; margin-bottom: 20px; }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
        }
        .metric { display: flex; justify-content: space-between; padding: 10px 0; }
        .value { font-weight: bold; font-size: 1.3em; }
        .badge { display: inline-block; padding: 5px 15px; border-radius: 20px; }
        .badge-success { background: #10b981; }
        .badge-danger { background: #ef4444; }
        #realtime-data { font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 ManaOS ULTIMATE Dashboard</h1>
        
        <div class="status">
            <span id="connection-status" class="badge badge-danger">❌ 切断</span>
            <span id="updates-count">Updates: 0</span>
        </div>
        
        <div class="card">
            <h2>⚡ リアルタイムメトリクス</h2>
            <div class="metric">
                <span>CPU使用率</span>
                <span class="value" id="cpu">--%</span>
            </div>
            <div class="metric">
                <span>メモリ使用率</span>
                <span class="value" id="memory">--%</span>
            </div>
            <div class="metric">
                <span>利用可能メモリ</span>
                <span class="value" id="memory-available">-- GB</span>
            </div>
            <div class="metric">
                <span>最終更新</span>
                <span class="value" id="last-update">--</span>
            </div>
        </div>
        
        <div class="card">
            <h2>📊 接続情報</h2>
            <div id="realtime-data">WebSocket接続中...</div>
        </div>
    </div>
    
    <script>
        const socket = io('http://localhost:5026');
        let updateCount = 0;
        
        socket.on('connect', () => {
            console.log('✅ WebSocket接続成功');
            document.getElementById('connection-status').textContent = '✅ 接続中';
            document.getElementById('connection-status').className = 'badge badge-success';
        });
        
        socket.on('disconnect', () => {
            console.log('❌ WebSocket切断');
            document.getElementById('connection-status').textContent = '❌ 切断';
            document.getElementById('connection-status').className = 'badge badge-danger';
        });
        
        socket.on('metrics_update', (data) => {
            updateCount++;
            document.getElementById('updates-count').textContent = `Updates: ${updateCount}`;
            document.getElementById('cpu').textContent = data.cpu_percent.toFixed(1) + '%';
            document.getElementById('memory').textContent = data.memory_percent.toFixed(1) + '%';
            document.getElementById('memory-available').textContent = data.memory_available_gb + ' GB';
            document.getElementById('last-update').textContent = new Date(data.timestamp).toLocaleTimeString();
            
            document.getElementById('realtime-data').textContent = JSON.stringify(data, null, 2);
        });
        
        socket.on('connection_response', (data) => {
            console.log('接続レスポンス:', data);
        });
    </script>
</body>
</html>
"""

@app.route('/dashboard')
def dashboard():
    """WebSocketダッシュボード"""
    return render_template_string(DASHBOARD_HTML)

# =============================================================================
# メイン
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 ManaOS ULTIMATE System 起動中...")
    print("=" * 80)
    print("✅ WebSocket: 有効")
    print(f"{'✅' if REDIS_AVAILABLE else '⚠️ '} Redis: {'有効' if REDIS_AVAILABLE else '無効（キャッシュなし）'}")
    print("✅ Prometheus: 有効")
    print("=" * 80)
    print("\n📍 エンドポイント:")
    print("  - http://localhost:5026/              - API情報")
    print("  - http://localhost:5026/dashboard     - WebSocketダッシュボード")
    print("  - http://localhost:5026/metrics       - Prometheusメトリクス")
    print("  - http://localhost:5026/api/system/status - システムステータス")
    print("  - http://localhost:5026/api/cache/stats   - キャッシュ統計")
    print("=" * 80)
    print()
    
    # バックグラウンドタスク起動
    socketio.start_background_task(broadcast_metrics)
    
    # サーバー起動
    socketio.run(
        app,
        host='0.0.0.0',
        port=5026,
        debug=False,
        allow_unsafe_werkzeug=True,
    )

