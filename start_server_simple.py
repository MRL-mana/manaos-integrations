"""
manaOS拡張フェーズ サーバー起動（簡易版）
エンコーディング問題を回避したシンプルな起動スクリプト
"""

import sys
import os
from pathlib import Path

# Windows環境でのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("=" * 60)
    print("manaOS拡張フェーズ 統合APIサーバー起動")
    print("=" * 60)
    
    try:
        from unified_api_server import app, start_initialization_background
        
        # 初期化をバックグラウンドで開始
        print("\n統合システムをバックグラウンドで初期化中...")
        init_thread = start_initialization_background()
        
        # ポートとホストを取得
        port = int(os.getenv("MANAOS_INTEGRATION_PORT", 9510))
        host = os.getenv("MANAOS_INTEGRATION_HOST", "127.0.0.1")
        
        print(f"\nサーバー起動: http://{host}:{port}")
        print(f"ローカル: http://127.0.0.1:{port}")
        print("\n利用可能なエンドポイント:")
        print("  GET  /health - ヘルスチェック（軽量：プロセス生存のみ）")
        print("  GET  /ready - レディネスチェック（初期化完了確認）")
        print("  [拡張フェーズ API]")
        print("  POST /api/llm/route - LLMルーティング")
        print("  POST /api/memory/store - 記憶への保存")
        print("  GET  /api/memory/recall - 記憶からの検索")
        print("  POST /api/notification/send - 通知送信")
        print("  POST /api/secretary/morning - 朝のルーチン")
        print("  POST /api/secretary/noon - 昼のルーチン")
        print("  POST /api/secretary/evening - 夜のルーチン")
        print("  POST /api/image/stock - 画像をストック")
        print("  GET  /api/image/search - 画像検索")
        print("  GET  /api/image/statistics - 画像統計情報")
        print("\n" + "=" * 60)
        print("サーバーを起動します...")
        print("初期化はバックグラウンドで進行中です")
        print("停止するには Ctrl+C を押してください")
        print("=" * 60)
        
        app.run(host=host, port=port, debug=True)
    
    except KeyboardInterrupt:
        print("\n\nサーバーを停止しました")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()






