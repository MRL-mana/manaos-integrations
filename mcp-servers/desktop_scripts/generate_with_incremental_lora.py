# -*- coding: utf-8 -*-
"""
インクリメンタル訓練したLoRAを使って画像生成
最新のチェックポイント（checkpoint-step-1506）を使用
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


def load_lora_from_checkpoint(pipeline, checkpoint_path, lora_rank=8, lora_alpha=16, device="cuda"):
    """チェックポイントからLoRAをロード（インクリメンタル訓練用）"""
    checkpoint_path = Path(checkpoint_path)
    
    print(f"チェックポイントからLoRAをロード: {checkpoint_path}")
    
    # model_2.safetensorsからPEFT LoRAアダプターをロード
    try:
        from peft import LoraConfig, get_peft_model
        import safetensors.torch
        
        # model_2.safetensorsを探す（PEFTモデルの完全な状態）
        model_file = checkpoint_path / "model_2.safetensors"
        if not model_file.exists():
            raise FileNotFoundError(f"model_2.safetensors not found in {checkpoint_path}")
        
        print(f"Loading PEFT LoRA from: {model_file.name}")
        
        # 状態辞書をロード
        state_dict_raw = safetensors.torch.load_file(str(model_file))
        
        # LoRAのキーを抽出
        lora_state_dict = {}
        for key, value in state_dict_raw.items():
            if "lora" in key.lower():
                # base_model.model.*プレフィックスを保持（PEFTモデルの形式）
                lora_state_dict[key] = value
        
        if not lora_state_dict:
            raise ValueError("No LoRA weights found in checkpoint")
        
        print(f"Found {len(lora_state_dict)} LoRA weight keys")
        
        # LoRA設定（訓練時と同じ: rank=8, alpha=16）
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
            print(f"[INFO] Missing keys: {len(missing_keys)} keys")
        if unexpected_keys:
            print(f"[INFO] Unexpected keys: {len(unexpected_keys)} keys")
        
        # LoRAを融合（効果を強化）
        pipeline.fuse_lora(lora_scale=1.0)
        print(f"[OK] LoRA loaded and fused from model_2.safetensors")
        return True
        
    except Exception as e:
        print(f"[ERROR] LoRA loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # デバイス設定
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用デバイス: {device}")
    
    # パイプラインを読み込み
    print("ベースモデルを読み込み中...")
    pipeline = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        safety_checker=None,
        requires_safety_checker=False,
    )
    pipeline = pipeline.to(device)
    pipeline.scheduler = DPMSolverMultistepScheduler.from_config(pipeline.scheduler.config)
    
    # LoRAをロード
    checkpoint_path = Path("lora_output_mana_favorite_incremental/checkpoint-step-1506")
    if not checkpoint_path.exists():
        print(f"[ERROR] チェックポイントが見つかりません: {checkpoint_path}")
        return
    
    print(f"最新チェックポイントを使用: {checkpoint_path.name}")
    success = load_lora_from_checkpoint(
        pipeline, 
        checkpoint_path, 
        lora_rank=8,  # 訓練時の設定
        lora_alpha=16,  # 訓練時の設定
        device=device
    )
    
    if not success:
        print("[ERROR] LoRAのロードに失敗しました")
        return
    
    # 出力ディレクトリ
    output_dir = Path("lora_generated_images_incremental")
    output_dir.mkdir(exist_ok=True)
    
    # プロンプト（訓練時のキャプションを含める）
    base_prompt = "woman, portrait, beautiful face"
    prompts = [
        f"{base_prompt}, mufufu style, anime style, detailed, high quality",
        f"{base_prompt}, mufufu style, cute, charming, detailed",
        f"{base_prompt}, mufufu style, elegant, beautiful, detailed",
        f"{base_prompt}, mufufu style, youthful, fresh, detailed",
        f"{base_prompt}, mufufu style, sweet, lovely, detailed",
        f"{base_prompt}, mufufu style, attractive, detailed",
        f"{base_prompt}, mufufu style, pretty, detailed",
        f"{base_prompt}, mufufu style, charming, detailed",
        f"{base_prompt}, mufufu style, cute, detailed",
        f"{base_prompt}, mufufu style, beautiful, detailed",
    ]
    
    negative_prompt = "blurry, low quality, distorted, bad anatomy, bad hands, text, watermark"
    
    # 画像生成
    print(f"\n画像を10枚生成します...")
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/10] 生成中: {prompt[:50]}...")
        
        # シードを設定（再現性のため）
        generator = torch.Generator(device=device).manual_seed(42 + i)
        
        # 画像生成
        image = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=50,
            guidance_scale=7.5,
            width=512,
            height=512,
            generator=generator,
        ).images[0]
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"incremental_lora_{i:02d}_{timestamp}.png"
        output_path = output_dir / filename
        image.save(output_path)
        print(f"  → 保存: {output_path}")
    
    print(f"\n[完了] 10枚の画像を生成しました")
    print(f"出力先: {output_dir.absolute()}")


if __name__ == "__main__":
    main()



