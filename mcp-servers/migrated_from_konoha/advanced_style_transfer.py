#!/usr/bin/env python3
"""
Trinity AI Advanced Style Transfer System
高度なスタイル転送システム
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from typing import List, Tuple, Dict
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedStyleTransfer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🎨 スタイル転送システム初期化: {self.device}")
        
    def apply_anime_style(self, image: Image.Image, intensity: float = 0.8) -> Image.Image:
        """アニメ風スタイルを適用"""
        try:
            # 画像をnumpy配列に変換
            img_array = np.array(image)
            
            # エッジ検出
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            
            # 色の鮮やかさを向上
            enhanced = cv2.convertScaleAbs(img_array, alpha=1.2, beta=10)
            
            # エッジと色をブレンド
            result = cv2.addWeighted(enhanced, 1-intensity, edges, intensity, 0)
            
            return Image.fromarray(result)
        except Exception as e:
            logger.error(f"アニメスタイル適用エラー: {e}")
            return image

    def apply_oil_painting_style(self, image: Image.Image, intensity: float = 0.7) -> Image.Image:
        """油絵風スタイルを適用"""
        try:
            # 画像をnumpy配列に変換
            img_array = np.array(image)
            
            # 油絵効果
            oil_painting = cv2.xphoto.oilPainting(img_array, 7, 1)
            
            # 色の鮮やかさを調整
            enhanced = cv2.convertScaleAbs(oil_painting, alpha=1.1, beta=5)
            
            return Image.fromarray(enhanced)
        except Exception as e:
            logger.error(f"油絵スタイル適用エラー: {e}")
            return image

    def apply_watercolor_style(self, image: Image.Image, intensity: float = 0.6) -> Image.Image:
        """水彩画風スタイルを適用"""
        try:
            # 画像をnumpy配列に変換
            img_array = np.array(image)
            
            # ガウシアンブラーで柔らかく
            blurred = cv2.GaussianBlur(img_array, (15, 15), 0)
            
            # エッジを強調
            edges = cv2.Canny(cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY), 50, 150)
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            
            # ブレンド
            result = cv2.addWeighted(blurred, 1-intensity, edges, intensity, 0)
            
            return Image.fromarray(result)
        except Exception as e:
            logger.error(f"水彩画スタイル適用エラー: {e}")
            return image

    def apply_cyberpunk_style(self, image: Image.Image, intensity: float = 0.8) -> Image.Image:
        """サイバーパンク風スタイルを適用"""
        try:
            # 画像をnumpy配列に変換
            img_array = np.array(image)
            
            # 色相をシフト（青/紫系に）
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            hsv[:, :, 0] = (hsv[:, :, 0] + 120) % 180  # 色相シフト
            result = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
            
            # コントラストを上げる
            result = cv2.convertScaleAbs(result, alpha=1.3, beta=20)
            
            # ネオン効果（エッジを強調）
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            edges = cv2.applyColorMap(edges, cv2.COLORMAP_PLASMA)
            
            # ブレンド
            result = cv2.addWeighted(result, 1-intensity, edges, intensity, 0)
            
            return Image.fromarray(result)
        except Exception as e:
            logger.error(f"サイバーパンクスタイル適用エラー: {e}")
            return image

    def apply_vintage_style(self, image: Image.Image, intensity: float = 0.7) -> Image.Image:
        """ヴィンテージ風スタイルを適用"""
        try:
            # セピア調
            img_array = np.array(image)
            
            # セピア効果
            sepia = np.array([[0.393, 0.769, 0.189],
                           [0.349, 0.686, 0.168],
                           [0.272, 0.534, 0.131]])
            sepia_img = np.dot(img_array, sepia.T)
            sepia_img = np.clip(sepia_img, 0, 255).astype(np.uint8)
            
            # ノイズを追加
            noise = np.random.normal(0, 10, sepia_img.shape).astype(np.uint8)
            result = np.clip(sepia_img + noise, 0, 255).astype(np.uint8)
            
            return Image.fromarray(result)
        except Exception as e:
            logger.error(f"ヴィンテージスタイル適用エラー: {e}")
            return image

    def apply_modern_art_style(self, image: Image.Image, intensity: float = 0.6) -> Image.Image:
        """モダンアート風スタイルを適用"""
        try:
            # 画像をnumpy配列に変換
            img_array = np.array(image)
            
            # ポスタリゼーション
            result = cv2.convertScaleAbs(img_array, alpha=1.5, beta=0)
            
            # 色の量子化
            result = cv2.convertScaleAbs(result, alpha=1.0, beta=0)
            result = (result // 64) * 64  # 色の量子化
            
            return Image.fromarray(result)
        except Exception as e:
            logger.error(f"モダンアートスタイル適用エラー: {e}")
            return image

    def apply_style_transfer(self, image: Image.Image, style: str, intensity: float = 0.7) -> Image.Image:
        """スタイル転送を適用"""
        style_methods = {
            "anime": self.apply_anime_style,
            "oil_painting": self.apply_oil_painting_style,
            "watercolor": self.apply_watercolor_style,
            "cyberpunk": self.apply_cyberpunk_style,
            "vintage": self.apply_vintage_style,
            "modern_art": self.apply_modern_art_style
        }
        
        if style not in style_methods:
            logger.warning(f"未知のスタイル: {style}")
            return image
            
        try:
            return style_methods[style](image, intensity)
        except Exception as e:
            logger.error(f"スタイル転送エラー ({style}): {e}")
            return image

    def batch_style_transfer(self, image_paths: List[str], styles: List[str], 
                           output_dir: str = "/root/trinity_workspace/generated_images") -> Dict:
        """バッチスタイル転送を実行"""
        os.makedirs(output_dir, exist_ok=True)
        
        results = {
            "total": len(image_paths) * len(styles),
            "success": 0,
            "failed": 0,
            "files": []
        }
        
        for image_path in image_paths:
            try:
                # 画像を読み込み
                image = Image.open(image_path)
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                
                for style in styles:
                    try:
                        # スタイル転送を適用
                        styled_image = self.apply_style_transfer(image, style)
                        
                        # 保存
                        output_filename = f"{base_name}_{style}.png"
                        output_path = os.path.join(output_dir, output_filename)
                        styled_image.save(output_path)
                        
                        results["success"] += 1
                        results["files"].append({
                            "original": image_path,
                            "style": style,
                            "output": output_path
                        })
                        
                        logger.info(f"✅ スタイル転送完了: {base_name} -> {style}")
                        
                    except Exception as e:
                        results["failed"] += 1
                        logger.error(f"❌ スタイル転送エラー ({base_name}, {style}): {e}")
                        
            except Exception as e:
                results["failed"] += 1
                logger.error(f"❌ 画像読み込みエラー ({image_path}): {e}")
        
        logger.info(f"🎉 バッチスタイル転送完了: {results['success']}/{results['total']} 成功")
        return results

    def get_available_styles(self) -> List[str]:
        """利用可能なスタイル一覧を取得"""
        return ["anime", "oil_painting", "watercolor", "cyberpunk", "vintage", "modern_art"]

def main():
    """メイン実行関数"""
    print("🎨 Trinity AI Advanced Style Transfer System")
    print("=" * 60)
    
    style_transfer = AdvancedStyleTransfer()
    
    # 利用可能なスタイル表示
    styles = style_transfer.get_available_styles()
    print(f"🎭 利用可能なスタイル:")
    for style in styles:
        print(f"   🎨 {style}")
    
    # サンプル画像でスタイル転送デモ
    sample_images = [
        "/root/mana-workspace/outputs/images/canva_poster_20251023_183358.png",
        "/root/mana-workspace/outputs/images/infographic_20251023_183358.png"
    ]
    
    # 存在する画像のみをフィルタ
    existing_images = [img for img in sample_images if os.path.exists(img)]
    
    if existing_images:
        print(f"\n🎨 スタイル転送デモ開始")
        print(f"   対象画像: {len(existing_images)}枚")
        print(f"   スタイル: {len(styles)}種類")
        
        # バッチスタイル転送実行
        results = style_transfer.batch_style_transfer(existing_images, styles)
        
        print(f"\n🎉 スタイル転送完了:")
        print(f"   成功: {results['success']}/{results['total']}")
        print(f"   失敗: {results['failed']}")
        
        if results["files"]:
            print(f"\n📁 生成されたファイル:")
            for file_info in results["files"][:5]:  # 最初の5個を表示
                print(f"   🎨 {os.path.basename(file_info['output'])}")
    else:
        print("❌ サンプル画像が見つかりません。")

if __name__ == "__main__":
    main()