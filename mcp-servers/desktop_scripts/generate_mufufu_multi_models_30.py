# -*- coding: utf-8 -*-
"""清楚系ギャルNSFW画像30枚生成（複数モデル対応）"""

import asyncio
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
from datetime import datetime
from typing import List, Optional

class StableDiffusionGeneratorMultiModel:
    """複数モデル対応Stable Diffusion生成クラス"""
    
    def __init__(
        self,
        model_id: str,
        device: Optional[str] = None,
        disable_safety_checker: bool = True
    ):
        """Stable Diffusion生成器を初期化"""
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
            except:
                pass
        
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
        output_dir: str = "generated_images"
    ) -> List[str]:
        """画像を生成"""
        os.makedirs(output_dir, exist_ok=True)
        
        generator = torch.Generator(device=self.device)
        if seed is not None:
            generator.manual_seed(seed)
        
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
        model_name_short = self.model_id.split("/")[-1].replace("-", "_")[:20]
        for i, image in enumerate(images):
            filename = f"sd_{timestamp}_{i+1:02d}_{model_name_short}.png"
            filepath = os.path.join(output_dir, filename)
            image.save(filepath)
            saved_paths.append(filepath)
        
        return saved_paths
    
    def cleanup(self):
        """メモリのクリーンアップ"""
        del self.pipe
        torch.cuda.empty_cache() if torch.cuda.is_available() else None


async def generate_mufufu_multi_models_30():
    print("=" * 60)
    print("清楚系ギャルNSFW画像30枚生成（複数モデル対応）")
    print("=" * 60)
    
    # おすすめNSFW対応モデル
    model_configs = [
        {
            "model_id": "SG161222/Realistic_Vision_V5.1_noVAE",
            "name": "Realistic Vision",
            "output_dir": "mufufu_realistic_vision_30"
        },
        {
            "model_id": "Lykon/DreamShaper",
            "name": "DreamShaper",
            "output_dir": "mufufu_dreamshaper_30"
        },
        {
            "model_id": "runwayml/stable-diffusion-v1-5",
            "name": "Stable Diffusion 1.5",
            "output_dir": "mufufu_sd15_30"
        },
        {
            "model_id": "stabilityai/stable-diffusion-2-1",
            "name": "Stable Diffusion 2.1",
            "output_dir": "mufufu_sd21_30"
        },
        {
            "model_id": "prompthero/openjourney-v4",
            "name": "OpenJourney V4",
            "output_dir": "mufufu_openjourney_30"
        },
    ]
    
    # 清楚系ギャルを強調したプロンプト
    base_prompts = [
        "mufufu, japanese clear pure gal, very clear pure gal style, completely naked, fully nude, exposed breasts, exposed pussy, having sex, sexual intercourse, missionary position, penetration, realistic, 4k, masterpiece, clear pure gal aesthetic",
        "mufufu, japanese clear pure gal, very clear pure gal style, completely nude, naked body, bare breasts, bare pussy, sex scene, doggy style, explicit, photorealistic, 4k, masterpiece, clear pure gal style",
        "mufufu, japanese clear pure gal, very clear pure gal style, naked, nude, exposed nipples, exposed genitals, making love, cowgirl position, explicit sex, realistic, 4k, masterpiece, clear pure gal",
        "mufufu, japanese clear pure gal, very clear pure gal style, fully nude, no clothes, exposed body, sexual act, explicit intercourse, photorealistic, 4k, masterpiece, clear pure gal aesthetic",
        "mufufu, japanese clear pure gal, very clear pure gal style, completely naked, exposed breasts, exposed vagina, sex, penetration, explicit, realistic, 4k, masterpiece, clear pure gal style",
    ]
    
    negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions, deformed, disfigured, poorly drawn, cartoon, anime, illustration, painting, drawing, sketch, 2d, fake, artificial, censored, clothed, wearing clothes, dressed, bikini, underwear, bra, panties, dark skin, tan, gyaru style"
    
    # 各モデルで30枚ずつ生成
    for model_idx, config in enumerate(model_configs, 1):
        print(f"\n{'='*60}")
        print(f"[{model_idx}/{len(model_configs)}] モデル: {config['name']} ({config['model_id']})")
        print(f"{'='*60}")
        
        try:
            generator = StableDiffusionGeneratorMultiModel(
                model_id=config['model_id'],
                disable_safety_checker=True
            )
            
            all_images = []
            total = 30
            current = 0
            
            # 各ベースプロンプトから6枚ずつ生成
            for i, base_prompt in enumerate(base_prompts, 1):
                print(f"\n[{i}/5] プロンプトセット {i}: {base_prompt[:70]}...")
                
                for j in range(6):
                    current += 1
                    print(f"  [{current}/{total}] 生成中...", end="", flush=True)
                    
                    try:
                        images = generator.generate(
                            prompt=base_prompt,
                            negative_prompt=negative_prompt,
                            width=512,
                            height=512,
                            num_inference_steps=50,
                            guidance_scale=7.5,
                            seed=None,
                            output_dir=config['output_dir']
                        )
                        all_images.extend(images)
                        print(f" [OK]")
                    except Exception as e:
                        print(f" [ERROR: {e}]")
                        continue
            
            print(f"\n[OK] {config['name']} 画像生成完了！")
            print(f"     合計 {len(all_images)} 枚生成されました")
            print(f"     保存先: {config['output_dir']}/")
            
            # メモリクリーンアップ
            generator.cleanup()
            
        except Exception as e:
            print(f"[ERROR] {config['name']} でエラー: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*60}")
    print("すべてのモデルでの生成が完了しました！")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(generate_mufufu_multi_models_30())

