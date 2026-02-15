"""
起動通知のテスト
"""

import sys
import time
import requests
from pathlib import Path

# UTF-8エンコーディング設定
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:9510"


def test_startup_notification():
    """起動通知をテスト"""
    print("=" * 60)
    print("manaOS起動通知テスト")
    print("=" * 60)
    
    # サーバーが起動しているか確認
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ サーバーが起動していません")
            return False
    except Exception:
        print("❌ サーバーに接続できません")
        return False
    
    print("✅ サーバーは起動しています")
    
    # 起動通知スクリプトを実行
    print("\n起動通知スクリプトを実行中...")
    try:
        from startup_notification import send_startup_report
        send_startup_report()
        print("✅ 起動通知を送信しました")
        return True
    except Exception as e:
        print(f"❌ 起動通知エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_startup_notification()













