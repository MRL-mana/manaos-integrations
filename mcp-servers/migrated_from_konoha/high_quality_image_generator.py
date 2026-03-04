#!/usr/bin/env python3
"""
High Quality Image Generator
高品質画像生成システム - クオリティー重視版
"""

import os
import time
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import numpy as np
from pathlib import Path
import requests
from io import BytesIO
import json

class HighQualityImageGenerator:
    def __init__(self):
        self.output_dir = Path("/root/mana-workspace/outputs/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 高品質カラーパレット
        self.premium_palettes = {
            "luxury": {
                "primary": "#1a1a2e",
                "secondary": "#16213e", 
                "accent": "#0f3460",
                "highlight": "#533483",
                "bright": "#e94560"
            },
            "corporate": {
                "primary": "#2c3e50",
                "secondary": "#34495e",
                "accent": "#7f8c8d", 
                "highlight": "#ecf0f1",
                "bright": "#3498db"
            },
            "creative": {
                "primary": "#ff6b6b",
                "secondary": "#4ecdc4",
                "accent": "#45b7d1",
                "highlight": "#96ceb4", 
                "bright": "#ffeaa7"
            },
            "minimal": {
                "primary": "#ffffff",
                "secondary": "#f8f9fa",
                "accent": "#e9ecef",
                "highlight": "#6c757d",
                "bright": "#212529"
            }
        }
    
    def hex_to_rgb(self, hex_color):
        """ヘックスカラーをRGBに変換"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def create_ultra_hd_poster(self, title, subtitle, theme="luxury", style="modern"):
        """Ultra HD ポスター作成（4K解像度）"""
        width, height = 3840, 2160  # 4K解像度
        
        # 背景作成
        colors = self.premium_palettes[theme]
        bg_color = self.hex_to_rgb(colors["primary"])
        
        image = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # 高品質グラデーション
        self._add_premium_gradient(draw, width, height, colors)
        
        # 装飾的な要素
        self._add_luxury_elements(draw, width, height, colors, style)
        
        # 高品質テキスト
        self._add_premium_text(draw, title, subtitle, width, height, colors)
        
        # 高品質フィルター適用
        image = self._apply_premium_filters(image)
        
        # 保存
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"ultra_hd_poster_{theme}_{timestamp}.png"
        filepath = self.output_dir / filename
        image.save(filepath, "PNG", quality=100, optimize=False)
        
        return str(filepath)
    
    def create_professional_banner(self, headline, cta_text, theme="corporate", size="large"):
        """プロフェッショナルバナー作成"""
        sizes = {
            "small": (728, 90),
            "medium": (1200, 630), 
            "large": (1920, 1080),
            "ultra": (3840, 2160)
        }
        
        width, height = sizes[size]
        colors = self.premium_palettes[theme]
        
        # 高解像度画像作成
        image = Image.new('RGB', (width, height), self.hex_to_rgb(colors["primary"]))
        draw = ImageDraw.Draw(image)
        
        # プロフェッショナルグラデーション
        self._add_corporate_gradient(draw, width, height, colors)
        
        # 高品質装飾
        self._add_professional_elements(draw, width, height, colors)
        
        # プロフェッショナルテキスト
        self._add_corporate_text(draw, headline, cta_text, width, height, colors)
        
        # 高品質フィルター
        image = self._apply_professional_filters(image)
        
        # 保存
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"professional_banner_{theme}_{size}_{timestamp}.png"
        filepath = self.output_dir / filename
        image.save(filepath, "PNG", quality=100, optimize=False)
        
        return str(filepath)
    
    def create_artistic_poster(self, title, description, style="abstract"):
        """アーティスティックポスター作成"""
        width, height = 2160, 2160  # 正方形高解像度
        
        # スタイル別設定
        styles = {
            "abstract": self.premium_palettes["creative"],
            "minimal": self.premium_palettes["minimal"],
            "luxury": self.premium_palettes["luxury"],
            "corporate": self.premium_palettes["corporate"]
        }
        
        colors = styles[style]
        image = Image.new('RGB', (width, height), self.hex_to_rgb(colors["primary"]))
        draw = ImageDraw.Draw(image)
        
        # アーティスティック要素
        self._add_artistic_elements(draw, width, height, colors, style)
        
        # アーティスティックテキスト
        self._add_artistic_text(draw, title, description, width, height, colors)
        
        # アーティスティックフィルター
        image = self._apply_artistic_filters(image, style)
        
        # 保存
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"artistic_poster_{style}_{timestamp}.png"
        filepath = self.output_dir / filename
        image.save(filepath, "PNG", quality=100, optimize=False)
        
        return str(filepath)
    
    def _add_premium_gradient(self, draw, width, height, colors):
        """プレミアムグラデーション追加"""
        for y in range(height):
            # 複数のグラデーションを重ね合わせ
            alpha1 = y / height
            alpha2 = 1 - alpha1
            
            # プライマリカラーからセカンダリカラーへ
            primary = self.hex_to_rgb(colors["primary"])
            secondary = self.hex_to_rgb(colors["secondary"])
            
            r = int(primary[0] * alpha2 + secondary[0] * alpha1)
            g = int(primary[1] * alpha2 + secondary[1] * alpha1)
            b = int(primary[2] * alpha2 + secondary[2] * alpha1)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    def _add_luxury_elements(self, draw, width, height, colors, style):
        """高級装飾要素追加"""
        if style == "modern":
            # モダンな幾何学装飾
            for i in range(20):
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                size = np.random.randint(100, 500)
                
                # 透明度付き円形
                accent_color = self.hex_to_rgb(colors["accent"])
                draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], 
                           fill=accent_color, outline=None)
        
        elif style == "classic":
            # クラシックな装飾
            for i in range(15):
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                size = np.random.randint(50, 200)
                
                highlight_color = self.hex_to_rgb(colors["highlight"])
                draw.rectangle([x-size//2, y-size//2, x+size//2, y+size//2], 
                              fill=highlight_color, outline=None)
    
    def _add_premium_text(self, draw, title, subtitle, width, height, colors):
        """プレミアムテキスト追加"""
        try:
            # 高品質フォント（システムフォントを使用）
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 200)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 100)
        except:
            # フォールバック
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # タイトル
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
        title_x = (width - title_width) // 2
        title_y = height // 2 - title_height - 50
        
        # テキストシャドウ（高品質）
        shadow_color = (0, 0, 0, 100)
        for offset in range(5, 0, -1):
            draw.text((title_x + offset, title_y + offset), title, 
                     font=title_font, fill=shadow_color)
        
        # メインテキスト
        text_color = self.hex_to_rgb(colors["bright"])
        draw.text((title_x, title_y), title, font=title_font, fill=text_color)
        
        # サブタイトル
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (width - subtitle_width) // 2
        subtitle_y = title_y + title_height + 50
        
        # サブタイトルシャドウ
        for offset in range(3, 0, -1):
            draw.text((subtitle_x + offset, subtitle_y + offset), subtitle, 
                     font=subtitle_font, fill=shadow_color)
        
        # サブタイトルメイン
        subtitle_color = self.hex_to_rgb(colors["highlight"])
        draw.text((subtitle_x, subtitle_y), subtitle, font=subtitle_font, fill=subtitle_color)
    
    def _apply_premium_filters(self, image):
        """プレミアムフィルター適用"""
        # シャープネス向上
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # コントラスト調整
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        # 彩度調整
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.05)
        
        return image
    
    def _add_corporate_gradient(self, draw, width, height, colors):
        """コーポレートグラデーション"""
        for x in range(width):
            alpha = x / width
            primary = self.hex_to_rgb(colors["primary"])
            accent = self.hex_to_rgb(colors["accent"])
            
            r = int(primary[0] * (1 - alpha) + accent[0] * alpha)
            g = int(primary[1] * (1 - alpha) + accent[1] * alpha)
            b = int(primary[2] * (1 - alpha) + accent[2] * alpha)
            
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
    
    def _add_professional_elements(self, draw, width, height, colors):
        """プロフェッショナル装飾要素"""
        # シンプルな装飾線
        line_color = self.hex_to_rgb(colors["highlight"])
        draw.line([(0, height//3), (width, height//3)], fill=line_color, width=3)
        draw.line([(0, height*2//3), (width, height*2//3)], fill=line_color, width=3)
    
    def _add_corporate_text(self, draw, headline, cta_text, width, height, colors):
        """コーポレートテキスト"""
        try:
            headline_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            cta_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        except:
            headline_font = ImageFont.load_default()
            cta_font = ImageFont.load_default()
        
        # ヘッドライン
        headline_bbox = draw.textbbox((0, 0), headline, font=headline_font)
        headline_width = headline_bbox[2] - headline_bbox[0]
        headline_x = (width - headline_width) // 2
        headline_y = height // 2 - 50
        
        headline_color = self.hex_to_rgb(colors["bright"])
        draw.text((headline_x, headline_y), headline, font=headline_font, fill=headline_color)
        
        # CTAボタン
        cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
        cta_width = cta_bbox[2] - cta_bbox[0]
        cta_height = cta_bbox[3] - cta_bbox[1]
        cta_x = width - cta_width - 50
        cta_y = height - cta_height - 50
        
        # CTA背景
        button_color = self.hex_to_rgb(colors["bright"])
        draw.rectangle([cta_x - 20, cta_y - 10, cta_x + cta_width + 20, cta_y + cta_height + 10], 
                      fill=button_color)
        
        # CTAテキスト
        text_color = self.hex_to_rgb(colors["primary"])
        draw.text((cta_x, cta_y), cta_text, font=cta_font, fill=text_color)
    
    def _apply_professional_filters(self, image):
        """プロフェッショナルフィルター"""
        # シャープネス
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)
        
        # コントラスト
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        return image
    
    def _add_artistic_elements(self, draw, width, height, colors, style):
        """アーティスティック要素"""
        if style == "abstract":
            # 抽象的な要素
            for i in range(30):
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                size = np.random.randint(20, 300)
                
                color = self.hex_to_rgb(colors["bright"])
                draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], 
                           fill=color, outline=None)
    
    def _add_artistic_text(self, draw, title, description, width, height, colors):
        """アーティスティックテキスト"""
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
            desc_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        except:
            title_font = ImageFont.load_default()
            desc_font = ImageFont.load_default()
        
        # タイトル
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = height // 3
        
        title_color = self.hex_to_rgb(colors["bright"])
        draw.text((title_x, title_y), title, font=title_font, fill=title_color)
        
        # 説明
        desc_bbox = draw.textbbox((0, 0), description, font=desc_font)
        desc_width = desc_bbox[2] - desc_bbox[0]
        desc_x = (width - desc_width) // 2
        desc_y = title_y + 150
        
        desc_color = self.hex_to_rgb(colors["highlight"])
        draw.text((desc_x, desc_y), description, font=desc_font, fill=desc_color)
    
    def _apply_artistic_filters(self, image, style):
        """アーティスティックフィルター"""
        if style == "abstract":
            # 抽象的なフィルター
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.3)
            
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
        
        return image


def main():
    """メイン関数"""
    generator = HighQualityImageGenerator()
    
    print("🎨 High Quality Image Generator 起動")
    print("=" * 60)
    
    # 高品質サンプル画像生成
    print("📊 高品質サンプル画像を生成中...")
    
    # 1. Ultra HD ポスター
    poster_path = generator.create_ultra_hd_poster(
        "Trinity System",
        "AI-Powered Automation Platform",
        "luxury",
        "modern"
    )
    print(f"✅ Ultra HD ポスター作成完了: {poster_path}")
    
    # 2. プロフェッショナルバナー
    banner_path = generator.create_professional_banner(
        "Advanced AI Solutions",
        "Learn More",
        "corporate",
        "ultra"
    )
    print(f"✅ プロフェッショナルバナー作成完了: {banner_path}")
    
    # 3. アーティスティックポスター
    artistic_path = generator.create_artistic_poster(
        "Creative Innovation",
        "Where Art Meets Technology",
        "abstract"
    )
    print(f"✅ アーティスティックポスター作成完了: {artistic_path}")
    
    print("\n🎉 すべての高品質画像生成完了！")
    print(f"📁 出力ディレクトリ: {generator.output_dir}")


if __name__ == "__main__":
    main()


