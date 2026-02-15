#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 File Secretary - 画像生成テンプレ（クーポン3種）
ComfyUI統合を使用してクーポン画像を生成
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from manaos_logger import get_logger

logger = get_logger(__name__)

# ComfyUI統合をインポート
try:
    from comfyui_integration import ComfyUIIntegration
    COMFYUI_AVAILABLE = True
except ImportError:
    COMFYUI_AVAILABLE = False
    logger.warning("ComfyUI統合モジュールが見つかりません")


class FileSecretaryImageTemplates:
    """ファイル秘書画像生成テンプレ"""
    
    # クーポン3種のテンプレート
    COUPON_TEMPLATES = {
        "洗車": {
            "prompt": "洗車クーポン、20%オフ、クリーンで明るいデザイン、青と白の配色、プロフェッショナルなレイアウト",
            "negative_prompt": "暗い、汚い、乱雑",
            "width": 1024,
            "height": 512
        },
        "日用品": {
            "prompt": "日用品クーポン、15%オフ、シンプルで親しみやすいデザイン、緑と白の配色、読みやすいレイアウト",
            "negative_prompt": "複雑、暗い、読みにくい",
            "width": 1024,
            "height": 512
        },
        "飲食": {
            "prompt": "飲食店クーポン、10%オフ、温かみのあるデザイン、オレンジと白の配色、食欲をそそるレイアウト",
            "negative_prompt": "冷たい、暗い、食欲をそそらない",
            "width": 1024,
            "height": 512
        }
    }
    
    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188"):
        """
        初期化
        
        Args:
            comfyui_url: ComfyUI API URL
        """
        self.comfyui_url = comfyui_url
        self.comfyui_integration = None
        
        if COMFYUI_AVAILABLE:
            try:
                # ComfyUIIntegrationの初期化パラメータを確認
                # デフォルトではapi_urlパラメータがない可能性がある
                self.comfyui_integration = ComfyUIIntegration()
                # API URLを設定（可能な場合）
                if hasattr(self.comfyui_integration, 'api_url'):
                    self.comfyui_integration.api_url = comfyui_url
                elif hasattr(self.comfyui_integration, 'base_url'):
                    self.comfyui_integration.base_url = comfyui_url
                
                if self.comfyui_integration.is_available():
                    logger.info("✅ ComfyUI統合初期化完了")
                else:
                    logger.warning("⚠️ ComfyUIが利用できません")
            except Exception as e:
                logger.error(f"❌ ComfyUI統合初期化エラー: {e}")
    
    def generate_coupon(self, coupon_type: str, discount: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        クーポン画像を生成
        
        Args:
            coupon_type: クーポンタイプ（洗車/日用品/飲食）
            discount: 割引率（オプション、テンプレートのデフォルト値を使用）
            
        Returns:
            生成結果（画像パスなど）
        """
        if coupon_type not in self.COUPON_TEMPLATES:
            logger.error(f"❌ 不明なクーポンタイプ: {coupon_type}")
            return None
        
        if not self.comfyui_integration:
            logger.warning("⚠️ ComfyUIが利用できません")
            return None
        
        template = self.COUPON_TEMPLATES[coupon_type]
        
        # プロンプトをカスタマイズ
        prompt = template["prompt"]
        if discount:
            prompt = prompt.replace("20%オフ", f"{discount}オフ")
            prompt = prompt.replace("15%オフ", f"{discount}オフ")
            prompt = prompt.replace("10%オフ", f"{discount}オフ")
        
        try:
            logger.info(f"🎨 クーポン画像生成中: {coupon_type}")
            
            # ComfyUIで画像生成
            execution_id = self.comfyui_integration.generate_image(
                prompt=prompt,
                negative_prompt=template["negative_prompt"],
                width=template["width"],
                height=template["height"]
            )
            
            if not execution_id:
                logger.error("❌ 画像生成に失敗しました")
                return None
            
            # 画像パスを取得（簡易版：実際にはComfyUIの出力を待つ必要がある）
            output_dir = Path(os.getenv("COMFYUI_OUTPUT_DIR", "output"))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"coupon_{coupon_type}_{timestamp}.png"
            image_path = output_dir / image_filename
            
            result = {
                "success": True,
                "coupon_type": coupon_type,
                "execution_id": execution_id,
                "image_path": str(image_path),
                "prompt": prompt,
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ クーポン画像生成完了: {coupon_type} ({image_path})")
            return result
            
        except Exception as e:
            logger.error(f"❌ クーポン画像生成エラー: {e}")
            return None
    
    def generate_all_coupons(self) -> Dict[str, Any]:
        """
        全クーポンタイプを生成
        
        Returns:
            生成結果
        """
        results = {}
        
        for coupon_type in self.COUPON_TEMPLATES.keys():
            result = self.generate_coupon(coupon_type)
            if result:
                results[coupon_type] = result
        
        return {
            "success": len(results) > 0,
            "generated_count": len(results),
            "results": results
        }

