#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EasyOCR Engine
GPU/CPU自動切替、日本語精度やや高め
"""

import easyocr
import time
import torch
from typing import Dict, Any

class EasyOCREngine:
    def __init__(self, gpu: bool = None):
        """
        Args:
            gpu: GPU使用フラグ（Noneの場合は自動判定）
        """
        self.name = "EasyOCR"
        
        # GPU自動判定
        if gpu is None:
            gpu = torch.cuda.is_available()
        
        self.gpu = gpu
        self.device = 'cuda' if gpu else 'cpu'
        
        # リーダー初期化（日本語・英語対応）
        print(f"[EasyOCR] Initializing... (GPU: {gpu})")
        self.reader = easyocr.Reader(['ja', 'en'], gpu=gpu)
        print(f"[EasyOCR] Ready on {self.device}")
        
    def extract_text(self, image_path: str, detail: int = 1) -> Dict[str, Any]:
        """
        画像からテキストを抽出
        
        Args:
            image_path: 画像ファイルパス
            detail: 詳細レベル (0=テキストのみ, 1=座標+信頼度)
            
        Returns:
            抽出結果の辞書
        """
        start_time = time.time()
        
        try:
            # OCR実行
            results = self.reader.readtext(image_path, detail=detail)
            
            # テキスト結合
            if detail == 0:
                text = ' '.join(results)
                avg_confidence = None
            else:
                text = ' '.join([item[1] for item in results])
                confidences = [item[2] for item in results]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            processing_time = time.time() - start_time
            
            result = {
                'success': True,
                'engine': 'easyocr',
                'text': text.strip(),
                'word_count': len(text.split()),
                'char_count': len(text),
                'processing_time': processing_time,
                'device': self.device
            }
            
            if detail == 1:
                result['confidence'] = float(avg_confidence * 100)  # パーセント表記
                result['details'] = {
                    'boxes': [[float(coord) for coord in box] for box in [item[0] for item in results]],
                    'texts': [item[1] for item in results],
                    'confidences': [float(item[2] * 100) for item in results]
                }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'engine': 'easyocr',
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def get_info(self) -> Dict[str, Any]:
        """エンジン情報を取得"""
        return {
            'name': self.name,
            'device': self.device,
            'gpu_available': torch.cuda.is_available(),
            'supported_languages': ['Japanese', 'English', '80+ others'],
            'cost': 'Free',
            'accuracy': '92-97%',
            'speed': 'Medium' if self.gpu else 'Slow'
        }

if __name__ == "__main__":
    # テスト
    engine = EasyOCREngine()
    print(f"EasyOCR Engine Info: {engine.get_info()}")

