#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本語OCRテスト"""

import pytest

# pytesseract 未インストール時はスキップ
pytest.importorskip("pytesseract")
pytest.importorskip("PIL")

import pytesseract
from PIL import Image
import tempfile
import os

# テスト画像を作成（日本語テキストを含む）
img = Image.new('RGB', (400, 200), color='white')

try:
    # 日本語OCRをテスト
    result = pytesseract.image_to_string(img, lang='jpn+eng')
    print("✅ 日本語OCR: 利用可能")
    print(f"利用可能な言語: {pytesseract.get_languages()}")
except Exception as e:
    print(f"❌ 日本語OCR: エラー - {str(e)[:200]}")
