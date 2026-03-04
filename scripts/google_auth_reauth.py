#!/usr/bin/env python3
"""Google API スコープを非対話モードで再認証"""

import sys
import json
from pathlib import Path
from datetime import datetime

# ManaOS統合モジュールパスを追加
sys.path.insert(0, str(Path(__file__).parent / "manaos_integrations"))

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║           Google API スコープ - ブラウザ認証フロー                           ║
╚════════════════════════════════════════════════════════════════════════════╝

🔐 認証プロセス開始...

以下の URL をブラウザで開いて、Google アカウントでログインしてください:

""")

from google_calendar_tasks_sheets_integration import GoogleProductivityIntegration

try:
    # GoogleProductivityIntegration の初期化
    # これにより、ブラウザが自動的に開く（または手動で開くURLが表示される）
    gp = GoogleProductivityIntegration(
        credentials_path="credentials.json",
        token_path="token.json"
    )
    
    print("\n✅ 認証が完了しました！\n")
    
    # トークンが正常に生成されたか確認
    token_path = Path(__file__).parent / "manaos_integrations" / "token.json"
    if token_path.exists():
        print(f"📄 トークン保存位置: {token_path}")
        print(f"📅 生成日時: {datetime.fromtimestamp(token_path.stat().st_mtime).isoformat()}")
        print()
        
        # 認証状態を確認
        if gp.is_available():
            print("✅ Google 生産性ツール統合は利用可能です")
            print("\n📋 次のコマンドでテストしてください:")
            print("   python .\\test_google_productivity.py")
        else:
            print("❌ 認証完了しましたが、統合が利用不可です")
    else:
        print("⚠️  トークンが生成されません")
        print("   ブラウザでログインが完了していないか、リダイレクトが失敗した可能性があります")
    
except Exception as e:
    print(f"\n❌ 認証エラーが発生しました:\n{e}")
    print("\n💡 解決方法:")
    print("  1. ブラウザが自動的に開かない場合は、上の URL をコピーして手動で開いてください")
    print("  2. Google ログイン後、ManaOS への権限を許可してください")
    print("  3. リダイレクト後のページが表示されます")
    print("  4. コマンドプロンプトに戻ると認証が完了します")
    sys.exit(1)
