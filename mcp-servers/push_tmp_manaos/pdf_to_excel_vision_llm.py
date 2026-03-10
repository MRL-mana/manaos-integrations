#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF→Excel変換（Vision LLM統合版）
Ollama Visionモデル（llava/qwen3-vl）を使用してPDFから直接テキスト抽出
既存システムを統合：
- Ollama Vision LLM（画像から直接テキスト抽出）
- Super OCR Pipeline（超解像・前処理）
- マルチプロバイダーOCR（フォールバック）
"""

import os
import sys
from manaos_logger import get_logger, get_service_logger
import pandas as pd
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

# Windowsでのエンコーディング修正
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("警告: PyMuPDFが必要です: pip install PyMuPDF")

try:
    from ocr_multi_provider import MultiProviderOCR
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("警告: ocr_multi_providerが見つかりません")

# ログ設定
logger = get_service_logger("pdf-to-excel-vision-llm")

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")


class PDFToExcelVisionLLM:
    """PDF→Excel変換（Vision LLM統合版）"""
    
    def __init__(
        self,
        vision_model: str = "llava:latest",
        use_ocr_fallback: bool = True,
        ocr_providers: List[str] = None  # type: ignore
    ):
        """
        初期化
        
        Args:
            vision_model: 使用するVision LLMモデル（llava:latest, qwen3-vl:30bなど）
            use_ocr_fallback: Vision LLMが失敗した場合にOCRを使用するか
            ocr_providers: OCRプロバイダー（優先順位順）
        """
        self.vision_model = vision_model
        self.use_ocr_fallback = use_ocr_fallback
        self.ocr_providers = ocr_providers or ["tesseract", "google", "microsoft", "amazon"]
        
        # OCR初期化
        if OCR_AVAILABLE and use_ocr_fallback:
            self.ocr = MultiProviderOCR()  # type: ignore[possibly-unbound]
            available = self.ocr.get_available_providers()
            logger.info(f"利用可能なOCRプロバイダー: {available}")
        else:
            self.ocr = None
        
        # Visionモデルの確認
        self._check_vision_model()
        
        # ページデータ
        self.page_data = []
    
    def _check_vision_model(self):
        """Visionモデルの存在を確認"""
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if self.vision_model not in model_names:
                    # 代替モデルを探す
                    vision_models = [m for m in model_names if any(x in m.lower() for x in ['llava', 'vl', 'vision'])]
                    if vision_models:
                        self.vision_model = vision_models[0]
                        logger.info(f"Visionモデル '{self.vision_model}' を使用します")
                    else:
                        logger.warning(f"Visionモデルが見つかりません。OCRフォールバックを使用します")
                else:
                    logger.info(f"Visionモデル '{self.vision_model}' が利用可能です")
        except Exception as e:
            logger.warning(f"Visionモデルの確認に失敗: {e}")
    
    def _image_to_base64(self, image_path: str) -> str:
        """画像をbase64エンコード"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _extract_text_with_vision_llm(self, image_path: str, page_num: int) -> Optional[str]:
        """
        Vision LLMで画像からテキストを抽出
        
        Args:
            image_path: 画像ファイルパス
            page_num: ページ番号
            
        Returns:
            抽出されたテキスト
        """
        try:
            # 画像をbase64エンコード
            image_base64 = self._image_to_base64(image_path)
            
            # Vision LLMに送信
            prompt = """この画像に含まれるすべてのテキストを正確に抽出してください。
以下の指示に従ってください：
1. 画像内のすべての文字、数字、記号を正確に読み取ってください
2. レイアウト（表、リスト、段落）を可能な限り保持してください
3. 表の場合は、行と列の構造を保持してください
4. 日本語と英語の両方を正確に認識してください
5. 数値データは特に注意深く読み取ってください
6. 改行や空白も適切に保持してください

抽出したテキストのみを返してください（説明は不要）:"""
            
            messages = [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64]
                }
            ]
            
            logger.info(f"  Vision LLM ({self.vision_model}) で認識中...")
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": self.vision_model,
                    "messages": messages,
                    "stream": False
                },
                timeout=600  # Visionモデルは時間がかかる場合がある（10分）
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('message', {}).get('content', '').strip()
                
                if text:
                    logger.info(f"  ✅ Vision LLM: {len(text)}文字を認識")
                    return text
                else:
                    logger.warning(f"  ⚠️ Vision LLM: テキストを認識できませんでした")
                    return None
            else:
                logger.warning(f"  ⚠️ Vision LLM APIエラー: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"  ⚠️ Vision LLM: タイムアウト")
            return None
        except Exception as e:
            logger.warning(f"  ⚠️ Vision LLMエラー: {e}")
            return None
    
    def _extract_text_with_ocr(self, image_path: str, page_num: int) -> Optional[Dict[str, Any]]:
        """
        OCRで画像からテキストを抽出（フォールバック）
        """
        if not self.ocr:
            return None
        
        for provider in self.ocr_providers:
            if provider not in self.ocr.get_available_providers():
                continue
            
            try:
                logger.info(f"  {provider} OCRで認識中...")
                result = self.ocr.recognize(image_path, provider=provider)
                
                if result and result.get('text'):
                    logger.info(f"  ✅ {provider}: {len(result.get('text', ''))}文字を認識")
                    return result
            except Exception as e:
                logger.warning(f"  ⚠️ {provider} OCRエラー: {e}")
                continue
        
        return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        PDFからテキストを抽出（Vision LLM優先、OCRフォールバック）
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDFが必要です: pip install PyMuPDF")
        
        doc = fitz.open(pdf_path)  # type: ignore[possibly-unbound]
        total_pages = len(doc)
        logger.info(f"PDFページ数: {total_pages}")
        
        all_text = []
        page_data = []
        
        for page_num in range(total_pages):
            logger.info(f"ページ {page_num + 1}/{total_pages} を処理中...")
            page = doc[page_num]
            
            # 高解像度で画像に変換（DPI 300）
            zoom = 3.0  # 300 DPI相当
            mat = fitz.Matrix(zoom, zoom)  # type: ignore[possibly-unbound]
            pix = page.get_pixmap(matrix=mat)
            
            # 一時画像ファイルに保存
            temp_image_path = f"temp_page_{page_num + 1}.png"
            pix.save(temp_image_path)
            
            # Vision LLMでテキスト抽出を試行
            text = None
            grid_data = None
            provider = None
            
            text = self._extract_text_with_vision_llm(temp_image_path, page_num + 1)
            
            # Vision LLMが失敗した場合、OCRフォールバック
            if not text and self.use_ocr_fallback:
                logger.info(f"  Vision LLMが失敗したため、OCRフォールバックを使用します...")
                ocr_result = self._extract_text_with_ocr(temp_image_path, page_num + 1)
                
                if ocr_result:
                    text = ocr_result.get('text', '')
                    grid_data = ocr_result.get('grid_data')
                    provider = ocr_result.get('provider', 'ocr')
                else:
                    provider = 'vision_llm_failed'
            else:
                provider = 'vision_llm'
            
            # ページデータに保存
            page_data.append({
                'page_num': page_num + 1,
                'text': text or '',
                'grid_data': grid_data,
                'provider': provider
            })
            
            all_text.append(text or '')
            
            # 一時ファイルを削除
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        
        doc.close()
        
        return {
            'text': '\n\n'.join(all_text),
            'page_data': page_data,
            'total_pages': total_pages
        }
    
    def convert_to_excel(
        self,
        pdf_path: str,
        excel_path: str
    ) -> str:
        """
        PDFをExcelに変換
        
        Args:
            pdf_path: PDFファイルパス
            excel_path: 出力Excelファイルパス
        """
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
                        logger.info(f"シート '{sheet_name}' を作成: {len(df)}行 × {len(df.columns)}列（{provider}）")
                    else:
                        # 通常のテキストをシートに書き込む
                        if text.strip():
                            lines = text.split('\n')
                            df = pd.DataFrame({'Text': lines})
                            sheet_name = f"Page{page_num}"
                            if len(sheet_name) > 31:
                                sheet_name = sheet_name[:31]
                            
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            logger.info(f"シート '{sheet_name}' を作成: {len(df)}行（{provider}）")
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
        print("使用方法: python pdf_to_excel_vision_llm.py <PDFファイルパス> [出力Excelパス] [Visionモデル名]")
        print("例: python pdf_to_excel_vision_llm.py input.pdf output.xlsx")
        print("例（モデル指定）: python pdf_to_excel_vision_llm.py input.pdf output.xlsx qwen3-vl:30b")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    excel_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace('.pdf', '_VISION_LLM.xlsx')
    vision_model = sys.argv[3] if len(sys.argv) > 3 else "llava:latest"
    
    if not os.path.exists(pdf_path):
        print(f"[ERROR] ファイルが見つかりません: {pdf_path}")
        sys.exit(1)
    
    converter = PDFToExcelVisionLLM(
        vision_model=vision_model,
        use_ocr_fallback=True
    )
    
    try:
        result_path = converter.convert_to_excel(pdf_path, excel_path)
        print(f"\n✅ 変換完了: {result_path}")
        print(f"\n📊 統計:")
        print(f"  - ページ数: {len(converter.page_data)}")
        vision_count = sum(1 for p in converter.page_data if p.get('provider') == 'vision_llm')
        ocr_count = sum(1 for p in converter.page_data if 'ocr' in str(p.get('provider', '')))
        print(f"  - Vision LLM処理: {vision_count}ページ")
        print(f"  - OCR処理: {ocr_count}ページ")
    except Exception as e:
        print(f"\n[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
