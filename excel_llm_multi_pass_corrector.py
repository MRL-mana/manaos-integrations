#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルのOCR結果を複数回のLLM修正で改善
複数回の修正処理を繰り返すことで精度を向上
"""

import sys
import os
from pathlib import Path

# Windowsでのエンコーディング設定は削除（バッチファイルで設定）

from excel_llm_ocr_corrector import ExcelLLMOCRCorrector

def multi_pass_correct(input_file: str, output_file: str, num_passes: int = 3, verbose: bool = True):
    """
    複数回の修正処理を実行
    
    Args:
        input_file: 入力Excelファイル
        output_file: 出力Excelファイル
        num_passes: 修正回数（デフォルト: 3回）
        verbose: 詳細出力
    """
    print("=" * 60)
    print(f"複数回修正処理（{num_passes}回）")
    print("=" * 60)
    
    # 環境変数を設定（LM Studio + 大きなモデル）
    os.environ['USE_LM_STUDIO'] = '1'
    os.environ['MANA_OCR_USE_LARGE_MODEL'] = '1'
    
    current_file = input_file
    
    for pass_num in range(1, num_passes + 1):
        print(f"\n{'=' * 60}")
        print(f"【修正パス {pass_num}/{num_passes}】")
        print(f"{'=' * 60}")
        
        # 中間ファイル名
        if pass_num < num_passes:
            temp_file = output_file.replace('.xlsx', f'_pass{pass_num}.xlsx')
        else:
            temp_file = output_file
        
        # 修正処理を実行
        corrector = ExcelLLMOCRCorrector()
        
        result = corrector.correct_excel(
            current_file,
            temp_file,
            verbose=verbose
        )
        
        if result:
            print(f"\n✓ パス {pass_num} 完了")
            print(f"  修正セル数: {corrector.stats.get('corrected_cells', 0)}")
            print(f"  修正率: {corrector.stats.get('corrected_cells', 0) / max(corrector.stats.get('total_cells', 1), 1) * 100:.1f}%")
            
            # 次のパスで使用するファイルを更新
            current_file = temp_file
        else:
            print(f"\n✗ パス {pass_num} 失敗")
            break
    
    print(f"\n{'=' * 60}")
    print("複数回修正処理完了")
    print(f"{'=' * 60}")
    print(f"最終ファイル: {output_file}")
    
    # 中間ファイルを削除
    for pass_num in range(1, num_passes):
        temp_file = output_file.replace('.xlsx', f'_pass{pass_num}.xlsx')
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                if verbose:
                    print(f"  中間ファイル削除: {temp_file}")
            except:
                pass
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ExcelファイルのOCR結果を複数回修正')
    parser.add_argument('input_file', help='入力Excelファイル')
    parser.add_argument('output_file', help='出力Excelファイル')
    parser.add_argument('--passes', type=int, default=3, help='修正回数（デフォルト: 3）')
    parser.add_argument('--verbose', action='store_true', help='詳細出力')
    
    args = parser.parse_args()
    
    multi_pass_correct(
        args.input_file,
        args.output_file,
        num_passes=args.passes,
        verbose=args.verbose
    )
