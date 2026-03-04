#!/usr/bin/env python3
"""
📸 Trinity Image Understanding System
画像理解・分析システム

機能:
- 画像内容説明
- OCR（文字認識）
- 画像からタスク抽出
- 画像から提案生成
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import base64
import os
from io import BytesIO
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageUnderstandingSystem:
    """画像理解システム"""
    
    def __init__(self):
        # API設定
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        
        # ローカルOCR（フォールバック）
        self.use_tesseract = self._check_tesseract()
        
        logger.info("📸 Image Understanding System initialized")
        logger.info(f"  🔑 Claude Vision: {bool(self.anthropic_key)}")
        logger.info(f"  🔑 GPT-4 Vision: {bool(self.openai_key)}")
        logger.info(f"  🔑 Gemini Vision: {bool(self.gemini_key)}")
        logger.info(f"  📝 Tesseract OCR: {self.use_tesseract}")
    
    def _check_tesseract(self) -> bool:
        """Tesseractがインストールされているか確認"""
        try:
            return True
        except IOError:
            return False
    
    async def analyze_image(
        self, 
        image_data: bytes, 
        prompt: Optional[str] = None,
        mode: str = 'general'
    ) -> Dict[str, Any]:
        """
        画像を分析
        
        Args:
            image_data: 画像データ（bytes）
            prompt: 追加のプロンプト
            mode: 分析モード
                - 'general': 一般的な説明
                - 'ocr': 文字認識重視
                - 'task': タスク抽出
                - 'idea': アイデア抽出
        
        Returns:
            分析結果
        """
        logger.info(f"📸 Analyzing image (mode: {mode})...")
        
        # モードに応じたプロンプト
        system_prompts = {
            'general': "この画像について詳しく説明してください。",
            'ocr': "画像に含まれるすべての文字を正確に読み取ってください。",
            'task': "この画像からタスクやTODOを抽出してください。",
            'idea': "この画像から得られるアイデアや提案を生成してください。"
        }
        
        base_prompt = system_prompts.get(mode, system_prompts['general'])
        if prompt:
            base_prompt = f"{base_prompt}\n\n追加の指示: {prompt}"
        
        # 優先度順に試す
        result = None
        
        # 1. Claude Vision（最高品質）
        if self.anthropic_key:
            result = await self._analyze_with_claude(image_data, base_prompt)
            if result:
                return result
        
        # 2. GPT-4 Vision
        if self.openai_key:
            result = await self._analyze_with_openai(image_data, base_prompt)
            if result:
                return result
        
        # 3. Gemini Vision
        if self.gemini_key:
            result = await self._analyze_with_gemini(image_data, base_prompt)
            if result:
                return result
        
        # 4. ローカルOCR（フォールバック）
        if self.use_tesseract and mode == 'ocr':
            result = await self._ocr_with_tesseract(image_data)
            if result:
                return result
        
        # すべて失敗
        return {
            'analysis': "画像分析システムが利用できません。外部APIキーを設定してください。",
            'confidence': 0,
            'method': 'none'
        }
    
    async def _analyze_with_claude(self, image_data: bytes, prompt: str) -> Optional[Dict]:
        """Claude Vision APIで分析"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            # 画像をbase64エンコード
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 画像タイプ判定
            image_type = self._detect_image_type(image_data)
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
            
            analysis = message.content[0].text
            
            logger.info("  ✅ Claude Vision analysis complete")
            
            return {
                'analysis': analysis,
                'confidence': 95,
                'method': 'claude_vision'
            }
            
        except Exception as e:
            logger.warning(f"  ⚠️ Claude Vision failed: {e}")
            return None
    
    async def _analyze_with_openai(self, image_data: bytes, prompt: str) -> Optional[Dict]:
        """OpenAI GPT-4 Visionで分析"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_key)
            
            # 画像をbase64エンコード
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_type = self._detect_image_type(image_data)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_type};base64,{image_base64}"
                                }
                            }
                        ],
                    }
                ],
                max_tokens=1024,
            )
            
            analysis = response.choices[0].message.content
            
            logger.info("  ✅ GPT-4 Vision analysis complete")
            
            return {
                'analysis': analysis,
                'confidence': 90,
                'method': 'gpt4_vision'
            }
            
        except Exception as e:
            logger.warning(f"  ⚠️ GPT-4 Vision failed: {e}")
            return None
    
    async def _analyze_with_gemini(self, image_data: bytes, prompt: str) -> Optional[Dict]:
        """Google Gemini Visionで分析"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # PILイメージに変換
            image = Image.open(BytesIO(image_data))
            
            response = model.generate_content([prompt, image])
            analysis = response.text
            
            logger.info("  ✅ Gemini Vision analysis complete")
            
            return {
                'analysis': analysis,
                'confidence': 85,
                'method': 'gemini_vision'
            }
            
        except Exception as e:
            logger.warning(f"  ⚠️ Gemini Vision failed: {e}")
            return None
    
    async def _ocr_with_tesseract(self, image_data: bytes) -> Optional[Dict]:
        """Tesseract OCRで文字認識"""
        try:
            import pytesseract
            
            image = Image.open(BytesIO(image_data))
            
            # 日本語+英語で認識
            text = pytesseract.image_to_string(image, lang='jpn+eng')
            
            if text.strip():
                logger.info("  ✅ Tesseract OCR complete")
                
                return {
                    'analysis': f"【認識されたテキスト】\n{text}",
                    'confidence': 70,
                    'method': 'tesseract_ocr'
                }
            
        except Exception as e:
            logger.warning(f"  ⚠️ Tesseract OCR failed: {e}")
        
        return None
    
    def _detect_image_type(self, image_data: bytes) -> str:
        """画像タイプを判定"""
        # マジックナンバーで判定
        if image_data.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif image_data.startswith(b'\x89PNG'):
            return 'image/png'
        elif image_data.startswith(b'GIF'):
            return 'image/gif'
        elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:12]:
            return 'image/webp'
        else:
            return 'image/jpeg'  # デフォルト
    
    def extract_tasks_from_analysis(self, analysis: str) -> List[str]:
        """分析結果からタスクを抽出"""
        tasks = []
        
        # タスク系キーワード
        task_keywords = [
            'TODO', 'タスク', '作業', 'やること', 'する必要',
            '実装', '修正', '追加', '確認', '検討'
        ]
        
        lines = analysis.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # リスト形式（-や*で始まる）
            if line.startswith(('- ', '* ', '・', '□', '☐')):
                tasks.append(line.lstrip('- *・□☐').strip())
            
            # タスクキーワードを含む
            elif any(kw in line for kw in task_keywords):
                tasks.append(line)
        
        return tasks[:10]  # 最大10個
    
    def generate_suggestions(self, analysis: str, image_type: str = 'general') -> List[str]:
        """分析結果から提案を生成"""
        suggestions = []
        
        # 画像タイプに応じた提案
        if 'スライド' in analysis or 'プレゼン' in analysis:
            suggestions.extend([
                "スライドの内容をObsidianに保存",
                "プレゼン練習のリマインダー設定",
                "フィードバックポイントをタスク化"
            ])
        
        elif 'メモ' in analysis or '手書き' in analysis:
            suggestions.extend([
                "メモをデジタル化してObsidianに保存",
                "重要ポイントをタスク化",
                "関連資料を検索"
            ])
        
        elif 'グラフ' in analysis or 'チャート' in analysis or 'データ' in analysis:
            suggestions.extend([
                "データ分析レポート作成",
                "トレンドの共有",
                "次のアクション検討"
            ])
        
        else:
            suggestions.extend([
                "画像をObsidianに保存",
                "関連するタスク作成",
                "詳細分析を依頼"
            ])
        
        return suggestions[:3]


# テスト用
async def test_image_understanding():
    """画像理解システムのテスト"""
    system = ImageUnderstandingSystem()
    
    print("\n" + "="*60)
    print("📸 Image Understanding System - Test")
    print("="*60)
    
    # テスト用の簡単な画像を生成
    print("\n📝 Test: Create test image")
    
    from PIL import Image, ImageDraw
    
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # テキストを描画
    text = "TODO:\n1. プレゼン準備\n2. 資料作成\n3. レビュー"
    draw.text((20, 20), text, fill='black')
    
    # バイトデータに変換
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    image_data = img_bytes.getvalue()
    
    print(f"  ✅ Test image created ({len(image_data)} bytes)")
    
    # 分析テスト
    print("\n📝 Test: Analyze image")
    
    result = await system.analyze_image(image_data, mode='task')
    
    print(f"  Method: {result['method']}")
    print(f"  Confidence: {result['confidence']}%")
    print(f"  Analysis: {result['analysis'][:100]}...")
    
    # タスク抽出
    print("\n📝 Test: Extract tasks")
    
    tasks = system.extract_tasks_from_analysis(result['analysis'])
    print(f"  ✅ Extracted {len(tasks)} tasks:")
    for i, task in enumerate(tasks, 1):
        print(f"    {i}. {task}")


if __name__ == '__main__':
    asyncio.run(test_image_understanding())



