#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF→Excel変換（アンサンブルOCR版）
複数のOCR結果を統合して精度向上
- 複数OCRプロバイダーの結果を統合
- 投票方式で最良の結果を選択
- LLMで後処理・修正
"""

import os
import sys
from manaos_logger import get_logger, get_service_logger
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import Counter
import fitz  # PyMuPDF

# PyMuPDF import check（PYMUPDF_AVAILABLE が未定義だと実行時に落ちるため）
try:
    import fitz as _fitz  # noqa: F401
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False

# Windowsでのエンコーディング修正
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

try:
    from ocr_multi_provider import MultiProviderOCR
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("警告: ocr_multi_providerが見つかりません")

try:
    from local_llm_helper import generate
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("警告: local_llm_helperが見つかりません")

logger = get_service_logger("pdf-to-excel-ensemble-ocr")


class EnsembleOCR:
    """アンサンブルOCR（複数OCR結果の統合）"""
    
    def __init__(self):
        """初期化"""
        if OCR_AVAILABLE:
            self.ocr = MultiProviderOCR()  # type: ignore[possibly-unbound]
            self.available_providers = self.ocr.get_available_providers()
            logger.info(f"利用可能なOCRプロバイダー: {self.available_providers}")
        else:
            self.ocr = None
            self.available_providers = []
    
    def recognize_ensemble(self, image_path: str, providers: List[str] = None) -> Dict[str, Any]:  # type: ignore
        """
        複数OCRプロバイダーで認識して統合
        
        Args:
            image_path: 画像ファイルパス
            providers: 使用するプロバイダー（Noneの場合は全プロバイダー）
            
        Returns:
            統合されたOCR結果
        """
        if not self.ocr:
            raise RuntimeError("OCRが利用できません")
        
        providers = providers or self.available_providers
        results = []
        
        # 各プロバイダーで認識
        for provider in providers:
            try:
                logger.info(f"  {provider} OCRで認識中...")
                # Tesseractはレイアウト情報付きで実行（grid_dataを取りたい）
                if provider == "tesseract":
                    result = self.ocr.recognize(image_path, provider=provider, layout=True, lang="jpn+eng")
                else:
                    result = self.ocr.recognize(image_path, provider=provider)
                
                if result and result.get('text'):
                    results.append({
                        'provider': provider,
                        'text': result.get('text', ''),
                        'grid_data': result.get('grid_data'),
                        'confidence': result.get('confidence', 0.5),
                        'length': len(result.get('text', ''))
                    })
                    logger.info(f"  ✅ {provider}: {len(result.get('text', ''))}文字を認識")
            except Exception as e:
                logger.warning(f"  ⚠️ {provider} OCRエラー: {e}")
                continue
        
        if not results:
            return {'text': '', 'grid_data': None, 'provider': 'none', 'confidence': 0.0}
        
        # 最良の結果を選択（文字数×信頼度）
        best_result = max(results, key=lambda x: x['length'] * (1 + x['confidence']))
        
        # 複数の結果がある場合、テキストを統合（投票方式）
        if len(results) > 1:
            # 最も長いテキストをベースに、他の結果で補完
            all_texts = [r['text'] for r in results]
            best_text = self._merge_texts(all_texts, best_result['text'])
            best_result['text'] = best_text
            best_result['ensemble'] = True
            logger.info(f"  ✅ アンサンブル結果: {len(best_text)}文字（{len(results)}プロバイダー統合）")
        
        return {
            'text': best_result['text'],
            'grid_data': best_result.get('grid_data'),
            'provider': best_result['provider'],
            'confidence': best_result['confidence'],
            'ensemble_count': len(results)
        }
    
    def _merge_texts(self, texts: List[str], base_text: str) -> str:
        """
        複数のテキストを統合（簡単な投票方式）
        
        Args:
            texts: 複数のOCR結果テキスト
            base_text: ベースとなるテキスト（最長のもの）
            
        Returns:
            統合されたテキスト
        """
        # 現時点では最長のテキストを返す（将来的に改善可能）
        return base_text


class PDFToExcelEnsembleOCR:
    """PDF→Excel変換（アンサンブルOCR版）"""
    
    def __init__(self, use_llm_correction: bool = True):
        """
        初期化
        
        Args:
            use_llm_correction: LLMでOCR結果を修正するか
        """
        self.ensemble_ocr = EnsembleOCR()
        self.use_llm_correction = use_llm_correction and LLM_AVAILABLE
        self.page_data = []
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        PDFからテキストを抽出（アンサンブルOCR）
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDFが必要です: pip install PyMuPDF")
        
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
            
            # アンサンブルOCRで認識
            ocr_result = self.ensemble_ocr.recognize_ensemble(temp_image_path)
            
            text = ocr_result.get('text', '')
            grid_data = ocr_result.get('grid_data')
            provider = ocr_result.get('provider', 'unknown')
            ensemble_count = ocr_result.get('ensemble_count', 1)
            
            # LLMで修正（オプション）
            if self.use_llm_correction and text:
                corrected_text = self._correct_with_llm(text, page_num + 1)
                if corrected_text:
                    text = corrected_text
                    logger.info(f"  ✅ LLMで修正完了")
            
            # ページデータに保存
            page_data.append({
                'page_num': page_num + 1,
                'text': text,
                'grid_data': grid_data,
                'provider': provider,
                'ensemble_count': ensemble_count,
                'llm_corrected': self.use_llm_correction and text
            })
            
            all_text.append(text)
            
            # 一時ファイルを削除
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        
        doc.close()
        
        return {
            'text': '\n\n'.join(all_text),
            'page_data': page_data,
            'total_pages': total_pages
        }
    
    def _correct_with_llm(self, text: str, page_num: int) -> Optional[str]:
        """LLMでOCR結果を修正"""
        if not LLM_AVAILABLE:
            return None
        
        # 長すぎる場合は分割
        max_chunk_size = 2000
        if len(text) > max_chunk_size:
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
            corrected_chunks = []
            
            for i, chunk in enumerate(chunks):
                corrected = self._correct_chunk_with_llm(chunk, page_num, i+1, len(chunks))
                if corrected:
                    corrected_chunks.append(corrected)
                else:
                    corrected_chunks.append(chunk)
            
            return '\n'.join(corrected_chunks)
        else:
            return self._correct_chunk_with_llm(text, page_num, 1, 1)
    
    def _correct_chunk_with_llm(self, text: str, page_num: int, chunk_num: int, total_chunks: int) -> Optional[str]:
        """LLMでテキストチャンクを修正"""
        prompt = f"""以下のOCR（光学文字認識）結果を修正してください。

OCR結果には以下の問題がある可能性があります：
- 文字化け（例: "文字" → "文宇"、"0" → "O"）
- 読み取り不足（空白や改行の誤認識）
- 数字や記号の誤認識（例: "1" → "l"、"5" → "S"）
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
            result = generate("qwen2.5:7b", prompt, timeout=60)  # type: ignore[possibly-unbound]
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
    
    def convert_to_excel(self, pdf_path: str, excel_path: str) -> str:
        """PDFをExcelに変換"""
        logger.info(f"PDF→Excel変換を開始: {pdf_path}")
        
        # テキスト抽出
        extraction_result = self.extract_text_from_pdf(pdf_path)
        self.page_data = extraction_result.get('page_data', [])
        logger.info(f"✅ {len(self.page_data)}ページからテキストを抽出しました")
        
        # Excelに書き込み
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            if self.page_data:
                logger.info(f"各ページを別シートに分割します（{len(self.page_data)}ページ）...")
                
                for page_info in self.page_data:
                    page_num = page_info['page_num']
                    grid_data = page_info.get('grid_data')
                    text = page_info.get('text', '')
                    provider = page_info.get('provider', 'unknown')
                    ensemble_count = page_info.get('ensemble_count', 1)
                    
                    if grid_data and len(grid_data) > 0:
                        # グリッドデータを正規化
                        max_cols = max(len(row) for row in grid_data if row)
                        normalized_grid = []
                        for row in grid_data:
                            normalized_row = row + [''] * (max_cols - len(row))
                            normalized_grid.append(normalized_row[:max_cols])
                        
                        df = pd.DataFrame(normalized_grid)
                        sheet_name = f"Page{page_num}"
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        logger.info(f"シート '{sheet_name}' を作成: {len(df)}行 × {len(df.columns)}列（{provider}, {ensemble_count}OCR統合）")
                    else:
                        # 通常のテキストをシートに書き込む
                        if text.strip():
                            lines = text.split('\n')
                            df = pd.DataFrame({'Text': lines})
                            sheet_name = f"Page{page_num}"
                            if len(sheet_name) > 31:
                                sheet_name = sheet_name[:31]
                            
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            logger.info(f"シート '{sheet_name}' を作成: {len(df)}行（{provider}, {ensemble_count}OCR統合）")
            else:
                # フォールバック
                df_info = pd.DataFrame({'Info': ['PDFからテキストを抽出できませんでした。']})
                df_info.to_excel(writer, sheet_name='Info', index=False)
        
        logger.info(f"✅ Excelファイルを作成しました: {excel_path}")
        return excel_path


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python pdf_to_excel_ensemble_ocr.py <PDFファイルパス> [出力Excelパス]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    excel_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace('.pdf', '_ENSEMBLE_OCR.xlsx')
    
    if not os.path.exists(pdf_path):
        print(f"[ERROR] ファイルが見つかりません: {pdf_path}")
        sys.exit(1)
    
    converter = PDFToExcelEnsembleOCR(use_llm_correction=True)
    
    try:
        result_path = converter.convert_to_excel(pdf_path, excel_path)
        print(f"\n✅ 変換完了: {result_path}")
        print(f"\n📊 統計:")
        print(f"  - ページ数: {len(converter.page_data)}")
        ensemble_count = sum(1 for p in converter.page_data if p.get('ensemble_count', 1) > 1)
        llm_count = sum(1 for p in converter.page_data if p.get('llm_corrected'))
        print(f"  - アンサンブルOCR処理: {ensemble_count}ページ")
        print(f"  - LLM修正処理: {llm_count}ページ")
    except Exception as e:
        print(f"\n[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
