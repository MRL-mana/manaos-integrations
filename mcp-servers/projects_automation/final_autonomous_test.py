#!/usr/bin/env python3
"""完全自律タスクテスト - Computer Use Orchestratorを使用"""
import sys
sys.path.insert(0, '/root')
from manaos_computer_use import ComputerUseOrchestrator  # type: ignore[attr-defined]

print("🚀 ManaOS Computer Use - 完全自律タスクテスト")
print("=" * 60)
print("AI画像認識を使って、自律的にGUI操作を実行します")
print("=" * 60)

# Orchestrator初期化
print("\n📦 Orchestrator初期化中...")
try:
    orchestrator = ComputerUseOrchestrator(vision_provider="claude")
    print("✅ 初期化成功")
except Exception as e:
    print(f"❌ 初期化失敗: {e}")
    sys.exit(1)

# タスク実行
task = """
X280の現在の画面を確認して、何が表示されているか分析してください。
メモ帳が開いていたら、その内容を確認してください。
確認できたら、タスクを完了としてください。
"""

print(f"\n📝 タスク: {task.strip()}")
print("\n🎮 実行開始...")
print("=" * 60)

result = orchestrator.execute_task(
    task=task,
    max_steps=5,  # 少なめに設定
    step_delay=2.0
)

# 結果表示
print("\n" + "=" * 60)
print("📊 実行結果")
print("=" * 60)
print(f"ステータス: {result.status.value}")
print(f"総ステップ数: {result.total_steps}")
print(f"成功率: {result.success_rate * 100:.1f}%")
if result.end_time and result.start_time:
    duration = (result.end_time - result.start_time).total_seconds()
    print(f"実行時間: {duration:.1f}秒")

if result.error_message:
    print(f"エラー: {result.error_message}")

# ステップ詳細
print("\n" + "=" * 60)
print("📋 実行ステップ詳細")
print("=" * 60)
for step in result.steps:
    print(f"\nStep {step.step_number}:")
    if step.ai_analysis:
        print(f"  状態: {step.ai_analysis.current_state}")
        print(f"  アクション: {step.ai_analysis.next_action.action_type.value}")
        print(f"  完了: {step.ai_analysis.is_complete}")
    print(f"  成功: {'✅' if step.success else '❌'}")

print("\n" + "=" * 60)
if result.status.value == "success":
    print("🎊 完全自律タスク実行成功！")
else:
    print(f"⚠️ ステータス: {result.status.value}")
print("=" * 60)


