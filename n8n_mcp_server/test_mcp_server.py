"""
MCPサーバーの動作確認スクリプト
"""
import sys
import os
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from n8n_mcp_server.server import server, N8N_BASE_URL, N8N_API_KEY
    print("=" * 60)
    print("MCPサーバー 動作確認")
    print("=" * 60)
    print(f"[OK] MCPサーバーモジュールをインポートできました")
    print(f"[OK] N8N_BASE_URL: {N8N_BASE_URL}")
    print(f"[{'OK' if N8N_API_KEY else 'NG'}] N8N_API_KEY: {'設定済み' if N8N_API_KEY else '未設定'}")
    print("=" * 60)
    
    if not N8N_API_KEY:
        print("\n[警告] APIキーが設定されていません")
        print("n8nのWeb UIからAPIキーを取得して設定してください")
        print("1. http://100.93.120.33:5678 にアクセス")
        print("2. Settings → API → Create API Key")
        print("3. 設定ファイルに追加: $env:USERPROFILE\\.cursor\\mcp.json")
    
    print("\n[OK] MCPサーバーは正常にインポートできました")
    
except Exception as e:
    print(f"[NG] エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


















