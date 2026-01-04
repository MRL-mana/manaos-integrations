"""
ManaOS記憶システムとの接続状況を確認
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

def check_memory_connection():
    """記憶システムとの接続状況を確認"""
    print("=" * 60)
    print("ManaOS記憶システムとの接続確認")
    print("=" * 60)
    
    # 1. UnifiedMemoryのインポート確認
    print("\n[1] UnifiedMemoryのインポート確認")
    try:
        from memory_unified import UnifiedMemory
        print("[OK] UnifiedMemoryをインポートできました")
    except ImportError as e:
        print(f"[ERROR] UnifiedMemoryのインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        return False
    
    # 2. UnifiedMemoryの初期化確認
    print("\n[2] UnifiedMemoryの初期化確認")
    try:
        memory = UnifiedMemory()
        print("[OK] UnifiedMemoryを初期化できました")
        print(f"   Vaultパス: {memory.vault_path}")
        print(f"   キャッシュディレクトリ: {memory.cache_dir}")
    except Exception as e:
        print(f"[ERROR] UnifiedMemoryの初期化エラー: {e}")
        return False
    
    # 3. Obsidian統合の確認
    print("\n[3] Obsidian統合の確認")
    if memory.obsidian:
        if memory.obsidian.is_available():
            print("[OK] Obsidian統合が利用可能です")
            print(f"   Obsidian Vault: {memory.vault_path}")
        else:
            print(f"[WARN] Obsidian Vaultが見つかりません: {memory.vault_path}")
            print("   ローカルキャッシュを使用します")
    else:
        print("[WARN] Obsidian統合が利用できません")
        print("   ローカルキャッシュを使用します")
    
    # 4. LLMRouterとの統合確認
    print("\n[4] LLMRouterとの統合確認")
    try:
        from llm_routing import LLMRouter
        router = LLMRouter()
        
        if router._unified_memory:
            print("[OK] LLMRouterがUnifiedMemoryと接続されています")
            print(f"   記憶システム: {type(router._unified_memory).__name__}")
        else:
            print("[ERROR] LLMRouterがUnifiedMemoryと接続されていません")
            return False
    except Exception as e:
        print(f"[ERROR] LLMRouterの確認エラー: {e}")
        return False
    
    # 5. 実際の保存・読み込みテスト
    print("\n[5] 保存・読み込みテスト")
    try:
        # テストデータを保存
        test_content = {
            "content": "これは接続テストです。ManaOSの記憶システムとの接続を確認しています。",
            "metadata": {
                "test": True,
                "user_id": "test_user"
            }
        }
        
        memory_id = memory.store(test_content, format_type="conversation")
        print(f"[OK] テストデータを保存しました: {memory_id}")
        
        # テストデータを検索
        results = memory.recall("接続テスト", scope="all", limit=1)
        if results:
            print(f"[OK] テストデータを検索できました: {len(results)}件")
            print(f"   内容: {results[0].get('content', '')[:50]}...")
        else:
            print("[WARN] テストデータの検索結果がありません")
        
    except Exception as e:
        print(f"[ERROR] 保存・読み込みテストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("[OK] すべての確認が完了しました")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = check_memory_connection()
    sys.exit(0 if success else 1)

