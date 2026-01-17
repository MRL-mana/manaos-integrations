#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルのOCR結果を超積極的に修正
- より多くの修正パターン
- より詳細なプロンプト
- より多くのパス
- より大きなモデルを使用
"""

import sys
import os
from pathlib import Path

# どのディレクトリから実行しても動くように、リポジトリルートを import パスに追加
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from excel_llm_ultra_corrector import ultra_correct


def ultra_aggressive_correct(input_file: str, output_file: str, num_passes: int = 5, verbose: bool = True):
    """
    超積極的な修正処理（より多くのパスとより大きなモデル）

    Args:
        input_file: 入力Excelファイル
        output_file: 出力Excelファイル
        num_passes: 修正パス数（デフォルト: 5）
        verbose: 詳細出力
    """
    print("=" * 60)
    print(f"超積極的修正処理（{num_passes}回のアンサンブル修正）")
    print("=" * 60)

    # 環境変数を設定（最大のモデルを使用）
    os.environ["USE_LM_STUDIO"] = "1"
    os.environ["MANA_OCR_USE_LARGE_MODEL"] = "1"

    # より多くのパスで超強力修正を実行
    ultra_correct(
        input_file,
        output_file,
        num_ensemble_passes=num_passes,
        verbose=verbose,
    )

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ExcelファイルのOCR結果を超積極的に修正")
    parser.add_argument("input_file", help="入力Excelファイル")
    parser.add_argument("output_file", help="出力Excelファイル")
    parser.add_argument("--passes", type=int, default=5, help="アンサンブル修正回数（デフォルト: 5）")
    parser.add_argument("--verbose", action="store_true", help="詳細出力")

    args = parser.parse_args()

    ultra_aggressive_correct(
        args.input_file,
        args.output_file,
        num_passes=args.passes,
        verbose=args.verbose,
    )

