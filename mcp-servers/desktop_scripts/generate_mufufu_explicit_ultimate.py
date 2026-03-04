# -*- coding: utf-8 -*-
"""過激なムフフ画像生成（複数LoRA対応・性行為・裸・フェラ含む）"""

import asyncio
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
from datetime import datetime
from typing import List, Optional
import random

class ExplicitMufufuGenerator:
    """過激な画像生成クラス（複数LoRA対応）"""
    
    def __init__(
        self,
        model_id: str = "SG161222/Realistic_Vision_V5.1_noVAE",
        lora_paths: Optional[List[str]] = None,
        lora_weights: Optional[List[float]] = None,
        device: Optional[str] = None,
        disable_safety_checker: bool = True
    ):
        """初期化"""
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.lora_paths = lora_paths or []
        self.lora_weights = lora_weights or [1.0] * len(self.lora_paths) if self.lora_paths else []
        
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
        
        # LoRAの読み込み
        if self.lora_paths:
            print(f"LoRAを読み込み中: {len(self.lora_paths)}個...")
            for i, (lora_path, weight) in enumerate(zip(self.lora_paths, self.lora_weights)):
                try:
                    self.pipe.load_lora_weights(lora_path, weight=weight)
                    print(f"  LoRA {i+1}: {lora_path} (weight: {weight})")
                except Exception as e:
                    print(f"  LoRA {i+1} 読み込みエラー: {e}")
                    print(f"    注意: LoRAが存在しない場合はスキップします")
        
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
        output_dir: str = "mufufu_explicit_ultimate"
    ) -> List[str]:
        """画像を生成"""
        os.makedirs(output_dir, exist_ok=True)
        
        generator = torch.Generator(device=self.device)
        if seed is not None:
            generator.manual_seed(seed)
        
        print(f"画像生成中...")
        print(f"プロンプト: {prompt[:100]}...")
        
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
            filename = f"explicit_{timestamp}_{i+1:02d}.png"
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


def add_variation_to_prompt(base_prompt: str, index: int) -> str:
    """プロンプトにバリエーションを追加"""
    # 表情のバリエーション
    expressions = [
        "soft smile", "seductive expression", "innocent look", "passionate expression",
        "gentle smile", "lustful gaze", "shy expression", "confident smile",
        "pleased expression", "ecstatic face", "blushing", "moaning"
    ]
    
    # ポーズのバリエーション
    poses = [
        "arms up", "legs spread wide", "bent over", "on knees", "lying down",
        "sitting", "standing", "arched back", "hands behind head", "reaching out",
        "bent knees", "one leg up", "spread eagle", "curved body"
    ]
    
    # アングルのバリエーション
    angles = [
        "close-up", "full body", "side view", "from above", "from below",
        "front view", "back view", "three-quarter view", "low angle", "high angle",
        "wide shot", "medium shot", "extreme close-up"
    ]
    
    # 照明のバリエーション
    lighting = [
        "natural lighting", "studio lighting", "dim lighting", "soft lighting",
        "dramatic lighting", "warm lighting", "cool lighting", "rim lighting",
        "backlit", "side lighting", "golden hour", "moody lighting"
    ]
    
    # 背景のバリエーション
    backgrounds = [
        "bedroom", "bathroom", "hotel room", "outdoor", "indoor",
        "bed", "sofa", "shower", "bath", "floor", "couch", "desk"
    ]
    
    # その他の詳細
    details = [
        "sweat", "wet", "glossy skin", "smooth skin", "perfect skin",
        "long hair", "short hair", "messy hair", "neat hair",
        "pale skin", "fair skin", "smooth body", "toned body"
    ]
    
    # ランダムに選択（インデックスベースで再現性を持たせる）
    random.seed(index * 1000 + hash(base_prompt) % 1000)
    
    variation_parts = []
    
    # 各カテゴリから1-2個ランダムに選択
    if random.random() < 0.7:
        variation_parts.append(random.choice(expressions))
    if random.random() < 0.6:
        variation_parts.append(random.choice(poses))
    if random.random() < 0.5:
        variation_parts.append(random.choice(angles))
    if random.random() < 0.6:
        variation_parts.append(random.choice(lighting))
    if random.random() < 0.5:
        variation_parts.append(random.choice(backgrounds))
    if random.random() < 0.4:
        variation_parts.append(random.choice(details))
    
    # プロンプトに追加
    if variation_parts:
        variation = ", ".join(variation_parts)
        return f"{base_prompt}, {variation}"
    return base_prompt


async def generate_mufufu_explicit_ultimate():
    print("=" * 60)
    print("過激なムフフ画像生成（性行為・裸・フェラ含む）")
    print("合計50枚生成します（各画像にバリエーション追加）")
    print("=" * 60)
    
    # LoRA候補（Hugging Face HubのIDまたはローカルパス）
    # 注意: 実際に存在するLoRAを使用してください
    # 例: "latent-consistency/lcm-lora-sdv1-5", "ByteDance/SDXL-Lightning" など
    lora_paths = [
        # NSFW特化LoRAがあれば追加
        # "user/nsfw-lora",
        # "user/japanese-girl-lora",
    ]
    lora_weights = [0.8] * len(lora_paths) if lora_paths else []
    
    # 超過激なプロンプト（性行為・裸・フェラを含む）
    base_prompts = [
        # 性行為シーン（正常位）
        "mufufu, japanese clear pure gal, completely naked, fully nude, no clothes, exposed breasts, exposed nipples, exposed pussy, exposed genitals, having sex, sexual intercourse, making love, missionary position, penetration, cock inside pussy, explicit sex scene, realistic, photorealistic, highly detailed, 4k, masterpiece",
        
        # 性行為シーン（バック）
        "mufufu, japanese clear pure gal, completely nude, naked body, bare breasts, bare pussy, doggy style, sex scene, anal sex, anal penetration, explicit sexual content, photorealistic, highly detailed, 4k, masterpiece",
        
        # フェラシーン
        "mufufu, japanese clear pure gal, completely naked, exposed breasts, giving blowjob, oral sex, fellatio, sucking cock, deep throat, cock in mouth, explicit oral sex, realistic, photorealistic, highly detailed, 4k, masterpiece",
        
        # 性行為シーン（騎乗位）
        "mufufu, japanese clear pure gal, fully nude, no clothes, exposed body, bare breasts, bare genitals, cowgirl position, riding cock, penetration, explicit sex, realistic, highly detailed, 4k, masterpiece",
        
        # 全裸・露出シーン
        "mufufu, japanese clear pure gal, completely naked, fully nude, no clothes at all, exposed breasts, exposed nipples, exposed pussy, exposed vagina, spread legs, explicit nudity, realistic, photorealistic, highly detailed, 4k, masterpiece",
        
        # 性行為シーン（複数ポーズ）
        "mufufu, japanese clear pure gal, naked, nude, exposed body, having sex, sexual intercourse, multiple positions, explicit sex scene, penetration, realistic, highly detailed, 4k, masterpiece",
        
        # フェラシーン（詳細）
        "mufufu, japanese clear pure gal, completely naked, giving head, oral sex, fellatio, blowjob, sucking dick, cock in mouth, deep throat, explicit oral sex scene, realistic, photorealistic, highly detailed, 4k, masterpiece",
        
        # 性行為シーン（立位）
        "mufufu, japanese clear pure gal, fully nude, standing sex, standing position, penetration, sexual intercourse, explicit sex, realistic, highly detailed, 4k, masterpiece",
    ]
    
    negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions, deformed, disfigured, poorly drawn, cartoon, anime, illustration, painting, drawing, sketch, 2d, fake, artificial, censored, clothed, wearing clothes, dressed, bikini, underwear, bra, panties, dark skin, tan, gyaru style, excessive makeup, multiple people, group"
    
    try:
        # モデルを変更（DreamShaperに変更）
        generator = ExplicitMufufuGenerator(
            model_id="Lykon/DreamShaper",
            lora_paths=lora_paths if lora_paths else None,
            lora_weights=lora_weights if lora_weights else None,
            disable_safety_checker=True
        )
        
        all_images = []
        total = 50
        images_per_prompt = 50 // len(base_prompts)  # 各プロンプトから生成する枚数
        remainder = 50 % len(base_prompts)  # 余り
        current = 0
        
        for i, base_prompt in enumerate(base_prompts, 1):
            # 最初のプロンプトに余りを追加
            count = images_per_prompt + (remainder if i == 1 else 0)
            
            print(f"\n[{i}/{len(base_prompts)}] プロンプトセット {i}: {base_prompt[:70]}...")
            print(f"     このプロンプトから {count} 枚生成します（各画像にバリエーション追加）")
            
            for j in range(count):
                current += 1
                # 各生成ごとにバリエーションを追加
                varied_prompt = add_variation_to_prompt(base_prompt, current)
                
                print(f"  [{current}/{total}] 生成中...")
                print(f"     バリエーション: {varied_prompt[len(base_prompt):][:50]}...")
                
                try:
                    images = generator.generate(
                        prompt=varied_prompt,
                        negative_prompt=negative_prompt,
                        width=512,
                        height=512,
                        num_inference_steps=50,
                        guidance_scale=7.5 + random.uniform(-0.5, 0.5),  # guidance_scaleも少し変える
                        seed=current * 1000 + hash(varied_prompt) % 1000,  # シードも変える
                        output_dir="mufufu_explicit_ultimate"
                    )
                    all_images.extend(images)
                    print(f"      [OK] 生成完了")
                except Exception as e:
                    print(f"      [ERROR] エラー: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        print(f"\n[OK] 画像生成完了！")
        print(f"     合計 {len(all_images)} 枚生成されました")
        print(f"     保存先: mufufu_explicit_ultimate/")
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'generator' in locals():
            generator.cleanup()

if __name__ == "__main__":
    asyncio.run(generate_mufufu_explicit_ultimate())

