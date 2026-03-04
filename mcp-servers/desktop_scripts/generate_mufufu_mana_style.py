# -*- coding: utf-8 -*-
"""マナ好みのムフフ画像生成（清楚系ギャルスタイル）"""

import asyncio
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
from datetime import datetime
from typing import List, Optional

class MufufuGenerator:
    """清楚系ギャルスタイル画像生成クラス"""
    
    def __init__(
        self,
        model_id: str = "SG161222/Realistic_Vision_V5.1_noVAE",
        device: Optional[str] = None,
        disable_safety_checker: bool = True
    ):
        """初期化"""
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"デバイス: {self.device}")
        print(f"モデルを読み込み中: {model_id}...")
        
        # パイプラインの読み込み
        self.pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            safety_checker=None if disable_safety_checker else None,
            requires_safety_checker=False if disable_safety_checker else True
        )
        
        # 安全フィルターを無効化
        if disable_safety_checker:
            self.pipe.safety_checker = None
            self.pipe.feature_extractor = None
            print("安全フィルターを無効化しました")
        
        # スケジューラーの設定
        try:
            scheduler_config = self.pipe.scheduler.config.copy()
            if 'final_sigmas_type' in scheduler_config and scheduler_config.get('final_sigmas_type') == 'zero':
                scheduler_config['final_sigmas_type'] = 'sigma_min'
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(scheduler_config)
        except Exception as e:
            print(f"スケジューラー設定エラー（デフォルトを使用）: {e}")
        
        # メモリ効率的なアテンション
        if hasattr(self.pipe, "enable_attention_slicing"):
            self.pipe.enable_attention_slicing()
        
        # デバイスに移動
        self.pipe = self.pipe.to(self.device)
        
        # xformers
        if hasattr(self.pipe, "enable_xformers_memory_efficient_attention"):
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
                print("xformersを有効化しました")
            except:
                print("xformersは利用できません")
        
        print("モデルの読み込みが完了しました！")
    
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        output_dir: str = "mufufu_mana_style"
    ) -> List[str]:
        """画像を生成"""
        os.makedirs(output_dir, exist_ok=True)
        
        generator = torch.Generator(device=self.device)
        if seed is not None:
            generator.manual_seed(seed)
        
        print(f"画像生成中...")
        print(f"プロンプト: {prompt}")
        print(f"ネガティブプロンプト: {negative_prompt}")
        print(f"サイズ: {width}x{height}, ステップ数: {num_inference_steps}")
        
        images = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
            num_images_per_prompt=1
        ).images
        
        # 画像を保存
        saved_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for i, image in enumerate(images):
            filename = f"mana_{timestamp}_{i+1:02d}.png"
            filepath = os.path.join(output_dir, filename)
            image.save(filepath)
            saved_paths.append(filepath)
            print(f"画像を保存しました: {filepath}")
        
        return saved_paths
    
    def cleanup(self):
        """メモリのクリーンアップ"""
        del self.pipe
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        print("GPUメモリをクリーンアップしました")


async def generate_mufufu_mana_style():
    print("=" * 60)
    print("マナ好みのムフフ画像生成（清楚系ギャルスタイル）")
    print("=" * 60)
    
    # 清楚系ギャルを強調したプロンプト（マナ好み）
    prompts = [
        "mufufu, japanese clear pure gal, very clear pure gal style, beautiful woman, elegant pose, soft smile, natural lighting, photorealistic, highly detailed, 4k, masterpiece, clear pure gal aesthetic, gentle expression",
        "mufufu, japanese clear pure gal, very clear pure gal style, attractive woman, charming expression, studio lighting, professional portrait, highly detailed, 4k, masterpiece, clear pure gal style, warm smile",
        "mufufu, japanese clear pure gal, very clear pure gal style, beautiful girl, elegant expression, cinematic lighting, photorealistic, highly detailed, 4k, masterpiece, clear pure gal, perfect skin",
    ]
    
    negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions, deformed, disfigured, poorly drawn, cartoon, anime, illustration, painting, drawing, sketch, 2d, fake, artificial, dark skin, tan, gyaru style, excessive makeup"
    
    try:
        generator = MufufuGenerator(
            model_id="SG161222/Realistic_Vision_V5.1_noVAE",
            disable_safety_checker=True
        )
        
        all_images = []
        total = len(prompts)
        
        for i, prompt in enumerate(prompts, 1):
            print(f"\n[{i}/{total}] 生成中...")
            print(f"プロンプト: {prompt[:80]}...")
            
            try:
                images = generator.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=512,
                    height=512,
                    num_inference_steps=50,
                    guidance_scale=7.5,
                    seed=None,
                    output_dir="mufufu_mana_style"
                )
                all_images.extend(images)
                print(f"  [OK] 生成完了")
            except Exception as e:
                print(f"  [ERROR] エラー: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n[OK] 画像生成完了！")
        print(f"     合計 {len(all_images)} 枚生成されました")
        print(f"     保存先: mufufu_mana_style/")
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'generator' in locals():
            generator.cleanup()

if __name__ == "__main__":
    asyncio.run(generate_mufufu_mana_style())



