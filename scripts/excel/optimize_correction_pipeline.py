#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正パイプラインのさらなる最適化
- セル修正のキャッシュ化（同じテキストを複数回修正しない）
- 並列処理の最適化
- より効率的なスキップ条件
"""

import sys
import os
from pathlib import Path
from typing import Dict
import hashlib
import pandas as pd

# どのディレクトリから実行しても動くように、リポジトリルートを import パスに追加
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from excel_llm_ocr_corrector import ExcelLLMOCRCorrector
from excel_llm_ensemble_corrector import EnsembleOCRCorrector


class OptimizedCorrector:
    """最適化された修正器（キャッシュ付き）"""

    def __init__(self, base_corrector):
        """
        初期化

        Args:
            base_corrector: ベースとなる修正器（ExcelLLMOCRCorrectorまたはEnsembleOCRCorrector）
        """
        self.base_corrector = base_corrector
        self.correction_cache: Dict[str, str] = {}  # テキストハッシュ -> 修正後テキスト
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_corrections": 0,
        }

    def _get_text_hash(self, text: str) -> str:
        """テキストのハッシュを取得（キャッシュキー用）"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def correct_cell(self, text: str, context: str = "") -> str:
        """
        セルを修正（キャッシュ付き）

        Args:
            text: 修正するテキスト
            context: 周辺コンテキスト

        Returns:
            修正後のテキスト
        """
        if not text or not str(text).strip():
            return text

        # キャッシュキー生成（テキストのみ、コンテキストは考慮しない）
        text_hash = self._get_text_hash(str(text).strip())

        # キャッシュチェック
        if text_hash in self.correction_cache:
            self.stats["cache_hits"] += 1
            return self.correction_cache[text_hash]

        # キャッシュミス → 実際に修正
        self.stats["cache_misses"] += 1
        self.stats["total_corrections"] += 1

        # ベース修正器で修正
        if isinstance(self.base_corrector, EnsembleOCRCorrector):
            corrected = self.base_corrector.correct_cell_ensemble(text, context)
        else:
            corrected = self.base_corrector.correct_cell_text(text, context)

        # キャッシュに保存（元のテキストと異なる場合のみ）
        if corrected != text:
            self.correction_cache[text_hash] = corrected

        return corrected

    def get_stats(self) -> dict:
        """統計情報を取得"""
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (self.stats["cache_hits"] / total_requests) if total_requests > 0 else 0

        return {
            **self.stats,
            "cache_hit_rate": hit_rate,
            "cache_size": len(self.correction_cache),
        }


def optimize_excel_correction(
    input_file: str,
    output_file: str,
    ensemble: bool = False,
    verbose: bool = True,
):
    """
    Excel修正を最適化して実行

    Args:
        input_file: 入力Excelファイル
        output_file: 出力Excelファイル
        ensemble: アンサンブル修正を使用するか
        verbose: 詳細出力
    """
    if verbose:
        print("=" * 60)
        print("最適化されたExcel修正（キャッシュ付き）")
        print("=" * 60)
        print(f"入力: {input_file}")
        print(f"出力: {output_file}")
        print(f"アンサンブル: {'有効' if ensemble else '無効'}")
        print("=" * 60)

    # ベース修正器を初期化
    if ensemble:
        base_corrector = EnsembleOCRCorrector()
    else:
        base_corrector = ExcelLLMOCRCorrector()

    # 最適化修正器を作成
    optimized = OptimizedCorrector(base_corrector)

    # Excelファイルを読み込み
    df = pd.read_excel(input_file, header=None)
    corrected_df = df.copy()

    total_cells = len(df) * len(df.columns)
    corrected_cells = 0

    # 各セルを修正（キャッシュ付き）
    for idx, row in df.iterrows():
        if verbose and (idx + 1) % 10 == 0:
            stats = optimized.get_stats()
            print(f"  行 {idx + 1}/{len(df)} 処理中... (キャッシュヒット率: {stats['cache_hit_rate']:.1%})")

        for col_idx, col_name in enumerate(df.columns):
            cell_value = row[col_name]
            if pd.isna(cell_value) or cell_value == "":
                continue

            cell_str = str(cell_value)

            # 簡易スキップ条件（明らかに不要なもの）
            if len(cell_str.strip()) < 2:
                continue

            # コンテキスト（簡易）
            row_context = " | ".join(
                [str(val)[:50] for val in row.values[:5] if pd.notna(val)]
            )

            corrected = optimized.correct_cell(cell_str, row_context)
            if corrected != cell_str:
                corrected_df.at[idx, col_name] = corrected
                corrected_cells += 1

    # 保存
    corrected_df.to_excel(output_file, index=False, header=False)

    # 結果表示
    stats = optimized.get_stats()
    if verbose:
        print("\n" + "=" * 60)
        print("修正完了")
        print("=" * 60)
        print(f"総セル数: {total_cells}")
        print(f"修正セル数: {corrected_cells}")
        print(f"キャッシュヒット: {stats['cache_hits']}")
        print(f"キャッシュミス: {stats['cache_misses']}")
        print(f"キャッシュヒット率: {stats['cache_hit_rate']:.1%}")
        print(f"キャッシュサイズ: {stats['cache_size']}")
        print("=" * 60)

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Excel修正パイプラインの最適化（キャッシュ付き）")
    parser.add_argument("input_file", help="入力Excelファイル")
    parser.add_argument("output_file", help="出力Excelファイル")
    parser.add_argument("--ensemble", action="store_true", help="アンサンブル修正を使用")
    parser.add_argument("--verbose", action="store_true", help="詳細出力")

    args = parser.parse_args()

    optimize_excel_correction(
        args.input_file,
        args.output_file,
        ensemble=args.ensemble,
        verbose=args.verbose,
    )

