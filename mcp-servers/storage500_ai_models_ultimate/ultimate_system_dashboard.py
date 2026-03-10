#!/usr/bin/env python3
"""
🚀 システム統合管理ダッシュボード
システム全体の監視、最適化、統合、管理を行う包括的なダッシュボード
"""

import os
import sys
import json
import time
import psutil
import subprocess
import threading
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import requests
from flask import Flask, render_template_string, jsonify, request
import logging

class UltimateSystemDashboard:
    def __init__(self):
        self.app = Flask(__name__)
        self.config_file = "dashboard_config.yaml"
        self.db_file = "dashboard.db"
        self.setup_logging()
        self.load_config()
        self.init_database()
        self.setup_routes()
        
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('dashboard.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """設定ファイル読み込み"""
        default_config = {
            'dashboard': {
                'port': 8080,
                'host': '0.0.0.0',
                'debug': False,
                'auto_refresh': 30
            },
            'monitoring': {
                'cpu_threshold': 80,
                'memory_threshold': 80,
                'disk_threshold': 85,
                'check_interval': 60
            },
            'services': {
                'obsidian_notion_mirror': True,
                'gemini_api': True,
                'voice_control': True,
                'ai_assistant': True,
                'ultimate_dashboard': True
            }
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = default_config
            self.save_config()
            
    def save_config(self):
        """設定ファイル保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                process_count INTEGER,
                network_io REAL,
                disk_io REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT,
                status TEXT,
                last_check TEXT,
                response_time REAL,
                error_count INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action TEXT,
                details TEXT,
                success BOOLEAN,
                duration REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def get_system_metrics(self):
        """システムメトリクス取得"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process_count = len(psutil.pids())
            
            # ネットワークI/O
            net_io = psutil.net_io_counters()
            network_io = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024  # MB
            
            # ディスクI/O
            disk_io = psutil.disk_io_counters()
            disk_io_mb = (disk_io.read_bytes + disk_io.write_bytes) / 1024 / 1024  # MB  # type: ignore[union-attr]
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'disk_usage': disk.percent,
                'process_count': process_count,
                'network_io': network_io,
                'disk_io': disk_io_mb,
                'memory_available': memory.available / 1024 / 1024,  # MB
                'disk_free': disk.free / 1024 / 1024 / 1024  # GB
            }
            
            # データベースに記録
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_metrics 
                (timestamp, cpu_usage, memory_usage, disk_usage, process_count, network_io, disk_io)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics['timestamp'], metrics['cpu_usage'], metrics['memory_usage'],
                metrics['disk_usage'], metrics['process_count'], metrics['network_io'], metrics['disk_io']
            ))
            conn.commit()
            conn.close()
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"システムメトリクス取得エラー: {e}")
            return None
            
    def check_service_status(self):
        """サービス状況チェック"""
        try:
            services = {
                'obsidian_notion_mirror': 'obsidian_notion_mirror_lightweight.py',
                'gemini_api': 'gemini_api_fix.py',
                'ultimate_dashboard': 'ultimate_integration_dashboard_fixed.py',
                'voice_control': 'voice_control_integration.py',
                'ai_assistant': 'ai_assistant_integration.py'
            }
            
            service_status = {}
            
            for service_name, script_name in services.items():
                start_time = time.time()
                
                # プロセス確認
                running = False
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if script_name in ' '.join(proc.info['cmdline'] or []):
                            running = True
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
                response_time = time.time() - start_time
                
                status = 'running' if running else 'stopped'
                service_status[service_name] = {
                    'status': status,
                    'response_time': response_time,
                    'last_check': datetime.now().isoformat()
                }
                
            # データベースに記録
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            for service_name, status_info in service_status.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO service_status 
                    (service_name, status, last_check, response_time)
                    VALUES (?, ?, ?, ?)
                ''', (service_name, status_info['status'], status_info['last_check'], status_info['response_time']))
                
            conn.commit()
            conn.close()
            
            return service_status
            
        except Exception as e:
            self.logger.error(f"サービス状況チェックエラー: {e}")
            return {}
            
    def get_optimization_history(self):
        """最適化履歴取得"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, action, details, success, duration 
                FROM optimization_history 
                ORDER BY timestamp DESC 
                LIMIT 20
            ''')
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'timestamp': row[0],
                    'action': row[1],
                    'details': row[2],
                    'success': bool(row[3]),
                    'duration': row[4]
                })
                
            conn.close()
            return history
            
        except Exception as e:
            self.logger.error(f"最適化履歴取得エラー: {e}")
            return []
            
    def get_system_trends(self):
        """システムトレンド取得"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 過去24時間のデータ
            yesterday = datetime.now() - timedelta(hours=24)
            
            cursor.execute('''
                SELECT timestamp, cpu_usage, memory_usage, disk_usage 
                FROM system_metrics 
                WHERE timestamp > ? 
                ORDER BY timestamp
            ''', (yesterday.isoformat(),))
            
            trends = []
            for row in cursor.fetchall():
                trends.append({
                    'timestamp': row[0],
                    'cpu_usage': row[1],
                    'memory_usage': row[2],
                    'disk_usage': row[3]
                })
                
            conn.close()
            return trends
            
        except Exception as e:
            self.logger.error(f"システムトレンド取得エラー: {e}")
            return []
            
    def setup_routes(self):
        """ルート設定"""
        
        @self.app.route('/')
        def dashboard():
            """メインダッシュボード"""
            metrics = self.get_system_metrics()
            service_status = self.check_service_status()
            optimization_history = self.get_optimization_history()
            system_trends = self.get_system_trends()
            
            return render_template_string(self.get_dashboard_template(), 
                                       metrics=metrics,
                                       service_status=service_status,
                                       optimization_history=optimization_history,
                                       system_trends=system_trends)
            
        @self.app.route('/api/metrics')
        def api_metrics():
            """API: システムメトリクス"""
            return jsonify(self.get_system_metrics())
            
        @self.app.route('/api/services')
        def api_services():
            """API: サービス状況"""
            return jsonify(self.check_service_status())
            
        @self.app.route('/api/optimize', methods=['POST'])
        def api_optimize():
            """API: 最適化実行"""
            try:
                action = request.json.get('action', 'full')
                
                if action == 'memory':
                    self.optimize_memory()
                elif action == 'cleanup':
                    self.cleanup_files()
                elif action == 'full':
                    self.run_full_optimization()
                    
                return jsonify({'success': True, 'message': f'{action}最適化完了'})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
                
        @self.app.route('/api/restart_service', methods=['POST'])
        def api_restart_service():
            """API: サービス再起動"""
            try:
                service_name = request.json.get('service_name')
                
                if self.restart_service(service_name):
                    return jsonify({'success': True, 'message': f'{service_name}再起動完了'})
                else:
                    return jsonify({'success': False, 'error': f'{service_name}再起動失敗'})
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
                
    def optimize_memory(self):
        """メモリ最適化"""
        try:
            self.logger.info("メモリ最適化を実行中...")
            
            # キャッシュクリア
            subprocess.run(['sync'], check=True)
            subprocess.run(['echo 3 > /proc/sys/vm/drop_caches'], shell=True, check=True)
            
            # 大きなログファイル圧縮
            for log_file in Path('.').glob('*.log'):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB以上
                    subprocess.run(['gzip', '-f', str(log_file)], check=True)
                    
            self.logger.info("メモリ最適化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"メモリ最適化エラー: {e}")
            return False
            
    def cleanup_files(self):
        """ファイルクリーンアップ"""
        try:
            self.logger.info("ファイルクリーンアップを実行中...")
            
            # 古いログファイル削除
            for pattern in ['*.log', '*.tmp', '*.cache']:
                for file_path in Path('.').glob(pattern):
                    if file_path.stat().st_mtime < time.time() - 7 * 24 * 3600:  # 7日前
                        file_path.unlink()
                        
            self.logger.info("ファイルクリーンアップ完了")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルクリーンアップエラー: {e}")
            return False
            
    def restart_service(self, service_name):
        """サービス再起動"""
        try:
            service_scripts = {
                'obsidian_notion_mirror': 'obsidian_notion_mirror_lightweight.py',
                'gemini_api': 'gemini_api_fix.py',
                'ultimate_dashboard': 'ultimate_integration_dashboard_fixed.py',
                'voice_control': 'voice_control_integration.py',
                'ai_assistant': 'ai_assistant_integration.py'
            }
            
            script_name = service_scripts.get(service_name)
            if script_name and os.path.exists(script_name):
                # 既存プロセス終了
                subprocess.run(['pkill', '-f', script_name], check=False)
                time.sleep(2)
                
                # サービス再起動
                subprocess.Popen(['python3', script_name], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                
                self.logger.info(f"サービス再起動: {service_name}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"サービス再起動エラー {service_name}: {e}")
            return False
            
    def run_full_optimization(self):
        """完全最適化実行"""
        try:
            self.logger.info("完全最適化を実行中...")
            
            # メモリ最適化
            self.optimize_memory()
            
            # ファイルクリーンアップ
            self.cleanup_files()
            
            # データベース最適化
            for db_file in Path('.').glob('*.db'):
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute('VACUUM')
                cursor.execute('REINDEX')
                conn.commit()
                conn.close()
                
            self.logger.info("完全最適化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"完全最適化エラー: {e}")
            return False
            
    def get_dashboard_template(self):
        """ダッシュボードテンプレート"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 システム統合管理ダッシュボード</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .metric { text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .metric-label { color: #666; font-size: 0.9em; }
        .status-good { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-danger { color: #dc3545; }
        .service-list { list-style: none; }
        .service-item { padding: 10px; margin: 5px 0; border-radius: 5px; background: #f8f9fa; }
        .service-running { border-left: 4px solid #28a745; }
        .service-stopped { border-left: 4px solid #dc3545; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: black; }
        .btn-danger { background: #dc3545; color: white; }
        .history-item { padding: 10px; margin: 5px 0; border-radius: 5px; background: #f8f9fa; }
        .chart-container { height: 300px; margin: 20px 0; }
        .refresh-btn { position: fixed; top: 20px; right: 20px; z-index: 1000; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 システム統合管理ダッシュボード</h1>
            <p>リアルタイムシステム監視・最適化・統合管理</p>
        </div>
        
        <button class="btn btn-primary refresh-btn" onclick="location.reload()">🔄 更新</button>
        
        <!-- システムメトリクス -->
        <div class="grid">
            <div class="card metric">
                <div class="metric-label">CPU使用率</div>
                <div class="metric-value status-{{ 'danger' if metrics.cpu_usage > 80 else 'warning' if metrics.cpu_usage > 60 else 'good' }}">
                    {{ "%.1f"|format(metrics.cpu_usage) }}%
                </div>
            </div>
            <div class="card metric">
                <div class="metric-label">メモリ使用率</div>
                <div class="metric-value status-{{ 'danger' if metrics.memory_usage > 80 else 'warning' if metrics.memory_usage > 60 else 'good' }}">
                    {{ "%.1f"|format(metrics.memory_usage) }}%
                </div>
            </div>
            <div class="card metric">
                <div class="metric-label">ディスク使用率</div>
                <div class="metric-value status-{{ 'danger' if metrics.disk_usage > 85 else 'warning' if metrics.disk_usage > 70 else 'good' }}">
                    {{ "%.1f"|format(metrics.disk_usage) }}%
                </div>
            </div>
            <div class="card metric">
                <div class="metric-label">プロセス数</div>
                <div class="metric-value">{{ metrics.process_count }}</div>
            </div>
        </div>
        
        <!-- サービス状況 -->
        <div class="grid">
            <div class="card">
                <h3>🔧 サービス状況</h3>
                <ul class="service-list">
                    {% for service_name, status in service_status.items() %}
                    <li class="service-item service-{{ status.status }}">
                        <strong>{{ service_name }}</strong>: {{ status.status }}
                        <button class="btn btn-sm btn-{{ 'danger' if status.status == 'running' else 'success' }}" 
                                onclick="restartService('{{ service_name }}')">
                            {{ '停止' if status.status == 'running' else '開始' }}
                        </button>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="card">
                <h3>⚡ 最適化アクション</h3>
                <button class="btn btn-primary" onclick="runOptimization('memory')">メモリ最適化</button>
                <button class="btn btn-warning" onclick="runOptimization('cleanup')">ファイルクリーンアップ</button>
                <button class="btn btn-success" onclick="runOptimization('full')">完全最適化</button>
            </div>
        </div>
        
        <!-- 最適化履歴 -->
        <div class="card">
            <h3>📊 最適化履歴</h3>
            {% for item in optimization_history[:10] %}
            <div class="history-item">
                <strong>{{ item.action }}</strong> - {{ item.timestamp[:19] }}
                <span class="status-{{ 'good' if item.success else 'danger' }}">
                    {{ '成功' if item.success else '失敗' }}
                </span>
            </div>
            {% endfor %}
        </div>
        
        <!-- システムトレンドチャート -->
        <div class="card">
            <h3>📈 システムトレンド</h3>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // システムトレンドチャート
        const ctx = document.getElementById('trendChart').getContext('2d');
        const trendData = {{ system_trends|tojson }};
        
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendData.map(d => d.timestamp.slice(11, 16)),
                datasets: [{
                    label: 'CPU使用率 (%)',
                    data: trendData.map(d => d.cpu_usage),
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    tension: 0.4
                }, {
                    label: 'メモリ使用率 (%)',
                    data: trendData.map(d => d.memory_usage),
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
        
        // 最適化実行
        function runOptimization(action) {
            fetch('/api/optimize', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: action})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('最適化完了: ' + data.message);
                    location.reload();
                } else {
                    alert('エラー: ' + data.error);
                }
            });
        }
        
        // サービス再起動
        function restartService(serviceName) {
            fetch('/api/restart_service', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({service_name: serviceName})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('サービス再起動完了: ' + data.message);
                    location.reload();
                } else {
                    alert('エラー: ' + data.error);
                }
            });
        }
        
        // 自動更新
        setInterval(() => {
            location.reload();
        }, 30000); // 30秒間隔
    </script>
</body>
</html>
        """
        
    def start_monitoring(self):
        """監視開始"""
        def monitor_loop():
            while True:
                try:
                    # システムメトリクス記録
                    self.get_system_metrics()
                    
                    # サービス状況チェック
                    self.check_service_status()
                    
                    time.sleep(self.config['monitoring']['check_interval'])
                    
                except Exception as e:
                    self.logger.error(f"監視ループエラー: {e}")
                    time.sleep(60)
                    
        # 監視スレッド開始
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
    def run(self):
        """ダッシュボード実行"""
        self.logger.info("🚀 システム統合管理ダッシュボードを開始...")
        
        # 監視開始
        self.start_monitoring()
        
        # Flaskアプリケーション実行
        self.app.run(
            host=self.config['dashboard']['host'],
            port=self.config['dashboard']['port'],
            debug=self.config['dashboard']['debug']
        )

def main():
    """メイン実行"""
    dashboard = UltimateSystemDashboard()
    dashboard.run()

if __name__ == "__main__":
    main() 