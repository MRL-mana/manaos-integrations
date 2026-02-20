#!/usr/bin/env python3
"""Google API 認証 - ブラウザURLを提示しない対話式認証"""

import sys
from pathlib import Path

# ManaOS統合モジュールパスを追加
sys.path.insert(0, str(Path(__file__).parent))

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║        Google Cloud API スコープ再認証 - 新権限で有効化                      ║
╚════════════════════════════════════════════════════════════════════════════╝

🔐 Authorization Process:

認証を開始します...
- Calendar API スコープ
- Tasks API スコープ
- Sheets API スコープ
- Keep API スコープ（既定では無効 / 任意）

⏳ ブラウザが開きます...

""")

import os
os.chdir(Path(__file__).parent)

try:
    # 古い token.json を確認
    token_path = Path("token.json")
    if token_path.exists():
        token_path.unlink()
        print("✅ 古いトークンを削除しました")
    
    # GoogleProductivityIntegration의 초기화
    # これにより、新しいスコープで認証フロー が開始される
    from google_calendar_tasks_sheets_integration import GoogleProductivityIntegration
    
    gp = GoogleProductivityIntegration(
        credentials_path="credentials.json",
        token_path="token.json"
    )
    gp.is_available()
    
    print("\n✅ 認証プロセスが完了しました！")
    
    # トークンの確認
    if token_path.exists():
        print(f"\n📄 新しいトークンが生成されました:")
        print(f"   位置: {token_path.absolute()}")
        
        from datetime import datetime
        mtime = token_path.stat().st_mtime
        print(f"   生成日時: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 状態確認
        print(f"\n📊 統合状態:")
        print(f"   利用可能: {gp.is_available()}")
        
        print(f"\n\n🎯 次のステップ:")
        print(f"   テストコマンド: python .\\test_google_productivity.py")
        print(f"\n")
    else:
        print("⚠️  トークンが生成されません")
        print("   ブラウザでの認証が成功しなかった可能性があります")
        sys.exit(1)

except Exception as e:
    import traceback
    print(f"\n❌ エラー: {e}")
    print("\n詳細:")
    traceback.print_exc()
    
    print("\n💡 確認項目:")
    print("  1. Google Cloud Console で以下がすべて有効化されているか:")
    print("     - Google Calendar API")
    print("     - Google Tasks API")
    print("  2. OAuth 同意画面で以下のスコープが追加されているか:")
    print("     - https://www.googleapis.com/auth/calendar")
    print("     - https://www.googleapis.com/auth/tasks")
    print("     - https://www.googleapis.com/auth/spreadsheets")
    print("  3. Keep を使う場合のみ以下を追加:")
    print("     - https://www.googleapis.com/auth/keep")
    print("     - 環境変数 MANAOS_ENABLE_GOOGLE_KEEP=true")
    print("  4. credentials.json が正しく配置されているか")
    
    sys.exit(1)
