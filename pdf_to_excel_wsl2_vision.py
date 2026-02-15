#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF→Excel変換（WSL2 Vision LLM版）
WSL2内のOllama Vision LLMを使用
"""

import os
import sys
from manaos_logger import get_logger
import pandas as pd
import base64
import subprocess
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
import fitz  # PyMuPDF

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

# Windowsでのエンコーディング修正
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logger = get_service_logger("pdf-to-excel-wsl2-vision")


class WSL2VisionLLM:
    """WSL2内のVision LLMを使用"""
    
    def __init__(self, vision_model: str = "llava:latest"):
        """
        初期化
        
        Args:
            vision_model: 使用するVision LLMモデル
        """
        self.vision_model = vision_model
        self.wsl_distro = "Ubuntu-22.04"
        # WSL2内で動いているOllamaでも、APIはlocalhostで叩ける（Windows→WSL2転送）
        self.ollama_url = DEFAULT_OLLAMA_URL
    
    def _call_wsl2_ollama_api(self, endpoint: str, method: str = "GET", json_data: dict = None) -> Optional[Dict]:
        """Ollama APIを呼び出す（Windows側から直接HTTP）"""
        url = f"{self.ollama_url}{endpoint}"
        try:
            if method == "GET":
                r = requests.get(url, timeout=30)
            else:
                # Visionは時間がかかることがあるので長め
                r = requests.request(method, url, json=json_data, timeout=1200)
            if r.status_code == 200:
                return r.json()
            logger.error(f"Ollama API error: {r.status_code} {r.text[:200]}")
        except Exception as e:
            logger.error(f"Ollama API呼び出しエラー: {e}")
        
        return None

    def _encode_image_base64_wsl2(self, image_path: str) -> Optional[str]:
        """画像をbase64エンコード（Windows側で実行）"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"画像エンコードエラー: {e}")
            return None

    def extract_text_from_image(self, image_path: str, page_num: int) -> Optional[str]:
        """画像からテキストを抽出（Vision LLM使用・フォールバック用）"""
        image_base64 = self._encode_image_base64_wsl2(image_path)
        if not image_base64:
            return None

        prompt = f"""この画像（ページ{page_num}）に含まれるすべてのテキストを正確に抽出してください。
出力はテキストのみ（説明は不要）。"""

        response = self._call_wsl2_ollama_api(
            "/api/chat",
            method="POST",
            json_data={
                "model": self.vision_model,
                "messages": [{"role": "user", "content": prompt, "images": [image_base64]}],
                "options": {"temperature": 0, "num_predict": 1024},
                "stream": False,
            },
        )
        if not response:
            return None
        return (response.get("message", {}) or {}).get("content", "") or None
    
    def extract_table_from_image(self, image_path: str, page_num: int) -> Optional[List[List[str]]]:
        """
        画像から表（TSV相当）を抽出（Vision LLM使用）
        
        Args:
            image_path: 画像ファイルパス（Windows側）
            page_num: ページ番号
            
        Returns:
            2次元配列（行×列）
        """
        image_base64 = self._encode_image_base64_wsl2(image_path)
        if not image_base64:
            return None
        
        # Vision LLMに送信（TSVで返させる：Excel化しやすい・精度向上版）
        prompt = f"""この画像（ページ{page_num}）に含まれる表・帳票を、TSV（タブ区切り）として抽出してください。

【重要】高精度抽出のための指示:
1. 出力はTSVのみ（説明、前置き、コードブロック ``` は禁止）
2. 1行が1レコード、列はタブ(\\t)区切り
3. 行ごとに列数を揃える（空欄は空のままタブで保持）
4. 列数は最大25列まで（それ以上に見える場合は、近い列を結合して25列以内に収める）
5. 日本語/英語/数字/記号を正確に。特に数値は慎重に。
6. 文字化けや誤認識を避けるため、不確実な文字は「?」ではなく可能な限り推測して記載
7. 表の構造（ヘッダー、データ行）を保持
8. 数値の小数点、カンマ、記号は元の通りに保持
9. 日本語の文字（漢字、ひらがな、カタカナ）は正確に認識
10. 空白セルは空文字列として保持（タブのみ）

抽出したTSVデータのみを返してください:
"""
        
        messages = [
            {
                "role": "user",
                "content": prompt,
                "images": [image_base64]
            }
        ]
        
        logger.info(f"  Vision LLM ({self.vision_model}) で表を抽出中...（GPUはWSL2側）")
        
        response = self._call_wsl2_ollama_api(
            "/api/chat",
            method="POST",
            json_data={
                "model": self.vision_model,
                "messages": messages,
                "options": {"temperature": 0, "num_predict": 1024},
                "stream": False
            }
        )
        
        if not response:
            return None

        text = response.get('message', {}).get('content', '').strip()
        if not text:
            return None

        # TSV -> grid
        lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip() != ""]
        if not lines:
            return None
        grid = [ln.split("\t") for ln in lines]
        max_cols = max(len(r) for r in grid)
        # 念のため上限
        if max_cols > 60:
            return None
        grid = [r + [""] * (max_cols - len(r)) for r in grid]
        logger.info(f"  ✅ Vision LLM: {len(grid)}行 × {max_cols}列 を抽出")
        return grid


class PDFToExcelWSL2Vision:
    """PDF→Excel変換（WSL2 Vision LLM版）"""
    
    def __init__(self):
        """初期化"""
        self.vision_llm = WSL2VisionLLM(vision_model="llava:latest")
        self.page_data = []
    
    def extract_text_from_pdf(self, pdf_path: str, max_pages: Optional[int] = None) -> Dict[str, Any]:
        """PDFからテキストを抽出（Vision LLM使用）"""
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if max_pages is not None:
            total_pages = min(total_pages, int(max_pages))
        logger.info(f"PDFページ数: {total_pages}")
        
        all_text = []
        page_data = []
        
        for page_num in range(total_pages):
            logger.info(f"ページ {page_num + 1}/{total_pages} を処理中...")
            page = doc[page_num]
            
            # 高解像度で画像に変換
            # Vision LLMは画像が大きいと遅くなるため、かなり抑える（速度優先）
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # 一時画像ファイルに保存
            temp_image_path = f"temp_page_{page_num + 1}.png"
            pix.save(temp_image_path)
            
            grid_data = self.vision_llm.extract_table_from_image(temp_image_path, page_num + 1)
            text = ""
            if not grid_data:
                logger.warning(f"  ⚠️ ページ {page_num + 1}: 表を抽出できませんでした（テキストのみで継続）")
                text = self.vision_llm.extract_text_from_image(temp_image_path, page_num + 1) or ""
                grid_data = None
            else:
                # TSV抽出成功時はテキストも保持
                text = "\n".join(["\t".join(row) for row in grid_data])
            
            page_data.append({
                'page_num': page_num + 1,
                'text': text,
                'grid_data': grid_data,
                'provider': 'wsl2_vision_llm'
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
    
    def convert_to_excel(self, pdf_path: str, excel_path: str, max_pages: Optional[int] = None) -> str:
        """PDFをExcelに変換"""
        logger.info(f"PDF→Excel変換を開始: {pdf_path}")
        
        extraction_result = self.extract_text_from_pdf(pdf_path, max_pages=max_pages)
        self.page_data = extraction_result.get('page_data', [])
        logger.info(f"✅ {len(self.page_data)}ページからテキストを抽出しました")
        
        # Excelに書き込み
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            if self.page_data:
                for page_info in self.page_data:
                    page_num = page_info['page_num']
                    text = page_info.get('text', '')
                    grid_data = page_info.get('grid_data')
                    
                    sheet_name = f"Page{page_num}"
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]

                    if grid_data and len(grid_data) > 0:
                        max_cols = max(len(r) for r in grid_data)
                        norm = [r + [""] * (max_cols - len(r)) for r in grid_data]
                        df = pd.DataFrame(norm)
                        df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        logger.info(f"シート '{sheet_name}' を作成: {len(df)}行 × {len(df.columns)}列（Vision TSV）")
                    elif text.strip():
                        lines = text.split('\n')
                        df = pd.DataFrame({'Text': lines})
                        sheet_name = f"Page{page_num}"
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        logger.info(f"シート '{sheet_name}' を作成: {len(df)}行")
            else:
                pd.DataFrame({"Info": ["No pages extracted."]}).to_excel(writer, sheet_name="Info", index=False)
        
        logger.info(f"✅ Excelファイルを作成しました: {excel_path}")
        return excel_path


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python pdf_to_excel_wsl2_vision.py <PDFファイルパス> [出力Excelパス] [最大ページ数]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    excel_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace('.pdf', '_WSL2_VISION.xlsx')
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    if not os.path.exists(pdf_path):
        print(f"[ERROR] ファイルが見つかりません: {pdf_path}")
        sys.exit(1)
    
    converter = PDFToExcelWSL2Vision()
    
    try:
        result_path = converter.convert_to_excel(pdf_path, excel_path, max_pages=max_pages)
        print(f"\n✅ 変換完了: {result_path}")
    except Exception as e:
        print(f"\n[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
