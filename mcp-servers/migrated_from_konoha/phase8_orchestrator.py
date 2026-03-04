#!/usr/bin/env python3
"""
Phase 8: 統合オーケストレーター
- 全Phase 8システムの統合管理
- 自動スケジューリング
- 統合レポート生成
"""

import os
import sys
import time
import json
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
import logging

class Phase8Orchestrator:
    def __init__(self):
        self.vault_dir = Path("/root/.mana_vault")
        self.tools_dir = Path("/root/trinity_workspace/tools")
        self.config_file = self.vault_dir / "phase8_config.json"
        
        # ログ設定
        self.setup_logging()
        
        # 設定読み込み
        self.config = self.load_config()
        
        # 実行中フラグ
        self.running = False
        self.threads = []

    def setup_logging(self):
        """ログ設定"""
        log_file = self.vault_dir / "phase8_orchestrator.log"
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
            "auto_vault_scan": {
                "enabled": True,
                "interval_hours": 6,
                "last_run": None
            },
            "health_monitor": {
                "enabled": True,
                "interval_hours": 3,
                "last_run": None
            },
            "vault_audit": {
                "enabled": True,
                "continuous": True,
                "last_report": None
            },
            "slack_notifications": {
                "enabled": True,
                "webhook_url": "",
                "channel": "#mana-security"
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
            # デフォルト設定を保存
            self.save_config(default_config)
            return default_config

    def save_config(self, config=None):
        """設定ファイル保存"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("設定ファイルを保存しました")
        except Exception as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")

    def run_auto_vault_scan(self):
        """自動Vaultスキャンを実行"""
        try:
            self.logger.info("自動Vaultスキャンを開始")
            
            # Pythonスクリプト実行
            script_path = self.tools_dir / "auto_vault_security.py"
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=60  # 1分タイムアウト
                )
                
                if result.returncode == 0:
                    self.logger.info("自動Vaultスキャン完了")
                    self.config["auto_vault_scan"]["last_run"] = datetime.now().isoformat()
                    self.save_config()
                    return True
                else:
                    self.logger.error(f"自動Vaultスキャンエラー: {result.stderr}")
                    return False
            else:
                self.logger.error("自動Vaultスキャンスクリプトが見つかりません")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("自動Vaultスキャンがタイムアウトしました")
            return False
        except Exception as e:
            self.logger.error(f"自動Vaultスキャン実行エラー: {e}")
            return False

    def run_health_monitor(self):
        """ヘルスモニターを実行"""
        try:
            self.logger.info("ヘルスモニターを開始")
            
            # シェルスクリプト実行
            script_path = "/usr/local/bin/mana_health.sh"
            if os.path.exists(script_path):
                result = subprocess.run(
                    [script_path],
                    capture_output=True,
                    text=True,
                    timeout=60  # 1分タイムアウト
                )
                
                if result.returncode == 0:
                    self.logger.info("ヘルスモニター完了")
                    self.config["health_monitor"]["last_run"] = datetime.now().isoformat()
                    self.save_config()
                    return True
                else:
                    self.logger.error(f"ヘルスモニターエラー: {result.stderr}")
                    return False
            else:
                self.logger.error("ヘルスモニタースクリプトが見つかりません")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("ヘルスモニターがタイムアウトしました")
            return False
        except Exception as e:
            self.logger.error(f"ヘルスモニター実行エラー: {e}")
            return False

    def start_vault_audit(self):
        """Vault監査ログを開始"""
        try:
            self.logger.info("Vault監査ログを開始")
            
            script_path = self.tools_dir / "vault_audit_logger.py"
            if script_path.exists():
                # バックグラウンドで実行
                def run_audit():
                    subprocess.run([sys.executable, str(script_path)])
                
                audit_thread = threading.Thread(target=run_audit, daemon=True)
                audit_thread.start()
                self.threads.append(audit_thread)
                
                self.logger.info("Vault監査ログをバックグラウンドで開始")
                return True
            else:
                self.logger.error("Vault監査ログスクリプトが見つかりません")
                return False
                
        except Exception as e:
            self.logger.error(f"Vault監査ログ開始エラー: {e}")
            return False

    def should_run_scan(self, scan_type):
        """スキャンを実行すべきかチェック"""
        config = self.config.get(scan_type, {})
        if not config.get("enabled", False):
            return False
        
        last_run = config.get("last_run")
        if not last_run:
            return True
        
        try:
            last_run_time = datetime.fromisoformat(last_run)
            interval_hours = config.get("interval_hours", 24)
            next_run_time = last_run_time + timedelta(hours=interval_hours)
            
            return datetime.now() >= next_run_time
        except Exception as e:
            self.logger.error(f"スケジュールチェックエラー: {e}")
            return True

    def generate_integration_report(self):
        """統合レポートを生成"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "phase": "Phase 8 - 自動検出＆監視強化",
                "components": {
                    "auto_vault_scan": {
                        "enabled": self.config["auto_vault_scan"]["enabled"],
                        "last_run": self.config["auto_vault_scan"]["last_run"],
                        "status": "active" if self.config["auto_vault_scan"]["enabled"] else "disabled"
                    },
                    "health_monitor": {
                        "enabled": self.config["health_monitor"]["enabled"],
                        "last_run": self.config["health_monitor"]["last_run"],
                        "status": "active" if self.config["health_monitor"]["enabled"] else "disabled"
                    },
                    "vault_audit": {
                        "enabled": self.config["vault_audit"]["enabled"],
                        "continuous": self.config["vault_audit"]["continuous"],
                        "status": "active" if self.config["vault_audit"]["enabled"] else "disabled"
                    }
                },
                "system_status": "operational"
            }
            
            # レポート保存
            report_file = self.vault_dir / f"phase8_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"統合レポートを生成: {report_file}")
            return report
            
        except Exception as e:
            self.logger.error(f"統合レポート生成エラー: {e}")
            return None

    def run_single_cycle(self):
        """単一サイクル実行"""
        self.logger.info("=== Phase 8 統合オーケストレーター実行 ===")
        
        # 自動Vaultスキャン
        if self.should_run_scan("auto_vault_scan"):
            self.run_auto_vault_scan()
        
        # ヘルスモニター
        if self.should_run_scan("health_monitor"):
            self.run_health_monitor()
        
        # Vault監査ログ（初回のみ）
        if self.config["vault_audit"]["enabled"] and not self.threads:
            self.start_vault_audit()
        
        # 統合レポート生成
        self.generate_integration_report()
        
        self.logger.info("=== Phase 8 統合オーケストレーター完了 ===")

    def run_continuous(self):
        """継続実行"""
        self.logger.info("Phase 8 統合オーケストレーターを開始")
        self.running = True
        
        try:
            while self.running:
                self.run_single_cycle()
                
                # 1時間待機
                time.sleep(3600)
                
        except KeyboardInterrupt:
            self.logger.info("Phase 8 統合オーケストレーターを停止")
            self.running = False
        except Exception as e:
            self.logger.error(f"継続実行エラー: {e}")
        finally:
            # スレッド終了待機
            for thread in self.threads:
                thread.join(timeout=5)

if __name__ == "__main__":
    orchestrator = Phase8Orchestrator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        orchestrator.run_continuous()
    else:
        orchestrator.run_single_cycle()
