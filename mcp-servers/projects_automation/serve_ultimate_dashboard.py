#!/usr/bin/env python3
"""
Ultimate Dashboard Web Server
統合ダッシュボードをWebサービスとして提供
"""

import os
from flask import Flask, jsonify
import psutil
import subprocess
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def dashboard():
    """ダッシュボード表示"""
    with open('/root/mana_ultimate_dashboard.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/stats')
def get_stats():
    """リアルタイム統計API"""
    return jsonify({
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "process_count": len(psutil.pids()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/optimize/<task>')
def run_optimization(task):
    """最適化タスク実行API"""
    scripts = {
        "backup": "/root/smart_backup.sh",
        "logs": "/root/log_management_system.sh",
        "documents": "/root/document_consolidation.sh",
        "full": "/root/mana_ultimate_optimizer.py"
    }
    
    if task not in scripts:
        return jsonify({"error": "Invalid task"}), 400
    
    try:
        result = subprocess.run(
            [scripts[task]],
            capture_output=True,
            text=True,
            timeout=300
        )
        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout[:500]  # 最初の500文字のみ
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Ultimate Dashboard"})

if __name__ == '__main__':
    print("🚀 Mana Ultimate Dashboard Server 起動中...")
    print("📊 アクセス: http://localhost:8888")
    print("📊 外部: http://163.44.120.49:8888")
    print("📊 Tailscale: http://100.93.120.33:8888")
    app.run(host='0.0.0.0', port=8888, debug=os.getenv("DEBUG", "False").lower() == "true")

