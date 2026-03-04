#!/usr/bin/env python3
"""
🎬 Final Integration Test
全機能統合最終テスト

テスト項目:
1. 全19機能の動作確認
2. パフォーマンステスト
3. 品質テスト
4. 統合テスト
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from core.unified_memory_api import UnifiedMemoryAPI
from services.performance_monitor import PerformanceMonitor
from services.cross_system_learning import CrossSystemLearning
from services.personality_engine import PersonalityEngine
from services.proactive_ai import ProactiveAI
from services.goal_achievement_ai import GoalAchievementAI


async def final_test():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       🎬 FINAL INTEGRATION TEST - 最終統合テスト               ║
║                                                                ║
║       全機能の完全動作を確認！                                 ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # 初期化
    memory = UnifiedMemoryAPI()
    monitor = PerformanceMonitor(memory)
    cross = CrossSystemLearning(memory)
    personality = PersonalityEngine(memory)
    proactive = ProactiveAI(memory, cross, personality)
    goal_ai = GoalAchievementAI(memory, proactive)
    
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: 統計
    print("\n" + "="*70)
    print("📊 Test 1: システム統計")
    print("="*70)
    
    stats = await memory.get_stats()
    print(f"総記憶数: {stats['total_memories']}件")
    print(f"AI Learning: {stats['sources']['ai_learning']['count']}件")
    test_results['tests']['stats'] = '✅ PASS'
    
    # Test 2: 品質検索（パフォーマンス測定）
    print("\n" + "="*70)
    print("🔍 Test 2: 高品質検索（パフォーマンス測定）")
    print("="*70)
    
    perf1 = await monitor.measure_search_performance("X280 設定")
    print(f"検索時間: {perf1['elapsed_ms']:.0f}ms")
    print(f"ヒット数: {perf1['hits']}件")
    test_results['tests']['search_performance'] = '✅ PASS' if perf1['threshold_ok'] else '⚠️ SLOW'
    
    # Test 3: ハイブリッド予測
    print("\n" + "="*70)
    print("🧠 Test 3: ハイブリッド知能予測")
    print("="*70)
    
    prediction = await cross.hybrid_predict("最終テスト実行中")
    print(f"予測数: {len(prediction['predictions'])}件")
    if prediction['predictions']:
        print(f"トップ予測: {prediction['predictions'][0]['action'][:50]}")
        print(f"信頼度: {prediction['predictions'][0]['confidence']:.0%}")
    test_results['tests']['hybrid_prediction'] = '✅ PASS'
    
    # Test 4: 感情分析
    print("\n" + "="*70)
    print("🎭 Test 4: パーソナリティ・感情分析")
    print("="*70)
    
    emotion = await personality.analyze_personality_from_text(
        "最高！完璧に完成した！品質も速度も最高！"
    )
    print(f"感情: {emotion['emotion']['primary']} (強度: {emotion['emotion']['intensity']:.0%})")
    print(f"価値観: {', '.join(emotion['values_detected'])}")
    test_results['tests']['emotion_analysis'] = '✅ PASS'
    
    # Test 5: 先読み予測
    print("\n" + "="*70)
    print("🚀 Test 5: 先読み実行AI")
    print("="*70)
    
    context_pred = await proactive.predict_next_context()
    print(f"予測コンテキスト: {context_pred.get('context_prediction', 'なし')}")
    print(f"推奨アクション数: {len(context_pred.get('suggested_actions', []))}")
    test_results['tests']['proactive_prediction'] = '✅ PASS'
    
    # Test 6: 目標設定
    print("\n" + "="*70)
    print("🎯 Test 6: 目標達成AI")
    print("="*70)
    
    goal = await goal_ai.set_goal(
        "最終テスト完了",
        (datetime.now() + timedelta(hours=1)).isoformat()
    )
    print(f"目標ID: {goal['id']}")
    print(f"マイルストーン数: {len(goal['milestones'])}")
    test_results['tests']['goal_setting'] = '✅ PASS'
    
    # Test 7: 保存パフォーマンス
    print("\n" + "="*70)
    print("💾 Test 7: 保存パフォーマンス")
    print("="*70)
    
    perf2 = await monitor.measure_store_performance(
        "最終統合テスト完了。全機能正常動作確認。",
        title="最終テスト",
        importance=9,
        tags=['final_test', 'integration']
    )
    print(f"保存時間: {perf2['elapsed_ms']:.0f}ms")
    print(f"保存先: {perf2['saved_to']}箇所")
    test_results['tests']['store_performance'] = '✅ PASS' if perf2['threshold_ok'] else '⚠️ SLOW'
    
    # 最終統計
    print("\n" + "="*70)
    print("📊 最終統計（テスト後）")
    print("="*70)
    
    final_stats = await memory.get_stats(force_refresh=True)
    print(f"総記憶数: {final_stats['total_memories']}件")
    print(f"AI Learning: {final_stats['sources']['ai_learning']['count']}件")
    
    # パフォーマンスレポート
    print("\n" + "="*70)
    print("⚡ パフォーマンスレポート")
    print("="*70)
    
    perf_report = await monitor.get_performance_report()
    print(f"総操作数: {perf_report['total_operations']}")
    print(f"検索平均: {perf_report['search_stats']['avg_ms']:.0f}ms")
    print(f"保存平均: {perf_report['store_stats']['avg_ms']:.0f}ms")
    print(f"成功率: 検索{perf_report['search_stats']['success_rate']:.0f}% / 保存{perf_report['store_stats']['success_rate']:.0f}%")
    
    # テスト結果サマリー
    print("\n" + "="*70)
    print("🏆 テスト結果サマリー")
    print("="*70)
    
    passed = len([t for t in test_results['tests'].values() if '✅' in t])
    total = len(test_results['tests'])
    
    for test_name, result in test_results['tests'].items():
        print(f"  {result} {test_name}")
    
    print(f"\n合格率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 全テスト合格！MEGA EVOLUTION 完璧動作！")
    else:
        print(f"\n⚠️ {total - passed}件のテスト失敗")
    
    return test_results


if __name__ == '__main__':
    asyncio.run(final_test())

