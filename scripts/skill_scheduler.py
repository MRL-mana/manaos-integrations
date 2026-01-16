#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills自動スケジューラー
定期的にSkillsを自動実行する
"""

import os
import sys
import json
import time
import schedule
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent
CONFIG_FILE = project_root / "data" / "skill_scheduler_config.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# デフォルト設定
DEFAULT_CONFIG = {
    "enabled": True,
    "tasks": [
        {
            "skill_name": "daily_ops",
            "schedule": "daily",
            "time": "09:00",
            "enabled": True,
            "kwargs": {}
        }
    ]
}


def load_config() -> Dict[str, Any]:
    """設定を読み込む"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  設定ファイルの読み込みエラー: {e}")
    
    # デフォルト設定を保存
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(config: Dict[str, Any]):
    """設定を保存"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def run_scheduled_task(task: Dict[str, Any]):
    """スケジュールされたタスクを実行"""
    skill_name = task.get("skill_name", "")
    kwargs = task.get("kwargs", {})
    
    if not skill_name:
        print("⚠️  skill_nameが指定されていません")
        return
    
    print(f"\n⏰ スケジュール実行: {skill_name} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    
    # auto_skill_runnerを呼び出し
    from auto_skill_runner import auto_run_skill
    success = auto_run_skill(skill_name, **kwargs)
    
    if success:
        print(f"✅ スケジュール実行完了: {skill_name}")
    else:
        print(f"❌ スケジュール実行失敗: {skill_name}")


def setup_scheduler(config: Dict[str, Any]):
    """スケジューラーを設定"""
    if not config.get("enabled", True):
        print("⚠️  スケジューラーが無効です")
        return
    
    tasks = config.get("tasks", [])
    
    for task in tasks:
        if not task.get("enabled", True):
            continue
        
        skill_name = task.get("skill_name", "")
        schedule_type = task.get("schedule", "daily")
        schedule_time = task.get("time", "09:00")
        
        if not skill_name:
            continue
        
        # スケジュールを設定
        if schedule_type == "daily":
            schedule.every().day.at(schedule_time).do(run_scheduled_task, task=task)
            print(f"📅 スケジュール設定: {skill_name} - 毎日 {schedule_time}")
        elif schedule_type == "hourly":
            schedule.every().hour.do(run_scheduled_task, task=task)
            print(f"⏰ スケジュール設定: {skill_name} - 毎時")
        elif schedule_type == "weekly":
            day = task.get("day", "monday")
            schedule_time_obj = schedule.every()
            if day == "monday":
                schedule_time_obj.monday.at(schedule_time).do(run_scheduled_task, task=task)
            elif day == "tuesday":
                schedule_time_obj.tuesday.at(schedule_time).do(run_scheduled_task, task=task)
            # ... 他の曜日も同様
            print(f"📅 スケジュール設定: {skill_name} - 毎週{day} {schedule_time}")


def main():
    """メイン処理"""
    print("🤖 Skills自動スケジューラーを開始します...")
    
    # 設定を読み込み
    config = load_config()
    
    # スケジューラーを設定
    setup_scheduler(config)
    
    print("\n✅ スケジューラー設定完了")
    print("   実行中のタスクを待機しています...")
    print("   Ctrl+Cで停止します\n")
    
    # メインループ
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分ごとにチェック
    except KeyboardInterrupt:
        print("\n\n⏹️  スケジューラーを停止します...")
        sys.exit(0)


if __name__ == "__main__":
    main()
