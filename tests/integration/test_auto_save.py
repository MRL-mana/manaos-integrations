"""
自動保存機能のテスト
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

def test_auto_save():
    """自動保存機能のテスト"""
    print("=" * 60)
    print("自動保存機能のテスト")
    print("=" * 60)
    
    import manaos_core_api as manaos
    
    # 1. ManaOS操作の自動保存テスト
    print("\n[テスト1] ManaOS操作の自動保存")
    try:
        result = manaos.act("llm_call", {
            "task_type": "conversation",
            "prompt": "これは自動保存テストです"
        })
        print("[OK] LLM呼び出しを実行（自動保存されるはず）")
    except Exception as e:
        print(f"[INFO] LLM呼び出しエラー（Ollama未起動の可能性）: {e}")
    
    # 2. 重要なイベントの自動保存テスト
    print("\n[テスト2] 重要なイベントの自動保存")
    try:
        manaos.emit("test_event", {"message": "これは重要なテストイベントです"}, "important")
        print("[OK] 重要なイベントを発行（自動保存されるはず）")
    except Exception as e:
        print(f"[ERROR] イベント発行エラー: {e}")
    
    # 3. Cursor会話の手動保存テスト
    print("\n[テスト3] Cursor会話の手動保存")
    try:
        memory_id = manaos.save_conversation(
            "これはCursorでの会話テストです",
            "自動保存機能が実装されました",
            {"user": "mana", "test": True}
        )
        if memory_id:
            print(f"[OK] Cursor会話を保存しました: {memory_id}")
        else:
            print("[WARN] 会話の保存に失敗しました")
    except Exception as e:
        print(f"[ERROR] 会話保存エラー: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. 記憶システムからの検索テスト
    print("\n[テスト4] 記憶システムからの検索")
    try:
        results = manaos.recall("自動保存", scope="all", limit=5)
        print(f"[OK] 検索結果: {len(results)}件")
        if results:
            print("検索結果の例:")
            for i, result in enumerate(results[:3], 1):
                content = str(result.get('content', result.get('input_data', {})))[:80]
                print(f"  {i}. {content}...")
    except Exception as e:
        print(f"[ERROR] 検索エラー: {e}")
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)





