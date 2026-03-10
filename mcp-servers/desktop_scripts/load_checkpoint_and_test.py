# -*- coding: utf-8 -*-
"""チェックポイントを読み込んで画像生成をテストするスクリプト"""

import argparse
import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
from pathlib import Path

def load_lora_and_generate(
    checkpoint_path: str,
    base_model: str = "runwayml/stable-diffusion-v1-5",
    prompt: str = "woman, portrait, beautiful face",
    negative_prompt: str = "",
    num_images: int = 4,
    output_dir: str = "./test_output"
):
    """チェックポイントからLoRAを読み込んで画像生成"""
    
    checkpoint_path = Path(checkpoint_path)  # type: ignore
    output_dir = Path(output_dir)  # type: ignore
    output_dir.mkdir(parents=True, exist_ok=True)  # type: ignore
    
    print(f"チェックポイントを読み込み: {checkpoint_path}")
    print(f"ベースモデル: {base_model}")
    print(f"プロンプト: {prompt}")
    print()
    
    # ベースモデルを読み込み
    print("ベースモデルを読み込み中...")
    pipe = StableDiffusionPipeline.from_pretrained(
        base_model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    
    # LoRAを読み込み
    print(f"LoRAを読み込み中: {checkpoint_path}")
    try:
        pipe.load_lora_weights(str(checkpoint_path))
        print("LoRAを読み込みました")
    except Exception as e:
        print(f"LoRAの読み込みエラー: {e}")
        print("PEFTモデルとして読み込みを試みます...")
        try:
            from peft import PeftModel
            # この場合は別の方法で読み込む必要がある
            print("直接読み込みができない場合は、checkpoint内のadapter_model.safetensorsを使用してください")
            return
        except ImportError:
            print("peftがインストールされていません")
            return
    
    pipe = pipe.to("cuda" if torch.cuda.is_available() else "cpu")
    
    # 画像を生成
    print(f"\n{num_images}枚の画像を生成中...")
    for i in range(num_images):
        print(f"  画像 {i+1}/{num_images} 生成中...")
        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=50,
            guidance_scale=7.5,
            width=512,
            height=512,
        ).images[0]
        
        output_file = output_dir / f"test_{checkpoint_path.name}_{i+1}.png"  # type: ignore[operator]
        image.save(output_file)
        print(f"    保存: {output_file}")
    
    print(f"\n完了！出力先: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CheckpointからLoRAを読み込んでテスト")
    parser.add_argument("checkpoint_path", type=str, help="チェックポイントのパス")
    parser.add_argument("--base_model", type=str, default="runwayml/stable-diffusion-v1-5",
                       help="ベースモデル")
    parser.add_argument("--prompt", type=str, default="woman, portrait, beautiful face",
                       help="プロンプト")
    parser.add_argument("--negative_prompt", type=str, default="",
                       help="ネガティブプロンプト")
    parser.add_argument("--num_images", type=int, default=4,
                       help="生成する画像数")
    parser.add_argument("--output_dir", type=str, default="./test_output",
                       help="出力ディレクトリ")
    
    args = parser.parse_args()
    load_lora_and_generate(
        args.checkpoint_path,
        args.base_model,
        args.prompt,
        args.negative_prompt,
        args.num_images,
        args.output_dir
    )


















