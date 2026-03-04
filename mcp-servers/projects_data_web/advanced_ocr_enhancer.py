#!/usr/bin/env python3
"""
高度OCR機能強化モジュール
日本語認識精度向上、複数OCRエンジン対応、前処理最適化
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import logging
import time
from typing import List, Dict, Any, Tuple
import os

class AdvancedOCREnhancer:
    def __init__(self):
        self.setup_logging()
        self.ocr_configs = {
            'japanese': '--oem 3 --psm 6 -l jpn',
            'english': '--oem 3 --psm 6 -l eng',
            'mixed': '--oem 3 --psm 6 -l jpn+eng',
            'table': '--oem 3 --psm 6 -l jpn --tessdata-dir /usr/share/tesseract-ocr/4.00/tessdata/'
        }
        self.preprocessing_methods = [
            'original', 'grayscale', 'binary', 'adaptive_binary',
            'gaussian_blur', 'median_blur', 'sharpen', 'enhance_contrast'
        ]
        
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('AdvancedOCREnhancer')
        
    def preprocess_image(self, image: Image.Image, method: str = 'adaptive_binary') -> Image.Image:
        """画像前処理の最適化"""
        self.logger.info(f"🔄 画像前処理開始: {method}")
        
        # PIL画像をOpenCV形式に変換
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        if method == 'original':
            processed = cv_image
        elif method == 'grayscale':
            processed = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        elif method == 'binary':
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            _, processed = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        elif method == 'adaptive_binary':
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            processed = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
        elif method == 'gaussian_blur':
            processed = cv2.GaussianBlur(cv_image, (5, 5), 0)
        elif method == 'median_blur':
            processed = cv2.medianBlur(cv_image, 5)
        elif method == 'sharpen':
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            processed = cv2.filter2D(cv_image, -1, kernel)
        elif method == 'enhance_contrast':
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            processed = cv2.merge([l, a, b])
            processed = cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)
        else:
            processed = cv_image
            
        # OpenCV形式をPIL形式に戻す
        if len(processed.shape) == 2:  # グレースケール
            return Image.fromarray(processed)
        else:
            return Image.fromarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))
    
    def extract_text_with_multiple_methods(self, image: Image.Image) -> Dict[str, str]:
        """複数OCR方法でのテキスト抽出"""
        results = {}
        
        for method in self.preprocessing_methods:
            try:
                self.logger.info(f"🔍 OCR実行: {method}")
                
                # 前処理
                processed_image = self.preprocess_image(image, method)
                
                # OCR実行
                for lang, config in self.ocr_configs.items():
                    try:
                        text = pytesseract.image_to_string(
                            processed_image, 
                            config=config
                        ).strip()
                        
                        if text:  # 空でない場合のみ記録
                            key = f"{method}_{lang}"
                            results[key] = text
                            
                    except Exception as e:
                        self.logger.warning(f"❌ OCR失敗: {method}_{lang} - {e}")
                        
            except Exception as e:
                self.logger.error(f"❌ 前処理失敗: {method} - {e}")
                
        return results
    
    def analyze_text_quality(self, text: str) -> Dict[str, Any]:
        """テキスト品質分析"""
        if not text:
            return {
                'length': 0,
                'japanese_ratio': 0,
                'english_ratio': 0,
                'numeric_ratio': 0,
                'special_char_ratio': 0,
                'line_count': 0,
                'quality_score': 0
            }
        
        # 文字数統計
        total_chars = len(text)
        japanese_chars = sum(1 for c in text if '\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FAF')
        english_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        numeric_chars = sum(1 for c in text if c.isdigit())
        special_chars = total_chars - japanese_chars - english_chars - numeric_chars
        
        # 比率計算
        japanese_ratio = japanese_chars / total_chars if total_chars > 0 else 0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0
        numeric_ratio = numeric_chars / total_chars if total_chars > 0 else 0
        special_char_ratio = special_chars / total_chars if total_chars > 0 else 0
        
        # 行数
        line_count = len(text.split('\n'))
        
        # 品質スコア計算
        quality_score = (
            min(japanese_ratio * 100, 40) +  # 日本語比率（最大40点）
            min(english_ratio * 100, 30) +   # 英語比率（最大30点）
            min(numeric_ratio * 100, 20) +   # 数字比率（最大20点）
            min(100 - special_char_ratio * 200, 10)  # 特殊文字ペナルティ（最大10点）
        )
        
        return {
            'length': total_chars,
            'japanese_ratio': japanese_ratio,
            'english_ratio': english_ratio,
            'numeric_ratio': numeric_ratio,
            'special_char_ratio': special_char_ratio,
            'line_count': line_count,
            'quality_score': quality_score
        }
    
    def select_best_result(self, results: Dict[str, str]) -> Tuple[str, str, Dict[str, Any]]:
        """最良のOCR結果を選択"""
        self.logger.info("🎯 最良のOCR結果選択開始")
        
        best_score = 0
        best_method = ""
        best_text = ""
        best_analysis = {}
        
        for method, text in results.items():
            analysis = self.analyze_text_quality(text)
            score = analysis['quality_score']
            
            self.logger.info(f"📊 {method}: スコア={score:.1f}, 文字数={analysis['length']}")
            
            if score > best_score:
                best_score = score
                best_method = method
                best_text = text
                best_analysis = analysis
        
        self.logger.info(f"🏆 最良結果: {best_method} (スコア: {best_score:.1f})")
        return best_method, best_text, best_analysis
    
    def enhance_ocr_accuracy(self, image_path: str) -> Dict[str, Any]:
        """OCR精度向上のメイン処理"""
        self.logger.info(f"🚀 OCR精度向上開始: {image_path}")
        
        start_time = time.time()
        
        try:
            # 画像読み込み
            image = Image.open(image_path)
            self.logger.info(f"📷 画像読み込み完了: {image.size}")
            
            # 複数方法でOCR実行
            results = self.extract_text_with_multiple_methods(image)
            self.logger.info(f"🔍 OCR結果数: {len(results)}")
            
            # 最良の結果を選択
            best_method, best_text, best_analysis = self.select_best_result(results)
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            # 結果まとめ
            result = {
                'image_path': image_path,
                'best_method': best_method,
                'best_text': best_text,
                'analysis': best_analysis,
                'all_results': results,
                'processing_time': processing_time,
                'success': True
            }
            
            self.logger.info(f"✅ OCR精度向上完了: {processing_time:.2f}秒")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ OCR精度向上エラー: {e}")
            return {
                'image_path': image_path,
                'error': str(e),
                'success': False,
                'processing_time': time.time() - start_time
            }
    
    def batch_ocr_enhancement(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """バッチOCR精度向上処理"""
        self.logger.info(f"🔄 バッチOCR精度向上開始: {len(image_paths)}ファイル")
        
        results = []
        for i, image_path in enumerate(image_paths, 1):
            self.logger.info(f"📁 処理中 ({i}/{len(image_paths)}): {os.path.basename(image_path)}")
            result = self.enhance_ocr_accuracy(image_path)
            results.append(result)
            
        # 統計計算
        success_count = sum(1 for r in results if r['success'])
        total_time = sum(r.get('processing_time', 0) for r in results)
        avg_score = np.mean([r.get('analysis', {}).get('quality_score', 0) for r in results if r['success']])
        
        self.logger.info(f"🎯 バッチ処理完了: 成功={success_count}/{len(image_paths)}, 平均品質スコア={avg_score:.1f}")
        
        return results

def main():
    """メイン実行関数"""
    print("🚀 高度OCR機能強化テスト開始")
    print("=" * 50)
    
    enhancer = AdvancedOCREnhancer()
    
    # テスト用画像パス（実際の画像ファイルに置き換え）
    test_images = [
        "/home/mana/Desktop/test_image.jpg",  # テスト用（存在しない場合はスキップ）
    ]
    
    # 存在する画像のみフィルタリング
    existing_images = [img for img in test_images if os.path.exists(img)]
    
    if not existing_images:
        print("📷 テスト用画像が見つかりません。模擬テストを実行します。")
        
        # 模擬テスト用の結果
        mock_result = {
            'image_path': 'mock_test.jpg',
            'best_method': 'adaptive_binary_japanese',
            'best_text': 'これは日本語OCRのテストです。\n英語Englishも含まれています。\n数字123も認識されます。',
            'analysis': {
                'length': 45,
                'japanese_ratio': 0.6,
                'english_ratio': 0.2,
                'numeric_ratio': 0.07,
                'special_char_ratio': 0.13,
                'line_count': 3,
                'quality_score': 85.2
            },
            'processing_time': 2.5,
            'success': True
        }
        
        print("🎯 模擬OCR結果:")
        print(f"✅ 最良方法: {mock_result['best_method']}")
        print(f"📊 品質スコア: {mock_result['analysis']['quality_score']:.1f}")
        print(f"📝 抽出テキスト: {mock_result['best_text'][:50]}...")
        print(f"⏱️ 処理時間: {mock_result['processing_time']:.2f}秒")
        
    else:
        # 実際の画像でテスト
        results = enhancer.batch_ocr_enhancement(existing_images)
        
        for result in results:
            if result['success']:
                print(f"✅ {os.path.basename(result['image_path'])}: スコア={result['analysis']['quality_score']:.1f}")
            else:
                print(f"❌ {os.path.basename(result['image_path'])}: エラー")
    
    print("\n🎉 OCR機能強化テスト完了!")

if __name__ == "__main__":
    main()

