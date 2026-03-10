#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision LLMの簡単なテスト
1ページだけ処理して動作確認
"""

import sys
import os
import base64
import requests

# fitz（PyMuPDF）が未インストールの場合にスタブを注入
import pytest
import sys
from unittest.mock import MagicMock

if "fitz" not in sys.modules:
    _fitz_stub = MagicMock()
    _fitz_stub.open = MagicMock()
    _fitz_stub.Matrix = MagicMock()
    sys.modules["fitz"] = _fitz_stub

import fitz  # PyMuPDF

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

from _paths import OLLAMA_PORT

OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
VISION_MODEL = "llava:latest"


@pytest.fixture
def pdf_path(tmp_path):
    """ダミーPDFパスを返す（fitz.open はモック済み）。"""
    dummy = tmp_path / "dummy.pdf"
    dummy.write_bytes(b"%PDF-1.4")
    return str(dummy)


def test_vision_llm_single_page(pdf_path: str, page_num: int = 0):
    """1ページだけVision LLMで処理"""
    print(f"PDFを読み込み中: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    if page_num >= len(doc):
        print(f"エラー: ページ {page_num} は存在しません（総ページ数: {len(doc)}）")
        return
    
    print(f"ページ {page_num + 1} を処理中...")
    page = doc[page_num]
    
    # 高解像度で画像に変換
    zoom = 2.0  # 200 DPI相当（軽量化）
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # 一時画像ファイルに保存
    temp_image_path = f"test_page_{page_num + 1}.png"
    pix.save(temp_image_path)
    print(f"画像を保存: {temp_image_path}")
    
    # 画像をbase64エンコード
    with open(temp_image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Vision LLMに送信
    prompt = """この画像に含まれるすべてのテキストを正確に抽出してください。
以下の指示に従ってください：
1. 画像内のすべての文字、数字、記号を正確に読み取ってください
2. レイアウト（表、リスト、段落）を可能な限り保持してください
3. 表の場合は、行と列の構造を保持してください
4. 日本語と英語の両方を正確に認識してください
5. 数値データは特に注意深く読み取ってください

抽出したテキストのみを返してください（説明は不要）:"""
    
    messages = [
        {
            "role": "user",
            "content": prompt,
            "images": [image_base64]
        }
    ]
    
    print(f"Vision LLM ({VISION_MODEL}) で認識中...（時間がかかる場合があります）")
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": VISION_MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=600  # 10分（GPU使用時は高速化）
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('message', {}).get('content', '').strip()
            
            if text:
                print(f"\n✅ 認識成功！")
                print(f"抽出されたテキスト（最初の500文字）:")
                print(text[:500])
                print(f"\n総文字数: {len(text)}文字")
                
                # テキストをファイルに保存
                output_file = f"test_vision_llm_page_{page_num + 1}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"\n結果を保存: {output_file}")
            else:
                print("⚠️ テキストを認識できませんでした")
        else:
            print(f"⚠️ APIエラー: {response.status_code}")
            print(response.text[:200])
            
    except requests.exceptions.Timeout:
        print("⚠️ タイムアウト: Vision LLMの処理に時間がかかりすぎています")
    except Exception as e:
        print(f"⚠️ エラー: {e}")
    
    # 一時ファイルを削除
    if os.path.exists(temp_image_path):
        os.remove(temp_image_path)
    
    doc.close()

if __name__ == "__main__":
    pdf_path = "SKM_C287i26011416440.pdf"  # type: ignore
    
    if not os.path.exists(pdf_path):  # type: ignore
        print(f"エラー: PDFファイルが見つかりません: {pdf_path}")
        print("Google Driveからダウンロードしてください")
        sys.exit(1)
    
    # 最初のページだけ処理
    test_vision_llm_single_page(pdf_path, page_num=0)  # type: ignore
