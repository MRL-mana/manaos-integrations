#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Vision API Engine
精度最高（99%+）、無料枠1000回/月
"""

from google.cloud import vision
import time
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

class VisionAPIEngine:
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Args:
            credentials_path: Google Cloud認証情報JSONパス
        """
        self.name = "Google Vision API"
        
        # 認証情報設定
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        # 使用量トラッキング用ファイル
        self.usage_file = '/root/ocr_system/vision_api_usage.json'
        self.monthly_limit = 1000  # 無料枠
        
        try:
            self.client = vision.ImageAnnotatorClient()
            self.available = True
        except Exception as e:
            print(f"[Vision API] Warning: {e}")
            self.available = False
    
    def check_quota(self) -> Dict[str, Any]:
        """使用量チェック"""
        if not os.path.exists(self.usage_file):
            usage_data = {
                'month': datetime.now().strftime('%Y-%m'),
                'count': 0,
                'history': []
            }
        else:
            with open(self.usage_file, 'r') as f:
                usage_data = json.load(f)
        
        # 月が変わったらリセット
        current_month = datetime.now().strftime('%Y-%m')
        if usage_data['month'] != current_month:
            usage_data = {
                'month': current_month,
                'count': 0,
                'history': []
            }
        
        remaining = self.monthly_limit - usage_data['count']
        
        return {
            'used': usage_data['count'],
            'limit': self.monthly_limit,
            'remaining': remaining,
            'quota_ok': remaining > 0
        }
    
    def update_usage(self):
        """使用量を更新"""
        quota = self.check_quota()
        
        usage_data = {
            'month': datetime.now().strftime('%Y-%m'),
            'count': quota['used'] + 1,
            'history': []
        }
        
        if os.path.exists(self.usage_file):
            with open(self.usage_file, 'r') as f:
                old_data = json.load(f)
                usage_data['history'] = old_data.get('history', [])
        
        usage_data['history'].append({
            'timestamp': datetime.now().isoformat(),
            'count': usage_data['count']
        })
        
        # 履歴は直近100件まで
        usage_data['history'] = usage_data['history'][-100:]
        
        with open(self.usage_file, 'w') as f:
            json.dump(usage_data, f, indent=2)
    
    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """
        画像からテキストを抽出
        
        Args:
            image_path: 画像ファイルパス
            
        Returns:
            抽出結果の辞書
        """
        start_time = time.time()
        
        if not self.available:
            return {
                'success': False,
                'engine': 'vision_api',
                'error': 'Vision API not available (credentials not configured)',
                'processing_time': time.time() - start_time
            }
        
        # クォータチェック
        quota = self.check_quota()
        if not quota['quota_ok']:
            return {
                'success': False,
                'engine': 'vision_api',
                'error': f"Monthly quota exceeded ({quota['used']}/{quota['limit']})",
                'quota': quota,
                'processing_time': time.time() - start_time
            }
        
        try:
            # 画像読み込み
            with open(image_path, 'rb') as f:
                content = f.read()
            
            image = vision.Image(content=content)
            
            # OCR実行（日本語・英語対応）
            response = self.client.document_text_detection(
                image=image,
                image_context={'language_hints': ['ja', 'en']}
            )
            
            if response.error.message:
                raise Exception(response.error.message)
            
            # テキスト抽出
            text = response.full_text_annotation.text if response.full_text_annotation else ''
            
            # 詳細データ
            details = {
                'pages': len(response.full_text_annotation.pages) if response.full_text_annotation else 0,
                'blocks': [],
                'paragraphs': [],
                'words': [],
                'symbols': []
            }
            
            if response.full_text_annotation:
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        details['blocks'].append({
                            'confidence': float(block.confidence),
                            'text': ''.join([
                                symbol.text 
                                for paragraph in block.paragraphs 
                                for word in paragraph.words 
                                for symbol in word.symbols
                            ])
                        })
            
            # 使用量更新
            self.update_usage()
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'engine': 'vision_api',
                'text': text.strip(),
                'confidence': details['blocks'][0]['confidence'] * 100 if details['blocks'] else 0,
                'word_count': len(text.split()),
                'char_count': len(text),
                'processing_time': processing_time,
                'quota': self.check_quota(),
                'details': details
            }
            
        except Exception as e:
            return {
                'success': False,
                'engine': 'vision_api',
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def get_info(self) -> Dict[str, Any]:
        """エンジン情報を取得"""
        quota = self.check_quota()
        
        return {
            'name': self.name,
            'available': self.available,
            'quota': quota,
            'supported_languages': ['80+ languages including Japanese and English'],
            'cost': 'Free tier: 1000/month, then $1.50/1000',
            'accuracy': '99%+',
            'speed': 'Fast'
        }

if __name__ == "__main__":
    # テスト
    engine = VisionAPIEngine()
    print(f"Vision API Engine Info: {engine.get_info()}")

