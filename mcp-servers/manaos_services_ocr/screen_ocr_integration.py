#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mana Screen Sharing System + OCR統合
リアルタイム画面監視→自動OCR→ログ保存
"""

import asyncio
import websockets
import json
import base64
import time
import sys
import io
from PIL import Image
from datetime import datetime
import logging

# OCRエンジンインポート
sys.path.insert(0, '/root/ocr_system')
from engines.tesseract_engine import TesseractEngine
from engines.easyocr_engine import EasyOCREngine
from engines.vision_api_engine import VisionAPIEngine

# ログ設定
logging.basicConfig(
    filename='/root/logs/screen_ocr_integration.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScreenOCRIntegration:
    def __init__(self, engine_name='tesseract', auto_mode=False):
        """
        Args:
            engine_name: 使用するエンジン (tesseract/easyocr/vision_api)
            auto_mode: 自動モード（定期的にOCR実行）
        """
        self.engine_name = engine_name
        self.auto_mode = auto_mode
        self.interval = 10  # 自動モード時の間隔（秒）
        
        # OCRエンジン初期化
        logger.info(f"Initializing {engine_name} engine...")
        
        if engine_name == 'tesseract':
            self.engine = TesseractEngine()
        elif engine_name == 'easyocr':
            self.engine = EasyOCREngine()
        elif engine_name == 'vision_api':
            self.engine = VisionAPIEngine()
        else:
            raise ValueError(f"Unknown engine: {engine_name}")
        
        logger.info(f"Engine ready: {self.engine.get_info()}")
        
        # OCR履歴
        self.history = []
        self.max_history = 100
        
    def process_screenshot(self, image_data: str) -> dict:
        """
        Base64画像データをOCR処理
        
        Args:
            image_data: Base64エンコードされた画像
            
        Returns:
            OCR結果
        """
        try:
            # Base64デコード
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # 一時ファイル保存
            temp_path = f"/tmp/screen_ocr_{int(time.time())}.png"
            image.save(temp_path)
            
            # OCR実行
            if self.engine_name == 'tesseract':
                result = self.engine.extract_text(temp_path, lang='jpn+eng')
            else:
                result = self.engine.extract_text(temp_path)
            
            # 履歴追加
            result['timestamp'] = datetime.now().isoformat()
            self.history.append(result)
            
            # 履歴制限
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            
            logger.info(f"OCR completed: {result.get('char_count', 0)} chars, {result.get('processing_time', 0):.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def connect_to_screen_sharing(self, ws_url='ws://localhost:5008/ws'):
        """
        Screen Sharing SystemのWebSocketに接続してリアルタイムOCR
        
        Args:
            ws_url: WebSocketエンドポイント
        """
        logger.info(f"Connecting to {ws_url}...")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info("Connected to Screen Sharing System")
                print("✅ Screen Sharing Systemに接続しました")
                print(f"エンジン: {self.engine_name}")
                print(f"自動モード: {'ON' if self.auto_mode else 'OFF'}")
                print("=" * 60)
                
                # スクリーンショット要求
                await websocket.send(json.dumps({
                    'action': 'request_screenshot'
                }))
                
                last_ocr_time = 0
                
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        if data.get('type') == 'screenshot':
                            # 自動モードチェック
                            current_time = time.time()
                            
                            if self.auto_mode and (current_time - last_ocr_time) >= self.interval:
                                image_data = data.get('image')
                                
                                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] OCR処理中...")
                                result = self.process_screenshot(image_data)
                                
                                if result.get('success'):
                                    print(f"✅ 成功: {result.get('char_count')} 文字検出")
                                    print(f"処理時間: {result.get('processing_time', 0):.2f}秒")
                                    
                                    # テキストプレビュー（最初の100文字）
                                    text = result.get('text', '')
                                    if text:
                                        preview = text[:100].replace('\n', ' ')
                                        print(f"テキスト: {preview}...")
                                else:
                                    print(f"❌ エラー: {result.get('error')}")
                                
                                last_ocr_time = current_time
                                
                                # 次のスクリーンショット要求
                                await websocket.send(json.dumps({
                                    'action': 'request_screenshot'
                                }))
                        
                    except asyncio.TimeoutError:
                        # タイムアウトは無視して続行
                        if self.auto_mode:
                            await websocket.send(json.dumps({
                                'action': 'request_screenshot'
                            }))
                        continue
                    
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            print(f"❌ 接続エラー: {e}")
    
    def get_history(self, limit=10):
        """
        OCR履歴を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            履歴リスト
        """
        return self.history[-limit:]
    
    def save_history(self, filepath='/root/ocr_system/ocr_history.json'):
        """履歴をJSONファイルに保存"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
        
        logger.info(f"History saved: {len(self.history)} items")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Screen Sharing + OCR Integration')
    parser.add_argument('--engine', choices=['tesseract', 'easyocr', 'vision_api'],
                       default='tesseract', help='OCR engine to use')
    parser.add_argument('--auto', action='store_true',
                       help='Enable auto mode (periodic OCR)')
    parser.add_argument('--interval', type=int, default=10,
                       help='Auto mode interval in seconds')
    parser.add_argument('--ws-url', default='ws://localhost:5008/ws',
                       help='Screen Sharing WebSocket URL')
    
    args = parser.parse_args()
    
    # 統合システム起動
    integration = ScreenOCRIntegration(
        engine_name=args.engine,
        auto_mode=args.auto
    )
    
    integration.interval = args.interval
    
    print("=" * 60)
    print("🔍 Mana Screen Sharing + OCR Integration")
    print("=" * 60)
    print(f"エンジン情報: {integration.engine.get_info()}")
    print("=" * 60)
    
    try:
        await integration.connect_to_screen_sharing(args.ws_url)
    except KeyboardInterrupt:
        print("\n\n終了します...")
        integration.save_history()
        print(f"履歴を保存しました: {len(integration.history)} 件")

if __name__ == '__main__':
    asyncio.run(main())














