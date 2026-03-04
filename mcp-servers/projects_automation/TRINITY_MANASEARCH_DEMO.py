#!/usr/bin/env python3
"""
🤖 トリニティがManaSearch Nexusを使うデモ
Remi, Luna, Minaが実際に情報検索する例
"""
import sys
sys.path.append('/root')
from manasearch_helper import manasearch_sync

print("\n" + "🤖 " + "=" * 66)
print("   トリニティがManaSearch Nexusを使うデモ")
print("=" * 70)
print()

# Remiのユースケース: 戦略立案のための情報収集
print("【Remi（戦略指令AI）の使い方】")
print("-" * 70)
print("シナリオ: 新しい技術の導入を検討中")
print()

remi_query = "FastAPI vs Flask 2025年の選択"
print(f"Remiが調査: 「{remi_query}」")
result = manasearch_sync(remi_query, use_web=True, models=["mina"])

print(f"✅ 信頼スコア: {result['confidence_score']:.0%}")
print("📝 統合回答（抜粋）:")
print(result['summary'][:250] + "...")
print()
print("→ Remiはこの情報を元に戦略を立案します")
print()

# Lunaのユースケース: 実務判断のための検証
print("【Luna（実務遂行AI）の使い方】")
print("-" * 70)
print("シナリオ: タスク管理ツールの選定")
print()

luna_query = "おすすめのタスク管理ツール 2025"
print(f"Lunaが検証: 「{luna_query}」")
result = manasearch_sync(luna_query, use_web=True, models=["mina"])

print(f"✅ 信頼スコア: {result['confidence_score']:.0%}")
print("📝 Gemini推奨:")
if 'mina' in result['ai_responses'] and not result['ai_responses']['mina'].get('error'):
    print(result['ai_responses']['mina']['answer'][:200] + "...")
print()
print("→ Lunaはこの情報を元に実務判断します")
print()

# Minaのユースケース: 記録前の事実確認
print("【Mina（洞察記録AI）の使い方】")
print("-" * 70)
print("シナリオ: 記録する前に事実を確認")
print()

mina_query = "Pythonの最新バージョン"
print(f"Minaが確認: 「{mina_query}」")
result = manasearch_sync(mina_query, use_web=True, models=["mina"])

print(f"✅ 信頼スコア: {result['confidence_score']:.0%}")
web_count = len(result.get('web_results', []))
print(f"🌐 Web検索結果: {web_count}件で裏付け確認")
print()
print("→ Minaは確認済みの正確な情報を記録します")
print()

print("=" * 70)
print("✅ トリニティ全員がManaSearch Nexusを活用できます！")
print("=" * 70)
print()
print("💡 ポイント:")
print("  - Remi: 戦略立案のための情報収集")
print("  - Luna: 実務判断のための検証")
print("  - Mina: 記録前の事実確認")
print()
print("各トリニティが自分の役割に応じて、")
print("ManaSearch Nexusで情報を収集・検証できます！")
print()


