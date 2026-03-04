#!/usr/bin/env python3
"""
REST API Server
全システムへのAPIアクセスを提供
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
from datetime import datetime
import sys

# モジュールパス追加
sys.path.insert(0, str(Path(__file__).parent))

from file_organizer.file_organizer import FileOrganizer
from file_organizer.duplicate_detector import DuplicateDetector
from maintenance.maintenance_scheduler import MaintenanceScheduler
from monitoring.monitor_engine import MonitorEngine
from report_generator import ReportGenerator
from notification_service import NotificationService

app = Flask(__name__)
CORS(app)

# エンジン初期化
engines = {
    "organizer": FileOrganizer(),
    "detector": DuplicateDetector(),
    "scheduler": MaintenanceScheduler(),
    "monitor": MonitorEngine(),
    "reporter": ReportGenerator(),
    "notifier": NotificationService()
}

# ==================== ヘルスチェック ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "file_organizer": "running",
            "duplicate_detector": "running",
            "maintenance": "running",
            "monitoring": "running",
            "reporting": "running",
            "notification": "running"
        }
    })

# ==================== ファイル整理 API ====================

@app.route('/api/file-organizer/status', methods=['GET'])
def file_organizer_status():
    """ファイル整理システムのステータス"""
    stats = engines["organizer"].get_system_stats()
    return jsonify(stats)

@app.route('/api/file-organizer/organize', methods=['POST'])
def organize_files():
    """ファイル整理実行"""
    dry_run = request.json.get('dry_run', False)
    results = engines["organizer"].organize_files(dry_run=dry_run)
    return jsonify(results)

@app.route('/api/file-organizer/duplicates', methods=['GET'])
def find_duplicates():
    """重複ファイル検出"""
    results = engines["detector"].scan_duplicates()
    return jsonify(results)

@app.route('/api/file-organizer/duplicates/delete', methods=['POST'])
def delete_duplicates():
    """重複ファイル削除"""
    keep_oldest = request.json.get('keep_oldest', True)
    dry_run = request.json.get('dry_run', True)
    results = engines["detector"].delete_duplicates(keep_oldest=keep_oldest, dry_run=dry_run)
    return jsonify(results)

# ==================== メンテナンス API ====================

@app.route('/api/maintenance/status', methods=['GET'])
def maintenance_status():
    """メンテナンスステータス"""
    status = engines["scheduler"].get_status()
    return jsonify(status)

@app.route('/api/maintenance/daily', methods=['POST'])
def run_daily_maintenance():
    """日次メンテナンス実行"""
    results = engines["scheduler"].run_daily_maintenance()
    return jsonify(results)

@app.route('/api/maintenance/weekly', methods=['POST'])
def run_weekly_maintenance():
    """週次メンテナンス実行"""
    results = engines["scheduler"].run_weekly_maintenance()
    return jsonify(results)

@app.route('/api/maintenance/logs/rotate', methods=['POST'])
def rotate_logs():
    """ログローテーション"""
    results = engines["scheduler"].rotate_logs()
    return jsonify(results)

@app.route('/api/maintenance/temp/cleanup', methods=['POST'])
def cleanup_temp_files():
    """一時ファイルクリーンアップ"""
    results = engines["scheduler"].cleanup_temp_files()
    return jsonify(results)

@app.route('/api/maintenance/database/optimize', methods=['POST'])
def optimize_databases():
    """データベース最適化"""
    results = engines["scheduler"].optimize_databases()
    return jsonify(results)

# ==================== 監視 API ====================

@app.route('/api/monitoring/status', methods=['GET'])
def monitoring_status():
    """監視システムステータス"""
    status = engines["monitor"].get_system_status()
    return jsonify(status)

@app.route('/api/monitoring/metrics', methods=['GET'])
def get_metrics():
    """メトリクス取得"""
    metrics = engines["monitor"].collect_all_metrics()
    return jsonify(metrics)

@app.route('/api/monitoring/health', methods=['GET'])
def get_health_score():
    """ヘルススコア取得"""
    health = engines["monitor"].get_health_score()
    return jsonify(health)

@app.route('/api/monitoring/alerts', methods=['GET'])
def get_alerts():
    """アラート取得"""
    limit = request.args.get('limit', 50, type=int)
    alerts = engines["monitor"].alerts[-limit:]
    return jsonify({"alerts": alerts, "count": len(alerts)})

@app.route('/api/monitoring/run', methods=['POST'])
def run_monitoring():
    """監視サイクル実行"""
    results = engines["monitor"].run_monitoring_cycle()
    return jsonify(results)

# ==================== レポート API ====================

@app.route('/api/reports/daily', methods=['POST'])
def generate_daily_report():
    """日次レポート生成"""
    report = engines["reporter"].generate_daily_report()
    return jsonify(report)

@app.route('/api/reports/weekly', methods=['POST'])
def generate_weekly_report():
    """週次レポート生成"""
    report = engines["reporter"].generate_weekly_report()
    return jsonify(report)

@app.route('/api/reports/monthly', methods=['POST'])
def generate_monthly_report():
    """月次レポート生成"""
    report = engines["reporter"].generate_monthly_report()
    return jsonify(report)

@app.route('/api/reports/list', methods=['GET'])
def list_reports():
    """レポート一覧"""
    reports_path = Path("/root/reports")
    reports = []
    
    for report_file in sorted(reports_path.glob("*.json"), reverse=True):
        reports.append({
            "name": report_file.name,
            "path": str(report_file),
            "size": report_file.stat().st_size,
            "modified": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat()
        })
    
    return jsonify({"reports": reports, "count": len(reports)})

# ==================== 通知 API ====================

@app.route('/api/notifications/send', methods=['POST'])
def send_notification():
    """通知送信"""
    data = request.json
    level = data.get('level', 'INFO')
    title = data.get('title', '')
    message = data.get('message', '')
    
    engines["notifier"].send_notification(level, title, message)
    
    return jsonify({
        "status": "success",
        "message": "通知を送信しました"
    })

@app.route('/api/notifications/history', methods=['GET'])
def get_notification_history():
    """通知履歴取得"""
    limit = request.args.get('limit', 50, type=int)
    history = engines["notifier"].get_notification_history(limit=limit)
    return jsonify({"history": history, "count": len(history)})

# ==================== システム情報 API ====================

@app.route('/api/system/info', methods=['GET'])
def system_info():
    """システム情報"""
    import platform
    import psutil
    
    return jsonify({
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor()
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation()
        },
        "resources": {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_total": psutil.disk_usage('/').total
        },
        "timestamp": datetime.now().isoformat()
    })

# ==================== 統計 API ====================

@app.route('/api/stats/summary', methods=['GET'])
def stats_summary():
    """統計サマリー"""
    # ファイル整理統計
    file_stats = engines["organizer"].get_system_stats()
    
    # 監視統計
    monitor_status = engines["monitor"].get_system_status()
    
    # ヘルススコア
    health = engines["monitor"].get_health_score()
    
    return jsonify({
        "file_organization": file_stats,
        "monitoring": {
            "alert_count_24h": monitor_status.get("alert_count_24h", 0),
            "last_check": monitor_status.get("last_check")
        },
        "health": health,
        "timestamp": datetime.now().isoformat()
    })

# ==================== エラーハンドリング ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# ==================== メイン実行 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 ManaOS REST API Server")
    print("=" * 60)
    print("\n📡 API Endpoints:")
    print("  GET  /api/health - ヘルスチェック")
    print("  GET  /api/system/info - システム情報")
    print("  GET  /api/stats/summary - 統計サマリー")
    print("\n📁 ファイル整理:")
    print("  GET  /api/file-organizer/status")
    print("  POST /api/file-organizer/organize")
    print("  GET  /api/file-organizer/duplicates")
    print("\n🔧 メンテナンス:")
    print("  GET  /api/maintenance/status")
    print("  POST /api/maintenance/daily")
    print("  POST /api/maintenance/weekly")
    print("\n📊 監視:")
    print("  GET  /api/monitoring/status")
    print("  GET  /api/monitoring/metrics")
    print("  GET  /api/monitoring/health")
    print("\n📈 レポート:")
    print("  POST /api/reports/daily")
    print("  POST /api/reports/weekly")
    print("  POST /api/reports/monthly")
    print("\n📢 通知:")
    print("  POST /api/notifications/send")
    print("  GET  /api/notifications/history")
    print("\n" + "=" * 60)
    print("🌐 サーバー起動: http://0.0.0.0:5000")
    print("📖 API ドキュメント: http://0.0.0.0:5000/api/health")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=os.getenv("DEBUG", "False").lower() == "true")

