# -*- coding: utf-8 -*-
"""CyberRealistic Ponyのみ生成"""

import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import torch
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import gc

class LocalModelGenerator:
    """ローカルのsafetensorsファイルからモデルを読み込む生成クラス"""
    
    def __init__(
        self,
        model_path: str,
        device: Optional[str] = None,
        disable_safety_checker: bool = True
    ):
        self.model_path = model_path
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"デバイス: {self.device}")
        print(f"モデルを読み込み中: {model_path}...")
        print("（大きなファイルのため時間がかかります...）")
        
        # メモリ効率的な設定で読み込み（SDXL対応）
        try:
            print("モデル読み込み中（時間がかかります）...")
            # まずSDXLパイプラインで試す
            try:
                self.pipe = StableDiffusionXLPipeline.from_single_file(
                    model_path,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    use_safetensors=True
                )
                print("SDXLパイプラインで読み込み成功！")
            except:
                # SDXLで失敗したら通常のパイプラインで試す
                print("SDXLパイプラインで失敗、通常パイプラインで再試行...")
                self.pipe = StableDiffusionPipeline.from_single_file(
                    model_path,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    safety_checker=None,
                    requires_safety_checker=False,
                    load_safety_checker=False,
                    use_safetensors=True
                )
                print("通常パイプラインで読み込み成功！")
        except Exception as e:
            print(f"モデル読み込みエラー: {e}")
            print("エラー詳細:")
            import traceback
            traceback.print_exc()
            raise
        
        if disable_safety_checker:
            self.pipe.safety_checker = None
            self.pipe.feature_extractor = None
        
        try:
            scheduler_config = self.pipe.scheduler.config.copy()
            if 'final_sigmas_type' in scheduler_config and scheduler_config.get('final_sigmas_type') == 'zero':
                scheduler_config['final_sigmas_type'] = 'sigma_min'
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(scheduler_config)
        except Exception as e:
            print(f"スケジューラー設定エラー（デフォルトを使用）: {e}")
        
        # メモリ効率化設定
        if hasattr(self.pipe, "enable_attention_slicing"):
            self.pipe.enable_attention_slicing(1)  # 最大スライシング
            print("attention slicingを有効化")
        
        if hasattr(self.pipe, "enable_vae_slicing"):
            self.pipe.enable_vae_slicing()
            print("VAE slicingを有効化")
        
        if hasattr(self.pipe, "enable_vae_tiling"):
            self.pipe.enable_vae_tiling()
            print("VAE tilingを有効化")
        
        self.pipe = self.pipe.to(self.device)
        
        if hasattr(self.pipe, "enable_xformers_memory_efficient_attention"):
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
                print("xformersを有効化しました")
            except:
                print("xformersは利用できません（通常動作に問題ありません）")
        
        print("モデルの読み込みが完了しました！")
    
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 768,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        output_dir: str = "generated_images"
    ) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)
        
        generator = torch.Generator(device=self.device)
        if seed is not None:
            generator.manual_seed(seed)
        
        # SDXLの場合は追加パラメータが必要
        pipe_kwargs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "generator": generator,
            "num_images_per_prompt": 1
        }
        
        # SDXLパイプラインの場合は追加パラメータ
        if hasattr(self.pipe, 'text_encoder_2'):
            # SDXLパイプライン
            pipe_kwargs["output_type"] = "pil"
        
        images = self.pipe(**pipe_kwargs).images
        
        saved_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = Path(self.model_path).stem[:30]
        for i, image in enumerate(images):
            filename = f"mufufu_{timestamp}_{i+1:02d}_{model_name}.png"
            filepath = os.path.join(output_dir, filename)
            image.save(filepath)
            saved_paths.append(filepath)
        
        return saved_paths
    
    def cleanup(self):
        del self.pipe
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        gc.collect()


def get_prompts():
    """プロンプト生成"""
    base_elements = [
        "mufufu",
        "beautiful woman",
        "japanese clear pure gal style",
        "very clear pure gal aesthetic",
        "photorealistic",
        "highly detailed",
        "4k",
        "masterpiece",
        "best quality",
        "ultra high res"
    ]
    
    poses = [
        "sitting pose, elegant",
        "standing pose, graceful",
        "lying pose, relaxed",
        "kneeling pose, cute",
        "leaning pose, charming",
        "looking back pose, seductive",
        "arms up pose, playful",
        "hand on face pose, gentle",
        "looking at viewer, direct gaze",
        "smiling, warm expression"
    ]
    
    states = [
        "completely naked, fully nude, exposed breasts, exposed pussy",
        "naked, nude, exposed body, natural beauty",
        "fully nude, no clothes, exposed nipples, exposed genitals",
        "completely naked, exposed breasts, exposed vagina",
        "nude, exposed body, bare skin",
        "completely naked, natural state",
        "fully nude, exposed body, beautiful skin",
        "naked, exposed breasts, exposed pussy",
        "completely nude, no clothing, exposed body",
        "fully naked, exposed genitals, natural beauty"
    ]
    
    lighting = [
        "natural lighting, soft",
        "studio lighting, professional",
        "warm lighting, cozy",
        "soft lighting, gentle",
        "cinematic lighting, dramatic",
        "natural sunlight, bright",
        "soft natural light, warm",
        "professional lighting, clear",
        "warm natural light, beautiful",
        "soft studio light, elegant"
    ]
    
    prompts = []
    for i in range(10):
        pose = random.choice(poses)
        state = random.choice(states)
        light = random.choice(lighting)
        
        prompt = ", ".join([
            ", ".join(base_elements),
            pose,
            state,
            light,
            "realistic skin texture",
            "perfect anatomy",
            "beautiful face",
            "attractive body"
        ])
        
        prompts.append(prompt)
    
    return prompts


def get_negative_prompt():
    return (
        "blurry, low quality, distorted, ugly, "
        "bad anatomy, bad proportions, deformed, disfigured, "
        "poorly drawn, cartoon, anime, illustration, "
        "painting, drawing, sketch, 2d, fake, artificial, "
        "extra fingers, missing fingers, extra arms, missing arms, "
        "extra legs, missing legs, extra hands, missing hands, "
        "bad hands, malformed hands, deformed hands, "
        "bad feet, malformed feet, deformed feet, "
        "bad body, malformed body, deformed body, "
        "bad face, malformed face, deformed face, "
        "mutation, mutated, mutation body, "
        "duplicate, duplicate body parts, "
        "long neck, short neck, "
        "bad eyes, malformed eyes, deformed eyes, "
        "bad breasts, malformed breasts, deformed breasts, "
        "bad pussy, malformed pussy, deformed pussy, "
        "censored, mosaic, blur, "
        "clothed, wearing clothes, dressed, bikini, underwear, bra, panties, "
        "dark skin, tan, gyaru style, "
        "text, watermark, signature"
    )


def main():
    print("=" * 80)
    print("CyberRealistic Pony 10枚生成")
    print("=" * 80)
    
    # 小さいバージョンを優先的に使用
    model_paths = [
        "models/cyberrealistic_pony_small.safetensors",
        "models/cyberrealistic_pony.safetensors"
    ]
    
    model_path = None
    for path in model_paths:
        if Path(path).exists():
            model_path = path
            print(f"使用モデル: {path}")
            break
    
    if not model_path:
        print(f"エラー: モデルファイルが見つかりません")
        return
    
    generator = LocalModelGenerator(model_path, disable_safety_checker=True)
    prompts = get_prompts()
    negative = get_negative_prompt()
    
    output_dir = "mufufu_cyberrealistic_10"
    os.makedirs(output_dir, exist_ok=True)
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/10] 生成中...")
        print(f"プロンプト: {prompt[:80]}...")
        
        try:
            seed = random.randint(0, 2**32 - 1)
            images = generator.generate(
                prompt=prompt,
                negative_prompt=negative,
                width=512,
                height=768,
                num_inference_steps=30,
                guidance_scale=7.5,
                seed=seed,
                output_dir=output_dir
            )
            print(f"  [OK] 保存先: {images[0]}")
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            continue
    
    generator.cleanup()
    print(f"\n[完了] CyberRealistic Pony: 10枚生成")
    print(f"保存先: {output_dir}/")


if __name__ == "__main__":
    main()

