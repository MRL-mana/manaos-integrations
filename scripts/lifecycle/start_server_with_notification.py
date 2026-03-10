"""
manaOS統合APIサーバー起動（起動通知付き）
"""

import sys
import os
import subprocess
import threading
from pathlib import Path

# Windows環境でのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))


def send_startup_notification_async():
    """起動通知を非同期で送信"""
    def notification_thread():
        import time
        # サーバー起動を少し待つ
        time.sleep(10)
        
        try:
            from startup_notification import send_startup_report
            send_startup_report()
        except Exception as e:
            print(f"起動通知エラー: {e}")
    
    thread = threading.Thread(target=notification_thread, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    print("=" * 60)
    print("manaOS拡張フェーズ 統合APIサーバー起動（起動通知付き）")
    print("=" * 60)
    
    # 起動通知を非同期で開始
    notification_thread = send_startup_notification_async()
    
    # サーバーを起動
    try:
        from unified_api_server import app, start_initialization_background  # type: ignore[attr-defined]
        
        # 初期化をバックグラウンドで開始
        print("\n統合システムをバックグラウンドで初期化中...")
        init_thread = start_initialization_background()
        
        # ポートとホストを取得
        port = int(os.getenv("MANAOS_INTEGRATION_PORT", 9502))
        host = os.getenv("MANAOS_INTEGRATION_HOST", "127.0.0.1")
        
        print(f"\nサーバー起動: http://{host}:{port}")
        print(f"ローカル: http://127.0.0.1:{port}")
        print("\n利用可能なエンドポイント:")
        print("  GET  /health - ヘルスチェック（軽量：プロセス生存のみ）")
        print("  GET  /ready - レディネスチェック（初期化完了確認）")
        print("  GET  /status - 初期化進捗ステータス")
        print("\n" + "=" * 60)
        print("サーバーを起動します...")
        print("初期化はバックグラウンドで進行中です")
        print("起動完了時にSlackに通知が送信されます")
        print("停止するには Ctrl+C を押してください")
        print("=" * 60)
        
        app.run(host=host, port=port, debug=True)
    
    except KeyboardInterrupt:
        print("\n\nサーバーを停止しました")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()













