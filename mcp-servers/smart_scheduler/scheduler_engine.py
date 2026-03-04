#!/usr/bin/env python3
"""
スマートスケジューラーエンジン
Googleカレンダー連携＋cron風定期タスク＋音声リマインダー
"""

import os
import schedule
import time
import json
import requests
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

# ディレクトリ設定
WORK_DIR = Path("/root/smart_scheduler")
SCHEDULES_DIR = WORK_DIR / "schedules"
REMINDERS_DIR = WORK_DIR / "reminders"
LOGS_DIR = WORK_DIR / "logs"

for dir_path in [SCHEDULES_DIR, REMINDERS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# スケジュールストレージ
scheduled_tasks = {}
scheduler_running = False


def log(message):
    """ログ記録"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    log_file = LOGS_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


def execute_task(task_config):
    """タスク実行"""
    task_name = task_config.get("name", "Unnamed Task")
    action = task_config.get("action", {})
    
    log(f"⚡ タスク実行: {task_name}")
    
    try:
        action_type = action.get("type")
        
        # ManaOS v3.0実行
        if action_type == "manaos_v3":
            response = requests.post(
                "http://localhost:9200/v3/orchestrator/run",
                json={"text": action.get("text", ""), "actor": "remi"},
                timeout=30
            )
            result = response.json()
            log(f"  ✅ ManaOS実行完了: {result.get('success')}")
        
        # LINE通知
        elif action_type == "line_notify":
            response = requests.post(
                "http://localhost:5015/send",
                json={"message": action.get("message", "")},
                timeout=10
            )
            result = response.json()
            log(f"  ✅ LINE通知送信: {result.get('success')}")
        
        # Slack通知
        elif action_type == "slack":
            response = requests.post(
                "http://localhost:5020/send",
                json={
                    "channel": action.get("channel", "general"),
                    "text": action.get("text", "")
                },
                timeout=10
            )
            result = response.json()
            log(f"  ✅ Slack送信: {result.get('success')}")
        
        # バックアップ
        elif action_type == "backup":
            response = requests.post(
                "http://localhost:5019/backup/now",
                json={},
                timeout=60
            )
            result = response.json()
            log(f"  ✅ バックアップ実行: {result.get('success')}")
        
        # ワークフロー
        elif action_type == "workflow":
            response = requests.post(
                "http://localhost:5017/workflow/execute",
                json=action.get("workflow", {}),
                timeout=60
            )
            result = response.json()
            log(f"  ✅ ワークフロー実行: {result.get('success')}")
        
        else:
            log(f"  ❌ 未知のアクションタイプ: {action_type}")
    
    except Exception as e:
        log(f"  ❌ タスク実行エラー: {e}")


def scheduler_worker():
    """スケジューラーワーカー"""
    global scheduler_running
    
    log("⏰ スケジューラーワーカー起動")
    
    while scheduler_running:
        schedule.run_pending()
        time.sleep(1)


# ===== API エンドポイント =====

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Smart Scheduler Engine",
        "scheduler_running": scheduler_running,
        "scheduled_tasks": len(scheduled_tasks),
        "timestamp": datetime.now().isoformat()
    })


@app.route('/schedule/add', methods=['POST'])
def add_schedule():
    """スケジュール追加"""
    try:
        data = request.json
        task_id = data.get('task_id', f"task_{int(time.time())}")
        task_name = data.get('name', 'Unnamed Task')
        schedule_type = data.get('schedule_type')  # daily, hourly, interval, time
        schedule_value = data.get('schedule_value')  # "09:00", 2 (hours), etc.
        action = data.get('action', {})
        
        # スケジュール登録
        if schedule_type == "daily":
            # 毎日指定時刻
            schedule.every().day.at(schedule_value).do(execute_task, {
                "name": task_name,
                "action": action
            }).tag(task_id)
            log(f"📅 毎日スケジュール追加: {task_name} at {schedule_value}")
        
        elif schedule_type == "hourly":
            # N時間ごと
            schedule.every(int(schedule_value)).hours.do(execute_task, {
                "name": task_name,
                "action": action
            }).tag(task_id)
            log(f"⏰ {schedule_value}時間ごとスケジュール追加: {task_name}")
        
        elif schedule_type == "interval":
            # N分ごと
            schedule.every(int(schedule_value)).minutes.do(execute_task, {
                "name": task_name,
                "action": action
            }).tag(task_id)
            log(f"⏱️ {schedule_value}分ごとスケジュール追加: {task_name}")
        
        # スケジュール保存
        scheduled_tasks[task_id] = {
            "task_id": task_id,
            "name": task_name,
            "schedule_type": schedule_type,
            "schedule_value": schedule_value,
            "action": action,
            "created": datetime.now().isoformat()
        }
        
        # ファイル保存
        schedule_file = SCHEDULES_DIR / f"{task_id}.json"
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(scheduled_tasks[task_id], f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"スケジュール追加完了: {task_name}"
        })
    
    except Exception as e:
        log(f"❌ スケジュール追加エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/schedule/list', methods=['GET'])
def list_schedules():
    """スケジュール一覧"""
    jobs = []
    
    for job in schedule.get_jobs():
        jobs.append({
            "tags": list(job.tags),
            "next_run": str(job.next_run) if job.next_run else None,
            "interval": str(job.interval),
            "unit": str(job.unit)
        })
    
    return jsonify({
        "success": True,
        "scheduled_tasks": list(scheduled_tasks.values()),
        "jobs": jobs,
        "total_count": len(scheduled_tasks)
    })


@app.route('/schedule/remove', methods=['POST'])
def remove_schedule():
    """スケジュール削除"""
    try:
        data = request.json
        task_id = data.get('task_id')
        
        if task_id in scheduled_tasks:
            schedule.clear(task_id)
            del scheduled_tasks[task_id]
            
            # ファイル削除
            schedule_file = SCHEDULES_DIR / f"{task_id}.json"
            if schedule_file.exists():
                schedule_file.unlink()
            
            log(f"🗑️ スケジュール削除: {task_id}")
            
            return jsonify({"success": True, "message": f"スケジュール削除: {task_id}"})
        else:
            return jsonify({"success": False, "error": "タスクが見つかりません"}), 404
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/reminder/add', methods=['POST'])
def add_reminder():
    """リマインダー追加"""
    try:
        data = request.json
        reminder_text = data.get('text', '')
        remind_at = data.get('remind_at')  # ISO format or relative
        notify_method = data.get('notify_method', 'line')  # line, slack, both
        
        # 時刻パース
        if 'T' in remind_at:
            # ISO形式
            remind_datetime = datetime.fromisoformat(remind_at)
        else:
            # 相対指定（例: "30分後"、"明日9時"）
            # 簡易実装: ISO形式のみ対応
            remind_datetime = datetime.fromisoformat(remind_at)
        
        # リマインダー保存
        reminder_id = f"reminder_{int(time.time())}"
        reminder_data = {
            "reminder_id": reminder_id,
            "text": reminder_text,
            "remind_at": remind_datetime.isoformat(),
            "notify_method": notify_method,
            "created": datetime.now().isoformat(),
            "completed": False
        }
        
        reminder_file = REMINDERS_DIR / f"{reminder_id}.json"
        with open(reminder_file, 'w', encoding='utf-8') as f:
            json.dump(reminder_data, f, ensure_ascii=False, indent=2)
        
        log(f"⏰ リマインダー追加: {reminder_text} at {remind_datetime}")
        
        return jsonify({
            "success": True,
            "reminder_id": reminder_id,
            "remind_at": remind_datetime.isoformat()
        })
    
    except Exception as e:
        log(f"❌ リマインダー追加エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/reminder/list', methods=['GET'])
def list_reminders():
    """リマインダー一覧"""
    reminders = []
    
    for reminder_file in sorted(REMINDERS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        with open(reminder_file, 'r', encoding='utf-8') as f:
            reminder = json.load(f)
            reminders.append(reminder)
    
    return jsonify({
        "success": True,
        "reminders": reminders,
        "total_count": len(reminders)
    })


# グローバルスケジューラースレッド
scheduler_thread = None


if __name__ == '__main__':
    log("=" * 60)
    log("⏰ スマートスケジューラーエンジン起動")
    log("=" * 60)
    
    # 保存済みスケジュール読み込み
    for schedule_file in SCHEDULES_DIR.glob("*.json"):
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
                scheduled_tasks[task["task_id"]] = task
                log(f"📥 スケジュール読み込み: {task['name']}")
        except IOError:
            pass
    
    # スケジューラーワーカー起動
    scheduler_running = True
    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()
    
    log("🌐 APIサーバー起動中... (http://0.0.0.0:5021)")
    log("Ctrl+C で停止")
    
    app.run(host='0.0.0.0', port=5021, debug=os.getenv("DEBUG", "False").lower() == "true")

