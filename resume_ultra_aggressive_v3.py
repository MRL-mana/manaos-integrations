#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改善版超積極修正の再開（V3 パス3から継続）
"""

import sys
import os
from pathlib import Path

# リポジトリルートを import パスに追加
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def resume_from_pass3():
    """パス3から継続してパス4、5を実行"""
    print("=" * 60)
    print("改善版超積極修正の再開（V3 パス3から継続）")
    print("=" * 60)
    
    # 環境変数を設定
    os.environ["USE_LM_STUDIO"] = "1"
    os.environ["MANA_OCR_USE_LARGE_MODEL"] = "1"
    os.environ["MANA_ENSEMBLE_MAX_MODELS"] = "1"
    
    # パス3のファイルを確認
    pass3_file = REPO_ROOT / "SKM_TEST_P1_ULTRA_AGGRESSIVE_V3_ultra_pass3.xlsx"
    if not pass3_file.exists():
        print("[NG] パス3のファイルが見つかりません")
        return False
    
    # パス3から継続してパス4、5を実行
    print(f"入力ファイル: {pass3_file.name}")
    print("残りパス: 2パス（パス4、パス5）")
    print("=" * 60)
    
    from excel_llm_ensemble_corrector import EnsembleOCRCorrector
    corrector = EnsembleOCRCorrector()
    
    current_file = str(pass3_file)
    
    # パス4を実行
    pass4_file = REPO_ROOT / "SKM_TEST_P1_ULTRA_AGGRESSIVE_V3_ultra_pass4.xlsx"
    print("\n【パス4実行中...】")
    result4 = corrector.correct_excel(current_file, str(pass4_file), verbose=True)
    
    if not result4:
        print("[NG] パス4失敗")
        return False
    
    print("[OK] パス4完了")
    current_file = str(pass4_file)
    
    # パス5を実行（最終ファイル）
    output_file = REPO_ROOT / "SKM_TEST_P1_ULTRA_AGGRESSIVE_V3.xlsx"
    print("\n【パス5実行中...】")
    result5 = corrector.correct_excel(current_file, str(output_file), verbose=True)
    
    if not result5:
        print("[NG] パス5失敗")
        return False
    
    print("[OK] パス5完了")
    print(f"\n[OK] 全パス完了: {output_file}")
    return True

if __name__ == "__main__":
    resume_from_pass3()
