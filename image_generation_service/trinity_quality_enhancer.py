#!/usr/bin/env python3
"""
Quality Enhancer
既存画像の品質向上システム
"""

import os
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pathlib import Path
import numpy as np

class QualityEnhancer:
    def __init__(self):
        self.output_dir = Path("/root/mana-workspace/outputs/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def enhance_image_quality(self, input_path, enhancement_level="high"):
        """画像品質向上"""
        try:
            # 画像読み込み
            image = Image.open(input_path)
            
            # 解像度向上
            if enhancement_level == "ultra":
                # 2倍アップスケール
                width, height = image.size
                image = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
            elif enhancement_level == "high":
                # 1.5倍アップスケール
                width, height = image.size
                image = image.resize((int(width * 1.5), int(height * 1.5)), Image.Resampling.LANCZOS)
            
            # シャープネス向上
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)
            
            # コントラスト調整
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # 彩度調整
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.1)
            
            # 明度調整
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.05)
            
            # ノイズ除去
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # 保存
            output_path = input_path.replace('.png', '_enhanced.png')
            image.save(output_path, "PNG", quality=100, optimize=False)
            
            return output_path
            
        except Exception as e:
            print(f"❌ 品質向上エラー: {str(e)}")
            return None
    
    def create_hdr_effect(self, input_path):
        """HDR効果追加"""
        try:
            image = Image.open(input_path)
            
            # HDR効果のための複数露光シミュレーション
            # 明るい版
            bright = ImageEnhance.Brightness(image).enhance(1.5)
            bright = ImageEnhance.Contrast(bright).enhance(1.3)
            
            # 暗い版
            dark = ImageEnhance.Brightness(image).enhance(0.7)
            dark = ImageEnhance.Contrast(dark).enhance(0.8)
            
            # ブレンド（簡易版）
            # 実際のHDR合成はより複雑だが、ここでは簡易版を実装
            hdr_image = Image.blend(bright, dark, 0.5)
            
            # 最終調整
            enhancer = ImageEnhance.Color(hdr_image)
            hdr_image = enhancer.enhance(1.2)
            
            output_path = input_path.replace('.png', '_hdr.png')
            hdr_image.save(output_path, "PNG", quality=100, optimize=False)
            
            return output_path
            
        except Exception as e:
            print(f"❌ HDR効果エラー: {str(e)}")
            return None
    
    def add_professional_effects(self, input_path, effect_type="cinematic"):
        """プロフェッショナルエフェクト追加"""
        try:
            image = Image.open(input_path)
            
            if effect_type == "cinematic":
                # シネマティック効果
                # 色温度調整
                enhancer = ImageEnhance.Color(image)
                image = enhancer.enhance(1.3)
                
                # コントラスト強化
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.4)
                
                # シャープネス
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.6)
                
            elif effect_type == "vintage":
                # ヴィンテージ効果
                # セピア調
                image = ImageOps.colorize(image.convert('L'), '#8B4513', '#F4A460')
                
                # ノイズ追加
                image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
                
            elif effect_type == "modern":
                # モダン効果
                # 高彩度
                enhancer = ImageEnhance.Color(image)
                image = enhancer.enhance(1.4)
                
                # 高コントラスト
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.3)
                
                # シャープネス
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.5)
            
            output_path = input_path.replace('.png', f'_{effect_type}.png')
            image.save(output_path, "PNG", quality=100, optimize=False)
            
            return output_path
            
        except Exception as e:
            print(f"❌ エフェクト追加エラー: {str(e)}")
            return None
    
    def batch_enhance_images(self, directory_path, enhancement_level="high"):
        """バッチ画像品質向上"""
        directory = Path(directory_path)
        enhanced_count = 0
        
        for image_file in directory.glob("*.png"):
            print(f"🔄 処理中: {image_file.name}")
            
            # 品質向上
            enhanced_path = self.enhance_image_quality(str(image_file), enhancement_level)
            if enhanced_path:
                enhanced_count += 1
                print(f"✅ 完了: {Path(enhanced_path).name}")
            
            # HDR効果
            hdr_path = self.create_hdr_effect(str(image_file))
            if hdr_path:
                print(f"✅ HDR効果追加: {Path(hdr_path).name}")
            
            # プロフェッショナルエフェクト
            for effect in ["cinematic", "vintage", "modern"]:
                effect_path = self.add_professional_effects(str(image_file), effect)
                if effect_path:
                    print(f"✅ {effect}効果追加: {Path(effect_path).name}")
        
        print(f"\n🎉 バッチ処理完了: {enhanced_count}枚の画像を処理")
        return enhanced_count


def main():
    """メイン関数"""
    enhancer = QualityEnhancer()
    
    print("🎨 Quality Enhancer 起動")
    print("=" * 50)
    
    # 既存画像の品質向上
    image_dir = "/root/mana-workspace/outputs/images"
    
    print("📊 既存画像の品質向上を実行中...")
    enhanced_count = enhancer.batch_enhance_images(image_dir, "high")
    
    print(f"\n🎉 品質向上処理完了！")
    print(f"📁 処理ディレクトリ: {image_dir}")
    print(f"✅ 処理済み画像: {enhanced_count}枚")


if __name__ == "__main__":
    main()


