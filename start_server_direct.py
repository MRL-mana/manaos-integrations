"""
manaOS統合APIサーバー起動（直接起動版）
Windows環境で確実に起動するためのスクリプト
"""
import sys
import os
from pathlib import Path

# Windows環境でのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("=" * 60)
    print("manaOS拡張フェーズ 統合APIサーバー起動（直接起動版）")
    print("=" * 60)
    
    try:
        from unified_api_server import app, start_initialization_background
        
        # 初期化をバックグラウンドで開始
        print("\n統合システムをバックグラウンドで初期化中...")
        init_thread = start_initialization_background()
        
        # ポートとホストを取得
        port = int(os.getenv("MANAOS_INTEGRATION_PORT", 9500))
        host = os.getenv("MANAOS_INTEGRATION_HOST", "127.0.0.1")  # ローカルホストに変更
        
        print(f"\nサーバー起動: http://{host}:{port}")
        print(f"ローカル: http://127.0.0.1:{port}")
        print("\n利用可能なエンドポイント:")
        print("  GET  /health - ヘルスチェック（軽量：プロセス生存のみ）")
        print("  GET  /ready - レディネスチェック（初期化完了確認）")
        print("  GET  /status - 初期化進捗ステータス")
        print("\n" + "=" * 60)
        print("サーバーを起動します...")
        print("初期化はバックグラウンドで進行中です")
        print("停止するには Ctrl+C を押してください")
        print("=" * 60)
        
        # Flaskのデバッグモードを無効にして、より安定に
        app.run(host=host, port=port, debug=False, use_reloader=False)
    
    except KeyboardInterrupt:
        print("\n\nサーバーを停止しました")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()











