#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルのOCR結果を超強力に修正
- 複数回のアンサンブル修正
- より積極的な修正パターン
- より大きなモデルを使用
"""

import sys
import os

# Windowsでのエンコーディング処理はバッチファイルでchcp 65001を使用するため削除
# if sys.platform == 'win32':
#     import io
#     sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

from excel_llm_ensemble_corrector import EnsembleOCRCorrector

def ultra_correct(input_file: str, output_file: str, num_ensemble_passes: int = 3, verbose: bool = True):
    """
    超強力な修正処理（複数回のアンサンブル修正）
    
    Args:
        input_file: 入力Excelファイル
        output_file: 出力Excelファイル
        num_ensemble_passes: アンサンブル修正の回数
        verbose: 詳細出力
    """
    print("=" * 60)
    print(f"超強力修正処理（{num_ensemble_passes}回のアンサンブル修正）")
    print("=" * 60)
    
    # 環境変数を設定
    os.environ['USE_LM_STUDIO'] = '1'
    os.environ['MANA_OCR_USE_LARGE_MODEL'] = '1'
    
    current_file = input_file

    # モデル検出・初期化は1回だけ（各パスでの無駄な再検出を防ぐ）
    corrector = EnsembleOCRCorrector()
    
    for pass_num in range(1, num_ensemble_passes + 1):
        print(f"\n{'=' * 60}")
        print(f"【アンサンブル修正パス {pass_num}/{num_ensemble_passes}】")
        print(f"{'=' * 60}")
        
        # 中間ファイル名
        if pass_num < num_ensemble_passes:
            temp_file = output_file.replace('.xlsx', f'_ultra_pass{pass_num}.xlsx')
        else:
            temp_file = output_file
        
        # アンサンブル修正を実行
        result = corrector.correct_excel(
            current_file,
            temp_file,
            verbose=verbose
        )
        
        if result:
            print(f"\n[OK] パス {pass_num} 完了")
            current_file = temp_file
        else:
            print(f"\n[NG] パス {pass_num} 失敗")
            break
    
    print(f"\n{'=' * 60}")
    print("超強力修正処理完了")
    print(f"{'=' * 60}")
    print(f"最終ファイル: {output_file}")
    
    # 中間ファイルを削除
    for pass_num in range(1, num_ensemble_passes):
        temp_file = output_file.replace('.xlsx', f'_ultra_pass{pass_num}.xlsx')
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                if verbose:
                    print(f"  中間ファイル削除: {temp_file}")
            except Exception:
                pass
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ExcelファイルのOCR結果を超強力に修正')
    parser.add_argument('input_file', help='入力Excelファイル')
    parser.add_argument('output_file', help='出力Excelファイル')
    parser.add_argument('--passes', type=int, default=3, help='アンサンブル修正回数（デフォルト: 3）')
    parser.add_argument('--verbose', action='store_true', help='詳細出力')
    
    args = parser.parse_args()
    
    ultra_correct(
        args.input_file,
        args.output_file,
        num_ensemble_passes=args.passes,
        verbose=args.verbose
    )
