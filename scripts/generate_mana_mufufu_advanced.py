#!/usr/bin/env python3
"""
マナ好みのムフフ画像生成スクリプト（高度版）
複数のモデルとLoRAを組み合わせて高品質な画像を生成
"""

import sys
import os
import random
import gc
import time
from pathlib import Path
from datetime import datetime

# Pathをインポート（既にインポート済みだが念のため）

# パスを追加
sys.path.insert(0, '/home/mana/scripts')

import torch
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
from diffusers.utils import load_image

# マナ好みのプロンプト（清楚系ギャル）- CLIPトークン制限対応（77トークン以内）
# NSFW画像生成のため、明確に指定（より刺激的な内容）
MANA_PROMPT_BASE = "清楚系ギャル, 日本人, nude, naked, explicit, sex, oral sex, フェラ, 性行為, 裸体, best quality, masterpiece, perfect face, beautiful eyes, flawless skin, 8k, erotic, seductive"

MANA_NEGATIVE_PROMPT = (
    "worst quality, low quality, normal quality, lowres, "
    "bad anatomy, bad hands, bad face, bad eyes, bad lips, bad teeth, "
    "ugly face, deformed face, disfigured face, distorted face, "
    "asymmetric face, asymmetric eyes, crooked face, "
    "mutation, mutated face, extra face, duplicate face, "
    "fused face, malformed face, missing face parts, "
    "blurry face, blurry eyes, out of focus face, "
    "long neck, extra neck, double chin, bad proportions, "
    "gross proportions, bad body, poorly drawn face, "
    "poorly drawn eyes, cloned face, cloned eyes, "
    "watermark, text, username, signature, logo, "
    "multiple people, two faces, three faces, crowd, "
    "distant shot, far away, "
    "western, caucasian, blonde hair, blue eyes, "
    "clothed, clothes, clothing, dress, shirt, bra, underwear"  # 服を排除
)

# 利用可能なモデル（ローカル + 母艦リソース）
def discover_models():
    """利用可能なモデルを動的に検索"""
    models = {}
    
    # ローカルモデル（SDXLモデル含む）
    local_models = {
        # SD 1.5モデル
        "majicMIX realistic v7": "/mnt/c/mana_workspace/storage500/civitai_models/majicmixRealistic_v7.safetensors",
        "majicMIX lux v3": "/mnt/c/mana_workspace/storage500/civitai_models/majicmixLux_v3.safetensors",
        "realisian v60": "/mnt/c/mana_workspace/storage500/civitai_models/realisian_v60.safetensors",
        "abyssorangemix2 hardcore": "/mnt/c/mana_workspace/storage500/civitai_models/abyssorangemix2_Hard.safetensors",
        # SDXLモデル（現在は使用しない）
        # dreamshaperXL_lightningInpaint はスケジューラー互換性の問題で除外
        # uwazumimixILL_v50 は使用しない
    }
    
    # 存在するモデルのみ追加
    for name, path in local_models.items():
        if os.path.exists(path):
            models[name] = path
    
    # 母艦リソースパスを検索
    search_paths = [
        "/mnt/c/mana_workspace/storage500/civitai_models",
        "/mnt/d/mana_workspace/storage500/civitai_models",
        "/mnt/mothership/storage500/civitai_models",
        "/mnt/konoha/storage500/civitai_models",
        "/root/mothership/storage500/civitai_models",
    ]
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for model_file in Path(search_path).glob("*.safetensors"):
                try:
                    size = model_file.stat().st_size
                    # モデルは通常100MB以上
                    if size >= 100 * 1024 * 1024:
                        model_name = model_file.stem.replace("_", " ").replace("-", " ")
                        if model_name not in models:
                            models[model_name] = str(model_file)
                except:
                    continue
    
    return models

AVAILABLE_MODELS = discover_models()

# 利用可能なLoRA（見つかったもの）
AVAILABLE_LORAS = [
    # LoRAパスがあれば追加
]

def find_loras():
    """LoRAファイルを検索（ローカル + 母艦リソース）"""
    loras = []
    lora_paths = [
        # ローカルパス
        "/mnt/c/mana_workspace/storage500/ComfyUI/models/loras",
        "/mnt/c/mana_workspace/storage500/civitai_models",
        "/mnt/d/mana_workspace/storage500/ComfyUI/models/loras",
        "/mnt/d/mana_workspace/storage500/civitai_models",
        # 母艦リソースパス（SSH経由またはマウント経由）
        # 例: "/mnt/mothership/models/loras" や "ssh://konoha:/root/storage500/loras"
    ]
    
    # 母艦のリソースパスを動的に検索
    # SSH経由でアクセス可能な場合は追加
    mothership_paths = [
        "/mnt/mothership",
        "/mnt/konoha",
        "/root/mothership",
    ]
    
    for path in mothership_paths:
        if os.path.exists(path):
            lora_paths.append(f"{path}/storage500/ComfyUI/models/loras")
            lora_paths.append(f"{path}/storage500/civitai_models")
            lora_paths.append(f"{path}/models/loras")
            lora_paths.append(f"{path}/loras")
    
    for lora_path in lora_paths:
        if os.path.exists(lora_path):
            for lora_file in Path(lora_path).rglob("*.safetensors"):
                try:
                    size = lora_file.stat().st_size
                    # LoRAは通常500MB以下
                    if size <= 500 * 1024 * 1024:
                        loras.append(str(lora_file))
                except:
                    continue
    
    return loras

def is_sdxl_model(model_path):
    """SDXLモデルかどうかを判定（現在はSDXLモデルを使用しない）"""
    # 現在はSDXLモデルを使用しないため、常にFalseを返す
    return False
    # model_name = Path(model_path).name.lower()
    # # SDXLモデルの特徴的な名前パターン
    # sdxl_keywords = [
    #     "uwazumimixill",  # uwazumimixILL_v50
    #     "sdxl",  # 明示的なSDXL
    # ]
    # # dreamshaperXL_lightningInpaint は除外（スケジューラー互換性の問題）
    # # "xl"だけでは誤検出が多いため、より具体的なパターンのみ
    # return any(keyword in model_name for keyword in sdxl_keywords)

def load_model_with_lora(model_path, lora_path=None, device="cuda"):
    """モデルとLoRAを読み込み（SDXL対応）"""
    print(f"📥 モデル読み込み中: {Path(model_path).name}")
    
    # SDXLモデルかどうかを判定
    is_sdxl = is_sdxl_model(model_path)
    
    if is_sdxl:
        print("   🎨 SDXLモデルを検出しました")
        try:
            pipeline = StableDiffusionXLPipeline.from_single_file(
                model_path,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
                use_safetensors=True
            )
            # SDXL用のスケジューラー設定は元の設定を保持（互換性のため）
            # Lightningモデルなど特殊なモデルではスケジューラーを変更しない
            # pipeline.scheduler = EulerDiscreteScheduler.from_config(pipeline.scheduler.config)
        except Exception as e:
            print(f"   ⚠️ SDXLパイプライン読み込みエラー: {e}")
            # フォールバック: 通常のパイプラインで試行
            pipeline = StableDiffusionPipeline.from_single_file(
                model_path,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False
            )
            is_sdxl = False  # SDXLとして扱わない
    else:
        pipeline = StableDiffusionPipeline.from_single_file(
            model_path,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            safety_checker=None,
            requires_safety_checker=False
        )
    
    pipeline = pipeline.to(device)
    
    # GPU最適化
    if device == "cuda":
        pipeline.enable_attention_slicing()
        if hasattr(pipeline, 'enable_vae_slicing'):
            pipeline.enable_vae_slicing()
        if hasattr(pipeline, 'enable_vae_tiling'):
            pipeline.enable_vae_tiling()  # SDXLで特に有効
    
    # LoRA読み込み（利用可能な場合）
    if lora_path and os.path.exists(lora_path):
        try:
            print(f"   💎 LoRA読み込み中: {Path(lora_path).name}")
            # diffusersのload_lora_weightsを使用
            from diffusers import DiffusionPipeline
            if hasattr(pipeline, 'load_lora_weights'):
                pipeline.load_lora_weights(lora_path, adapter_name="lora")
                pipeline.set_adapters(["lora"])
        except Exception as e:
            print(f"   ⚠️ LoRA読み込み失敗（続行）: {e}")
    
    return pipeline, is_sdxl

def generate_image(pipeline, prompt, negative_prompt, num_inference_steps=50, guidance_scale=7.5, seed=None, portrait=True, is_sdxl=False):
    """画像生成（SDXL対応）"""
    generator = torch.Generator(device=pipeline.device)
    if seed is None:
        seed = random.randint(0, 2**32)
    generator.manual_seed(seed)
    
    # 解像度設定（SDXLは高解像度対応）
    if is_sdxl:
        # SDXLモデルは1024x1024以上推奨
        if portrait:
            width = 768
            height = 1024  # 縦長（3:4の比率、SDXL推奨サイズ）
        else:
            width = 1024
            height = 1024  # 正方形（SDXL標準）
    else:
        # SD 1.5モデルは512x512基準
        if portrait:
            width = 512
            height = 768  # 縦長（3:4の比率）
        else:
            width = 512
            height = 512  # 正方形
    
    # SDXLモデルや特定のモデルで added_cond_kwargs が None になる問題を回避
    # より確実なエラーハンドリング
    try:
        # まず通常の方法で試行（added_cond_kwargsを明示的に空辞書で指定してNone問題を回避）
        call_kwargs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
            "generator": generator,
        }
        # added_cond_kwargsを常に空辞書で指定（None問題を回避）
        if hasattr(pipeline.unet.config, 'addition_embed_type'):
            call_kwargs["added_cond_kwargs"] = {}
        
        image = pipeline(**call_kwargs).images[0]
    except TypeError as e:
        error_str = str(e)
        if "NoneType" in error_str and "not iterable" in error_str:
            # added_cond_kwargs の問題を回避
            # SDXLモデルや特定のモデルでは added_cond_kwargs を明示的に空の辞書で指定
            try:
                # 方法1: added_cond_kwargs を空の辞書で指定
                image = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    width=width,
                    height=height,
                    generator=generator,
                    added_cond_kwargs={}
                ).images[0]
            except Exception as e2:
                # 方法2: 標準サイズ（512x512）で再試行
                try:
                    image = pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        generator=generator
                    ).images[0]
                except Exception as e3:
                    # 方法3: 最小限のパラメータで再試行
                    image = pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=num_inference_steps,
                        generator=generator
                    ).images[0]
        else:
            raise
    except Exception as e:
        # その他のエラーもキャッチして再試行
        error_str = str(e)
        if "added_cond_kwargs" in error_str or "NoneType" in error_str:
            try:
                # 最小限のパラメータで再試行
                image = pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=num_inference_steps,
                    generator=generator
                ).images[0]
            except:
                raise e
        else:
            raise
    
    return image, seed

def generate_mana_mufufu_advanced(num_images=50):
    """マナ好みのムフフ画像生成（高度版）"""
    print("🎨 マナ好みのムフフ画像生成開始（高度版）！")
    print(f"   生成枚数: {num_images}枚")
    print(f"   プロンプト: {MANA_PROMPT_BASE[:60]}...")
    print("=" * 60)
    
    # GPU確認
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"✅ GPU利用可能: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ GPUが利用できません。CPUモードで実行します。")
    
    # LoRA検索
    print("\n🔍 LoRA検索中...")
    loras = find_loras()
    print(f"   💎 見つかったLoRA: {len(loras)}個")
    
    # 出力先
    output_dir = Path("/home/mana/storage500/generated_images")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # モデルリスト
    model_list = list(AVAILABLE_MODELS.items())
    if not model_list:
        print("❌ 利用可能なモデルが見つかりません")
        return
    
    generated_count = 0
    failed_count = 0
    
    current_pipeline = None
    current_model = None
    current_is_sdxl = False
    
    for i in range(num_images):
        # SDXLモデルを優先的に選択
        sdxl_models = [(n, p) for n, p in model_list if is_sdxl_model(p)]
        
        if sdxl_models:
            # SDXLモデルがある場合はSDXLモデルから選択
            filtered_models = sdxl_models
            print(f"   🎨 SDXLモデルを使用します")
        else:
            # SDXLモデルがない場合は通常のフィルタリング
            filtered_models = [(n, p) for n, p in model_list if "realisian" not in n.lower()]
            if not filtered_models:
                filtered_models = model_list  # すべてrealisianの場合はそのまま使用
        
        model_name, model_path = random.choice(filtered_models)
        
        # モデルが変わったら再読み込み
        if current_model != model_name:
            if current_pipeline:  # type: ignore[possibly-unbound]
                del current_pipeline
                gc.collect()
                if device == "cuda":
                    torch.cuda.empty_cache()
            
            # LoRA選択（ランダム、ただしPEFT backendがない場合はLoRAなし）
            # LoRA読み込みが失敗するため、一旦LoRAなしで生成
            lora_path = None  # LoRAは一旦無効化（PEFT backend問題解決まで）
            
            try:
                current_pipeline, is_sdxl = load_model_with_lora(model_path, lora_path, device)
                current_model = model_name
                current_is_sdxl = is_sdxl
                print(f"\n✅ モデル読み込み完了: {model_name}")
                if is_sdxl:
                    print(f"   🎨 SDXLモデル（高解像度対応）")
                if lora_path:
                    print(f"   💎 LoRA適用: {Path(lora_path).name}")
            except Exception as e:
                print(f"❌ モデル読み込み失敗: {e}")
                failed_count += 1
                continue
        
        # プロンプトのバリエーション（トークン制限内、より刺激的な内容）
        prompt_variations = [
            MANA_PROMPT_BASE,
            f"{MANA_PROMPT_BASE}, seductive pose, explicit content",
            f"{MANA_PROMPT_BASE}, sensual, alluring, erotic",
            f"{MANA_PROMPT_BASE}, perfect body, explicit, sex scene",
            f"{MANA_PROMPT_BASE}, oral sex, explicit, seductive",
            f"{MANA_PROMPT_BASE}, erotic pose, explicit, best quality",
        ]
        prompt = random.choice(prompt_variations)
        
        # トークン数チェック（念のため）
        from transformers import CLIPTokenizer
        try:
            tokenizer = CLIPTokenizer.from_pretrained('openai/clip-vit-large-patch14')
            tokens = tokenizer.encode(prompt)
            if len(tokens) > 77:
                # 長すぎる場合は基本プロンプトに戻す
                prompt = MANA_PROMPT_BASE
        except:
            pass  # チェック失敗時はそのまま続行
        
        print(f"\n📸 {i+1}/{num_images} 枚目生成中...")
        print(f"   モデル: {model_name}")
        if loras:
            print(f"   LoRA: {Path(random.choice(loras)).name if random.choice(loras) else 'なし'}")
        
        try:
            start_time = time.time()
            # ステップ数最適化（50-60ステップがコストパフォーマンス最良）
            # 100ステップ以上は劇的な品質向上なし、処理時間のみ増加
            # SDXLモデルは少し多めのステップ数が推奨
            # 環境変数でステップ数を指定可能（デフォルトは最適化値）
            custom_steps = int(os.environ.get('MUFUFU_STEPS', 0))
            if custom_steps > 0:
                optimal_steps = custom_steps  # 環境変数で指定されたステップ数を使用
                print(f"   ⚙️ カスタムステップ数: {optimal_steps}")
            elif current_is_sdxl:
                optimal_steps = 40 if device == "cuda" else 25  # SDXL: GPU 40ステップ、CPU 25ステップ
            else:
                optimal_steps = 50 if device == "cuda" else 30  # SD 1.5: GPU 50ステップ、CPU 30ステップ
            
            image, seed = generate_image(
                current_pipeline,  # type: ignore[possibly-unbound]
                prompt,
                MANA_NEGATIVE_PROMPT,
                num_inference_steps=optimal_steps,  # 最適化されたステップ数
                guidance_scale=7.5,  # NSFW画像生成のため、guidance_scaleは標準値
                portrait=True,  # 縦長で生成
                is_sdxl=current_is_sdxl  # SDXLモデルかどうか
            )
            
            # ファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mana_mufufu_{model_name.replace(' ', '_')}_{timestamp}_{seed}.png"
            filepath = output_dir / filename
            
            image.save(filepath)
            
            elapsed = time.time() - start_time
            generated_count += 1
            print(f"   ✅ {generated_count}枚目完了: {filename} ({elapsed:.1f}秒)")
            
        except Exception as e:
            failed_count += 1
            print(f"   ❌ 生成失敗: {e}")
            import traceback
            traceback.print_exc()
        
        # メモリクリア
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        time.sleep(0.5)
    
    # クリーンアップ
    if current_pipeline:  # type: ignore[possibly-unbound]
        del current_pipeline
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
    
    print(f"\n🎉 マナ好みのムフフ画像生成完了！")
    print(f"   ✅ 成功: {generated_count}枚")
    print(f"   ❌ 失敗: {failed_count}枚")
    print(f"📁 保存先: {output_dir}")
    print(f"🌐 ギャラリー: http://localhost:5557")

if __name__ == "__main__":
    num_images = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    generate_mana_mufufu_advanced(num_images=num_images)

