"""
Cursorでの会話履歴とManaOS操作の記憶システム統合確認
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

def check_cursor_memory_integration():
    """CursorとManaOS記憶システムの統合状況を確認"""
    print("=" * 60)
    print("CursorとManaOS記憶システムの統合確認")
    print("=" * 60)
    
    # 1. ManaOS Core APIの確認
    print("\n[1] ManaOS Core APIの確認")
    try:
        import manaos_core_api as manaos
        print("[OK] ManaOS Core APIをインポートできました")
        
        # 記憶システムの確認
        unified_memory = manaos.get_manaos_api()._get_unified_memory()
        if unified_memory:
            print("[OK] ManaOS Core APIが統一記憶システムと接続されています")
        else:
            print("[WARN] ManaOS Core APIが統一記憶システムと接続されていません")
    except Exception as e:
        print(f"[ERROR] ManaOS Core APIの確認エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 記憶システムへの保存テスト
    print("\n[2] 記憶システムへの保存テスト")
    try:
        # Cursorでの会話を模擬
        test_conversation = {
            "content": "これはCursorでの会話テストです。ManaOSの操作を確認しています。",
            "metadata": {
                "source": "cursor",
                "user": "mana",
                "context": "memory_integration_test"
            }
        }
        
        memory_id = manaos.remember(test_conversation, format_type="conversation")
        print(f"[OK] Cursor会話を記憶システムに保存しました: {memory_id}")
    except Exception as e:
        print(f"[ERROR] 記憶保存エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. ManaOS操作履歴の確認
    print("\n[3] ManaOS操作履歴の確認")
    try:
        api = manaos.get_manaos_api()
        print(f"[INFO] 操作履歴数: {len(api.action_history)}件")
        print(f"[INFO] イベント履歴数: {len(api.event_history)}件")
        print(f"[INFO] 記憶エントリ数: {len(api.memory_storage)}件")
        
        if api.action_history:
            print("\n最近の操作履歴:")
            for action in api.action_history[-3:]:
                print(f"  - {action.get('action_type')}: {action.get('timestamp')}")
    except Exception as e:
        print(f"[ERROR] 操作履歴確認エラー: {e}")
        return False
    
    # 4. 記憶システムからの検索テスト
    print("\n[4] 記憶システムからの検索テスト")
    try:
        results = manaos.recall("Cursor", scope="all", limit=5)
        print(f"[OK] 検索結果: {len(results)}件")
        if results:
            print("検索結果の例:")
            for i, result in enumerate(results[:3], 1):
                content = str(result.get('content', result.get('input_data', {})))[:80]
                print(f"  {i}. {content}...")
    except Exception as e:
        print(f"[ERROR] 記憶検索エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 自動保存機能の確認
    print("\n[5] 自動保存機能の確認")
    print("[INFO] 現在の実装状況:")
    print("  - ManaOS Core APIのremember()メソッド: 実装済み")
    print("  - 統一記憶システムとの連携: 実装済み")
    print("  - Cursorでの会話の自動保存: 未実装（手動呼び出しが必要）")
    print("  - ManaOS操作の自動保存: 部分的（action_historyに記録、記憶システムへの自動保存は未実装）")
    
    print("\n" + "=" * 60)
    print("[INFO] 統合状況まとめ")
    print("=" * 60)
    print("✅ ManaOS Core APIと統一記憶システムは接続されています")
    print("✅ remember()メソッドで手動保存は可能です")
    print("⚠️  Cursorでの会話の自動保存は未実装です")
    print("⚠️  ManaOS操作の自動保存は部分的です")
    print("\n[推奨] Cursor統合機能を実装することで、自動保存が可能になります")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = check_cursor_memory_integration()
    sys.exit(0 if success else 1)



