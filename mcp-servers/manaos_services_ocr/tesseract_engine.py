#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tesseract OCR Engine
完全無料、オープンソース、90-95%精度
"""

import pytesseract
from PIL import Image
import time
from typing import Dict, Any

class TesseractEngine:
    def __init__(self):
        self.name = "Tesseract OCR"
        self.version = pytesseract.get_tesseract_version()
        
    def extract_text(self, image_path: str, lang: str = 'jpn+eng') -> Dict[str, Any]:
        """
        画像からテキストを抽出
        
        Args:
            image_path: 画像ファイルパス
            lang: 言語 (jpn=日本語, eng=英語, jpn+eng=両方)
            
        Returns:
            抽出結果の辞書
        """
        start_time = time.time()
        
        try:
            # 画像読み込み
            image = Image.open(image_path)
            
            # OCR実行
            text = pytesseract.image_to_string(image, lang=lang)
            
            # 詳細データ取得（座標、信頼度など）
            data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
            
            # 平均信頼度計算
            confidences = [float(conf) for conf in data['conf'] if conf != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'engine': 'tesseract',
                'text': text.strip(),
                'confidence': avg_confidence,
                'word_count': len(text.split()),
                'char_count': len(text),
                'language': lang,
                'processing_time': processing_time,
                'details': {
                    'words': data['text'],
                    'confidences': [float(c) for c in data['conf']],
                    'boxes': [(int(l), int(t), int(w), int(h)) for l, t, w, h in zip(data['left'], data['top'], data['width'], data['height'])]
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'engine': 'tesseract',
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def get_supported_languages(self):
        """サポートされている言語一覧を取得"""
        return pytesseract.get_languages()
    
    def get_info(self) -> Dict[str, Any]:
        """エンジン情報を取得"""
        return {
            'name': self.name,
            'version': str(self.version),
            'supported_languages': self.get_supported_languages(),
            'cost': 'Free',
            'accuracy': '90-95%',
            'speed': 'Fast'
        }

if __name__ == "__main__":
    # テスト
    engine = TesseractEngine()
    print(f"Tesseract Engine Info: {engine.get_info()}")

