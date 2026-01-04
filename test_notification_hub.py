"""
通知ハブのテスト
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from notification_hub import NotificationHub
import manaos_core_api as manaos


def test_notification_hub():
    """通知ハブのテスト"""
    print("=" * 60)
    print("通知ハブ テスト")
    print("=" * 60)
    
    hub = NotificationHub()
    
    # 1. 通常通知
    print("\n[1] 通常通知（normal）")
    print("-" * 60)
    try:
        results = hub.notify("テスト通知です", priority="normal")
        print(f"✅ 通知送信完了")
        print(f"   Slack: {results.get('slack', False)}")
        print(f"   Discord: {results.get('discord', False)}")
        print(f"   Email: {results.get('email', False)}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 2. 重要通知
    print("\n[2] 重要通知（important）")
    print("-" * 60)
    try:
        results = hub.notify("重要な通知です", priority="important")
        print(f"✅ 通知送信完了")
        print(f"   Slack: {results.get('slack', False)}")
        print(f"   Discord: {results.get('discord', False)}")
        print(f"   Email: {results.get('email', False)}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 3. クリティカル通知
    print("\n[3] クリティカル通知（critical）")
    print("-" * 60)
    try:
        results = hub.notify("緊急通知です", priority="critical")
        print(f"✅ 通知送信完了")
        print(f"   Slack: {results.get('slack', False)}")
        print(f"   Discord: {results.get('discord', False)}")
        print(f"   Email: {results.get('email', False)}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 4. 失敗通知の再送
    print("\n[4] 失敗通知の再送")
    print("-" * 60)
    try:
        stats = hub.retry_failed_notifications(limit=10)
        print(f"✅ 再送完了")
        print(f"   総数: {stats['total']}")
        print(f"   成功: {stats['success']}")
        print(f"   失敗: {stats['failed']}")
    except Exception as e:
        print(f"❌ エラー: {e}")


def test_manaos_core_api_notification():
    """manaOS標準API経由での通知テスト"""
    print("\n" + "=" * 60)
    print("manaOS標準API経由 通知テスト")
    print("=" * 60)
    
    # 1. イベント発行（通知）
    print("\n[1] イベント発行（emit）")
    print("-" * 60)
    try:
        event = manaos.emit("test_event", {"message": "テストイベント"}, "normal")
        print(f"✅ イベント発行: {event['event_id']}")
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    # 通知ハブのテスト
    test_notification_hub()
    
    # manaOS標準API経由のテスト
    test_manaos_core_api_notification()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


















