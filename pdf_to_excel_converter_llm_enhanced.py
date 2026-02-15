#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF→Excel変換（LLM強化版）
既存システムを統合してOCR精度を向上
- Super OCR Pipeline（超解像・前処理）
- ローカルLLM（OCR結果の後処理・修正）
- マルチプロバイダーOCR（複数OCR結果の統合）
"""

import os
import sys
from manaos_logger import get_logger
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

# Windowsでのエンコーディング修正
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 既存システムのインポート
try:
    from ocr_multi_provider import MultiProviderOCR
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("警告: ocr_multi_providerが見つかりません")

try:
    from local_llm_helper import chat, generate
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("警告: local_llm_helperが見つかりません")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("警告: PyMuPDFが見つかりません")

# ログ設定
logger = get_logger(__name__)


class PDFToExcelConverterLLMEnhanced:
    """PDF→Excel変換（LLM強化版）"""
    
    def __init__(
        self,
        use_llm_correction: bool = True,
        llm_model: str = "qwen2.5:7b",
        ocr_providers: List[str] = None,
        use_super_ocr: bool = False
    ):
        """
        初期化
        
        Args:
            use_llm_correction: LLMでOCR結果を修正するか
            llm_model: 使用するLLMモデル
            ocr_providers: 使用するOCRプロバイダー（優先順位順）
            use_super_ocr: Super OCR Pipelineを使用するか
        """
        self.use_llm_correction = use_llm_correction and LLM_AVAILABLE
        self.llm_model = llm_model
        self.ocr_providers = ocr_providers or ["tesseract", "google", "microsoft", "amazon"]
        self.use_super_ocr = use_super_ocr
        
        # OCR初期化
        if OCR_AVAILABLE:
            self.ocr = MultiProviderOCR()
            available = self.ocr.get_available_providers()
            logger.info(f"利用可能なOCRプロバイダー: {available}")
        else:
            self.ocr = None
        
        # ページデータ
        self.page_data = []
    
    def extract_text_with_ocr(self, pdf_path: str) -> Dict[str, Any]:
        """
        OCRでPDFからテキストを抽出（複数プロバイダー対応）
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDFが必要です: pip install PyMuPDF")
        
        if not self.ocr:
            raise RuntimeError("OCRが利用できません")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        logger.info(f"PDFページ数: {total_pages}")
        
        all_text = []
        page_data = []
        
        for page_num in range(total_pages):
            logger.info(f"ページ {page_num + 1}/{total_pages} を処理中...")
            page = doc[page_num]
            
            # 高解像度で画像に変換（DPI 300）
            zoom = 3.0  # 300 DPI相当
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # 一時画像ファイルに保存
            temp_image_path = f"temp_page_{page_num + 1}.png"
            pix.save(temp_image_path)
            
            # 複数OCRプロバイダーで試行
            ocr_results = []
            best_result = None
            
            for provider in self.ocr_providers:
                if provider not in self.ocr.get_available_providers():
                    logger.debug(f"{provider} OCRは利用できません")
                    continue
                
                try:
                    logger.info(f"  {provider} OCRで認識中...")
                    result = self.ocr.recognize(temp_image_path, provider=provider)
                    
                    if result and result.get('text'):
                        ocr_results.append({
                            'provider': provider,
                            'text': result.get('text', ''),
                            'grid_data': result.get('grid_data'),
                            'confidence': result.get('confidence', 0.0)
                        })
                        logger.info(f"  ✅ {provider}: {len(result.get('text', ''))}文字を認識")
                    else:
                        logger.warning(f"  ⚠️ {provider}: テキストを認識できませんでした")
                except Exception as e:
                    logger.warning(f"  ⚠️ {provider} OCRエラー: {e}")
                    continue
            
            # 最良の結果を選択（文字数が多い、または信頼度が高い）
            if ocr_results:
                best_result = max(ocr_results, key=lambda x: len(x['text']) * (1 + x.get('confidence', 0)))
                logger.info(f"  ✅ 最良の結果: {best_result['provider']} ({len(best_result['text'])}文字)")
            else:
                logger.warning(f"  ⚠️ ページ {page_num + 1}: OCRでテキストを認識できませんでした")
                best_result = {'provider': None, 'text': '', 'grid_data': None}
            
            # LLMで修正（オプション）
            if self.use_llm_correction and best_result.get('text'):
                corrected_text = self._correct_ocr_with_llm(
                    best_result['text'],
                    page_num + 1
                )
                if corrected_text:
                    best_result['text'] = corrected_text
                    best_result['llm_corrected'] = True
                    logger.info(f"  ✅ LLMで修正完了")
            
            # ページデータに保存
            page_data.append({
                'page_num': page_num + 1,
                'text': best_result.get('text', ''),
                'grid_data': best_result.get('grid_data'),
                'provider': best_result.get('provider'),
                'llm_corrected': best_result.get('llm_corrected', False)
            })
            
            all_text.append(best_result.get('text', ''))
            
            # 一時ファイルを削除
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        
        doc.close()
        
        return {
            'text': '\n\n'.join(all_text),
            'page_data': page_data,
            'total_pages': total_pages
        }
    
    def _correct_ocr_with_llm(self, ocr_text: str, page_num: int) -> Optional[str]:
        """
        LLMでOCR結果を修正・補完
        """
        if not LLM_AVAILABLE:
            return None
        
        # 長すぎる場合は分割
        max_chunk_size = 2000
        if len(ocr_text) > max_chunk_size:
            # チャンクに分割して処理
            chunks = [ocr_text[i:i+max_chunk_size] for i in range(0, len(ocr_text), max_chunk_size)]
            corrected_chunks = []
            
            for i, chunk in enumerate(chunks):
                logger.debug(f"  LLM修正中: チャンク {i+1}/{len(chunks)}")
                corrected = self._correct_chunk_with_llm(chunk, page_num, i+1, len(chunks))
                if corrected:
                    corrected_chunks.append(corrected)
                else:
                    corrected_chunks.append(chunk)  # 修正失敗時は元のテキスト
            
            return '\n'.join(corrected_chunks)
        else:
            return self._correct_chunk_with_llm(ocr_text, page_num, 1, 1)
    
    def _correct_chunk_with_llm(self, text: str, page_num: int, chunk_num: int, total_chunks: int) -> Optional[str]:
        """
        LLMでテキストチャンクを修正
        """
        prompt = f"""以下のOCR（光学文字認識）結果を修正してください。

OCR結果には以下の問題がある可能性があります：
- 文字化け（例: "文字" → "文宇"）
- 読み取り不足（空白や改行の誤認識）
- 数字や記号の誤認識
- 日本語と英語の混在による誤認識

OCR結果（ページ {page_num}, チャンク {chunk_num}/{total_chunks}）:
{text}

修正指示:
1. 明らかな誤字・脱字を修正してください
2. 文脈から推測できる正しい文字に修正してください
3. 数字や記号は正確に保持してください
4. 元のレイアウト（改行、空白）は可能な限り保持してください
5. 修正できない部分はそのまま残してください

修正後のテキストのみを返してください（説明は不要）:"""
        
        try:
            result = generate(self.llm_model, prompt, timeout=60)
            if result and result.get('response'):
                corrected = result['response'].strip()
                # プロンプトの繰り返しを削除
                if "修正後のテキスト" in corrected:
                    corrected = corrected.split("修正後のテキスト")[-1].strip()
                if ":" in corrected:
                    corrected = corrected.split(":", 1)[-1].strip()
                return corrected
        except Exception as e:
            logger.warning(f"LLM修正エラー: {e}")
        
        return None
    
    def convert_to_excel(
        self,
        pdf_path: str,
        excel_path: str,
        use_ocr: bool = True
    ) -> str:
        """
        PDFをExcelに変換
        
        Args:
            pdf_path: PDFファイルパス
            excel_path: 出力Excelファイルパス
            use_ocr: OCRを使用するか（Falseの場合はテキスト抽出のみ）
        """
        logger.info(f"PDF→Excel変換を開始: {pdf_path}")
        
        # OCRでテキスト抽出
        if use_ocr:
            extraction_result = self.extract_text_with_ocr(pdf_path)
            self.page_data = extraction_result.get('page_data', [])
            logger.info(f"✅ {len(self.page_data)}ページからテキストを抽出しました")
        else:
            # 通常のテキスト抽出（pdfplumberなど）
            logger.warning("通常のテキスト抽出は未実装です。OCRを使用してください。")
            return excel_path
        
        # Excelに書き込み
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            if self.page_data:
                logger.info(f"各ページを別シートに分割します（{len(self.page_data)}ページ）...")
                
                for page_info in self.page_data:
                    page_num = page_info['page_num']
                    grid_data = page_info.get('grid_data')
                    text = page_info.get('text', '')
                    
                    if grid_data and len(grid_data) > 0:
                        # グリッドデータを正規化
                        max_cols = max(len(row) for row in grid_data if row)
                        normalized_grid = []
                        for row in grid_data:
                            normalized_row = row + [''] * (max_cols - len(row))
                            normalized_grid.append(normalized_row[:max_cols])
                        
                        df = pd.DataFrame(normalized_grid)
                        sheet_name = f"Page{page_num}"
                        # シート名制限（31文字）
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        logger.info(f"シート '{sheet_name}' を作成: {len(df)}行 × {len(df.columns)}列（レイアウト保持）")
                    else:
                        # 通常のテキストをシートに書き込む
                        if text.strip():
                            lines = text.split('\n')
                            df = pd.DataFrame({'Text': lines})
                            sheet_name = f"Page{page_num}"
                            if len(sheet_name) > 31:
                                sheet_name = sheet_name[:31]
                            
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            logger.info(f"シート '{sheet_name}' を作成: {len(df)}行（テキスト）")
            else:
                # フォールバック: 情報シート
                df_info = pd.DataFrame({
                    'Info': ['PDFからテキストを抽出できませんでした。']
                })
                df_info.to_excel(writer, sheet_name='Info', index=False)
                logger.warning("テキストを抽出できませんでした。Infoシートを作成しました。")
        
        logger.info(f"✅ Excelファイルを作成しました: {excel_path}")
        return excel_path


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python pdf_to_excel_converter_llm_enhanced.py <PDFファイルパス> [出力Excelパス]")
        print("例: python pdf_to_excel_converter_llm_enhanced.py input.pdf output.xlsx")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    excel_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace('.pdf', '_LLM_ENHANCED.xlsx')
    
    # コンバーター初期化（LLM修正を有効化）
    converter = PDFToExcelConverterLLMEnhanced(
        use_llm_correction=True,
        llm_model="qwen2.5:7b",
        ocr_providers=["tesseract", "google", "microsoft", "amazon"]
    )
    
    try:
        result_path = converter.convert_to_excel(pdf_path, excel_path, use_ocr=True)
        print(f"\n✅ 変換完了: {result_path}")
        print(f"\n📊 統計:")
        print(f"  - ページ数: {len(converter.page_data)}")
        llm_corrected_count = sum(1 for p in converter.page_data if p.get('llm_corrected'))
        print(f"  - LLM修正済みページ: {llm_corrected_count}/{len(converter.page_data)}")
    except Exception as e:
        print(f"\n[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
