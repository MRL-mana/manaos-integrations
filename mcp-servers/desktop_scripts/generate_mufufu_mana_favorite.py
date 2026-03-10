# -*- coding: utf-8 -*-
"""
マナ好みのムフフ画像生成スクリプト
各モデルで10枚ずつ、さらに2モデル組み合わせでも生成
"""

import torch
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
import random
import asyncio
import sys
import io
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import gc

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# LLMを使ったプロンプト生成（オプション）
LLM_AVAILABLE = False
LocalLLM = None
try:
    from local_llm_helper_simple import LocalLLM
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    # 型ヒント用のダミークラス
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from local_llm_helper_simple import LocalLLM

class LocalModelGenerator:
    """ローカルのsafetensorsファイルからモデルを読み込む生成クラス"""
    
    def __init__(
        self,
        model_path: str,
        device: Optional[str] = None,
        disable_safety_checker: bool = True
    ):
        """Stable Diffusion生成器を初期化"""
        self.model_path = model_path
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"デバイス: {self.device}")
        print(f"モデルを読み込み中: {model_path}...")
        
        # ローカルファイルから読み込み（SDXL対応）
        # CyberRealistic Ponyなどは通常のSDベースの可能性が高いため、通常パイプラインを優先
        self.is_sdxl = False
        model_name_lower = Path(model_path).stem.lower()
        
        # モデル名からSDXLかどうかを推測
        is_likely_sdxl = "xl" in model_name_lower or "sdxl" in model_name_lower
        
        if is_likely_sdxl:
            # SDXLの可能性が高い場合はSDXLパイプラインを先に試す
            try:
                self.pipe = StableDiffusionXLPipeline.from_single_file(
                    model_path,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    use_safetensors=True
                )
                self.is_sdxl = True
                print("SDXLパイプラインで読み込み成功")
            except Exception as e:
                print(f"SDXLパイプラインで読み込み失敗、通常パイプラインで再試行: {e}")
                try:
                    self.pipe = StableDiffusionPipeline.from_single_file(
                        model_path,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                        safety_checker=None if disable_safety_checker else None,
                        requires_safety_checker=False if disable_safety_checker else True
                    )
                    print("通常パイプラインで読み込み成功")
                except Exception as e2:
                    print(f"モデル読み込みエラー: {e2}")
                    raise
        else:
            # 通常のSDベースの可能性が高い場合は通常パイプラインを先に試す
            try:
                self.pipe = StableDiffusionPipeline.from_single_file(
                    model_path,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    safety_checker=None if disable_safety_checker else None,
                    requires_safety_checker=False if disable_safety_checker else True
                )
                print("通常パイプラインで読み込み成功")
            except Exception as e:
                print(f"通常パイプラインで読み込み失敗、SDXLパイプラインで再試行: {e}")
                try:
                    self.pipe = StableDiffusionXLPipeline.from_single_file(
                        model_path,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                        use_safetensors=True
                    )
                    self.is_sdxl = True
                    print("SDXLパイプラインで読み込み成功")
                except Exception as e2:
                    print(f"モデル読み込みエラー: {e2}")
                    raise
        
        # 安全フィルターを無効化
        if disable_safety_checker:
            self.pipe.safety_checker = None
            self.pipe.feature_extractor = None
        
        # スケジューラーの設定（majicMIX推奨設定）
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
                pass
        
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
        output_dir: str = "generated_images",
        clip_skip: int = 2
    ) -> List[str]:
        """画像を生成"""
        os.makedirs(output_dir, exist_ok=True)
        
        generator = torch.Generator(device=self.device)
        if seed is not None:
            generator.manual_seed(seed)
        
        # clip_skipの設定（majicMIX推奨）
        if hasattr(self.pipe, 'text_encoder') and clip_skip > 1:
            # clip_skipはパイプラインの設定で行う
            pass
        
        # パイプライン呼び出しパラメータ
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
        if self.is_sdxl:
            pipe_kwargs["output_type"] = "pil"
        
        try:
            images = self.pipe(**pipe_kwargs).images
        except TypeError as e:
            # added_cond_kwargs関連のエラーの場合、通常パイプラインとして再試行
            if "added_cond_kwargs" in str(e) or "NoneType" in str(e):
                print(f"SDXLパイプラインでエラー発生、通常パイプラインとして再試行: {e}")
                # 通常パイプラインとして再読み込み
                try:
                    self.pipe = StableDiffusionPipeline.from_single_file(
                        self.model_path,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                        safety_checker=None,
                        requires_safety_checker=False
                    )
                    self.pipe = self.pipe.to(self.device)
                    self.is_sdxl = False
                    # 再度生成を試みる
                    images = self.pipe(**pipe_kwargs).images
                except Exception as e2:
                    print(f"再試行も失敗: {e2}")
                    raise
            else:
                raise
        
        # 画像を保存
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
        """メモリのクリーンアップ"""
        del self.pipe
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        gc.collect()


async def generate_prompt_with_llm(llm, request: str) -> Optional[str]:
    """LLMを使ってプロンプトを生成"""
    if not llm or not LLM_AVAILABLE:
        return None
    
    try:
        system_prompt = """You are an expert at creating prompts for Stable Diffusion image generation.
Generate a high-quality, detailed prompt for "mufufu" style images (Japanese clear pure gal aesthetic).

Requirements:
- Write in English
- Include: mufufu, beautiful woman, japanese clear pure gal style, very clear pure gal aesthetic
- Add quality keywords: photorealistic, highly detailed, 4k, masterpiece, best quality, ultra high res
- Include pose, lighting, and atmosphere descriptions
- Use comma-separated format
- Make it unique and creative each time

User request: {request}""".format(request=request)
        
        user_prompt = f"Generate a unique Stable Diffusion prompt for: {request}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await asyncio.wait_for(
            llm.chat(messages),
            timeout=60
        )
        
        # プロンプトを抽出
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Prompt:') or (len(line) > 50 and ',' in line):
                if line.startswith('Prompt:'):
                    return line.split(':', 1)[1].strip()
                return line
        
        return response.strip()[:500]  # 最初の500文字を使用
    except Exception as e:
        print(f"[WARN] LLMプロンプト生成エラー: {e}")
        return None


def get_mana_favorite_prompts():
    """マナ好みのムフフプロンプトを生成（毎回変わる）"""
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
    
    # ポーズバリエーション
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
    
    # 服装・状態バリエーション
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
    
    # 照明・雰囲気
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
    """ネガティブプロンプト（身体の異常を避ける）"""
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


async def main_async():
    """メイン関数（非同期版）"""
    print("=" * 80)
    print("マナ好みのムフフ画像生成")
    print("=" * 80)
    
    # LLMの初期化（オプション）
    llm = None
    if LLM_AVAILABLE:
        try:
            llm = LocalLLM(default_model="gurubot/llama3-guru-uncensored:latest")  # type: ignore[operator]
            if await llm.check_connection():
                print("[OK] LLM接続成功 - AIプロンプト生成を使用")
            else:
                print("[INFO] LLM接続失敗 - ランダムプロンプトを使用")
                llm = None
        except Exception as e:
            print(f"[INFO] LLM初期化失敗 - ランダムプロンプトを使用: {e}")
            llm = None
    else:
        print("[INFO] LLM機能なし - ランダムプロンプトを使用")
    
    # モデルパス
    models_dir = Path("models")
    model_configs = [
        {
            "path": str(models_dir / "majicMIX realistic 麦橘写实_v1_majicmixRealistic_v1.safetensors"),
            "name": "majicMIX realistic",
            "output_dir": "mufufu_majicmix_10"
        },
        {
            "path": str(models_dir / "urpm_sd15.safetensors"),
            "name": "URPM-SD15",
            "output_dir": "mufufu_urpm_10"
        },
        {
            "path": str(models_dir / "cyberrealistic_pony.safetensors"),
            "name": "CyberRealistic Pony",
            "output_dir": "mufufu_cyberrealistic_10"
        }
    ]
    
    # モデルファイルの存在確認
    available_models = []
    for config in model_configs:
        if Path(config["path"]).exists():
            available_models.append(config)
            print(f"[OK] {config['name']}: {config['path']}")
        else:
            print(f"[NG] {config['name']}: ファイルが見つかりません ({config['path']})")
    
    if not available_models:
        print("\nエラー: 利用可能なモデルがありません")
        return
    
    print(f"\n利用可能なモデル: {len(available_models)}個")
    print("=" * 80)
    
    negative_prompt = get_negative_prompt()
    
    # 各モデルで10枚ずつ生成
    for model_idx, config in enumerate(available_models, 1):
        print(f"\n{'='*80}")
        print(f"[{model_idx}/{len(available_models)}] モデル: {config['name']}")
        print(f"{'='*80}")
        
        try:
            generator = LocalModelGenerator(
                model_path=config["path"],
                disable_safety_checker=True
            )
            
            # プロンプト生成（LLM使用またはランダム）
            all_images = []
            
            for i in range(10):
                # LLMでプロンプト生成を試みる
                if llm and i % 3 == 0:  # 3枚に1回はLLMを使用
                    request = f"mufufu style image {i+1}, japanese clear pure gal, beautiful woman"
                    llm_prompt = await generate_prompt_with_llm(llm, request)
                    if llm_prompt:
                        prompt = llm_prompt
                        print(f"[AI] LLM生成プロンプト使用")
                    else:
                        prompts = get_mana_favorite_prompts()
                        prompt = prompts[i % len(prompts)]
                else:
                    prompts = get_mana_favorite_prompts()
                    prompt = prompts[i % len(prompts)]
                print(f"\n[{i}/10] 生成中...")
                print(f"プロンプト: {prompt[:80]}...")
                
                try:
                    seed = random.randint(0, 2**32 - 1)
                    images = generator.generate(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=512,
                        height=768,
                        num_inference_steps=30,
                        guidance_scale=7.5,
                        seed=seed,
                        output_dir=config['output_dir'],
                        clip_skip=2
                    )
                    all_images.extend(images)
                    print(f"  [OK] 保存先: {images[0]}")
                except Exception as e:
                    print(f"  [ERROR] {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"\n[完了] {config['name']}: {len(all_images)}枚生成")
            print(f"保存先: {config['output_dir']}/")
            
            # メモリクリーンアップ
            generator.cleanup()
            del generator
            gc.collect()
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
        except Exception as e:
            print(f"[ERROR] {config['name']} でエラー: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 2モデル組み合わせ生成（最初の2つのモデルを使用）
    if len(available_models) >= 2:
        print(f"\n{'='*80}")
        print("2モデル組み合わせ生成")
        print(f"{'='*80}")
        
        model1_config = available_models[0]
        model2_config = available_models[1]
        
        print(f"\nモデル1: {model1_config['name']}")
        print(f"モデル2: {model2_config['name']}")
        
        # 各モデルで同じプロンプトを生成して比較
        combined_output_dir = "mufufu_combined_10"
        
        for i in range(10):
            # プロンプト生成（LLM使用またはランダム）
            if llm and i % 3 == 0:  # 3枚に1回はLLMを使用
                request = f"mufufu style image {i+1}, japanese clear pure gal, beautiful woman"
                llm_prompt = await generate_prompt_with_llm(llm, request)
                if llm_prompt:
                    prompt = llm_prompt
                    print(f"[AI] LLM生成プロンプト使用")
                else:
                    prompts = get_mana_favorite_prompts()
                    prompt = prompts[i % len(prompts)]
            else:
                prompts = get_mana_favorite_prompts()
                prompt = prompts[i % len(prompts)]
            print(f"\n[{i}/10] 組み合わせ生成中...")
            
            # モデル1で生成
            try:
                generator1 = LocalModelGenerator(
                    model_path=model1_config["path"],
                    disable_safety_checker=True
                )
                
                seed = random.randint(0, 2**32 - 1)
                images1 = generator1.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=512,
                    height=768,
                    num_inference_steps=30,
                    guidance_scale=7.5,
                    seed=seed,
                    output_dir=f"{combined_output_dir}/model1_{model1_config['name']}"
                )
                generator1.cleanup()
                del generator1
                gc.collect()
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                
                print(f"  [OK] モデル1: {images1[0]}")
            except Exception as e:
                print(f"  [ERROR] モデル1: {e}")
            
            # モデル2で生成
            try:
                generator2 = LocalModelGenerator(
                    model_path=model2_config["path"],
                    disable_safety_checker=True
                )
                
                images2 = generator2.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=512,
                    height=768,
                    num_inference_steps=30,
                    guidance_scale=7.5,
                    seed=seed,  # 同じシードで比較  # type: ignore[possibly-unbound]
                    output_dir=f"{combined_output_dir}/model2_{model2_config['name']}"
                )
                generator2.cleanup()
                del generator2
                gc.collect()
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                
                print(f"  [OK] モデル2: {images2[0]}")
            except Exception as e:
                print(f"  [ERROR] モデル2: {e}")
        
        print(f"\n[完了] 組み合わせ生成完了")
        print(f"保存先: {combined_output_dir}/")
    
    print(f"\n{'='*80}")
    print("すべての生成が完了しました！")
    print(f"{'='*80}")


def main():
    """メイン関数（同期ラッパー）"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

