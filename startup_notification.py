"""
manaOS起動通知スクリプト
サーバー起動時にSlackに通知
"""

import sys
import time
import requests
import os
from pathlib import Path
from datetime import datetime

# 環境変数の読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# 通知システムをインポート
try:
    from notification_system import NotificationSystem
    notification_system = NotificationSystem()
    
    # 環境変数からSlack Webhook URLを取得
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook and not notification_system.slack_webhook_url:
        notification_system.configure_slack(slack_webhook)
except ImportError:
    notification_system = None


def wait_for_ready(max_wait: int = 120, poll_interval: int = 5):
    """サーバーがreadyになるまで待つ"""
    base_url = "http://localhost:9500"
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{base_url}/ready", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        time.sleep(poll_interval)
    
    return None


def send_startup_report():
    """起動レポートを送信"""
    if not notification_system:
        print("通知システムが利用できません")
        return
    
    # readyを待つ
    print("サーバーの初期化完了を待機中...")
    ready_data = wait_for_ready()
    
    if not ready_data:
        message = "⚠️ manaOS統合APIサーバー: 起動しましたが、初期化が完了しませんでした（120秒タイムアウト）"
        notification_system.send_slack(message)
        return
    
    # 起動レポートを生成
    status = ready_data.get("status", "unknown")
    integrations = ready_data.get("integrations", {})
    checks = ready_data.get("readiness_checks", {})
    
    # 利用可能な統合システムをカウント
    available_count = sum(1 for v in integrations.values() if v)
    total_count = len(integrations)
    
    # 必須チェックの状態
    required_checks = ["memory_db", "obsidian_path", "notification_hub", "llm_routing", "image_stock"]
    check_statuses = []
    for check_name in required_checks:
        check = checks.get(check_name, {})
        status_icon = "✅" if check.get("status") == "ok" else "⚠️" if check.get("status") == "warning" else "❌"
        check_statuses.append(f"{status_icon} {check_name}: {check.get('status', 'unknown')}")
    
    # メッセージを生成
    message = f"""🚀 **manaOS統合APIサーバー起動完了**

**ステータス**: {status}
**統合システム**: {available_count}/{total_count} 利用可能

**必須チェック**:
{chr(10).join(check_statuses)}

**起動時刻**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # Slackに送信
    notification_system.send_slack(message)
    print("起動レポートを送信しました")


if __name__ == "__main__":
    send_startup_report()

