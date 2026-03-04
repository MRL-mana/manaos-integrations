#!/usr/bin/env python3
"""
Mana Metrics Exporter
カスタムメトリクスをPrometheus形式で公開
"""

import os
from flask import Flask, Response
import psutil
import subprocess
from datetime import datetime

app = Flask(__name__)

def get_service_status():
    """サービス状態を0/1で返す"""
    services = [
        "unified-portal", "security-monitor", "ai-model-hub",
        "ai-predictive", "task-executor", "cost-optimizer",
        "notification-service", "grafana-server", "prometheus"
    ]
    
    status_metrics = []
    for service in services:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True
        )
        value = 1 if result.stdout.strip() == "active" else 0
        status_metrics.append(f'mana_service_status{{service="{service}"}} {value}')
    
    return status_metrics

@app.route('/metrics')
def metrics():
    """Prometheusメトリクスエンドポイント"""
    
    # システムメトリクス
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # ネットワークメトリクス
    net_io = psutil.net_io_counters()
    
    # プロセス数
    process_count = len(psutil.pids())
    
    # サービス状態
    service_metrics = get_service_status()
    
    # Prometheus形式でメトリクスを生成
    metrics_output = f"""# HELP mana_cpu_usage_percent CPU使用率
# TYPE mana_cpu_usage_percent gauge
mana_cpu_usage_percent {cpu_percent}

# HELP mana_memory_usage_percent メモリ使用率
# TYPE mana_memory_usage_percent gauge
mana_memory_usage_percent {memory.percent}

# HELP mana_memory_used_bytes メモリ使用量
# TYPE mana_memory_used_bytes gauge
mana_memory_used_bytes {memory.used}

# HELP mana_disk_usage_percent ディスク使用率
# TYPE mana_disk_usage_percent gauge
mana_disk_usage_percent {disk.percent}

# HELP mana_disk_free_bytes ディスク空き容量
# TYPE mana_disk_free_bytes gauge
mana_disk_free_bytes {disk.free}

# HELP mana_network_bytes_sent 送信バイト数
# TYPE mana_network_bytes_sent counter
mana_network_bytes_sent {net_io.bytes_sent}

# HELP mana_network_bytes_recv 受信バイト数
# TYPE mana_network_bytes_recv counter
mana_network_bytes_recv {net_io.bytes_recv}

# HELP mana_process_count プロセス数
# TYPE mana_process_count gauge
mana_process_count {process_count}

# HELP mana_service_status サービス状態 (1=active, 0=inactive)
# TYPE mana_service_status gauge
{chr(10).join(service_metrics)}

# HELP mana_uptime_seconds システム稼働時間
# TYPE mana_uptime_seconds counter
mana_uptime_seconds {int((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds())}
"""
    
    return Response(metrics_output, mimetype='text/plain')

@app.route('/health')
def health():
    """ヘルスチェック"""
    return {'status': 'healthy', 'service': 'mana-metrics-exporter'}

if __name__ == '__main__':
    print("📊 Mana Metrics Exporter starting on http://localhost:9200")
    app.run(host='0.0.0.0', port=9200, debug=os.getenv("DEBUG", "False").lower() == "true")

