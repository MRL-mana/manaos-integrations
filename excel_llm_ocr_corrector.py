#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルのOCR結果をLLMで修正・補完
既存のExcelファイルを読み込んで、LLMで文字化けや誤認識を修正
"""

import sys
import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import re
import unicodedata

# Windowsでのエンコーディング修正
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from local_llm_helper import generate, chat
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("警告: local_llm_helperが見つかりません")


class ExcelLLMOCRCorrector:
    """ExcelファイルのOCR結果をLLMで修正"""
    
    def __init__(
        self,
        llm_model: str = "qwen2.5:7b",
        batch_size: int = 100,  # 一度に処理するセル数
        max_cell_length: int = 500  # セルあたりの最大文字数
    ):
        """
        初期化
        
        Args:
            llm_model: 使用するLLMモデル
            batch_size: バッチ処理サイズ
            max_cell_length: セルあたりの最大文字数
        """
        self.llm_model = llm_model
        self.batch_size = batch_size
        self.max_cell_length = max_cell_length
        self.stats = {
            'total_cells': 0,
            'corrected_cells': 0,
            'skipped_cells': 0
        }

    _CIRCLED_MAP = str.maketrans({
        "①":"1","②":"2","③":"3","④":"4","⑤":"5","⑥":"6","⑦":"7","⑧":"8","⑨":"9","⑩":"10",
        "⑪":"11","⑫":"12","⑬":"13","⑭":"14","⑮":"15","⑯":"16","⑰":"17","⑱":"18","⑲":"19","⑳":"20",
        "㉑":"21","㉒":"22","㉓":"23","㉔":"24","㉕":"25",
    })

    def _normalize_text(self, text: str) -> str:
        """丸数字・全角などを正規化（数字は壊さない）"""
        if text is None:
            return ""
        t = str(text)
        # 全角→半角（可能な範囲）
        t = unicodedata.normalize("NFKC", t)
        # 丸数字→通常数字
        t = t.translate(self._CIRCLED_MAP)
        # 余計な連続空白を整理
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()
    
    # よくあるOCR誤認識パターン（文字化け・文字間違い）
    _OCR_FIX_PATTERNS = [
        # 数字と文字の誤認識（より積極的に）
        (r'\bO\b', '0'),  # 単独のO → 0
        (r'\bl\b', '1'),  # 単独のl → 1
        (r'\bS\b', '5'),  # 単独のS → 5
        (r'\bB\b', '8'),  # 単独のB → 8
        (r'\bI\b', '1'),  # 単独のI → 1
        (r'\bZ\b', '2'),  # 単独のZ → 2
        # よくある文字化けパターン（拡張）
        (r'文宇', '文字'),
        (r'読取', '読取'),
        (r'認識', '認識'),
        (r'文字化け', '文字化け'),
        (r'誤認識', '誤認識'),
        (r'読み取り', '読み取り'),
        # 全角/半角の統一（数字・英字・記号）
        (r'０', '0'), (r'１', '1'), (r'２', '2'), (r'３', '3'), (r'４', '4'),
        (r'５', '5'), (r'６', '6'), (r'７', '7'), (r'８', '8'), (r'９', '9'),
        (r'（', '('), (r'）', ')'), (r'，', ','), (r'．', '.'), (r'：', ':'),
        (r'；', ';'), (r'？', '?'), (r'！', '!'), (r'ー', '-'), (r'～', '~'),
        # よくある誤認識パターン
        (r'ハイオク', 'ハイオク'),
        (r'レギュラー', 'レギュラー'),
        (r'軽油', '軽油'),
        (r'数量', '数量'),
        (r'金額', '金額'),
        (r'合計', '合計'),
    ]
    
    def _fix_common_ocr_errors(self, text: str) -> str:
        """よくあるOCR誤認識を自動修正"""
        if not text:
            return text
        t = str(text)
        # パターンマッチで修正（ただし、文脈を考慮して慎重に）
        for pattern, replacement in self._OCR_FIX_PATTERNS:
            # 単独の文字のみ（単語境界で囲まれた場合）
            if pattern.startswith(r'\b') and pattern.endswith(r'\b'):
                # 数字の前後が数字や記号でない場合のみ置換
                t = re.sub(pattern, replacement, t)
            else:
                t = re.sub(pattern, replacement, t)
        return t

    def _looks_numeric(self, s: str) -> bool:
        """数値っぽい（ここは絶対にLLMで触らない）"""
        s = s.strip()
        if not s:
            return True
        # カンマ・小数点・括弧・% を許容して数値判定
        s2 = s.replace(",", "").replace(" ", "")
        s2 = s2.replace("(", "").replace(")", "").replace("%", "")
        s2 = s2.replace("－", "-")
        return bool(re.fullmatch(r"[-+]?\d+(\.\d+)?", s2))

    def _has_japanese(self, s: str) -> bool:
        return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", s))
    
    def correct_cell_text(self, text: str, context: str = "") -> Optional[str]:
        """
        セルのテキストをLLMで修正
        
        Args:
            text: 修正するテキスト
            context: 周辺コンテキスト（同じ行・列の情報）
        """
        if not text or not str(text).strip():
            return text

        # まず正規化（丸数字→数字、全角→半角など）
        normalized = self._normalize_text(str(text))
        if normalized != str(text):
            text = normalized
        
        # よくあるOCR誤認識を自動修正
        fixed = self._fix_common_ocr_errors(text)
        if fixed != text:
            text = fixed
        
        # 数値セルは絶対に触らない
        if self._looks_numeric(text):
            self.stats['skipped_cells'] += 1
            return text

        # 文字化けがある場合は修正対象（日本語がなくても）
        has_mojibake = '' in text or len([c for c in text if ord(c) > 0xFFFF]) > 0
        if not self._has_japanese(text) and not has_mojibake:
            # 日本語も文字化けもない場合はスキップ
            self.stats['skipped_cells'] += 1
            return text

        # 長すぎる場合は切り詰め
        if len(text) > self.max_cell_length:
            text = text[:self.max_cell_length]
        
        context_prefix = f"周辺コンテキスト: {context}\n" if context else ""

        prompt = f"""以下のOCR（光学文字認識）結果を修正してください。

OCR結果には以下の問題がある可能性があります：
- 文字化け（例: "文字" → "文宇"、"0" → "O"、"1" → "l"、"5" → "S"）
- 読み取り不足（空白や改行の誤認識）
- 数字や記号の誤認識（例: "1" → "l"、"5" → "S"、"0" → "O"、"8" → "B"）
- 日本語と英語の混在による誤認識
- 似た文字の誤認識（例: "O"と"0"、"1"と"l"、"5"と"S"）

{context_prefix}OCR結果:
{text}

修正指示:
1. 明らかな誤字・脱字を積極的に修正してください
2. 文脈から推測できる正しい文字に修正してください（特に数字・記号）
3. 数字や記号は正確に保持してください（特に数値データ、金額、数量）
4. 似た文字の誤認識を修正してください（O/0、1/l、5/S、8/Bなど）
5. 元の形式（空白、改行）は可能な限り保持してください
6. 修正できない部分はそのまま残してください
7. 修正が不要な場合は元のテキストをそのまま返してください

修正後のテキストのみを返してください（説明やJSON形式は不要）:"""
        
        try:
            result = generate(self.llm_model, prompt, timeout=30)
            if result and result.get('response'):
                corrected = result['response'].strip()
                
                # プロンプトの繰り返しや説明を削除
                lines = corrected.split('\n')
                # 最初の実質的なテキスト行を取得
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('修正') and not line.startswith('OCR'):
                        corrected = line
                        break
                
                # 元のテキストと異なる場合のみ修正としてカウント
                if corrected != text:
                    self.stats['corrected_cells'] += 1
                    return corrected
                else:
                    return text
        except Exception as e:
            print(f"  [WARNING] LLM修正エラー: {e}")
        
        return text
    
    def correct_sheet(self, df: pd.DataFrame, sheet_name: str, verbose: bool = True) -> pd.DataFrame:
        """
        シート全体を修正
        
        Args:
            df: データフレーム
            sheet_name: シート名
            verbose: 詳細出力
        """
        if verbose:
            print(f"  シート '{sheet_name}': {len(df)}行 × {len(df.columns)}列を処理中...")
        
        corrected_df = df.copy()
        total_cells = len(df) * len(df.columns)
        processed = 0
        
        # 行ごとに処理（コンテキストを保持）
        for idx, row in df.iterrows():
            if verbose and (idx + 1) % 10 == 0:
                print(f"    行 {idx + 1}/{len(df)} を処理中...")
            
            # 行のコンテキストを作成
            row_context = " | ".join([str(val)[:50] for val in row.values[:5] if pd.notna(val)])
            
            for col_idx, col_name in enumerate(df.columns):
                cell_value = row[col_name]
                
                # 空セルや数値のみのセルはスキップ
                if pd.isna(cell_value):
                    continue
                
                cell_str = str(cell_value)
                
                # 正規化
                cell_str_norm = self._normalize_text(cell_str)
                if cell_str_norm != cell_str:
                    corrected_df.at[idx, col_name] = cell_str_norm
                    cell_str = cell_str_norm
                
                # よくあるOCR誤認識を自動修正（ルールベース）
                fixed = self._fix_common_ocr_errors(cell_str)
                if fixed != cell_str:
                    corrected_df.at[idx, col_name] = fixed
                    cell_str = fixed
                    self.stats['corrected_cells'] += 1

                # 純粋な数値セルはスキップ（数値の誤認識は危険）
                # ただし、数値と文字が混在している場合は修正対象
                is_pure_numeric = self._looks_numeric(cell_str) and not self._has_japanese(cell_str)
                if is_pure_numeric:
                    self.stats['skipped_cells'] += 1
                    continue
                
                # 短すぎるセルもスキップ（修正の必要性が低い）
                if len(cell_str) < 2:  # 2文字以上に変更（"0"→"O"などの修正のため）
                    continue
                
                # LLMで修正（より積極的に適用）
                # 文字化けの可能性をチェック（ や異常な文字が含まれている場合）
                has_mojibake = '' in cell_str or len([c for c in cell_str if ord(c) > 0xFFFF]) > 0
                # 日本語が含まれている、または文字化けの可能性がある、または長い文字列の場合
                should_correct = (
                    self._has_japanese(cell_str) or 
                    has_mojibake or 
                    len(cell_str) >= 5  # 5文字以上は修正対象に
                )
                
                if should_correct:
                    corrected = self.correct_cell_text(cell_str, row_context)
                    if corrected != cell_str:
                        corrected_df.at[idx, col_name] = corrected
                
                processed += 1
                self.stats['total_cells'] += 1
        
        if verbose:
            print(f"  ✅ シート '{sheet_name}' の処理完了")
        
        return corrected_df
    
    def correct_excel(
        self,
        input_excel_path: str,
        output_excel_path: str,
        sheet_names: Optional[List[str]] = None,
        max_sheets: Optional[int] = None,
        verbose: bool = True
    ) -> str:
        """
        Excelファイル全体を修正
        
        Args:
            input_excel_path: 入力Excelファイルパス
            output_excel_path: 出力Excelファイルパス
            sheet_names: 処理するシート名（Noneの場合は全シート）
            verbose: 詳細出力
        """
        if not LLM_AVAILABLE:
            raise RuntimeError("LLMが利用できません。local_llm_helperをインストールしてください。")
        
        print(f"Excelファイルを読み込み中: {input_excel_path}")
        df_dict = pd.read_excel(input_excel_path, sheet_name=None)
        
        if sheet_names:
            df_dict = {name: df_dict[name] for name in sheet_names if name in df_dict}
        
        # 最大シート数制限
        if max_sheets and len(df_dict) > max_sheets:
            print(f"  注意: {len(df_dict)}シート中、最初の{max_sheets}シートのみ処理します")
            df_dict = dict(list(df_dict.items())[:max_sheets])
        
        print(f"  {len(df_dict)}シートを処理します")
        
        corrected_dict = {}
        
        for sheet_name, df in df_dict.items():
            print(f"\nシート '{sheet_name}' を処理中...")
            corrected_df = self.correct_sheet(df, sheet_name, verbose=verbose)
            corrected_dict[sheet_name] = corrected_df
        
        # Excelに書き込み
        print(f"\n修正済みExcelファイルを保存中: {output_excel_path}")
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            for sheet_name, df in corrected_dict.items():
                # シート名制限（31文字）
                safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False, header=False)
        
        print(f"\n✅ 修正完了: {output_excel_path}")
        print(f"\n📊 統計:")
        print(f"  - 処理セル数: {self.stats['total_cells']}")
        print(f"  - 修正セル数: {self.stats['corrected_cells']}")
        print(f"  - 修正率: {self.stats['corrected_cells'] / max(self.stats['total_cells'], 1) * 100:.1f}%")
        
        return output_excel_path


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python excel_llm_ocr_corrector.py <入力Excelファイル> [出力Excelファイル] [最大シート数]")
        print("例: python excel_llm_ocr_corrector.py input.xlsx output_corrected.xlsx")
        print("例（最初の3シートのみ）: python excel_llm_ocr_corrector.py input.xlsx output.xlsx 3")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace('.xlsx', '_LLM_CORRECTED.xlsx')
    max_sheets = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    if not os.path.exists(input_path):
        print(f"[ERROR] ファイルが見つかりません: {input_path}")
        sys.exit(1)
    
    corrector = ExcelLLMOCRCorrector(
        llm_model="qwen2.5:7b",
        batch_size=100
    )
    
    try:
        result_path = corrector.correct_excel(input_path, output_path, max_sheets=max_sheets, verbose=True)
        print(f"\n完了！修正済みファイル: {result_path}")
    except KeyboardInterrupt:
        print("\n[INFO] ユーザーによって中断されました")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
