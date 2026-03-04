"""
Stable Diffusion 画像生成システム
本格的なAI画像生成ツール
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
from datetime import datetime
from functools import lru_cache
from typing import List, Optional, Tuple
import json

class StableDiffusionGenerator:
    """Stable Diffusion画像生成クラス"""
    
    def __init__(
        self,
        model_id: str = "runwayml/stable-diffusion-v1-5",
        device: Optional[str] = None,
        use_safetensors: bool = True,
        torch_dtype: torch.dtype = torch.float16 if torch.cuda.is_available() else torch.float32,
        enable_memory_efficient_attention: bool = True,
        disable_safety_checker: bool = False
    ):
        """
        Stable Diffusion生成器を初期化
        
        Args:
            model_id: 使用するモデルのID（Hugging Face Hub）
            device: 使用するデバイス（Noneの場合は自動検出）
            use_safetensors: safetensors形式を使用するか
            torch_dtype: 使用するデータ型
            enable_memory_efficient_attention: メモリ効率的なアテンションを使用するか
            disable_safety_checker: 安全フィルターを無効化するか（ローカル環境用）
        """
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.torch_dtype = torch_dtype
        
        print(f"デバイス: {self.device}")
        print(f"モデルを読み込み中: {model_id}...")
        
        # パイプラインの読み込み
        self.pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            use_safetensors=use_safetensors,
            safety_checker=None if disable_safety_checker else None,
            requires_safety_checker=False if disable_safety_checker else True
        )
        
        # 安全フィルターを無効化（ローカル環境用）
        if disable_safety_checker:
            self.pipe.safety_checker = None
            self.pipe.feature_extractor = None
            print("安全フィルターを無効化しました（ローカル環境用）")
        
        # スケジューラーの設定（高品質生成用）
        try:
            scheduler_config = self.pipe.scheduler.config.copy()
            # Realistic Visionなどの一部モデル用の設定
            if 'final_sigmas_type' in scheduler_config and scheduler_config.get('final_sigmas_type') == 'zero':
                scheduler_config['final_sigmas_type'] = 'sigma_min'
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(scheduler_config)
        except Exception as e:
            print(f"スケジューラー設定エラー（デフォルトを使用）: {e}")
            # エラー時はデフォルトのスケジューラーを使用
            pass
        
        # メモリ効率的なアテンション
        if enable_memory_efficient_attention and hasattr(self.pipe, "enable_attention_slicing"):
            self.pipe.enable_attention_slicing()
        
        # デバイスに移動
        self.pipe = self.pipe.to(self.device)
        
        # xformersを使用可能な場合
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
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        num_images_per_prompt: int = 1,
        seed: Optional[int] = None,
        output_dir: str = "generated_images",
        save_metadata: bool = True
    ) -> List[Image.Image]:
        """
        画像を生成
        
        Args:
            prompt: プロンプト（生成したい画像の説明）
            negative_prompt: ネガティブプロンプト（避けたい要素）
            width: 画像の幅
            height: 画像の高さ
            num_inference_steps: 推論ステップ数（多いほど高品質、時間がかかる）
            guidance_scale: ガイダンススケール（プロンプトへの従順度、7.5が標準）
            num_images_per_prompt: 生成する画像数
            seed: 乱数シード（再現性のため）
            output_dir: 出力ディレクトリ
            save_metadata: メタデータを保存するか
        
        Returns:
            生成された画像のリスト
        """
        # 出力ディレクトリの作成
        os.makedirs(output_dir, exist_ok=True)
        
        # シードの設定
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        print(f"\n画像生成中...")
        print(f"プロンプト: {prompt}")
        if negative_prompt:
            print(f"ネガティブプロンプト: {negative_prompt}")
        print(f"サイズ: {width}x{height}, ステップ数: {num_inference_steps}")
        
        # 画像生成
        with torch.autocast(self.device):
            images = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                num_images_per_prompt=num_images_per_prompt,
                generator=generator
            ).images
        
        # 画像の保存
        saved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, image in enumerate(images):
            # ファイル名の生成
            safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_prompt = safe_prompt.replace(' ', '_')
            filename = f"sd_{timestamp}_{i+1:02d}_{safe_prompt}.png"
            filepath = os.path.join(output_dir, filename)
            
            # 画像の保存
            image.save(filepath)
            saved_files.append(filepath)
            print(f"画像を保存しました: {filepath}")
            
            # メタデータの保存
            if save_metadata:
                metadata = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": num_inference_steps,
                    "guidance_scale": guidance_scale,
                    "seed": seed,
                    "model_id": self.model_id,
                    "timestamp": timestamp
                }
                metadata_path = filepath.replace('.png', '_metadata.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return images
    
    def generate_batch(
        self,
        prompts: List[str],
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        num_images_per_prompt: int = 1,
        seeds: Optional[List[int]] = None,
        output_dir: str = "generated_images",
        save_metadata: bool = True
    ) -> List[List[Image.Image]]:
        """
        複数のプロンプトでバッチ生成
        
        Args:
            prompts: プロンプトのリスト
            negative_prompt: ネガティブプロンプト
            width: 画像の幅
            height: 画像の高さ
            num_inference_steps: 推論ステップ数
            guidance_scale: ガイダンススケール
            num_images_per_prompt: 各プロンプトで生成する画像数
            seeds: シードのリスト（Noneの場合はランダム）
            output_dir: 出力ディレクトリ
            save_metadata: メタデータを保存するか
        
        Returns:
            各プロンプトの生成画像のリスト
        """
        all_results = []
        total = len(prompts)
        
        print(f"\nバッチ生成を開始します（{total}個のプロンプト）")
        print("=" * 60)
        
        for idx, prompt in enumerate(prompts, 1):
            print(f"\n[{idx}/{total}] 処理中...")
            seed = seeds[idx - 1] if seeds and idx - 1 < len(seeds) else None
            images = self.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                num_images_per_prompt=num_images_per_prompt,
                seed=seed,
                output_dir=output_dir,
                save_metadata=save_metadata
            )
            all_results.append(images)
        
        print("\n" + "=" * 60)
        print(f"バッチ生成が完了しました！合計 {sum(len(imgs) for imgs in all_results)} 枚の画像を生成しました。")
        
        return all_results
    
    def generate_with_variations(
        self,
        base_prompt: str,
        variations: List[str],
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        output_dir: str = "generated_images",
        save_metadata: bool = True
    ) -> List[List[Image.Image]]:
        """
        ベースプロンプトにバリエーションを追加して生成
        
        Args:
            base_prompt: ベースとなるプロンプト
            variations: 追加するバリエーションのリスト
            negative_prompt: ネガティブプロンプト
            width: 画像の幅
            height: 画像の高さ
            num_inference_steps: 推論ステップ数
            guidance_scale: ガイダンススケール
            output_dir: 出力ディレクトリ
            save_metadata: メタデータを保存するか
        
        Returns:
            各バリエーションの生成画像のリスト
        """
        prompts = [f"{base_prompt}, {variation}" for variation in variations]
        return self.generate_batch(
            prompts=prompts,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            output_dir=output_dir,
            save_metadata=save_metadata
        )
    
    def cleanup(self):
        """メモリのクリーンアップ"""
        del self.pipe
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        print("メモリをクリーンアップしました")


def main():
    """メイン関数 - サンプル画像を生成"""
    print("=" * 60)
    print("Stable Diffusion 画像生成システム")
    print("=" * 60)
    
    # 生成器の初期化
    generator = StableDiffusionGenerator(
        model_id="runwayml/stable-diffusion-v1-5",
        # より高品質なモデルを使用する場合:
        # model_id="stabilityai/stable-diffusion-2-1",
    )
    
    try:
        # サンプル1: 単一画像生成
        print("\n" + "=" * 60)
        print("サンプル1: 単一画像生成")
        print("=" * 60)
        generator.generate(
            prompt="a beautiful landscape with mountains and a lake, sunset, highly detailed, 4k",
            negative_prompt="blurry, low quality, distorted",
            width=512,
            height=512,
            num_inference_steps=30,
            guidance_scale=7.5,
            seed=42
        )
        
        # サンプル2: バッチ生成
        print("\n" + "=" * 60)
        print("サンプル2: バッチ生成")
        print("=" * 60)
        prompts = [
            "a cute cat sitting on a windowsill, natural lighting",
            "a futuristic city at night, neon lights, cyberpunk style",
            "a peaceful Japanese garden with cherry blossoms"
        ]
        generator.generate_batch(
            prompts=prompts,
            negative_prompt="blurry, low quality",
            num_inference_steps=30,
            guidance_scale=7.5
        )
        
        # サンプル3: バリエーション生成
        print("\n" + "=" * 60)
        print("サンプル3: バリエーション生成")
        print("=" * 60)
        variations = [
            "chinese woman, elegant dress",
            "japanese woman, traditional kimono",
            "korean woman, modern fashion"
        ]
        generator.generate_with_variations(
            base_prompt="portrait of a beautiful woman, highly detailed, professional photography",
            variations=variations,
            negative_prompt="blurry, low quality, distorted face",
            num_inference_steps=40,
            guidance_scale=7.5
        )
        
    finally:
        # メモリのクリーンアップ
        generator.cleanup()
    
    print("\n" + "=" * 60)
    print("すべての画像生成が完了しました！")
    print("=" * 60)


if __name__ == "__main__":
    main()
