# -*- coding: utf-8 -*-
"""
改善版LoRA（20枚、100エポック）で画像生成
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
import argparse
from peft import LoraConfig, get_peft_model
import safetensors.torch

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def load_lora_from_checkpoint(pipeline, checkpoint_path, lora_rank=8, lora_alpha=16, device="cuda", merge=True):
    """チェックポイントからLoRAをロード"""
    checkpoint_path = Path(checkpoint_path)
    
    print(f"チェックポイントからLoRAをロード: {checkpoint_path}")
    
    # model_2.safetensorsからPEFT LoRAアダプターをロード
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
        print(f"[INFO] Missing keys: {len(missing_keys)} keys")
    if unexpected_keys:
        print(f"[INFO] Unexpected keys: {len(unexpected_keys)} keys")
    
    # LoRAをベースモデルにマージ（効果を強くする）
    if merge:
        print("LoRAをベースモデルにマージ中（強度を上げます）...")
        pipeline.unet = pipeline.unet.merge_and_unload()
        print(f"[OK] LoRA merged into base model (より強く反映されます)")
    else:
        print(f"[OK] LoRA loaded from model_2.safetensors (マージせず適用)")
    
    return pipeline


def main():
    parser = argparse.ArgumentParser(description="改善版LoRAで画像生成")
    parser.add_argument("--lora_path", type=str, required=True, help="LoRAチェックポイントのパス")
    parser.add_argument("--lora_rank", type=int, default=8, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=16, help="LoRA alpha")
    parser.add_argument("--num_images", type=int, default=10, help="生成する画像数")
    parser.add_argument("--prompt", type=str, default="manaPerson, woman, close-up portrait, beautiful face, high quality", help="プロンプト")
    parser.add_argument("--output_dir", type=str, default="output_lora_20_improved", help="出力ディレクトリ")
    parser.add_argument("--num_inference_steps", type=int, default=30, help="推論ステップ数")
    parser.add_argument("--guidance_scale", type=float, default=7.5, help="ガイダンススケール")
    parser.add_argument("--seed", type=int, default=None, help="ランダムシード")
    parser.add_argument("--merge_lora", action="store_true", default=True, help="LoRAをベースモデルにマージ（強度を上げる）")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("改善版LoRAで画像生成")
    print("=" * 80)
    
    # デバイス
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"デバイス: {device}")
    
    # ベースモデル
    base_model = "runwayml/stable-diffusion-v1-5"
    print(f"ベースモデル: {base_model}")
    
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
    print(f"\nLoRAをロード中: {args.lora_path}")
    if args.merge_lora:
        print("⚠️  LoRAマージモード: ON (強度を上げます)")
    pipeline = load_lora_from_checkpoint(
        pipeline, 
        args.lora_path, 
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
        device=device,
        merge=args.merge_lora
    )
    
    # 出力ディレクトリを作成
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ネガティブプロンプト
    negative_prompt = (
        "blurry, low quality, distorted, ugly, "
        "bad anatomy, bad proportions, deformed, disfigured, "
        "poorly drawn, cartoon, anime, illustration, "
        "painting, drawing, sketch, 2d, fake, artificial, "
        "extra fingers, missing fingers, extra arms, missing arms, "
        "bad hands, malformed hands, deformed hands, "
        "text, watermark, signature"
    )
    
    # 画像生成
    print(f"\n画像を{args.num_images}枚生成します...")
    print(f"プロンプト: {args.prompt}")
    print(f"出力先: {output_dir}")
    
    for i in range(args.num_images):
        seed = args.seed + i if args.seed is not None else random.randint(0, 2**32 - 1)
        generator = torch.Generator(device=device).manual_seed(seed)
        
        print(f"\n[{i+1}/{args.num_images}] 生成中... (seed: {seed})")
        
        image = pipeline(
            prompt=args.prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=args.num_inference_steps,
            guidance_scale=args.guidance_scale,
            generator=generator,
            height=512,
            width=512
        ).images[0]
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"generated_{i+1:03d}_{timestamp}.png"
        image.save(filename)
        print(f"保存: {filename}")
    
    print(f"\n完了！{args.num_images}枚の画像を生成しました。")
    print(f"出力先: {output_dir}")


if __name__ == "__main__":
    main()

