# -*- coding: utf-8 -*-
"""清楚系ギャルNSFW画像30枚生成（LoRA + 複数モデル対応）"""

import asyncio
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
from datetime import datetime
from typing import List, Optional

class StableDiffusionGeneratorWithLoRA:
    """LoRA対応Stable Diffusion生成クラス"""
    
    def __init__(
        self,
        model_id: str = "SG161222/Realistic_Vision_V5.1_noVAE",
        lora_paths: Optional[List[str]] = None,
        lora_weights: Optional[List[float]] = None,
        device: Optional[str] = None,
        disable_safety_checker: bool = True
    ):
        """
        LoRA対応Stable Diffusion生成器を初期化
        
        Args:
            model_id: ベースモデルのID
            lora_paths: LoRAファイルのパスリスト（Hugging Face HubのIDまたはローカルパス）
            lora_weights: LoRAの重みリスト（0.0-1.0）
            device: 使用するデバイス
            disable_safety_checker: 安全フィルターを無効化するか
        """
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.lora_paths = lora_paths or []
        self.lora_weights = lora_weights or [1.0] * len(self.lora_paths)
        
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
        
        # LoRAの読み込み（PEFT形式対応）
        if self.lora_paths:
            print(f"LoRAを読み込み中: {len(self.lora_paths)}個...")
            for i, (lora_path, weight) in enumerate(zip(self.lora_paths, self.lora_weights)):
                try:
                    import os
                    import json
                    from safetensors import safe_open
                    
                    # adapter_model.safetensorsが存在するか確認
                    adapter_path = os.path.join(lora_path, "adapter_model.safetensors")
                    adapter_config_path = os.path.join(lora_path, "adapter_config.json")
                    
                    if os.path.exists(adapter_path) or os.path.exists(adapter_config_path):
                        # PEFT形式のLoRA: パスを変換してdiffusers形式に変換
                        print(f"  LoRA {i+1}: PEFT形式を検出、diffusers形式に変換中...")
                        try:
                            # adapter_config.jsonを読み込んでlora_alphaを取得
                            lora_alpha = 32  # デフォルト値
                            if os.path.exists(adapter_config_path):
                                with open(adapter_config_path, 'r') as f:
                                    config = json.load(f)
                                    lora_alpha = config.get('lora_alpha', 32)
                            
                            # safetensorsファイルを読み込んで、パスを変換
                            state_dict = {}
                            with safe_open(adapter_path, framework="pt", device="cpu") as f:
                                for key in f.keys():
                                    # base_model.model.base_model.model. を削除
                                    new_key = key.replace("base_model.model.base_model.model.", "")
                                    tensor = f.get_tensor(key)
                                    
                                    # lora_alphaで正規化（diffusers形式に合わせる）
                                    if 'lora_B' in new_key:
                                        # lora_Bにはalpha/rのスケールを適用
                                        tensor = tensor * (lora_alpha / 32.0)
                                    
                                    # 重みを適用
                                    if weight != 1.0:
                                        tensor = tensor * weight
                                    
                                    state_dict[new_key] = tensor
                            
                            # 一時ディレクトリに変換したLoRAを保存
                            import tempfile
                            from safetensors.torch import save_file
                            with tempfile.TemporaryDirectory() as temp_dir:
                                temp_lora_path = os.path.join(temp_dir, "pytorch_lora_weights.safetensors")
                                save_file(state_dict, temp_lora_path)
                                
                                # 変換したLoRAを読み込む（weightパラメータは既に適用済み）
                                self.pipe.load_lora_weights(temp_lora_path)
                                print(f"  LoRA {i+1}: {lora_path} (weight: {weight}, alpha: {lora_alpha}) - PEFT形式で読み込み成功")
                        except Exception as e1:
                            print(f"  LoRA {i+1} パス変換エラー: {e1}")
                            import traceback
                            traceback.print_exc()
                            # フォールバック: 通常の方法で試す
                            try:
                                self.pipe.load_lora_weights(lora_path, weight=weight)
                                print(f"  LoRA {i+1}: {lora_path} (weight: {weight}) - 通常方法で読み込み成功")
                            except Exception as e2:
                                print(f"  LoRA {i+1} 読み込みエラー（スキップ）: {e2}")
                                print(f"  注意: LoRAが適用されない可能性があります")
                    else:
                        # 通常のLoRA形式
                        self.pipe.load_lora_weights(lora_path, weight=weight)
                        print(f"  LoRA {i+1}: {lora_path} (weight: {weight}) - 読み込み成功")
                except Exception as e:
                    print(f"  LoRA {i+1} 読み込みエラー（スキップ）: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"  注意: LoRAが適用されない可能性があります")
        
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
        output_dir: str = "generated_images"
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
            filename = f"sd_{timestamp}_{i+1:02d}_{prompt[:30].replace(' ', '_')}.png"
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


async def generate_mufufu_clear_gal_lora_30():
    print("=" * 60)
    print("清楚系ギャルNSFW画像30枚生成（LoRA + 複数モデル対応）")
    print("=" * 60)
    
    # 清楚系ギャル向けのモデルとLoRA候補
    # 訓練済みLoRAを使用
    lora_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lora_output_mana_favorite")
    model_configs = [
        {
            "model_id": "runwayml/stable-diffusion-v1-5",  # LoRAのベースモデルに合わせる
            "lora_paths": [lora_path] if os.path.exists(lora_path) else [],
            "lora_weights": [1.0],
            "name": "Stable Diffusion v1.5 + LoRA"
        },
        # 他のモデルも追加可能
        # {
        #     "model_id": "Lykon/DreamShaper",
        #     "lora_paths": [],
        #     "lora_weights": [],
        #     "name": "DreamShaper"
        # },
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
    
    # 最初のモデルを使用
    config = model_configs[0]
    print(f"\n使用モデル: {config['name']} ({config['model_id']})")
    
    try:
        generator = StableDiffusionGeneratorWithLoRA(
            model_id=config['model_id'],
            lora_paths=config['lora_paths'],
            lora_weights=config['lora_weights'],
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
                print(f"  [{current}/{total}] 生成中...")
                
                try:
                    images = generator.generate(
                        prompt=base_prompt,
                        negative_prompt=negative_prompt,
                        width=512,
                        height=512,
                        num_inference_steps=50,
                        guidance_scale=7.5,
                        seed=None,
                        output_dir="mufufu_clear_gal_lora_30"
                    )
                    all_images.extend(images)
                    print(f"      [OK] 生成完了")
                except Exception as e:
                    print(f"      [ERROR] エラー: {e}")
                    continue
        
        print(f"\n[OK] 画像生成完了！")
        print(f"     合計 {len(all_images)} 枚生成されました")
        print(f"     保存先: mufufu_clear_gal_lora_30/")
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'generator' in locals():
            generator.cleanup()

if __name__ == "__main__":
    asyncio.run(generate_mufufu_clear_gal_lora_30())




