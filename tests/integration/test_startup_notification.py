"""
起動通知のテスト
"""

import sys
import time
import os
import requests
from pathlib import Path

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

# UTF-8エンコーディング設定
sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

BASE_URL = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")


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
















