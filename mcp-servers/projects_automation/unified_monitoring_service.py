#!/usr/bin/env python3
"""
統合監視サービス - ALL-IN-ONE
health_checker + auto_recovery + auto_health_monitor + security_monitor + trinity_health_monitor を統合
"""

import requests
import subprocess
import time
import json
from datetime import datetime
from threading import Thread
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/unified_monitoring.log'),
        logging.StreamHandler()
    ]
)

class UnifiedMonitoringService:
    def __init__(self):
        self.logger = logging.getLogger('UnifiedMonitoring')
        
        # 監視対象エンドポイント
        self.endpoints = {
            "ManaOS Orchestrator": "http://localhost:9200/health",
            "ManaOS Intention": "http://localhost:9201/health",
            "ManaOS Policy": "http://localhost:9202/health",
            "ManaOS Actuator": "http://localhost:9203/health",
            "ManaOS Ingestor": "http://localhost:9204/health",
            "ManaOS Insight": "http://localhost:9205/health",
            "Screen Sharing": "http://localhost:5008",
            "Command Center": "http://localhost:10000",
            "Grafana": "http://localhost:3000",
            "Prometheus": "http://localhost:9090"
        }
        
        # 自動復旧対象サービス
        self.recovery_services = [
            {"name": "カレンダーリマインダー", "process": "calendar_reminder_system.py", "cmd": "systemctl restart manaos-calendar-reminder"},
            {"name": "自動バックアップ", "process": "auto_backup_scheduler.py", "cmd": "systemctl restart manaos-auto-backup"},
            {"name": "アラートシステム", "process": "alert_system.py", "cmd": "systemctl restart manaos-alert-system"}
        ]
        
        self.failure_count = {}
        self.recovery_count = {}
        self.alert_threshold = 3
        
    def check_endpoint(self, name, url):
        """エンドポイント監視"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                self.failure_count[name] = 0
                return True, response.elapsed.total_seconds() * 1000
            else:
                self.failure_count[name] = self.failure_count.get(name, 0) + 1
                return False, 0
        except Exception:
            self.failure_count[name] = self.failure_count.get(name, 0) + 1
            return False, 0
    
    def monitor_endpoints(self):
        """全エンドポイント監視（1分ごと）"""
        while True:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.logger.info(f"🔍 エンドポイント監視開始 - {timestamp}")
                
                alerts = []
                healthy = 0
                
                for name, url in self.endpoints.items():
                    is_healthy, response_time = self.check_endpoint(name, url)
                    
                    if is_healthy:
                        healthy += 1
                        self.logger.info(f"✅ {name}: OK ({response_time:.0f}ms)")
                    else:
                        fail_count = self.failure_count.get(name, 0)
                        self.logger.warning(f"❌ {name}: 失敗 ({fail_count}回)")
                        
                        if fail_count >= self.alert_threshold:
                            alerts.append(f"{name}が{fail_count}回連続失敗")
                
                # アラート送信
                if alerts:
                    self.send_alert("エンドポイント異常", "\n".join(alerts))
                
                self.logger.info(f"📊 結果: {healthy}/{len(self.endpoints)} 正常")
                
                time.sleep(60)
            except Exception as e:
                self.logger.error(f"監視エラー: {e}")
                time.sleep(30)
    
    def check_process_running(self, process_name):
        """プロセス稼働確認"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def auto_recovery(self):
        """自動復旧（1分ごと）"""
        while True:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.logger.info(f"🔄 自動復旧チェック - {timestamp}")
                
                recovered = 0
                for service in self.recovery_services:
                    if not self.check_process_running(service["process"]):
                        self.logger.warning(f"⚠️ {service['name']} が停止")
                        
                        # 再起動
                        try:
                            subprocess.run(service["cmd"].split(), timeout=30)
                            time.sleep(3)
                            
                            if self.check_process_running(service["process"]):
                                self.logger.info(f"✅ {service['name']} 復旧成功")
                                recovered += 1
                            else:
                                self.logger.error(f"❌ {service['name']} 復旧失敗")
                        except Exception as e:
                            self.logger.error(f"❌ {service['name']} エラー: {e}")
                    else:
                        self.logger.info(f"✅ {service['name']}: 正常")
                
                if recovered > 0:
                    self.send_alert("サービス復旧", f"{recovered}個のサービスを復旧しました")
                
                time.sleep(60)
            except Exception as e:
                self.logger.error(f"復旧エラー: {e}")
                time.sleep(30)
    
    def monitor_security(self):
        """セキュリティ監視（5分ごと）"""
        while True:
            try:
                # 失敗したログイン試行を確認
                result = subprocess.run(
                    ["grep", "Failed password", "/var/log/auth.log"],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    recent = result.stdout.split('\n')[-10:]
                    if len(recent) > 5:
                        self.logger.warning(f"⚠️ 失敗ログイン試行: {len(recent)}件")
                
                time.sleep(300)  # 5分
            except Exception:
                time.sleep(300)
    
    def send_alert(self, title, message):
        """LINE通知送信"""
        try:
            subprocess.run([
                'curl', '-X', 'POST',
                'http://localhost:5099/api/line/alert',
                '-H', 'Content-Type: application/json',
                '-d', json.dumps({"title": title, "message": message, "level": "warning"})
            ], timeout=10, capture_output=True)
        except subprocess.SubprocessError:
            pass
    
    def run(self):
        """全機能を並列実行"""
        self.logger.info("🚀 統合監視サービス起動")
        self.logger.info("   - エンドポイント監視")
        self.logger.info("   - 自動復旧")
        self.logger.info("   - セキュリティ監視")
        
        # スレッドで並列実行
        threads = [
            Thread(target=self.monitor_endpoints, daemon=True),
            Thread(target=self.auto_recovery, daemon=True),
            Thread(target=self.monitor_security, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
        
        # メインスレッドは稼働状態を定期報告
        while True:
            try:
                time.sleep(600)  # 10分ごと
                self.logger.info("💓 統合監視サービス稼働中")
            except KeyboardInterrupt:
                self.logger.info("👋 統合監視サービス停止")
                break

if __name__ == "__main__":
    service = UnifiedMonitoringService()
    service.run()


