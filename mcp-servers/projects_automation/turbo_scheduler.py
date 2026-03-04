#!/usr/bin/env python3
"""
⏰ Turbo Scheduler - 自動タスクスケジューラー
cron不要、YAML設定で簡単スケジューリング
"""

import time
import yaml
import subprocess
from datetime import datetime
from pathlib import Path
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/turbo_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TurboScheduler')

class TurboScheduler:
    def __init__(self, config_file="/root/turbo_schedule.yaml"):
        self.config_file = Path(config_file)
        self.schedules = self.load_schedules()
        self.running = True
        self.last_run = {}
    
    def load_schedules(self):
        """スケジュール読み込み"""
        if not self.config_file.exists():
            self.create_default_schedule()
        
        with open(self.config_file) as f:
            return yaml.safe_load(f)
    
    def create_default_schedule(self):
        """デフォルトスケジュール作成"""
        default = {
            "schedules": [
                {
                    "name": "daily_optimize",
                    "command": "turbo optimize",
                    "interval": "daily",
                    "time": "03:00",
                    "enabled": True
                },
                {
                    "name": "hourly_monitor",
                    "command": "turbo monitor",
                    "interval": "hourly",
                    "enabled": True
                },
                {
                    "name": "daily_backup",
                    "command": "python3 /root/smart_backup.py backup /root/projects",
                    "interval": "daily",
                    "time": "02:00",
                    "enabled": True
                },
                {
                    "name": "every_5min_check",
                    "command": "turbo monitor",
                    "interval": "minutes",
                    "value": 5,
                    "enabled": False
                }
            ]
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(default, f, default_flow_style=False)
        
        logger.info(f"📄 デフォルトスケジュール作成: {self.config_file}")
    
    def should_run(self, schedule):
        """実行すべきか判定"""
        name = schedule["name"]
        interval = schedule["interval"]
        
        # 最終実行時刻
        last = self.last_run.get(name)
        now = datetime.now()
        
        if interval == "hourly":
            # 毎時0分に実行
            if now.minute == 0 and (not last or (now - last).total_seconds() >= 3600):
                return True
        
        elif interval == "daily":
            # 指定時刻に実行
            target_time = schedule.get("time", "00:00")
            hour, minute = map(int, target_time.split(":"))
            
            if now.hour == hour and now.minute == minute and (not last or (now - last).days >= 1):
                return True
        
        elif interval == "minutes":
            # 指定分間隔
            minutes = schedule.get("value", 5)
            if not last or (now - last).total_seconds() >= minutes * 60:
                return True
        
        return False
    
    def run_task(self, schedule):
        """タスク実行"""
        name = schedule["name"]
        command = schedule["command"]
        
        logger.info(f"🚀 実行: {name}")
        logger.info(f"   コマンド: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {name} 成功")
            else:
                logger.error(f"❌ {name} 失敗: {result.stderr[:200]}")
            
            self.last_run[name] = datetime.now()
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ {name} タイムアウト")
        except Exception as e:
            logger.error(f"❌ {name} エラー: {e}")
    
    def run(self):
        """スケジューラー実行"""
        logger.info("=" * 60)
        logger.info("⏰ Turbo Scheduler 起動")
        logger.info("=" * 60)
        logger.info(f"設定ファイル: {self.config_file}")
        logger.info(f"スケジュール数: {len(self.schedules['schedules'])}")
        logger.info("Ctrl+C で停止")
        logger.info("=" * 60)
        
        # 有効なスケジュール表示
        for schedule in self.schedules['schedules']:
            if schedule.get("enabled", True):
                logger.info(f"📅 {schedule['name']}: {schedule['interval']}")
        
        logger.info("=" * 60)
        
        try:
            while self.running:
                # 各スケジュールチェック
                for schedule in self.schedules['schedules']:
                    if not schedule.get("enabled", True):
                        continue
                    
                    if self.should_run(schedule):
                        # 別スレッドで実行（ブロッキング回避）
                        thread = threading.Thread(
                            target=self.run_task,
                            args=(schedule,)
                        )
                        thread.start()
                
                time.sleep(30)  # 30秒ごとにチェック
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ Turbo Scheduler 停止")
            self.running = False

if __name__ == "__main__":
    scheduler = TurboScheduler()
    scheduler.run()

