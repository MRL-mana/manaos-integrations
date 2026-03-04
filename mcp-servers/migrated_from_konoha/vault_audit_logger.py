#!/usr/bin/env python3
"""
Phase 8: Vaultアクセス監査ログシステム
- .mana_vault/access.log にアクセス記録
- セキュリティ層の可視化を実現
- リアルタイム監視とアラート
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
import psutil
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VaultAuditLogger:
    def __init__(self):
        self.vault_dir = Path("/root/.mana_vault")
        self.vault_dir.mkdir(exist_ok=True, mode=0o700)
        
        # 監査ログファイル
        self.audit_log = self.vault_dir / "access.log"
        self.security_log = self.vault_dir / "security_events.log"
        
        # ログ設定
        self.setup_logging()
        
        # 監視対象ファイル
        self.watched_files = [
            self.vault_dir / "service_secrets.env",
            self.vault_dir / "api_keys.json",
            self.vault_dir / "tokens.json",
            self.vault_dir / "credentials.json"
        ]
        
        # 既存ファイルの監視開始
        for file_path in self.watched_files:
            if file_path.exists():
                self.log_access("FILE_EXISTS", str(file_path), "system", "initial_check")
        
        # ファイルシステム監視開始
        self.start_file_monitoring()

    def setup_logging(self):
        """ログ設定"""
        # 監査ログ（アクセス記録）
        audit_handler = logging.FileHandler(self.audit_log)
        audit_handler.setLevel(logging.INFO)
        audit_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        
        # セキュリティログ（重要イベント）
        security_handler = logging.FileHandler(self.security_log)
        security_handler.setLevel(logging.WARNING)
        security_formatter = logging.Formatter(
            '%(asctime)s | SECURITY | %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        
        # ロガー設定
        self.audit_logger = logging.getLogger('vault_audit')
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.addHandler(audit_handler)
        
        self.security_logger = logging.getLogger('vault_security')
        self.security_logger.setLevel(logging.WARNING)
        self.security_logger.addHandler(security_handler)
        
        # コンソール出力も追加
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.audit_logger.addHandler(console_handler)

    def log_access(self, action, file_path, user, process_info="", details=""):
        """アクセスログを記録"""
        timestamp = datetime.now().isoformat()
        
        # プロセス情報取得
        if not process_info:
            process_info = self.get_process_info()
        
        # ログエントリ作成
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "file": str(file_path),
            "user": user,
            "process": process_info,
            "details": details
        }
        
        # 監査ログに記録
        self.audit_logger.info(
            f"{action} | {file_path} | {user} | {process_info} | {details}"
        )
        
        # セキュリティ上重要なアクションをチェック
        if action in ["WRITE", "DELETE", "MODIFY"]:
            self.security_logger.warning(
                f"SECURITY EVENT: {action} on {file_path} by {user} ({process_info})"
            )
            
            # 即座にSlack通知
            self.send_security_alert(log_entry)

    def get_process_info(self):
        """現在のプロセス情報を取得"""
        try:
            current_process = psutil.Process()
            return f"PID:{current_process.pid} CMD:{current_process.cmdline()[0]}"
        except:
            return "unknown"

    def send_security_alert(self, log_entry):
        """セキュリティアラートをSlackに送信"""
        try:
            # Slack設定読み込み
            slack_config = self.vault_dir / "slack_config.json"
            if not slack_config.exists():
                return
            
            with open(slack_config, 'r') as f:
                config = json.load(f)
            
            webhook_url = config.get('webhook_url')
            if not webhook_url:
                return
            
            # アラートメッセージ作成
            message = {
                "text": f"🔒 **Vault Security Alert**",
                "attachments": [{
                    "color": "danger",
                    "fields": [
                        {"title": "Action", "value": log_entry['action'], "short": True},
                        {"title": "File", "value": log_entry['file'], "short": False},
                        {"title": "User", "value": log_entry['user'], "short": True},
                        {"title": "Process", "value": log_entry['process'], "short": True},
                        {"title": "Time", "value": log_entry['timestamp'], "short": True}
                    ]
                }]
            }
            
            # Slack送信
            response = requests.post(webhook_url, json=message, timeout=5)
            if response.status_code == 200:
                self.audit_logger.info("Security alert sent to Slack")
            else:
                self.audit_logger.error(f"Failed to send Slack alert: {response.status_code}")
                
        except Exception as e:
            self.audit_logger.error(f"Slack alert error: {e}")

    def start_file_monitoring(self):
        """ファイルシステム監視を開始"""
        class VaultFileHandler(FileSystemEventHandler):
            def __init__(self, audit_logger):
                self.audit_logger = audit_logger
            
            def on_modified(self, event):
                if not event.is_directory:
                    self.audit_logger.log_access(
                        "MODIFY", event.src_path, "system", "file_monitor"
                    )
            
            def on_created(self, event):
                if not event.is_directory:
                    self.audit_logger.log_access(
                        "CREATE", event.src_path, "system", "file_monitor"
                    )
            
            def on_deleted(self, event):
                if not event.is_directory:
                    self.audit_logger.log_access(
                        "DELETE", event.src_path, "system", "file_monitor"
                    )
        
        # 監視開始
        event_handler = VaultFileHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(self.vault_dir), recursive=True)
        observer.start()
        
        self.audit_logger.info("Vault file monitoring started")
        return observer

    def generate_security_report(self):
        """セキュリティレポートを生成"""
        try:
            # 過去24時間のアクセスログを分析
            with open(self.audit_log, 'r') as f:
                lines = f.readlines()
            
            # 統計情報
            stats = {
                "total_accesses": len(lines),
                "read_operations": 0,
                "write_operations": 0,
                "delete_operations": 0,
                "unique_users": set(),
                "unique_files": set(),
                "security_events": 0
            }
            
            for line in lines:
                if "READ" in line:
                    stats["read_operations"] += 1
                elif "WRITE" in line:
                    stats["write_operations"] += 1
                elif "DELETE" in line:
                    stats["delete_operations"] += 1
                
                # ユーザーとファイルを抽出
                parts = line.split(" | ")
                if len(parts) >= 4:
                    stats["unique_users"].add(parts[2])
                    stats["unique_files"].add(parts[1])
            
            # セキュリティイベント数
            with open(self.security_log, 'r') as f:
                security_lines = f.readlines()
            stats["security_events"] = len(security_lines)
            
            # レポート生成
            report = {
                "timestamp": datetime.now().isoformat(),
                "period": "24h",
                "statistics": {
                    "total_accesses": stats["total_accesses"],
                    "read_operations": stats["read_operations"],
                    "write_operations": stats["write_operations"],
                    "delete_operations": stats["delete_operations"],
                    "unique_users": len(stats["unique_users"]),
                    "unique_files": len(stats["unique_files"]),
                    "security_events": stats["security_events"]
                },
                "users": list(stats["unique_users"]),
                "files": list(stats["unique_files"])
            }
            
            # レポート保存
            report_file = self.vault_dir / f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.audit_logger.info(f"Security report generated: {report_file}")
            return report
            
        except Exception as e:
            self.audit_logger.error(f"Report generation error: {e}")
            return None

    def run_continuous_monitoring(self):
        """継続監視を実行"""
        self.audit_logger.info("=== Phase 8: Vault監査ログシステム開始 ===")
        
        try:
            # ファイル監視開始
            observer = self.start_file_monitoring()
            
            # 定期レポート生成（1時間ごと）
            last_report_time = time.time()
            report_interval = 3600  # 1時間
            
            while True:
                current_time = time.time()
                
                # 定期レポート生成
                if current_time - last_report_time >= report_interval:
                    self.generate_security_report()
                    last_report_time = current_time
                
                time.sleep(60)  # 1分間隔でチェック
                
        except KeyboardInterrupt:
            self.audit_logger.info("監視を停止します")
            observer.stop()
        except Exception as e:
            self.audit_logger.error(f"監視エラー: {e}")
        finally:
            observer.join()

if __name__ == "__main__":
    # 監査ログシステム起動
    audit_logger = VaultAuditLogger()
    
    # 初回レポート生成
    audit_logger.generate_security_report()
    
    # 継続監視開始
    audit_logger.run_continuous_monitoring()
