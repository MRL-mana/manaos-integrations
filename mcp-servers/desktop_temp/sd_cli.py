"""
Stable Diffusion CLI ツール
コマンドラインから簡単に画像生成
"""

import argparse
import sys
from stable_diffusion_generator import StableDiffusionGenerator

def main():
    parser = argparse.ArgumentParser(
        description="Stable Diffusion 画像生成CLIツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な画像生成
  python sd_cli.py "a beautiful sunset over mountains"
  
  # 高品質な画像生成（ステップ数とサイズを指定）
  python sd_cli.py "a cat sitting on a windowsill" --steps 50 --width 768 --height 768
  
  # ネガティブプロンプトを指定
  python sd_cli.py "portrait of a woman" --negative "blurry, low quality, distorted"
  
  # 複数画像を生成
  python sd_cli.py "landscape painting" --num-images 4
  
  # シードを指定（再現性のため）
  python sd_cli.py "abstract art" --seed 42
  
  # バッチ生成（複数プロンプト）
  python sd_cli.py --batch "prompt1" "prompt2" "prompt3"
        """
    )
    
    # 基本オプション
    parser.add_argument(
        "prompt",
        nargs="*",
        help="生成したい画像の説明（プロンプト）"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="runwayml/stable-diffusion-v1-5",
        help="使用するモデルID（デフォルト: runwayml/stable-diffusion-v1-5）"
    )
    
    parser.add_argument(
        "--negative",
        type=str,
        default="",
        help="ネガティブプロンプト（避けたい要素）"
    )
    
    parser.add_argument(
        "--width",
        type=int,
        default=512,
        help="画像の幅（デフォルト: 512）"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=512,
        help="画像の高さ（デフォルト: 512）"
    )
    
    parser.add_argument(
        "--steps",
        type=int,
        default=50,
        help="推論ステップ数（デフォルト: 50、多いほど高品質だが時間がかかる）"
    )
    
    parser.add_argument(
        "--guidance",
        type=float,
        default=7.5,
        help="ガイダンススケール（デフォルト: 7.5、プロンプトへの従順度）"
    )
    
    parser.add_argument(
        "--num-images",
        type=int,
        default=1,
        help="生成する画像数（デフォルト: 1）"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="乱数シード（再現性のため）"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="generated_images",
        help="出力ディレクトリ（デフォルト: generated_images）"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="バッチモード（複数のプロンプトを処理）"
    )
    
    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu"],
        default=None,
        help="使用するデバイス（デフォルト: 自動検出）"
    )
    
    args = parser.parse_args()
    
    # プロンプトの確認
    if not args.prompt:
        parser.print_help()
        sys.exit(1)
    
    # プロンプトの結合
    if args.batch:
        prompts = args.prompt
    else:
        prompts = [" ".join(args.prompt)]
    
    print("=" * 60)
    print("Stable Diffusion 画像生成")
    print("=" * 60)
    print(f"モデル: {args.model}")
    print(f"デバイス: {args.device or '自動検出'}")
    print(f"プロンプト数: {len(prompts)}")
    print("=" * 60)
    
    # 生成器の初期化
    try:
        generator = StableDiffusionGenerator(
            model_id=args.model,
            device=args.device
        )
    except Exception as e:
        print(f"エラー: モデルの読み込みに失敗しました: {e}")
        print("\nヒント:")
        print("1. Hugging Face Hubにログインしているか確認してください")
        print("2. インターネット接続を確認してください")
        print("3. モデルIDが正しいか確認してください")
        sys.exit(1)
    
    try:
        # バッチ生成
        if len(prompts) > 1:
            generator.generate_batch(
                prompts=prompts,
                negative_prompt=args.negative,
                width=args.width,
                height=args.height,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                num_images_per_prompt=args.num_images,
                seed=args.seed,
                output_dir=args.output_dir
            )
        else:
            # 単一生成
            generator.generate(
                prompt=prompts[0],
                negative_prompt=args.negative,
                width=args.width,
                height=args.height,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                num_images_per_prompt=args.num_images,
                seed=args.seed,
                output_dir=args.output_dir
            )
        
        print("\n" + "=" * 60)
        print("画像生成が完了しました！")
        print(f"画像は '{args.output_dir}' フォルダに保存されています。")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n生成が中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        generator.cleanup()


if __name__ == "__main__":
    main()
