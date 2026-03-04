# -*- coding: utf-8 -*-
"""
訓練したLoRAを使って画像生成
マナ好みのムフフ画像を10枚生成
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import os
import random
from pathlib import Path
from datetime import datetime
import sys
import io

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def load_lora_from_checkpoint(pipeline, checkpoint_path, lora_rank=16, lora_alpha=32, device="cuda"):
    """チェックポイントからLoRAをロード（Accelerator形式のチェックポイントから）"""
    checkpoint_path = Path(checkpoint_path)
    
    print(f"チェックポイントからLoRAをロード: {checkpoint_path}")
    
    # 方法1: PEFTのPeftModel.from_pretrainedを使用（PEFTアダプター形式の場合）
    try:
        from peft import PeftModel
        print("方法1: PeftModel.from_pretrained を試行...")
        pipeline.unet = PeftModel.from_pretrained(pipeline.unet, str(checkpoint_path))
        print(f"[OK] LoRA loaded using PeftModel.from_pretrained")
        return
    except Exception as e:
        print(f"[INFO] 方法1: PEFTアダプター形式ではありません ({type(e).__name__})")
    
    # 方法2: model_2.safetensorsからPEFT LoRAアダプターをロード
    try:
        print("方法2: model_2.safetensorsからPEFT LoRAアダプターをロード...")
        from peft import LoraConfig, get_peft_model
        import safetensors.torch
        
        # model_2.safetensorsを探す（PEFTモデルの完全な状態）
        model_file = checkpoint_path / "model_2.safetensors"
        if not model_file.exists():
            raise FileNotFoundError(f"model_2.safetensors not found in {checkpoint_path}")
        
        print(f"Loading PEFT LoRA from: {model_file.name}")
        
        # 状態辞書をロード
        state_dict_raw = safetensors.torch.load_file(str(model_file))
        
        # LoRAのキーを抽出（base_model.model.*.lora_A.* や base_model.model.*.lora_B.*）
        # PEFTモデルでは、base_model.model.*プレフィックスを保持する必要がある
        lora_state_dict = {}
        for key, value in state_dict_raw.items():
            if "lora" in key.lower():
                # base_model.model.*プレフィックスを保持（PEFTモデルの形式）
                lora_state_dict[key] = value
        
        if not lora_state_dict:
            raise ValueError("No LoRA weights found in checkpoint")
        
        print(f"Found {len(lora_state_dict)} LoRA weight keys")
        
        # LoRA設定（訓練時と同じ）
        lora_config = LoraConfig(
            r=lora_rank,
            lora_alpha=lora_alpha,
            target_modules=["to_k", "to_q", "to_v", "to_out.0"],
            lora_dropout=0.0,
        )
        
        # UNetにLoRAを適用
        pipeline.unet = get_peft_model(pipeline.unet, lora_config)
        
        # LoRAの重みを適用
        missing_keys, unexpected_keys = pipeline.unet.load_state_dict(lora_state_dict, strict=False)
        
        if missing_keys:
            print(f"[INFO] Missing keys: {len(missing_keys)} keys (first 5: {missing_keys[:5]})")
        if unexpected_keys:
            print(f"[INFO] Unexpected keys: {len(unexpected_keys)} keys (first 5: {unexpected_keys[:5]})")
        
        print(f"[OK] LoRA loaded from model_2.safetensors")
        return
        
    except Exception as e2:
        print(f"[WARN] 方法2失敗: {e2}")
        import traceback
        traceback.print_exc()
    
    # 方法3: LoRAアダプターを手動で構築してロード
    try:
        print("方法3: LoRAアダプターを手動構築してロード...")
        from peft import LoraConfig, get_peft_model
        import safetensors.torch
        
        # LoRA設定（訓練時と同じ）
        lora_config = LoraConfig(
            r=lora_rank,
            lora_alpha=lora_alpha,
            target_modules=["to_k", "to_q", "to_v", "to_out.0"],
            lora_dropout=0.0,
        )
        
        # UNetにLoRAを適用
        pipeline.unet = get_peft_model(pipeline.unet, lora_config)
        
        # model.safetensorsからLoRAの重みを抽出
        model_file = checkpoint_path / "model.safetensors"
        if not model_file.exists():
            model_files = list(checkpoint_path.glob("model*.safetensors"))
            model_file = next((f for f in model_files if f.name == "model.safetensors"), None)
            if not model_file and model_files:
                model_file = model_files[0]
            if not model_file:
                raise FileNotFoundError(f"Model file not found")
        
        state_dict = safetensors.torch.load_file(str(model_file))
        
        # LoRAの重みだけを抽出
        lora_state_dict = {}
        for key, value in state_dict.items():
            # LoRAアダプターのキー（base_model.model.to_k.lora_A.weight など）を探す
            if "lora" in key.lower() or ".lora_" in key or "lora_A" in key or "lora_B" in key:
                lora_state_dict[key] = value
            # base_model.model プレフィックスを削除したキーも試す
            elif "base_model.model." in key:
                new_key = key.replace("base_model.model.", "")
                if "lora" in new_key.lower() or ".lora_" in new_key:
                    lora_state_dict[new_key] = value
        
        if lora_state_dict:
            print(f"Found {len(lora_state_dict)} LoRA weight keys")
            pipeline.unet.load_state_dict(lora_state_dict, strict=False)
            print(f"[OK] LoRA loaded manually from safetensors")
            return
        else:
            # LoRAの重みが見つからない場合、全体を試す
            print("[INFO] LoRA-specific keys not found, trying full state_dict...")
            pipeline.unet.load_state_dict(state_dict, strict=False)
            print(f"[OK] State loaded from safetensors (full)")
            return
            
    except Exception as e3:
        print(f"[WARN] 方法3失敗: {e3}")
        import traceback
        traceback.print_exc()
    
    raise Exception("すべてのLoRAロード方法が失敗しました。チェックポイントの形式を確認してください。")


def get_mana_favorite_prompts():
    """マナ好みのムフフプロンプトを生成（訓練時のキャプションを含む）"""
    # 訓練時に使用したキャプションを先頭に含める（これがLoRAのトリガー）
    training_caption = "woman, portrait, beautiful face"
    
    base_elements = [
        training_caption,  # 訓練時のキャプションを先頭に
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
    """ネガティブプロンプト"""
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
    """メイン関数"""
    print("=" * 80)
    print("訓練したLoRAで画像生成（マナ好みのムフフ画像）")
    print("=" * 80)
    
    # デバイス
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"デバイス: {device}")
    
    # ベースモデル
    base_model = "runwayml/stable-diffusion-v1-5"
    print(f"ベースモデル: {base_model}")
    
    # コマンドライン引数を解析
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lora_path", type=str, default=None, help="LoRAチェックポイントパス")
    parser.add_argument("--prompt", type=str, default=None, help="生成プロンプト")
    parser.add_argument("--num_images", type=int, default=1, help="生成画像数")
    parser.add_argument("--output_dir", type=str, default="lora_generated_images_mana_favorite", help="出力ディレクトリ")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha")
    args = parser.parse_args()
    
    # LoRA出力ディレクトリ
    if args.lora_path:
        lora_output_dir = Path(args.lora_path).parent if Path(args.lora_path).is_file() else Path(args.lora_path)
    else:
        lora_output_dir = Path("lora_output_mana_favorite_japanese_clear_gal")
    
    # チェックポイントパスを決定
    if args.lora_path:
        if Path(args.lora_path).is_dir():
            latest_checkpoint = Path(args.lora_path)
        else:
            latest_checkpoint = Path(args.lora_path)
        use_checkpoint = True
        adapter_path = None
        print(f"指定されたチェックポイント: {latest_checkpoint}")
    else:
        # PEFTアダプターが保存されているか確認
        adapter_file = lora_output_dir / "adapter_model.safetensors"
        if adapter_file.exists():
            print(f"PEFTアダプターが見つかりました: {adapter_file}")
            use_checkpoint = False
            adapter_path = lora_output_dir
            latest_checkpoint = None
        else:
            # チェックポイントからロード
            checkpoint_dir = lora_output_dir
            checkpoints = sorted(checkpoint_dir.glob("checkpoint-step-*"), key=lambda x: int(x.name.split("-")[-1]))
            if not checkpoints:
                print(f"エラー: LoRAアダプターもチェックポイントも見つかりません: {lora_output_dir}")
                return
            
            latest_checkpoint = checkpoints[-1]
            print(f"使用するチェックポイント: {latest_checkpoint.name}")
            use_checkpoint = True
            adapter_path = None
    
    # パイプラインを読み込み
    print("\nベースモデルを読み込み中...")
    pipeline = StableDiffusionPipeline.from_pretrained(
        base_model,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        safety_checker=None,
        requires_safety_checker=False
    )
    
    # スケジューラーを設定
    pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config)
    
    # メモリ効率的な設定
    if hasattr(pipeline, "enable_attention_slicing"):
        pipeline.enable_attention_slicing()
    if hasattr(pipeline, "enable_xformers_memory_efficient_attention"):
        try:
            pipeline.enable_xformers_memory_efficient_attention()
            print("xformersを有効化しました")
        except:
            pass
    
    pipeline = pipeline.to(device)
    
    # LoRAをロード
    print("\nLoRAを読み込み中...")
    if not use_checkpoint and adapter_path:
        # PEFTアダプター形式でロード
        print(f"PEFTアダプター形式のLoRAをロード: {adapter_path}")
        try:
            from peft import PeftModel
            peft_model = PeftModel.from_pretrained(pipeline.unet, str(adapter_path))
            
            # LoRAをベースモデルにマージ（より効果的に動作する）
            print("LoRAをベースモデルにマージ中...")
            pipeline.unet = peft_model.merge_and_unload()
            print(f"[OK] LoRA merged into base model (これによりLoRAの効果がより強く反映されます)")
        except Exception as e:
            print(f"[ERROR] PEFTアダプターのロードに失敗: {e}")
            import traceback
            traceback.print_exc()
            return
    else:
        # チェックポイントからロード
        try:
            load_lora_from_checkpoint(pipeline, latest_checkpoint, lora_rank=4, lora_alpha=32, device=device)
        except Exception as e:
            print(f"[ERROR] LoRAの読み込みに失敗: {e}")
            import traceback
            traceback.print_exc()
            print("\n別の方法でLoRAをロードします...")
            # チェックポイントから直接UNetをロードする方法
            try:
                from diffusers import UNet2DConditionModel
                from peft import PeftModel
                
                # ベースUNetをロード
                unet = UNet2DConditionModel.from_pretrained(
                    base_model,
                    subfolder="unet",
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32
                )
                unet = unet.to(device)
                
                # LoRAアダプターをロード
                unet = PeftModel.from_pretrained(unet, str(latest_checkpoint))
                pipeline.unet = unet
                print(f"[OK] LoRA loaded using PeftModel.from_pretrained (alternative method)")
            except Exception as e2:
                print(f"[ERROR] LoRAの読み込みに完全に失敗しました: {e2}")
                import traceback
                traceback.print_exc()
                print("\nチェックポイントの構造を確認してください。")
                return
    
    # 出力ディレクトリ
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # プロンプト生成
    if args.prompt:
        prompts = [args.prompt] * args.num_images
        print(f"指定されたプロンプト: {args.prompt}")
    else:
        prompts = get_mana_favorite_prompts()
    negative_prompt = get_negative_prompt()
    
    # 画像生成
    print("\n" + "=" * 80)
    print(f"画像生成開始（{len(prompts)}枚）")
    print("=" * 80)
    
    generator = torch.Generator(device=device)
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] 生成中...")
        print(f"プロンプト: {prompt[:100]}...")
        
        try:
            seed = random.randint(0, 2**32 - 1)
            generator.manual_seed(seed)
            
            image = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=512,
                height=768,
                num_inference_steps=30,
                guidance_scale=7.5,
                generator=generator,
                num_images_per_prompt=1
            ).images[0]
            
            # 保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mana_favorite_lora_{timestamp}_{i:02d}.png"
            filepath = output_dir / filename
            image.save(filepath)
            
            print(f"  [OK] 保存: {filepath}")
            
        except Exception as e:
            print(f"  [ERROR] 生成エラー: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 80)
    print("画像生成完了！")
    print(f"保存先: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()

