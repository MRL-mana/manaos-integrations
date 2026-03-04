#!/usr/bin/env python3
"""
自動化マネージャー
全システムの自動実行、スケジューリング、通知管理
"""

import schedule
import time
import json
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutomationManager:
    """自動化マネージャー"""
    
    def __init__(self):
        self.base_path = Path("/root/system_automation")
        self.config_path = self.base_path / ".automation_config.json"
        
        self.default_config = {
            "enabled": True,
            "schedule": {
                "monitoring": {
                    "enabled": True,
                    "interval_minutes": 5
                },
                "file_organization": {
                    "enabled": True,
                    "time": "02:00",
                    "days": ["sunday"]
                },
                "duplicate_detection": {
                    "enabled": True,
                    "time": "03:00",
                    "days": ["sunday"]
                },
                "maintenance_daily": {
                    "enabled": True,
                    "time": "01:00"
                },
                "maintenance_weekly": {
                    "enabled": True,
                    "time": "00:00",
                    "day": "sunday"
                }
            },
            "notifications": {
                "enabled": True,
                "email": False,
                "telegram": False,
                "log_file": True
            }
        }
        
        self.config = self.load_config()
        self.running = False
        
    def load_config(self) -> dict:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def run_monitoring(self):
        """監視システム実行"""
        logger.info("🔍 監視システム実行中...")
        try:
            subprocess.run([
                "python3",
                str(self.base_path / "monitoring/monitor_engine.py")
            ], check=True, capture_output=True)
            logger.info("✅ 監視システム完了")
        except Exception as e:
            logger.error(f"❌ 監視システムエラー: {e}")
    
    def run_file_organization(self):
        """ファイル整理実行"""
        logger.info("📁 ファイル整理実行中...")
        try:
            subprocess.run([
                "python3",
                str(self.base_path / "file_organizer/file_organizer.py")
            ], check=True, capture_output=True)
            logger.info("✅ ファイル整理完了")
        except Exception as e:
            logger.error(f"❌ ファイル整理エラー: {e}")
    
    def run_duplicate_detection(self):
        """重複検出実行"""
        logger.info("🔍 重複検出実行中...")
        try:
            subprocess.run([
                "python3",
                str(self.base_path / "file_organizer/duplicate_detector.py")
            ], check=True, capture_output=True)
            logger.info("✅ 重複検出完了")
        except Exception as e:
            logger.error(f"❌ 重複検出エラー: {e}")
    
    def run_daily_maintenance(self):
        """日次メンテナンス実行"""
        logger.info("🔧 日次メンテナンス実行中...")
        try:
            subprocess.run([
                "python3",
                str(self.base_path / "maintenance/maintenance_scheduler.py")
            ], check=True, capture_output=True)
            logger.info("✅ 日次メンテナンス完了")
        except Exception as e:
            logger.error(f"❌ 日次メンテナンスエラー: {e}")
    
    def run_weekly_maintenance(self):
        """週次メンテナンス実行"""
        logger.info("🔧 週次メンテナンス実行中...")
        try:
            subprocess.run([
                "python3",
                str(self.base_path / "maintenance/maintenance_scheduler.py")
            ], check=True, capture_output=True)
            logger.info("✅ 週次メンテナンス完了")
        except Exception as e:
            logger.error(f"❌ 週次メンテナンスエラー: {e}")
    
    def setup_schedule(self):
        """スケジュール設定"""
        schedule.clear()
        
        config = self.config.get("schedule", {})
        
        # 監視システム（5分ごと）
        if config.get("monitoring", {}).get("enabled"):
            interval = config["monitoring"].get("interval_minutes", 5)
            schedule.every(interval).minutes.do(self.run_monitoring)
            logger.info(f"📅 監視システム: {interval}分ごと")
        
        # ファイル整理（毎週日曜 2:00）
        if config.get("file_organization", {}).get("enabled"):
            time = config["file_organization"].get("time", "02:00")
            schedule.every().sunday.at(time).do(self.run_file_organization)
            logger.info(f"📅 ファイル整理: 毎週日曜 {time}")
        
        # 重複検出（毎週日曜 3:00）
        if config.get("duplicate_detection", {}).get("enabled"):
            time = config["duplicate_detection"].get("time", "03:00")
            schedule.every().sunday.at(time).do(self.run_duplicate_detection)
            logger.info(f"📅 重複検出: 毎週日曜 {time}")
        
        # 日次メンテナンス（毎日 1:00）
        if config.get("maintenance_daily", {}).get("enabled"):
            time = config["maintenance_daily"].get("time", "01:00")
            schedule.every().day.at(time).do(self.run_daily_maintenance)
            logger.info(f"📅 日次メンテナンス: 毎日 {time}")
        
        # 週次メンテナンス（毎週日曜 0:00）
        if config.get("maintenance_weekly", {}).get("enabled"):
            time = config["maintenance_weekly"].get("time", "00:00")
            schedule.every().sunday.at(time).do(self.run_weekly_maintenance)
            logger.info(f"📅 週次メンテナンス: 毎週日曜 {time}")
    
    def run(self):
        """自動化マネージャー実行"""
        logger.info("🚀 自動化マネージャー起動")
        logger.info("=" * 60)
        
        if not self.config.get("enabled"):
            logger.warning("⚠️ 自動化が無効化されています")
            return
        
        # スケジュール設定
        self.setup_schedule()
        
        logger.info(f"📊 スケジュール設定完了: {len(schedule.jobs)}個のタスク")
        logger.info("=" * 60)
        
        self.running = True
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n⏹️ 自動化マネージャー停止")
            self.running = False
    
    def stop(self):
        """停止"""
        self.running = False


def main():
    """メイン実行"""
    manager = AutomationManager()
    
    print("=" * 60)
    print("🚀 ManaOS 自動化マネージャー")
    print("=" * 60)
    
    # ステータス表示
    print("\n📊 ステータス:")
    print(f"  有効: {'✅' if manager.config['enabled'] else '❌'}")
    print(f"  スケジュール: {len(manager.config.get('schedule', {}))}個")
    
    # スケジュール表示
    print("\n📅 スケジュール:")
    for task, config in manager.config.get("schedule", {}).items():
        status = "✅" if config.get("enabled") else "❌"
        print(f"  {status} {task}")
    
    # メニュー
    print("\n実行する操作を選択:")
    print("  1. 自動化マネージャー起動（バックグラウンド）")
    print("  2. 今すぐ全タスク実行")
    print("  3. 監視システム実行")
    print("  4. ファイル整理実行")
    print("  5. 重複検出実行")
    print("  6. メンテナンス実行")
    print("  0. 終了")
    
    choice = input("\n選択 (0-6): ").strip()
    
    if choice == "1":
        print("\n🚀 自動化マネージャーを起動します...")
        print("停止するには Ctrl+C を押してください")
        print("=" * 60)
        manager.run()
    
    elif choice == "2":
        print("\n🚀 全タスク実行中...")
        manager.run_monitoring()
        manager.run_file_organization()
        manager.run_duplicate_detection()
        manager.run_daily_maintenance()
        print("\n✅ 全タスク完了")
    
    elif choice == "3":
        manager.run_monitoring()
    
    elif choice == "4":
        manager.run_file_organization()
    
    elif choice == "5":
        manager.run_duplicate_detection()
    
    elif choice == "6":
        manager.run_daily_maintenance()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

