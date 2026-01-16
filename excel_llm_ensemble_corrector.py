#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルのOCR結果を複数モデルでアンサンブル修正
複数のLLMモデルで修正して、最良の結果を選択
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

# Windowsでのエンコーディング設定（バッチファイルで設定されるため削除）

from excel_llm_ocr_corrector import ExcelLLMOCRCorrector
from local_llm_helper import generate

class EnsembleOCRCorrector:
    """複数モデルでアンサンブル修正"""
    
    def __init__(self, models: List[str] = None):
        """
        初期化
        
        Args:
            models: 使用するモデルリスト（Noneの場合は自動選択）
        """
        if models is None:
            # 利用可能なモデルを自動検出
            models = self._detect_available_models()
        
        self.models = models
        self.correctors = {}
        for model in models:
            try:
                self.correctors[model] = ExcelLLMOCRCorrector(llm_model=model)
            except Exception as e:
                print(f"  [WARNING] モデル {model} の初期化に失敗: {e}")
        
        if not self.correctors:
            raise ValueError("使用可能なモデルがありません")
        
        print(f"アンサンブル修正: {len(self.correctors)}個のモデルを使用")
        for i, (model, corrector) in enumerate(self.correctors.items(), 1):
            print(f"  {i}. {model}")
    
    def _detect_available_models(self) -> List[str]:
        """利用可能なモデルを自動検出"""
        models = []
        
        # LM Studioが利用可能な場合
        if os.getenv("USE_LM_STUDIO", "0").strip().lower() in ("1", "true", "yes", "y", "on"):
            try:
                import requests
                r = requests.get('http://localhost:1234/v1/models', timeout=5)
                if r.status_code == 200:
                    models_data = r.json().get('data', [])
                    available_models = [model.get('id', '') for model in models_data]
                    
                    # 優先順位順にモデルを選択
                    preferred_models = [
                        "qwen2.5-coder-32b-instruct",
                        "qwen2.5-coder-14b-instruct",
                        "openai/gpt-oss-20b",
                        "qwen2.5-coder-7b-instruct",
                    ]
                    
                    for preferred in preferred_models:
                        for available in available_models:
                            if preferred.lower() in available.lower() or available.lower() in preferred.lower():
                                if available not in models:
                                    models.append(available)
                                break
                    
                    # 最大3モデルまで使用
                    return models[:3]
            except:
                pass
        
        # デフォルトモデル
        if not models:
            models = ["qwen2.5-coder-14b-instruct"]
        
        return models
    
    def correct_cell_ensemble(self, text: str, context: str = "") -> str:
        """
        複数モデルでセルを修正して最良の結果を選択
        
        Args:
            text: 修正するテキスト
            context: 周辺コンテキスト
        
        Returns:
            修正後のテキスト
        """
        if not text or not str(text).strip():
            return text
        
        # 各モデルで修正
        results = {}
        for model_name, corrector in self.correctors.items():
            try:
                corrected = corrector.correct_cell_text(text, context)
                if corrected and corrected != text:
                    results[model_name] = corrected
            except Exception as e:
                print(f"  [WARNING] {model_name}での修正エラー: {e}")
        
        if not results:
            return text
        
        # 最良の結果を選択（最も長い、または最も変更が多い）
        if len(results) == 1:
            return list(results.values())[0]
        
        # 複数の結果がある場合、投票方式で選択
        # 1. 最も多くのモデルが一致した結果
        # 2. 最も長い結果（より詳細な修正）
        # 3. 元のテキストとの差が大きい結果（より積極的な修正）
        
        # 結果の頻度をカウント
        result_counts = {}
        for result in results.values():
            result_counts[result] = result_counts.get(result, 0) + 1
        
        # 最も多く一致した結果を選択
        best_result = max(result_counts.items(), key=lambda x: x[1])[0]
        
        # 同数の場合は、最も長い結果を選択
        if result_counts[best_result] == 1:
            best_result = max(results.values(), key=len)
        
        return best_result
    
    def correct_excel(self, input_file: str, output_file: str, verbose: bool = True) -> bool:
        """
        Excelファイルをアンサンブル修正
        
        Args:
            input_file: 入力Excelファイル
            output_file: 出力Excelファイル
            verbose: 詳細出力
        
        Returns:
            成功したかどうか
        """
        print("=" * 60)
        print("アンサンブル修正処理")
        print("=" * 60)
        print(f"入力ファイル: {input_file}")
        print(f"出力ファイル: {output_file}")
        print(f"使用モデル数: {len(self.models)}")
        
        try:
            # Excelファイルを読み込み
            excel_file = pd.ExcelFile(input_file)
            corrected_data = {}
            
            for sheet_name in excel_file.sheet_names:
                if verbose:
                    print(f"\nシート '{sheet_name}' を処理中...")
                
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                corrected_df = df.copy()
                
                total_cells = len(df) * len(df.columns)
                processed = 0
                
                # 各セルをアンサンブル修正
                for idx, row in df.iterrows():
                    if verbose and (idx + 1) % 10 == 0:
                        print(f"  行 {idx + 1}/{len(df)} を処理中...")
                    
                    # 行のコンテキストを作成
                    row_context = " | ".join([str(val)[:50] for val in row.values[:5] if pd.notna(val)])
                    
                    for col_idx, col_name in enumerate(df.columns):
                        cell_value = row[col_name]
                        
                        if pd.isna(cell_value):
                            continue
                        
                        cell_str = str(cell_value)
                        
                        # アンサンブル修正
                        corrected = self.correct_cell_ensemble(cell_str, row_context)
                        if corrected != cell_str:
                            corrected_df.at[idx, col_name] = corrected
                            processed += 1
                
                corrected_data[sheet_name] = corrected_df
                
                if verbose:
                    print(f"  シート '{sheet_name}': {processed}/{total_cells}セル修正")
            
            # 結果を保存
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for sheet_name, df in corrected_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
            
            print(f"\n✓ アンサンブル修正完了: {output_file}")
            return True
            
        except Exception as e:
            print(f"\n✗ エラー: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ExcelファイルのOCR結果を複数モデルでアンサンブル修正')
    parser.add_argument('input_file', help='入力Excelファイル')
    parser.add_argument('output_file', help='出力Excelファイル')
    parser.add_argument('--models', nargs='+', help='使用するモデルリスト（指定しない場合は自動選択）')
    parser.add_argument('--verbose', action='store_true', help='詳細出力')
    
    args = parser.parse_args()
    
    # 環境変数を設定
    os.environ['USE_LM_STUDIO'] = '1'
    os.environ['MANA_OCR_USE_LARGE_MODEL'] = '1'
    
    corrector = EnsembleOCRCorrector(models=args.models)
    corrector.correct_excel(args.input_file, args.output_file, verbose=args.verbose)

if __name__ == "__main__":
    main()
