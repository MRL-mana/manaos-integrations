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
from tools.lm_studio_model_selector import ModelSelectionConfig, select_models

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
                max_models_env = os.getenv("MANA_ENSEMBLE_MAX_MODELS", "").strip()
                try:
                    max_models = int(max_models_env) if max_models_env else 3
                except Exception:
                    max_models = 3
                max_models = max(1, min(max_models, 3))

                cfg = ModelSelectionConfig(
                    preferred_models=[
                        # 速い/安定を先に（ただし精度重視なら32Bを手動で事前ロード推奨）
                        "qwen2.5-coder-7b-instruct",
                        "qwen/qwen2.5-coder-14b-instruct",
                        "openai/gpt-oss-20b",
                        "qwen2.5-coder-32b-instruct",
                        "qwen2.5-coder-14b-instruct",
                    ],
                    skip_substrings=["ggml-org/qwen2.5-coder-14b-instruct"],
                    max_models=max_models,
                )
                models = select_models(cfg)
                if models:
                    for m in models:
                        print(f"アンサンブル用モデル選択（キャッシュ/テスト済み）: {m}")
                    return models[:max_models]
            except:
                pass
        
        # デフォルトモデル
        if not models:
            models = ["qwen2.5-coder-14b-instruct"]
        
        return models

    def _build_col_headers(self, df: pd.DataFrame, top_n: int = 6) -> Dict[int, str]:
        """列ごとに上側から見出しっぽい値を拾う（なければ空）"""
        headers: Dict[int, str] = {}
        n = min(len(df), top_n)
        for col_idx in range(len(df.columns)):
            header = ""
            for r in range(n):
                v = df.iat[r, col_idx]
                if pd.isna(v):
                    continue
                s = str(v).strip()
                if s:
                    header = s[:40]
                    break
            headers[col_idx] = header
        return headers

    def _build_cell_context(self, df: pd.DataFrame, row_idx: int, col_idx: int, col_headers: Dict[int, str]) -> str:
        """近傍・列見出し・行スニペットを短くまとめてLLMに渡す"""
        def _s(v) -> str:
            if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
                return ""
            return str(v).strip()

        left = _s(df.iat[row_idx, col_idx - 1]) if col_idx - 1 >= 0 else ""
        right = _s(df.iat[row_idx, col_idx + 1]) if col_idx + 1 < len(df.columns) else ""
        up = _s(df.iat[row_idx - 1, col_idx]) if row_idx - 1 >= 0 else ""
        down = _s(df.iat[row_idx + 1, col_idx]) if row_idx + 1 < len(df) else ""

        # 行の周辺2セルずつ
        c0 = max(0, col_idx - 2)
        c1 = min(len(df.columns) - 1, col_idx + 2)
        row_snip_vals = []
        for c in range(c0, c1 + 1):
            if c == col_idx:
                continue
            sv = _s(df.iat[row_idx, c])
            if sv:
                row_snip_vals.append(sv[:30])
        row_snip = " | ".join(row_snip_vals[:5])

        header = (col_headers.get(col_idx) or "").strip()

        parts = []
        if header:
            parts.append(f"列: {header}")
        if up:
            parts.append(f"上: {up[:40]}")
        if left:
            parts.append(f"左: {left[:40]}")
        if right:
            parts.append(f"右: {right[:40]}")
        if down:
            parts.append(f"下: {down[:40]}")
        if row_snip:
            parts.append(f"同行: {row_snip}")
        return " / ".join(parts)
    
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

                base_corrector = next(iter(self.correctors.values()))
                col_headers = self._build_col_headers(df, top_n=6)
                
                total_cells = len(df) * len(df.columns)
                corrected_count = 0
                
                # 各セルをアンサンブル修正
                for idx, row in df.iterrows():
                    if verbose and (idx + 1) % 10 == 0:
                        print(f"  行 {idx + 1}/{len(df)} を処理中...")
                    
                    for col_idx, col_name in enumerate(df.columns):
                        cell_value = row[col_name]
                        
                        if pd.isna(cell_value):
                            continue
                        
                        cell_str = str(cell_value)

                        # まず軽量な正規化＆ルール補正（全モデル共通で同じ前処理）
                        cell_norm = base_corrector._normalize_text(cell_str)
                        if cell_norm != cell_str:
                            corrected_df.at[idx, col_name] = cell_norm
                            cell_str = cell_norm
                        fixed = base_corrector._fix_common_ocr_errors(cell_str)
                        if fixed != cell_str:
                            corrected_df.at[idx, col_name] = fixed
                            cell_str = fixed

                        # 数値のみは絶対に触らない（高速化＆事故防止）
                        if base_corrector._looks_numeric(cell_str) and not base_corrector._has_japanese(cell_str):
                            continue

                        # 1文字は効果薄いので基本スキップ（ただし日本語や文字化けっぽいものは対象）
                        if len(cell_str.strip()) < 2 and not base_corrector._has_japanese(cell_str):
                            continue

                        context = self._build_cell_context(df, idx, col_idx, col_headers)
                        
                        # アンサンブル修正
                        corrected = self.correct_cell_ensemble(cell_str, context)
                        if corrected != cell_str:
                            corrected_df.at[idx, col_name] = corrected
                            corrected_count += 1
                
                corrected_data[sheet_name] = corrected_df
                
                if verbose:
                    print(f"  シート '{sheet_name}': {corrected_count}/{total_cells}セル修正")
            
            # 結果を保存
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                for sheet_name, df in corrected_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
            
            print(f"\n[OK] アンサンブル修正完了: {output_file}")
            return True
            
        except Exception as e:
            print(f"\n[NG] エラー: {e}")
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
