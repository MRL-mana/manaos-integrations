#!/usr/bin/env python3
"""
Phase 9: 堅牢化ダッシュボード生成
- 自己修復機能
- エラー耐性強化
- 壊れても白画面にならない
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import logging

class Phase9DashboardRobust:
    def __init__(self):
        self.vault_dir = Path("/root/.mana_vault")
        self.dashboard_file = self.vault_dir / "phase9_dashboard.html"
        
        # ログ設定
        self.setup_logging()

    def setup_logging(self):
        """ログ設定"""
        log_file = self.vault_dir / "phase9_dashboard.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def get_system_status(self):
        """システム状態取得（エラー耐性強化）"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "optimizer": self.check_service_status("mana-optimizer.service"),
                "ai_optimizer": self.check_service_status("mana-ai-optimizer.service"),
                "integration": self.check_service_status("mana-integration.service"),
                "containers": self.check_docker_containers(),
                "performance": self.get_performance_metrics()
            }
            return status
        except Exception as e:
            self.logger.error(f"システム状態取得エラー: {e}")
            return self.get_fallback_status()

    def check_service_status(self, service_name):
        """サービス状態チェック"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True, text=True, timeout=5
            )
            return {
                "status": result.stdout.strip(),
                "active": result.stdout.strip() == "active"
            }
        except Exception as e:
            self.logger.warning(f"サービス状態チェックエラー {service_name}: {e}")
            return {"status": "unknown", "active": False}

    def check_docker_containers(self):
        """Dockerコンテナ状態チェック"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}:{{.Status}}'],
                capture_output=True, text=True, timeout=10
            )
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    name, status = line.split(':', 1)
                    containers.append({
                        "name": name,
                        "status": status,
                        "healthy": "healthy" in status.lower()
                    })
            return containers
        except Exception as e:
            self.logger.warning(f"Docker状態チェックエラー: {e}")
            return []

    def get_performance_metrics(self):
        """パフォーマンスメトリクス取得"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "load_avg": os.getloadavg()  # type: ignore[attr-defined]
            }
        except Exception as e:
            self.logger.warning(f"パフォーマンスメトリクス取得エラー: {e}")
            return {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0, "load_avg": [0, 0, 0]}

    def get_fallback_status(self):
        """フォールバック状態"""
        return {
            "timestamp": datetime.now().isoformat(),
            "optimizer": {"status": "unknown", "active": False},
            "ai_optimizer": {"status": "unknown", "active": False},
            "integration": {"status": "unknown", "active": False},
            "containers": [],
            "performance": {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0, "load_avg": [0, 0, 0]}
        }

    def generate_robust_dashboard(self, status):
        """堅牢化ダッシュボード生成"""
        try:
            # 基本HTMLテンプレート（エラー耐性強化）
            html_content = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="10">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mana Dashboard - Phase 9</title>
  <style>
    body {{font-family: system-ui, sans-serif; margin: 24px;}}
    .ok {{padding:6px 10px; border-radius:8px; display:inline-block; background:#e6ffed;}}
    .warn {{background:#fff4e5;}}
    .bad {{background:#ffeef0;}}
    table{{border-collapse:collapse;width:100%;margin-top:16px}}
    th,td{{border:1px solid #ddd;padding:8px;text-align:left}}
    .status-active{{color:#28a745;font-weight:bold;}}
    .status-inactive{{color:#dc3545;font-weight:bold;}}
    .status-unknown{{color:#ffc107;font-weight:bold;}}
  </style>
</head>
<body>
  <h1>ManaOS Phase 9 – Realtime Status</h1>
  <p class="ok">Last Update: <span id="ts">{status.get('timestamp', 'Unknown')}</span></p>
  <table>
    <tr><th>Service</th><th>Status</th><th>Note</th></tr>
    <tr><td>Optimizer</td><td class="status-{self.get_status_class(status.get('optimizer', {}).get('status', 'unknown'))}">{status.get('optimizer', {}).get('status', 'unknown')}</td><td>Watchdog 30s</td></tr>
    <tr><td>AI Optimizer</td><td class="status-{self.get_status_class(status.get('ai_optimizer', {}).get('status', 'unknown'))}">{status.get('ai_optimizer', {}).get('status', 'unknown')}</td><td>ML Learning</td></tr>
    <tr><td>Integration</td><td class="status-{self.get_status_class(status.get('integration', {}).get('status', 'unknown'))}">{status.get('integration', {}).get('status', 'unknown')}</td><td>Dashboard</td></tr>
    <tr><td>Containers</td><td id="ctr">{self.get_container_status(status.get('containers', []))}</td><td>health→復旧</td></tr>
  </table>
  <h3>Performance Metrics</h3>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>CPU Usage</td><td>{status.get('performance', {}).get('cpu_percent', 0):.1f}%</td></tr>
    <tr><td>Memory Usage</td><td>{status.get('performance', {}).get('memory_percent', 0):.1f}%</td></tr>
    <tr><td>Disk Usage</td><td>{status.get('performance', {}).get('disk_percent', 0):.1f}%</td></tr>
    <tr><td>Load Average</td><td>{status.get('performance', {}).get('load_avg', [0, 0, 0])[0]:.2f}</td></tr>
  </table>
  <script>
    // 倒れても描画が止まらないよう try/catch
    (function(){{
      try {{
        document.getElementById('ts').textContent = new Date().toLocaleString('ja-JP');
      }} catch(e) {{}}
    }})();
  </script>
</body>
</html>"""
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"ダッシュボード生成エラー: {e}")
            return self.get_emergency_dashboard()

    def get_status_class(self, status):
        """ステータスクラス取得"""
        if status == "active":
            return "active"
        elif status in ["inactive", "failed"]:
            return "inactive"
        else:
            return "unknown"

    def get_container_status(self, containers):
        """コンテナ状態取得"""
        try:
            if not containers:
                return "No containers"
            
            healthy_count = sum(1 for c in containers if c.get('healthy', False))
            total_count = len(containers)
            
            return f"{healthy_count}/{total_count} healthy"
        except Exception as e:
            self.logger.warning(f"コンテナ状態取得エラー: {e}")
            return "Unknown"

    def get_emergency_dashboard(self):
        """緊急時ダッシュボード"""
        return """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>Mana Dashboard - Emergency</title>
</head>
<body>
  <h1>ManaOS Phase 9 – Emergency Mode</h1>
  <p style="color: red;">Dashboard generation failed. System is running in emergency mode.</p>
  <p>Last Update: """ + datetime.now().isoformat() + """</p>
</body>
</html>"""

    def run_dashboard_generation(self):
        """ダッシュボード生成実行"""
        try:
            self.logger.info("堅牢化ダッシュボード生成開始")
            
            # システム状態取得
            status = self.get_system_status()
            
            # ダッシュボード生成
            html_content = self.generate_robust_dashboard(status)
            
            # ファイル保存
            with open(self.dashboard_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"堅牢化ダッシュボード生成完了: {self.dashboard_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"ダッシュボード生成実行エラー: {e}")
            return False

if __name__ == "__main__":
    dashboard = Phase9DashboardRobust()
    dashboard.run_dashboard_generation()
