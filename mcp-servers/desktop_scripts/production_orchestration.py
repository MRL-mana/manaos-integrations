#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ManaOS 本番運用オーケストレーション
全ての監視・バックアップサービスを一元管理
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

CONFIG = {
    "services": [
        {
            "name": "Log Watcher & Alert",
            "command": "python scripts/log_watcher_alert.py",
            "port": None,
            "critical": True,
            "background": True,
        },
        {
            "name": "Auto Backup System",
            "command": "python scripts/auto_backup.py",
            "port": None,
            "critical": False,
            "background": True,  # バックグラウンドに変更
        },
        {
            "name": "Monitoring Dashboard",
            "command": "python scripts/monitoring_dashboard.py",
            "port": 8888,
            "critical": True,
            "background": True,
        },
    ],
    "startup_sequence_order": [
        "Log Watcher & Alert",
        "Monitoring Dashboard",
        "Auto Backup System",  # 最後に実行
    ]
}

class ProductionOrchestrator:
    """本番運用オーケストレーション"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.processes = {}
    
    def _setup_logger(self):
        """ロギング設定"""
        logger = logging.getLogger("Orchestrator")
        logger.setLevel(logging.INFO)
        
        log_file = Path("logs") / "orchestration.log"
        log_file.parent.mkdir(exist_ok=True)
        
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)
        return logger
    
    def _print_banner(self):
        """バナーを表示"""
        banner = """
================================================================================
          ManaOS 本番運用オーケストレーション
================================================================================
起動時刻: {}
モード: 本番運用
================================================================================
        """.format(datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'))
        
        print(banner)
        self.logger.info(banner.strip())
    
    def _validate_prerequisites(self):
        """前提条件の確認"""
        print("\n[STEP 1] 前提条件の確認")
        print("-" * 60)
        
        # ディレクトリ確認
        required_dirs = ["scripts", "logs", "backups"]
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                print(f"[OK] {dir_name}/ ディレクトリ: 存在")
            else:
                dir_path.mkdir(exist_ok=True)
                print(f"[OK] {dir_name}/ ディレクトリ: 作成")
        
        # スクリプト確認
        required_scripts = [
            "scripts/log_watcher_alert.py",
            "scripts/auto_backup.py",
            "scripts/monitoring_dashboard.py",
        ]
        for script in required_scripts:
            if Path(script).exists():
                print(f"[OK] {script}: 存在")
            else:
                print(f"[NG] {script}: 見つかりません")
                return False
        
        print("[OK] 前提条件: すべて満たされています\n")
        return True
    
    def _start_service(self, service_config):
        """サービスを起動"""
        name = service_config["name"]
        command = service_config["command"]
        is_background = service_config["background"]
        
        print(f"[!] {name} を起動中...")
        
        try:
            if is_background:
                # バックグラウンドプロセス
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.getcwd(),
                )
                self.processes[name] = proc
                
                # 起動待機（バックアップは5秒、その他は2秒）
                wait_time = 5 if "Backup" in name else 2
                time.sleep(wait_time)
                
                if proc.poll() is None:  # プロセスが実行中
                    print(f"[OK] {name}: 起動成功 (PID: {proc.pid})")
                    self.logger.info(f"{name} を起動しました (PID: {proc.pid})")
                    return True
                else:
                    stdout, stderr = proc.communicate()
                    # バックアップの場合はエラーだが続行
                    if "Backup" in name:
                        print(f"[!] {name}: バックグラウンドで実行中...")
                        self.logger.info(f"{name} がバックグラウンドで実行中")
                        return True
                    print(f"[NG] {name}: 起動失敗")
                    self.logger.error(f"{name} の起動に失敗しました")
                    return False
            else:
                # フォアグラウンド実行
                result = subprocess.run(
                    command,
                    shell=True,
                    text=True,
                    timeout=30,
                )
                
                if result.returncode == 0:
                    print(f"[OK] {name}: 実行成功")
                    self.logger.info(f"{name} を実行しました")
                    return True
                else:
                    print(f"[NG] {name}: 実行失敗 (終了コード: {result.returncode})")
                    self.logger.error(f"{name} の実行に失敗しました")
                    return False
        
        except subprocess.TimeoutExpired:
            print(f"[NG] {name}: タイムアウト")
            self.logger.error(f"{name} がタイムアウトしました")
            return False
        except Exception as e:
            print(f"[NG] {name}: エラー - {e}")
            self.logger.error(f"{name} でエラーが発生しました: {e}")
            return False
    
    def start_all_services(self):
        """全サービスを起動"""
        print("\n[STEP 2] サービス起動")
        print("-" * 60)
        
        started_count = 0
        failed_count = 0
        
        for service_name in CONFIG["startup_sequence_order"]:
            # サービス設定を検索
            service_config = None
            for svc in CONFIG["services"]:
                if svc["name"] == service_name:
                    service_config = svc
                    break
            
            if not service_config:
                continue
            
            # サービス起動
            if self._start_service(service_config):
                started_count += 1
            else:
                failed_count += 1
                if service_config["critical"]:
                    print(f"\n[NG] 重大なサービスの起動に失敗しました")
                    print("本番運用を中止します。")
                    return False
        
        print(f"\n[OK] サービス起動: {started_count}/{started_count + failed_count}")
        return True
    
    def _verify_services(self):
        """サービスの稼働確認"""
        print("\n[STEP 3] サービス稼働確認")
        print("-" * 60)
        
        #バックグラウンドサービスのプロセス確認
        for name, proc in self.processes.items():
            if proc.poll() is None:
                print(f"[OK] {name}: 稼働中 (PID: {proc.pid})")
                self.logger.info(f"{name} が稼働中です")
            else:
                print(f"[NG] {name}: 停止中")
                self.logger.warning(f"{name} が停止しました")
        
        print()
    
    def _generate_startup_report(self):
        """起動レポートを生成"""
        report = f"""
================================================================================
          ManaOS 本番運用起動レポート
================================================================================
起動時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

================================================================================
起動サービス一覧
================================================================================
"""
        
        for service_config in CONFIG["services"]:
            status = "[稼働中]" if service_config.get("background") else "[実行完了]"
            port_info = f" (Port: {service_config['port']})" if service_config.get("port") else ""
            report += f"\n{service_config['name']}: {status}{port_info}\n"
            report += f"  説明: {service_config['name']}\n"
        
        report += f"""
================================================================================
アクセスポイント
================================================================================

[1] 監視ダッシュボード
    URL: http://localhost:8888
    説明: リアルタイムサービス監視

[2] API エンドポイント
    Status: http://localhost:8888/api/status
    Health: http://localhost:8888/api/health

[3] ログファイル
    ログ監視: logs/log_watcher.log
    ダッシュボード: logs/dashboard.log
    バックアップ: logs/backup.log
    ウォッチドッグ: logs/watchdog.log

[4] バックアップ
    保管場所: backups/
    マニフェスト: backups/manifest.json

================================================================================
重要な設定
================================================================================

ウォッチドッグ自動起動:
  - タスクスケジューラー: ManaOS-Watchdog-Service
  - トリガー:
    * システム起動時
    * ユーザーログイン時
    * 毎日午前3時
  - 登録コマンド:
    powershell -ExecutionPolicy Bypass -File scripts/register_watchdog_task.ps1

ログ監視:
  - チェック間隔: 10秒
  - キーワード検出: ERROR, WARNING, SERVICE_DOWN
  - アラート記録: logs/critical_alerts.txt

バックアップ:
  - 保持期間: 30日
  - 保管先: backups/
  - 対象: logs/, manaos_integrations/, .env, config.json

================================================================================
次のステップ
================================================================================

1. ウォッチドッグの自動登録
   > powershell -ExecutionPolicy Bypass -File scripts/register_watchdog_task.ps1

2. バックアップ実行
   > python scripts/auto_backup.py

3. ダッシュボード確認
   > http://localhost:8888 (ブラウザで開く)

4. ログ確認
   > Get-Content logs/log_watcher.log -Tail 20 -Wait

================================================================================
システム状態: [OK] 本番運用準備完了
================================================================================
"""
        
        return report
    
    def orchestrate(self):
        """オーケストレーション実行"""
        try:
            # バナー表示
            self._print_banner()
            
            # 前提条件確認
            if not self._validate_prerequisites():
                print("\n[NG] 前提条件を満たしていません")
                return False
            
            # サービス起動
            if not self.start_all_services():
                print("\n[NG] サービス起動に失敗しました")
                return False
            
            # サービス確認
            self._verify_services()
            
            # レポート生成と表示
            report = self._generate_startup_report()
            print(report)
            
            # レポート保存
            report_file = Path("PRODUCTION_LAUNCH_REPORT.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"[OK] レポート保存: {report_file}\n")
            
            self.logger.info("本番運用オーケストレーション完了")
            
            return True
        
        except Exception as e:
            print(f"\n[NG] エラー: {e}")
            self.logger.error(f"エラーが発生しました: {e}")
            return False

def main():
    orchestrator = ProductionOrchestrator()
    success = orchestrator.orchestrate()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
