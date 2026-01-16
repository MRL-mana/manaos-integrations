#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""マナ好みのクイック画像生成"""

import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_mana_favorite_image():
    """マナ好みの画像を生成"""
    
    # Hugging Face統合を試す
    try:
        from huggingface_integration import HuggingFaceManaOSIntegration
        logger.info("✓ Hugging Face統合を初期化中...")
        integration = HuggingFaceManaOSIntegration()
        
        # マナ好みのプロンプト
        prompt = """
        masterpiece, best quality, ultra detailed, 8k, cinematic lighting,
        beautiful Japanese girl, cute gyaru style, pink beige hair, joyful expression,
        wearing oversized white shirt, unbuttoned, lace lingerie visible,
        laying on bed in cozy bedroom, sunlight filtering through curtains,
        soft skin, depth of field, seductive gaze looking at viewer,
        high quality, smooth skin, detailed face, perfect proportions
        """
        
        negative_prompt = """
        blurry, low quality, distorted, ugly, nsfw, nude, explicit,
        poorly drawn, worst quality, watermark, text, deformed
        """
        
        logger.info("🎨 マナ好みの画像を生成中...")
        logger.info(f"📝 プロンプト: {prompt[:50]}...")
        
        result = integration.generate_image(
            prompt=prompt.strip(),
            negative_prompt=negative_prompt.strip(),
            width=768,
            height=768,
            num_inference_steps=30,
            guidance_scale=7.5
        )
        
        if result.get("success"):
            images = result.get("images", [])
            logger.info(f"✓ 画像生成成功！ {len(images)}枚")
            for i, img in enumerate(images, 1):
                logger.info(f"  📷 画像{i}: {img['path']}")
            return result
        else:
            logger.error(f"✗ 生成失敗: {result.get('error')}")
            return result
    
    except ImportError as e:
        logger.error(f"✗ Hugging Face統合エラー: {e}")
        logger.info("💡 代替方法を試中...")
        
        # 代替1: 画像ストックから推奨を取得
        try:
            from image_stock import ImageStock
            stock = ImageStock()
            logger.info("✓ 画像ストックから既存の推奨画像を探中...")
            
            suggestions = stock.suggest_for_generation(
                "cute gyaru girl, cozy bedroom, beautiful, joyful"
            )
            
            if suggestions:
                logger.info(f"✓ {len(suggestions)}件の推奨画像を発見！")
                for i, sugg in enumerate(suggestions, 1):
                    logger.info(f"  {i}. {sugg.get('image_path')}")
                    logger.info(f"     推奨プロンプト: {sugg.get('recommended_prompt')[:60]}...")
                return {"success": True, "suggestions": suggestions}
            else:
                logger.info("ℹ️  保存済み画像がありません")
                return {"success": False, "error": "保存済み画像がありません"}
        
        except Exception as e:
            logger.error(f"✗ 画像ストックエラー: {e}")
            logger.info("💡 ComfyUI APIを試中...")
            
            # 代替2: ComfyUI API
            try:
                import requests
                payload = {
                    "prompt": "cute anime girl, beautiful, masterpiece",
                    "negative_prompt": "blurry, low quality",
                    "width": 512,
                    "height": 512,
                    "steps": 20,
                    "cfg_scale": 7.0
                }
                
                response = requests.post(
                    "http://localhost:8188/api/prompt",
                    json={"prompt": payload},
                    timeout=5
                )
                
                if response.status_code == 200:
                    logger.info("✓ ComfyUIで生成開始")
                    return response.json()
                
            except Exception as e2:
                logger.error(f"✗ ComfyUI API エラー: {e2}")
    
    return {"success": False, "error": "すべての画像生成方法が利用不可です"}

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🎨 マナ好みの画像生成を開始します！")
    logger.info("=" * 60)
    
    result = generate_mana_favorite_image()
    
    logger.info("=" * 60)
    if result.get("success"):
        logger.info("✓ 完了！")
    else:
        logger.info(f"✗ エラー: {result.get('error')}")
    logger.info("=" * 60)
