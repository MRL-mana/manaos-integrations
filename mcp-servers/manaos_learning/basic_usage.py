#!/usr/bin/env python3
"""
ManaOS 共通学習レイヤー - 基本的な使い方の例
"""

import sys
sys.path.insert(0, '/root')

from manaos_learning import (
    get_learning_api,  # type: ignore[attr-defined]
    register_correction,  # type: ignore[attr-defined]
    suggest_improvement,  # type: ignore[attr-defined]
    apply_rules  # type: ignore[attr-defined]
)


def example_register_correction():
    """修正履歴を登録する例"""
    print("=== 修正履歴の登録 ===")

    log_id = register_correction(
        tool="pdf_excel",
        input_data="PDFから抽出したテキスト: 1;200円",
        raw_output="1;200",  # 修正前（セミコロンが混じってる）
        corrected_output="1,200",  # 修正後（カンマに修正）
        feedback="good",
        tags=["金額", "数値修正"],
        meta={"user": "mana", "source": "test"}
    )

    print(f"✅ ログID: {log_id}")


def example_apply_rules():
    """共通ルールを適用する例"""
    print("\n=== 共通ルールの適用 ===")

    test_cases = [
        "1;200",  # セミコロン → カンマ
        "Ｏ",      # 全角O
        "　",      # 全角スペース
        "R7.11.24"  # 令和日付
    ]

    for text in test_cases:
        fixed = apply_rules(text, "pdf_excel")
        print(f"  {text} → {fixed}")


def example_suggest_improvement():
    """改善案を提案してもらう例"""
    print("\n=== 改善案の提案 ===")

    improvement = suggest_improvement(
        tool="pdf_excel",
        input_text="PDFから抽出: 売上 1;200円",
        raw_output="1;200",
        task="amount_fix"
    )

    if improvement:
        print(f"💡 改善案: {improvement}")
    else:
        print("⚠️  Oollamaが利用できないか、改善案が生成できませんでした")


def example_get_statistics():
    """統計情報を取得する例"""
    print("\n=== 統計情報 ===")

    api = get_learning_api()
    stats = api.get_statistics(tool="pdf_excel")

    print(f"総数: {stats['total']}")
    print(f"成功: {stats['good']}")
    print(f"失敗: {stats['bad']}")
    print(f"要レビュー: {stats['needs_review']}")


def example_get_best_examples():
    """過去の成功事例を取得する例"""
    print("\n=== 成功事例の取得 ===")

    api = get_learning_api()
    examples = api.get_best_examples(
        tool="pdf_excel",
        task="amount_fix",
        limit=3
    )

    for i, example in enumerate(examples, 1):
        print(f"\n事例{i}:")
        print(f"  入力: {example['input'][:50]}...")
        print(f"  修正前: {example['raw_output'][:50]}...")
        print(f"  修正後: {example['corrected_output'][:50]}...")


if __name__ == "__main__":
    print("🧠 ManaOS 共通学習レイヤー - 使用例\n")

    # 各例を実行
    example_register_correction()
    example_apply_rules()
    example_suggest_improvement()
    example_get_statistics()
    example_get_best_examples()

    print("\n✅ 完了！")









