#!/usr/bin/env python3
"""
Phase 9: ManaOS統合システム
- 既存システムとの完全統合
- 統合ダッシュボード
- 全Phase 9システムの統括管理
"""

import os
import sys
import json
import time
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
import logging
import psutil

class Phase9ManaOSIntegration:
    def __init__(self):
        self.vault_dir = Path("/root/.mana_vault")
        self.tools_dir = Path("/root/trinity_workspace/tools")
        self.manaos_dir = Path("/root/manaos_v3")
        self.config_file = self.vault_dir / "phase9_manaos_config.json"
        
        # ログ設定
        self.setup_logging()
        
        # 設定読み込み
        self.config = self.load_config()
        
        # 統合管理
        self.integration_running = False
        self.managed_services = []
        self.performance_metrics = {}
        self.optimization_history = []

    def setup_logging(self):
        """ログ設定"""
        log_file = self.vault_dir / "phase9_manaos_integration.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # コンソール出力も追加
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def load_config(self):
        """設定ファイル読み込み"""
        default_config = {
            "integration": {
                "enabled": True,
                "monitoring_interval_seconds": 60,
                "optimization_interval_seconds": 300,
                "dashboard_update_interval_seconds": 30
            },
            "manaos_services": {
                "orchestrator": "mana-orchestrator",
                "intention": "mana-intention", 
                "policy": "mana-policy",
                "actuator": "mana-actuator",
                "ingestor": "mana-ingestor",
                "insight": "mana-insight"
            },
            "phase9_services": {
                "performance_optimizer": "phase9-performance-optimizer.service",
                "ai_optimizer": "phase9-ai-optimizer.service",
                "orchestrator": "phase8-orchestrator.service"
            },
            "dashboard": {
                "enabled": True,
                "port": 8080,
                "auto_refresh": True
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # デフォルト設定とマージ
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                self.logger.error(f"設定ファイル読み込みエラー: {e}")
                return default_config
        else:
            self.save_config(default_config)
            return default_config

    def save_config(self, config=None):
        """設定ファイル保存"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("ManaOS統合設定ファイルを保存しました")
        except Exception as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")

    def check_manaos_services(self):
        """ManaOSサービス状態チェック"""
        try:
            services_status = {}
            
            for service_name, container_name in self.config['manaos_services'].items():
                try:
                    # Dockerコンテナ状態チェック
                    result = subprocess.run(
                        ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Status}}'],
                        capture_output=True, text=True, timeout=10
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        status = result.stdout.strip()
                        services_status[service_name] = {
                            'status': 'running' if 'Up' in status else 'stopped',
                            'container': container_name,
                            'details': status
                        }
                    else:
                        services_status[service_name] = {
                            'status': 'not_found',
                            'container': container_name,
                            'details': 'Container not found'
                        }
                        
                except Exception as e:
                    services_status[service_name] = {
                        'status': 'error',
                        'container': container_name,
                        'details': str(e)
                    }
            
            return services_status
            
        except Exception as e:
            self.logger.error(f"ManaOSサービス状態チェックエラー: {e}")
            return {}

    def check_phase9_services(self):
        """Phase 9サービス状態チェック"""
        try:
            services_status = {}
            
            for service_name, systemd_service in self.config['phase9_services'].items():
                try:
                    # systemdサービス状態チェック
                    result = subprocess.run(
                        ['systemctl', 'is-active', systemd_service],
                        capture_output=True, text=True, timeout=10
                    )
                    
                    services_status[service_name] = {
                        'status': result.stdout.strip(),
                        'service': systemd_service,
                        'details': f"systemctl status: {result.stdout.strip()}"
                    }
                    
                except Exception as e:
                    services_status[service_name] = {
                        'status': 'error',
                        'service': systemd_service,
                        'details': str(e)
                    }
            
            return services_status
            
        except Exception as e:
            self.logger.error(f"Phase 9サービス状態チェックエラー: {e}")
            return {}

    def get_system_performance_metrics(self):
        """システムパフォーマンスメトリクス取得"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_avg': os.getloadavg(),  # type: ignore[attr-defined]
                'process_count': len(psutil.pids()),
                'network_io': psutil.net_io_counters()._asdict(),
                'disk_io': psutil.disk_io_counters()._asdict()  # type: ignore[union-attr]
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"パフォーマンスメトリクス取得エラー: {e}")
            return {}

    def generate_integration_dashboard(self):
        """統合ダッシュボード生成"""
        try:
            # サービス状態取得
            manaos_services = self.check_manaos_services()
            phase9_services = self.check_phase9_services()
            
            # パフォーマンスメトリクス取得
            performance_metrics = self.get_system_performance_metrics()
            
            # ダッシュボードデータ構築
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'system_info': {
                    'hostname': os.uname().nodename,  # type: ignore[attr-defined]
                    'uptime': time.time() - psutil.boot_time(),
                    'kernel': os.uname().release  # type: ignore[attr-defined]
                },
                'manaos_services': manaos_services,
                'phase9_services': phase9_services,
                'performance_metrics': performance_metrics,
                'optimization_history': self.optimization_history[-10:],  # 最新10件
                'system_health_score': self.calculate_system_health_score(performance_metrics)
            }
            
            # ダッシュボードHTML生成
            dashboard_html = self.generate_dashboard_html(dashboard_data)
            
            # ダッシュボード保存
            dashboard_file = self.vault_dir / "phase9_dashboard.html"
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(dashboard_html)
            
            self.logger.info(f"統合ダッシュボード生成: {dashboard_file}")
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"統合ダッシュボード生成エラー: {e}")
            return None

    def calculate_system_health_score(self, metrics):
        """システムヘルススコア計算"""
        try:
            score = 100.0
            
            # CPU使用率スコア
            cpu_percent = metrics.get('cpu_percent', 0)
            if cpu_percent > 90:
                score -= 30
            elif cpu_percent > 80:
                score -= 20
            elif cpu_percent > 70:
                score -= 10
            
            # メモリ使用率スコア
            memory_percent = metrics.get('memory_percent', 0)
            if memory_percent > 90:
                score -= 25
            elif memory_percent > 80:
                score -= 15
            elif memory_percent > 70:
                score -= 5
            
            # ディスク使用率スコア
            disk_percent = metrics.get('disk_percent', 0)
            if disk_percent > 90:
                score -= 20
            elif disk_percent > 80:
                score -= 10
            elif disk_percent > 70:
                score -= 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"ヘルススコア計算エラー: {e}")
            return 0

    def generate_dashboard_html(self, dashboard_data):
        """ダッシュボードHTML生成"""
        try:
            # シンプルなHTMLテンプレート
            html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Phase 9 - ManaOS統合ダッシュボード</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #667eea; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .health-score {{ font-size: 2em; font-weight: bold; text-align: center; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Phase 9 - ManaOS統合ダッシュボード</h1>
        <p>AI最適化システム統合管理</p>
    </div>
    <div class="grid">
        <div class="card">
            <h3>📊 システムヘルススコア</h3>
            <div class="health-score">{dashboard_data.get('system_health_score', 0)}/100</div>
        </div>
        <div class="card">
            <h3>⚡ パフォーマンスメトリクス</h3>
            <div class="metric">
                <span>CPU使用率:</span>
                <span>{dashboard_data.get('performance_metrics', {}).get('cpu_percent', 0)}%</span>
            </div>
            <div class="metric">
                <span>メモリ使用率:</span>
                <span>{dashboard_data.get('performance_metrics', {}).get('memory_percent', 0)}%</span>
            </div>
            <div class="metric">
                <span>ディスク使用率:</span>
                <span>{dashboard_data.get('performance_metrics', {}).get('disk_percent', 0)}%</span>
            </div>
            <div class="metric">
                <span>プロセス数:</span>
                <span>{dashboard_data.get('performance_metrics', {}).get('process_count', 0)}</span>
            </div>
        </div>
        <div class="card">
            <h3>🔧 ManaOSサービス</h3>
            {self.generate_services_html(dashboard_data.get('manaos_services', {}))}
        </div>
        <div class="card">
            <h3>🤖 Phase 9サービス</h3>
            {self.generate_services_html(dashboard_data.get('phase9_services', {}))}
        </div>
    </div>
</body>
</html>"""
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"ダッシュボードHTML生成エラー: {e}")
            return "<html><body><h1>エラー: ダッシュボード生成に失敗しました</h1></body></html>"

    def generate_services_html(self, services_data):
        """サービスHTML生成"""
        try:
            html = ""
            for service_name, service_data in services_data.items():
                status = service_data.get('status', 'unknown')
                html += f'<div class="metric"><span>{service_name}:</span><span>{status}</span></div>'
            return html
        except Exception as e:
            self.logger.error(f"サービスHTML生成エラー: {e}")
            return "<div>エラー: サービス情報取得失敗</div>"

    def run_integration_cycle(self):
        """統合サイクル実行"""
        try:
            self.logger.info("=== Phase 9: ManaOS統合サイクル開始 ===")
            
            # ダッシュボード生成
            dashboard_data = self.generate_integration_dashboard()
            
            if dashboard_data:
                # 最適化履歴に追加
                self.optimization_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'health_score': dashboard_data.get('system_health_score', 0),
                    'services_status': {
                        'manaos': len([s for s in dashboard_data.get('manaos_services', {}).values() if s.get('status') == 'running']),
                        'phase9': len([s for s in dashboard_data.get('phase9_services', {}).values() if s.get('status') == 'active'])
                    }
                })
                
                # 履歴保持（最新100件）
                if len(self.optimization_history) > 100:
                    self.optimization_history = self.optimization_history[-100:]
                
                self.logger.info("ManaOS統合サイクル完了")
                return True
            else:
                self.logger.error("ダッシュボード生成失敗")
                return False
                
        except Exception as e:
            self.logger.error(f"統合サイクルエラー: {e}")
            return False

    def run_continuous_integration(self):
        """継続統合実行"""
        self.logger.info("Phase 9: ManaOS継続統合を開始")
        self.integration_running = True
        
        try:
            while self.integration_running:
                self.run_integration_cycle()
                
                # 設定された間隔で待機
                interval = self.config['integration']['monitoring_interval_seconds']
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("統合を停止します")
            self.integration_running = False
        except Exception as e:
            self.logger.error(f"継続統合エラー: {e}")
        finally:
            self.integration_running = False

if __name__ == "__main__":
    integration = Phase9ManaOSIntegration()
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        integration.run_continuous_integration()
    else:
        integration.run_integration_cycle()
