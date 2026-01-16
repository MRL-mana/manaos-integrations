#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルのOCR結果をVision LLMで修正・補完
既存のExcelファイルを読み込んで、Vision LLMで文字化けや誤認識を修正
"""

import sys
import os
import pandas as pd
import base64
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
import io

# Windowsでのエンコーディング修正
if sys.platform == 'win32':
    import io as io_module
    sys.stdout = io_module.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io_module.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

OLLAMA_URL = "http://localhost:11434"


class ExcelVisionLLMCorrector:
    """ExcelファイルのOCR結果をVision LLMで修正"""
    
    def __init__(
        self,
        vision_model: str = "llava:latest",
        max_sheet_preview: int = 5  # シートプレビュー用の最大行数
    ):
        """
        初期化
        
        Args:
            vision_model: 使用するVision LLMモデル
            max_sheet_preview: シートプレビュー用の最大行数
        """
        self.vision_model = vision_model
        self.max_sheet_preview = max_sheet_preview
        self.stats = {
            'total_cells': 0,
            'corrected_cells': 0,
            'skipped_cells': 0
        }
    
    def _create_sheet_image(self, df: pd.DataFrame, sheet_name: str) -> Optional[bytes]:
        """
        シートの画像を作成（Vision LLM用）
        
        Args:
            df: データフレーム
            sheet_name: シート名
            
        Returns:
            画像のバイトデータ
        """
        try:
            # プレビュー用に最大行数を制限
            preview_df = df.head(self.max_sheet_preview)
            
            # 画像サイズを計算
            width = min(1200, len(preview_df.columns) * 150)
            height = min(800, len(preview_df) * 40 + 100)
            
            # 画像を作成
            from matplotlib import pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # GUI不要
            
            fig, ax = plt.subplots(figsize=(width/100, height/100))
            ax.axis('tight')
            ax.axis('off')
            
            # テーブルを作成
            table = ax.table(
                cellText=preview_df.values,
                colLabels=preview_df.columns,
                cellLoc='left',
                loc='center'
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 2)
            
            plt.title(f"Sheet: {sheet_name}", fontsize=10)
            
            # 画像をバイトデータに変換
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            image_bytes = buf.read()
            plt.close()
            
            return image_bytes
        except Exception as e:
            print(f"  [WARNING] 画像作成エラー: {e}")
            return None
    
    def _correct_sheet_with_vision_llm(self, df: pd.DataFrame, sheet_name: str) -> Optional[pd.DataFrame]:
        """
        Vision LLMでシート全体を修正
        
        Args:
            df: データフレーム
            sheet_name: シート名
            
        Returns:
            修正されたデータフレーム
        """
        # シートの画像を作成
        image_bytes = self._create_sheet_image(df, sheet_name)
        if not image_bytes:
            return None
        
        # base64エンコード
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # データのサンプルを取得
        sample_data = df.head(10).to_string()
        
        prompt = f"""この画像はExcelシート '{sheet_name}' のOCR結果です。
OCR結果には以下の問題がある可能性があります：
- 文字化け（例: "文字" → "文宇"、"0" → "O"）
- 読み取り不足（空白や改行の誤認識）
- 数字や記号の誤認識（例: "1" → "l"、"5" → "S"）
- 日本語と英語の混在による誤認識

サンプルデータ:
{sample_data}

修正指示:
1. 画像内のすべてのテキストを正確に読み取ってください
2. 明らかな誤字・脱字を修正してください
3. 文脈から推測できる正しい文字に修正してください
4. 数字や記号は正確に保持してください（特に数値データ）
5. 表の構造（行・列）を保持してください

修正が必要なセルの位置（行,列）と修正後のテキストをJSON形式で返してください:
{{
  "corrections": [
    {{"row": 0, "col": 0, "original": "誤認識テキスト", "corrected": "正しいテキスト"}},
    ...
  ]
}}

修正が不要な場合は空の配列を返してください:"""
        
        try:
            messages = [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64]
                }
            ]
            
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": self.vision_model,
                    "messages": messages,
                    "stream": False
                },
                timeout=600  # Vision LLMは時間がかかるため延長（10分）
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('message', {}).get('content', '').strip()
                
                # JSONを抽出
                try:
                    # JSON部分を抽出
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        corrections_data = json.loads(json_match.group())
                        corrections = corrections_data.get('corrections', [])
                        
                        if corrections:
                            corrected_df = df.copy()
                            for correction in corrections:
                                row_idx = correction.get('row')
                                col_idx = correction.get('col')
                                corrected_text = correction.get('corrected')
                                
                                if 0 <= row_idx < len(corrected_df) and 0 <= col_idx < len(corrected_df.columns):
                                    col_name = corrected_df.columns[col_idx]
                                    original = str(corrected_df.iloc[row_idx, col_idx])
                                    
                                    if original != corrected_text:
                                        corrected_df.iloc[row_idx, col_idx] = corrected_text
                                        self.stats['corrected_cells'] += 1
                                        print(f"    修正: ({row_idx}, {col_idx}): '{original}' → '{corrected_text}'")
                            
                            self.stats['total_cells'] += len(corrections)
                            return corrected_df
                except Exception as e:
                    print(f"  [WARNING] JSON解析エラー: {e}")
                    print(f"  LLM応答: {content[:200]}...")
            
        except Exception as e:
            print(f"  [WARNING] Vision LLM修正エラー: {e}")
        
        return None
    
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
            max_sheets: 最大シート数
            verbose: 詳細出力
        """
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
            print(f"\nシート '{sheet_name}' を処理中... ({len(df)}行 × {len(df.columns)}列)")
            
            # Vision LLMで修正
            corrected_df = self._correct_sheet_with_vision_llm(df, sheet_name)
            
            if corrected_df is not None:
                corrected_dict[sheet_name] = corrected_df
                print(f"  ✅ シート '{sheet_name}' の処理完了")
            else:
                corrected_dict[sheet_name] = df
                print(f"  ⚠️ シート '{sheet_name}' の修正に失敗（元のデータを保持）")
        
        # Excelに書き込み
        print(f"\n修正済みExcelファイルを保存中: {output_excel_path}")
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            for sheet_name, df in corrected_dict.items():
                safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False, header=False)
        
        print(f"\n✅ 修正完了: {output_excel_path}")
        print(f"\n📊 統計:")
        print(f"  - 修正セル数: {self.stats['corrected_cells']}")
        print(f"  - 処理セル数: {self.stats['total_cells']}")
        
        return output_excel_path


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python excel_vision_llm_corrector.py <入力Excelファイル> [出力Excelファイル] [最大シート数]")
        print("例: python excel_vision_llm_corrector.py input.xlsx output_corrected.xlsx")
        print("例（最初の2シートのみ）: python excel_vision_llm_corrector.py input.xlsx output.xlsx 2")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace('.xlsx', '_VISION_LLM_CORRECTED.xlsx')
    max_sheets = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    if not os.path.exists(input_path):
        print(f"[ERROR] ファイルが見つかりません: {input_path}")
        sys.exit(1)
    
    corrector = ExcelVisionLLMCorrector(
        vision_model="llava:latest"
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
