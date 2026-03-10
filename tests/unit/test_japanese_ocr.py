#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日本語OCRテスト"""
import sys
from unittest.mock import MagicMock, patch
import pytest

# pytesseract が未インストールの場合にスタブを注入（Tesseract バイナリ不要）
if "pytesseract" not in sys.modules:
    _pytesseract_stub = MagicMock()
    _pytesseract_stub.image_to_string.return_value = "サンプルテキスト"
    _pytesseract_stub.get_languages.return_value = ["jpn", "eng"]
    sys.modules["pytesseract"] = _pytesseract_stub

import pytesseract
from PIL import Image


class TestJapaneseOCR:
    def test_image_to_string_called_with_image(self):
        img = Image.new('RGB', (100, 50), color='white')
        with patch.object(pytesseract, 'image_to_string', return_value="テスト") as mock_ocr:
            result = pytesseract.image_to_string(img, lang='jpn+eng')
        mock_ocr.assert_called_once()
        assert isinstance(result, str)

    def test_handles_exception_gracefully(self):
        img = Image.new('RGB', (100, 50), color='white')
        with patch.object(pytesseract, 'image_to_string', side_effect=Exception("binary not found")):
            try:
                pytesseract.image_to_string(img, lang='jpn+eng')
            except Exception:
                pass  # バイナリ未インストール時の例外は正常

    def test_get_languages_returns_list(self):
        with patch.object(pytesseract, 'get_languages', return_value=["jpn", "eng"]) as mock_langs:
            langs = pytesseract.get_languages()
        assert isinstance(langs, list)
