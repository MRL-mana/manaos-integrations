#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回帰テスト実行スクリプト
"""

import json
import sys
from pathlib import Path

from step_deep_research.orchestrator import StepDeepResearchOrchestrator
from step_deep_research.regression_tests import RegressionTestRunner

# 設定読み込み
config_path = Path("step_deep_research_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# オーケストレーター初期化
orchestrator = StepDeepResearchOrchestrator(config)

# テストランナー初期化
runner = RegressionTestRunner(orchestrator)

# テスト実行
print("=" * 60)
print("回帰テスト実行中...")
print("=" * 60)

summary = runner.run_all_tests()

# 結果表示
print("\n" + "=" * 60)
print("テスト結果サマリー")
print("=" * 60)
print(f"総テスト数: {summary['total_tests']}")
print(f"合格: {summary['passed']}")
print(f"不合格: {summary['failed']}")
print(f"合格率: {summary['pass_rate']:.1%}")

print("\nカテゴリ別結果:")
for category, stats in summary['by_category'].items():
    print(f"  {category}: {stats['passed']}/{stats['total']} ({stats['passed']/stats['total']:.1%})")

print("\n指標:")
metrics = summary['metrics']
print(f"  平均スコア: {metrics['avg_score']:.1f}")
print(f"  平均引用数: {metrics['avg_citations']:.1f}")
print(f"  平均コスト（トークン）: {metrics['avg_cost_tokens']:.0f}")
print(f"  致命エラー率: {metrics['fatal_error_rate']:.1%}")
print(f"  引用カバレッジ: {metrics['citation_coverage']:.1%}")

# 詳細結果
print("\n" + "=" * 60)
print("詳細結果")
print("=" * 60)
for result in summary['results']:
    status = "✅" if result.get("passed", False) else "❌"
    print(f"{status} [{result['test_id']}] {result.get('query', '')[:50]}...")
    if not result.get("passed", False):
        if "error" in result:
            print(f"    エラー: {result['error']}")
        if "validation" in result and result["validation"].get("errors"):
            for error in result["validation"]["errors"]:
                print(f"    検証エラー: {error}")

# 結果をJSONで保存
output_file = Path("logs/step_deep_research/regression_test_results.json")
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"\n結果を保存しました: {output_file}")

# 終了コード
sys.exit(0 if summary['pass_rate'] >= 0.8 else 1)  # 80%以上で合格


