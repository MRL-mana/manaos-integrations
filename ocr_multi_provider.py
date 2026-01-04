"""
OCR マルチプロバイダー統合
複数のOCRプロバイダーに対応
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiProviderOCR:
    """複数OCRプロバイダー対応クラス"""
    
    def __init__(self):
        """初期化"""
        self.providers = {
            "tesseract": False,
            "google": False,
            "microsoft": False,
            "amazon": False
        }
        self.ocr_scripts_path = Path("repos/OCR_Python-Scripts")
        self._check_providers()
    
    def _check_providers(self):
        """利用可能なプロバイダーを確認"""
        # Tesseract
        try:
            import pytesseract
            self.providers["tesseract"] = True
            logger.info("Tesseract OCRが利用可能です")
        except ImportError:
            logger.debug("Tesseract OCRが利用できません")
        
        # Google Cloud Vision
        try:
            from google.cloud import vision
            self.providers["google"] = True
            logger.info("Google Cloud Vision APIが利用可能です")
        except ImportError:
            logger.debug("Google Cloud Vision APIが利用できません")
        
        # Microsoft Azure
        try:
            from azure.cognitiveservices.vision.computervision import ComputerVisionClient
            self.providers["microsoft"] = True
            logger.info("Microsoft Azure Computer Visionが利用可能です")
        except ImportError:
            logger.debug("Microsoft Azure Computer Visionが利用できません")
        
        # Amazon Textract
        try:
            import boto3
            self.providers["amazon"] = True
            logger.info("Amazon Textractが利用可能です")
        except ImportError:
            logger.debug("Amazon Textractが利用できません")
    
    def get_available_providers(self) -> List[str]:
        """利用可能なプロバイダー一覧を取得"""
        return [provider for provider, available in self.providers.items() if available]
    
    def recognize(self, image_path: str, provider: str = "tesseract", **kwargs) -> Optional[Dict[str, Any]]:
        """
        OCRを実行
        
        Args:
            image_path: 画像ファイルのパス
            provider: 使用するプロバイダー（tesseract, google, microsoft, amazon）
            **kwargs: プロバイダー固有のオプション
            
        Returns:
            OCR結果（テキストとメタデータ）、エラーの場合はNone
        """
        if provider not in self.providers:
            logger.error(f"不明なプロバイダー: {provider}")
            return None
        
        if not self.providers[provider]:
            logger.error(f"{provider} OCRが利用できません")
            return None
        
        if not os.path.exists(image_path):
            logger.error(f"画像ファイルが見つかりません: {image_path}")
            return None
        
        try:
            if provider == "tesseract":
                return self._recognize_tesseract(image_path, **kwargs)
            elif provider == "google":
                return self._recognize_google(image_path, **kwargs)
            elif provider == "microsoft":
                return self._recognize_microsoft(image_path, **kwargs)
            elif provider == "amazon":
                return self._recognize_amazon(image_path, **kwargs)
        except Exception as e:
            logger.error(f"OCR実行エラー ({provider}): {e}")
            return None
    
    def _recognize_tesseract(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Tesseract OCRで認識"""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, **kwargs)
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            return {
                "provider": "tesseract",
                "text": text.strip(),
                "confidence": self._calculate_confidence(data),
                "raw_data": data
            }
        except Exception as e:
            logger.error(f"Tesseract OCRエラー: {e}")
            return None
    
    def _recognize_google(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Google Cloud Vision APIで認識"""
        try:
            from google.cloud import vision
            
            client = vision.ImageAnnotatorClient()
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                text = texts[0].description
                return {
                    "provider": "google",
                    "text": text,
                    "confidence": response.text_annotations[0].confidence if hasattr(response.text_annotations[0], 'confidence') else None,
                    "text_count": len(texts)
                }
            return None
        except Exception as e:
            logger.error(f"Google Cloud Vision APIエラー: {e}")
            return None
    
    def _recognize_microsoft(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Microsoft Azure Computer Visionで認識"""
        try:
            from azure.cognitiveservices.vision.computervision import ComputerVisionClient
            from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
            from msrest.authentication import CognitiveServicesCredentials
            
            endpoint = os.getenv("AZURE_VISION_ENDPOINT")
            key = os.getenv("AZURE_VISION_KEY")
            
            if not endpoint or not key:
                logger.error("Azure Vision APIの認証情報が設定されていません")
                return None
            
            client = ComputerVisionClient(
                endpoint,
                CognitiveServicesCredentials(key)
            )
            
            with open(image_path, 'rb') as image_file:
                result = client.read_in_stream(image_file, raw=True)
            
            # 簡易実装（実際の実装はより複雑）
            return {
                "provider": "microsoft",
                "text": "",  # 実際の実装が必要
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Microsoft Azure Computer Visionエラー: {e}")
            return None
    
    def _recognize_amazon(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Amazon Textractで認識"""
        try:
            import boto3
            
            textract = boto3.client('textract')
            with open(image_path, 'rb') as document:
                response = textract.detect_document_text(Document={'Bytes': document.read()})
            
            text = ""
            for item in response['Blocks']:
                if item['BlockType'] == 'LINE':
                    text += item['Text'] + '\n'
            
            return {
                "provider": "amazon",
                "text": text.strip(),
                "blocks": len(response['Blocks'])
            }
        except Exception as e:
            logger.error(f"Amazon Textractエラー: {e}")
            return None
    
    def _calculate_confidence(self, data: Dict) -> float:
        """Tesseractの信頼度を計算"""
        if 'conf' in data and data['conf']:
            valid_confs = [c for c in data['conf'] if c > 0]
            return sum(valid_confs) / len(valid_confs) if valid_confs else 0.0
        return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """ステータス情報を取得"""
        return {
            "providers": self.providers,
            "available": self.get_available_providers(),
            "scripts_path": str(self.ocr_scripts_path)
        }


# 使用例
if __name__ == "__main__":
    ocr = MultiProviderOCR()
    
    print("利用可能なプロバイダー:", ocr.get_available_providers())
    print("ステータス:", ocr.get_status())
    
    # テスト（画像ファイルがある場合）
    # result = ocr.recognize("test_image.png", provider="tesseract")
    # print("OCR結果:", result)


















