#!/usr/bin/env python3
"""
神モード統合テスト - 全コンポーネント動作確認
"""

import sys
from pathlib import Path

# パス追加
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_thinking_audit():
    """思考ログ監査システムテスト"""
    print("\n[1/5] 思考ログ監査システム")
    try:
        from god_mode.thinking_audit_system import ThinkingAuditSystem
        
        system = ThinkingAuditSystem()
        session_id = system.start_session("テストタスク")
        
        system.log_thought(
            thought="テスト思考",
            action="test_action",
            result="成功",
            success=True,
            confidence=0.95,
            duration=1.0
        )
        
        analysis = system.end_session("完了", True)
        
        assert analysis['total_steps'] == 1
        assert analysis['success'] == True
        
        print("  ✅ 思考ログ監査システム: OK")
        return True
    except Exception as e:
        print(f"  ❌ 思考ログ監査システム: {e}")
        return False

def test_rag_memory():
    """RAG記憶検索システムテスト"""
    print("\n[2/5] RAG記憶検索システム")
    try:
        from god_mode.rag_memory_system import RAGMemorySystem
        
        system = RAGMemorySystem()
        
        fragment_id = system.store_memory(
            content="テストメモリ: Pythonのデコレータは関数を拡張する",
            category="programming",
            tags=["python", "decorator"],
            importance=0.8
        )
        
        results = system.search("Python デコレータ", limit=3)
        
        assert len(results) > 0
        assert "デコレータ" in results[0]['content']
        
        print("  ✅ RAG記憶検索システム: OK")
        return True
    except Exception as e:
        print(f"  ❌ RAG記憶検索システム: {e}")
        return False

def test_lightweight_monitor():
    """軽量監視システムテスト"""
    print("\n[3/5] 軽量監視システム")
    try:
        from god_mode.lightweight_monitor import LightweightMonitor
        
        monitor = LightweightMonitor()
        status = monitor.get_current_status()
        
        assert 'metrics' in status
        assert 'health_score' in status
        assert 0 <= status['health_score'] <= 100
        
        print(f"  健全性スコア: {status['health_score']}/100")
        print("  ✅ 軽量監視システム: OK")
        return True
    except Exception as e:
        print(f"  ❌ 軽量監視システム: {e}")
        return False

def test_obsidian_sync():
    """Obsidian同期テスト"""
    print("\n[4/5] Obsidian/Notion連携")
    try:
        from god_mode.obsidian_notion_sync import ObsidianSync
        
        sync = ObsidianSync("/root/obsidian_vault_test")
        count = sync.sync_from_manaos()
        
        assert count > 0
        
        print(f"  同期ファイル数: {count}")
        print("  ✅ Obsidian同期: OK")
        return True
    except Exception as e:
        print(f"  ❌ Obsidian同期: {e}")
        return False

def test_predictive_engine():
    """予測的改善エンジンテスト"""
    print("\n[5/5] 予測的改善エンジン")
    try:
        from god_mode.predictive_improvement_engine import PredictiveImprovementEngine
        
        engine = PredictiveImprovementEngine()
        predictions = engine.analyze_trends()
        
        report = engine.generate_report()
        assert report is not None
        
        print(f"  予測数: {len(predictions)}")
        print("  ✅ 予測的改善エンジン: OK")
        return True
    except Exception as e:
        print(f"  ❌ 予測的改善エンジン: {e}")
        return False

def main():
    """メインテスト実行"""
    print("\n" + "=" * 70)
    print("🧪 神モード統合テスト")
    print("=" * 70)
    
    tests = [
        test_thinking_audit,
        test_rag_memory,
        test_lightweight_monitor,
        test_obsidian_sync,
        test_predictive_engine
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ テスト失敗: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("📊 テスト結果")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  合格: {passed}/{total}")
    print(f"  成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n  🎉 全テスト合格！")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed}件のテストが失敗")
        return 1

if __name__ == "__main__":
    exit(main())

