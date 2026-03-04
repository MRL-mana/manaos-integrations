#!/usr/bin/env python3
"""
AI Image Generator using CPU-optimized models
CPU環境でも動作する軽量なAI画像生成システム
"""

import os
import time
from PIL import Image
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
import torch
from pathlib import Path
import numpy as np

class CPUImageGenerator:
    def __init__(self):
        self.output_dir = Path("/root/mana-workspace/outputs/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # CPU最適化設定
        self.device = "cpu"
        torch.set_num_threads(4)  # CPUスレッド数制限
        
        # 軽量モデルのロード
        self.pipeline = None
        self.load_model()
    
    def load_model(self):
        """軽量モデルをロード"""
        try:
            print("🤖 AI画像生成モデルをロード中...")
            
            # 軽量でCPUに最適化されたモデル
            model_id = "runwayml/stable-diffusion-v1-5"
            
            # CPU最適化パイプライン
            self.pipeline = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float32,  # CPU用にfloat32を使用
                use_safetensors=True,
                variant="fp16" if torch.cuda.is_available() else None
            )
            
            # CPU最適化スケジューラー
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )
            
            # CPUに移動
            self.pipeline = self.pipeline.to(self.device)
            
            # メモリ最適化
            self.pipeline.enable_attention_slicing()
            # CPU環境では enable_model_cpu_offload は不要
            
            print("✅ AI画像生成モデルロード完了")
            
        except Exception as e:
            print(f"❌ モデルロードエラー: {str(e)}")
            self.pipeline = None
    
    def generate_image(self, prompt, negative_prompt="", width=512, height=512, num_inference_steps=20):
        """AI画像生成"""
        if self.pipeline is None:
            print("❌ モデルがロードされていません")
            return None
        
        try:
            print(f"🎨 画像生成中: '{prompt}'")
            start_time = time.time()
            
            # CPU最適化設定
            generator = torch.Generator(device=self.device).manual_seed(42)
            
            # 画像生成
            image = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                generator=generator,
                guidance_scale=7.5
            ).images[0]
            
            # 保存
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"ai_generated_{timestamp}.png"
            filepath = self.output_dir / filename
            image.save(filepath)
            
            generation_time = time.time() - start_time
            print(f"✅ 画像生成完了: {generation_time:.2f}秒")
            print(f"📁 保存先: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            print(f"❌ 画像生成エラー: {str(e)}")
            return None
    
    def generate_multiple_images(self, prompts, **kwargs):
        """複数画像生成"""
        results = []
        for i, prompt in enumerate(prompts):
            print(f"\n📸 画像 {i+1}/{len(prompts)} 生成中...")
            result = self.generate_image(prompt, **kwargs)
            results.append(result)
        return results
    
    def generate_with_style(self, base_prompt, style="photorealistic"):
        """スタイル付き画像生成"""
        style_prompts = {
            "photorealistic": "photorealistic, high quality, detailed, 8k",
            "anime": "anime style, manga, high quality, detailed",
            "oil_painting": "oil painting, artistic, detailed, masterpiece",
            "watercolor": "watercolor painting, artistic, soft colors",
            "digital_art": "digital art, concept art, detailed, high quality",
            "sketch": "pencil sketch, black and white, detailed",
            "cartoon": "cartoon style, colorful, fun, detailed",
            "minimalist": "minimalist, simple, clean, modern design"
        }
        
        style_prompt = style_prompts.get(style, style_prompts["photorealistic"])
        full_prompt = f"{base_prompt}, {style_prompt}"
        
        return self.generate_image(full_prompt)
    
    def generate_logo(self, company_name, style="modern"):
        """ロゴ生成"""
        logo_prompts = {
            "modern": f"modern logo design for {company_name}, minimalist, clean, professional",
            "vintage": f"vintage logo design for {company_name}, retro style, classic",
            "tech": f"tech logo design for {company_name}, futuristic, digital, modern",
            "creative": f"creative logo design for {company_name}, artistic, unique, colorful"
        }
        
        prompt = logo_prompts.get(style, logo_prompts["modern"])
        negative_prompt = "text, watermark, signature, low quality, blurry"
        
        return self.generate_image(prompt, negative_prompt, width=512, height=512)
    
    def generate_character(self, description, style="anime"):
        """キャラクター生成"""
        character_prompt = f"{description}, {style} style, high quality, detailed, full body"
        negative_prompt = "low quality, blurry, distorted, extra limbs, bad anatomy"
        
        return self.generate_image(character_prompt, negative_prompt, width=512, height=768)


def main():
    """メイン関数"""
    print("🤖 AI Image Generator (CPU版) 起動")
    print("=" * 50)
    
    generator = CPUImageGenerator()
    
    if generator.pipeline is None:
        print("❌ モデルのロードに失敗しました")
        return
    
    print("\n📊 サンプル画像を生成中...")
    
    # サンプル画像生成
    samples = [
        ("a beautiful sunset over mountains", "photorealistic"),
        ("a cute robot in a garden", "anime"),
        ("modern office building", "photorealistic"),
        ("abstract art with vibrant colors", "digital_art"),
        ("Trinity System logo", "modern")
    ]
    
    for prompt, style in samples:
        print(f"\n🎨 生成中: {prompt} ({style})")
        result = generator.generate_with_style(prompt, style)
        if result:
            print(f"✅ 完了: {result}")
    
    print("\n🎉 すべての画像生成完了！")
    print(f"📁 出力ディレクトリ: {generator.output_dir}")


if __name__ == "__main__":
    main()
