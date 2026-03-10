#!/usr/bin/env python3
"""
自動パターン抽出の使用例
修正履歴から自動でルールを生成
"""

import sys
sys.path.insert(0, '/root')

from manaos_learning import get_pattern_extractor  # type: ignore[attr-defined]


def example_extract_patterns():
    """パターン抽出の例"""
    print("=== パターン抽出 ===")

    extractor = get_pattern_extractor()

    # PDF→Excelの修正履歴からパターンを抽出
    patterns = extractor.extract_patterns_from_corrections(
        tool="pdf_excel",
        min_occurrences=2,  # 2回以上出現したパターンのみ
        limit=50  # 最新50件を分析
    )

    print(f"抽出されたパターン: {len(patterns)}個\n")

    for i, pattern in enumerate(patterns, 1):
        print(f"パターン{i}:")
        print(f"  タイプ: {pattern['type']}")
        if pattern['type'] == 'replacement':
            print(f"  {pattern['from']} → {pattern['to']}")
            print(f"  出現回数: {pattern['occurrences']}")
        elif pattern['type'] == 'regex':
            print(f"  正規表現: {pattern['regex']}")
            print(f"  置換: {pattern['replace']}")
            print(f"  説明: {pattern['description']}")
            print(f"  出現回数: {pattern['occurrences']}")
        print()


def example_auto_add_rules():
    """自動ルール追加の例（dry_run）"""
    print("\n=== 自動ルール追加（dry_run） ===")

    extractor = get_pattern_extractor()

    # dry_run=True で追加予定のルールを確認
    rules = extractor.auto_add_rules(
        tool="pdf_excel",
        min_occurrences=2,
        dry_run=True  # 実際には追加しない
    )

    print(f"追加予定のルール: {len(rules)}個\n")

    for rule in rules:
        print(f"  - {rule['rule_id']}")
        print(f"    タイプ: {rule['type']}")
        print()


def example_auto_add_rules_real():
    """自動ルール追加の例（実際に追加）"""
    print("\n=== 自動ルール追加（実際に追加） ===")

    extractor = get_pattern_extractor()

    # 実際にルールを追加
    rules = extractor.auto_add_rules(
        tool="pdf_excel",
        min_occurrences=3,  # 3回以上出現したパターンのみ
        dry_run=False  # 実際に追加
    )

    print(f"✅ {len(rules)}個のルールを追加しました")


if __name__ == "__main__":
    print("🔍 ManaOS 自動パターン抽出 - 使用例\n")

    # パターン抽出
    example_extract_patterns()

    # 自動ルール追加（dry_run）
    example_auto_add_rules()

    # 実際に追加する場合は以下をコメントアウト
    # example_auto_add_rules_real()

    print("\n✅ 完了！")









