#!/usr/bin/env python3
"""
自動復旧システム
異常検知 → 自動復旧を実行
"""

import subprocess
from datetime import datetime
from pathlib import Path
import psutil
import requests

class AutoRecoverySystem:
    def __init__(self):
        self.log_file = Path("/root/logs/auto_recovery.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 監視対象サービス
        self.critical_services = [
            "unified-portal",
            "security-monitor",
            "ai-model-hub",
            "ai-predictive",
            "task-executor",
            "cost-optimizer",
            "notification-service"
        ]
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
        
        print(log_entry)
    
    def check_service_health(self, service_name):
        """サービスの健全性チェック"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() == "active"
        except Exception as e:
            self.log(f"サービスチェックエラー {service_name}: {e}", "ERROR")
            return False
    
    def restart_service(self, service_name):
        """サービス再起動"""
        try:
            self.log(f"サービス再起動: {service_name}", "WARN")
            
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log(f"再起動成功: {service_name}", "INFO")
                
                # 通知送信
                self.send_notification(
                    "サービス自動復旧",
                    f"{service_name} を自動的に再起動しました",
                    "warning"
                )
                return True
            else:
                self.log(f"再起動失敗: {service_name} - {result.stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"再起動エラー {service_name}: {e}", "ERROR")
            return False
    
    def check_disk_space(self):
        """ディスク容量チェック"""
        disk = psutil.disk_usage('/')
        
        if disk.percent > 90:
            self.log(f"ディスク容量警告: {disk.percent}%", "CRITICAL")
            self.cleanup_disk()
            return False
        elif disk.percent > 80:
            self.log(f"ディスク容量注意: {disk.percent}%", "WARN")
            return True
        
        return True
    
    def cleanup_disk(self):
        """ディスククリーンアップ"""
        self.log("ディスククリーンアップ開始", "INFO")
        
        cleanup_commands = [
            # Dockerクリーンアップ
            "docker system prune -f",
            # ログ圧縮
            "find /root/logs -name '*.log' -size +10M -exec gzip {} \\;",
            # Pythonキャッシュ削除
            "find /root -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            # 古いレポート削除（30日以上）
            "find /root/reports -type f -mtime +30 -delete 2>/dev/null || true"
        ]
        
        for cmd in cleanup_commands:
            try:
                subprocess.run(cmd, shell=True, timeout=60)
                self.log(f"クリーンアップ実行: {cmd[:50]}...", "INFO")
            except Exception as e:
                self.log(f"クリーンアップエラー: {e}", "WARN")
        
        self.send_notification(
            "ディスククリーンアップ実行",
            "自動的にディスク容量を確保しました",
            "info"
        )
    
    def check_memory(self):
        """メモリ使用率チェック"""
        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            self.log(f"メモリ使用率警告: {memory.percent}%", "CRITICAL")
            self.free_memory()
            return False
        
        return True
    
    def free_memory(self):
        """メモリ解放"""
        self.log("メモリ解放開始", "INFO")
        
        try:
            # ページキャッシュ・dentries・inodesのクリア
            subprocess.run(
                "sync; echo 3 > /proc/sys/vm/drop_caches",
                shell=True,
                timeout=10
            )
            self.log("メモリキャッシュをクリアしました", "INFO")
            
            self.send_notification(
                "メモリ解放実行",
                "メモリキャッシュを自動的にクリアしました",
                "info"
            )
        except Exception as e:
            self.log(f"メモリ解放エラー: {e}", "ERROR")
    
    def check_cpu(self):
        """CPU使用率チェック"""
        cpu_percent = psutil.cpu_percent(interval=5)
        
        if cpu_percent > 95:
            self.log(f"CPU使用率警告: {cpu_percent}%", "CRITICAL")
            self.find_cpu_hogs()
            return False
        
        return True
    
    def find_cpu_hogs(self):
        """CPU使用率が高いプロセスを特定"""
        self.log("高CPU使用プロセスを検索", "INFO")
        
        high_cpu_procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['cpu_percent'] > 50:
                    high_cpu_procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if high_cpu_procs:
            msg = "高CPU使用プロセス:\n"
            for proc in high_cpu_procs[:5]:
                msg += f"  - {proc['name']} (PID: {proc['pid']}, CPU: {proc['cpu_percent']}%)\n"
            
            self.log(msg, "WARN")
            self.send_notification("高CPU使用検知", msg, "warning")
    
    def send_notification(self, title, message, level="info"):
        """通知送信"""
        try:
            requests.post(
                "http://localhost:8009/api/notify",
                json={
                    "title": title,
                    "message": message,
                    "level": level
                },
                timeout=5
            )
        except:
            pass  # 通知失敗してもシステムは続行
    
    def run_health_check(self):
        """健全性チェック実行"""
        self.log("=== 健全性チェック開始 ===", "INFO")
        
        issues_found = 0
        
        # サービスチェック
        for service in self.critical_services:
            if not self.check_service_health(service):
                self.log(f"サービス異常検知: {service}", "WARN")
                if self.restart_service(service):
                    issues_found += 1
        
        # リソースチェック
        if not self.check_disk_space():
            issues_found += 1
        
        if not self.check_memory():
            issues_found += 1
        
        if not self.check_cpu():
            issues_found += 1
        
        self.log(f"=== 健全性チェック完了（問題: {issues_found}件）===", "INFO")
        
        return issues_found

if __name__ == "__main__":
    system = AutoRecoverySystem()
    issues = system.run_health_check()
    
    exit(0 if issues == 0 else 1)

