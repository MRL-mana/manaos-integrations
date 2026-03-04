"""
Llama 3 Guru Uncensored + Stable Diffusion CLI
コマンドラインから簡単に画像生成
"""

import asyncio
import argparse
import sys
from llama3_guru_image_generator import Llama3GuruImageGenerator


async def interactive_mode():
    """インタラクティブモード"""
    print("=" * 60)
    print("Llama 3 Guru Uncensored + Stable Diffusion")
    print("インタラクティブ画像生成モード")
    print("=" * 60)
    print("\n'quit'または'exit'で終了します\n")
    
    # 生成器の初期化
    generator = Llama3GuruImageGenerator(
        llama_model="gurubot/llama3-guru-uncensored:latest"
    )
    
    # 接続確認
    if not await generator.check_llama_connection():
        print("❌ Llama 3への接続に失敗しました")
        models = await generator.list_available_models()
        if models:
            print("\n利用可能なモデル:")
            for model in models:
                print(f"  - {model}")
            print("\nヒント: モデル名を確認して、スクリプト内のllama_modelを変更してください")
        return
    
    print("✅ Llama 3への接続成功\n")
    
    try:
        while True:
            # ユーザー入力
            user_request = input("画像のリクエストを入力してください: ").strip()
            
            if not user_request:
                continue
            
            if user_request.lower() in ['quit', 'exit', 'q']:
                print("\n終了します。")
                break
            
            # オプション設定
            print("\nオプション設定（Enterでデフォルト）:")
            style = input("スタイル [detailed]: ").strip() or "detailed"
            width = input("幅 [512]: ").strip() or "512"
            height = input("高さ [512]: ").strip() or "512"
            steps = input("ステップ数 [30]: ").strip() or "30"
            
            try:
                width = int(width)
                height = int(height)
                steps = int(steps)
            except ValueError:
                print("数値が無効です。デフォルト値を使用します。")
                width, height, steps = 512, 512, 30
            
            # 画像生成
            try:
                await generator.generate_image(
                    user_request=user_request,
                    style=style,
                    width=width,
                    height=height,
                    num_inference_steps=steps
                )
                print("\n✅ 画像生成が完了しました！\n")
            except Exception as e:
                print(f"\n❌ エラー: {e}\n")
    
    except KeyboardInterrupt:
        print("\n\n終了します。")
    finally:
        generator.cleanup()


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Llama 3 Guru Uncensored + Stable Diffusion 画像生成CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # インタラクティブモード
  python llama3_guru_image_cli.py
  
  # 直接生成
  python llama3_guru_image_cli.py "美しい風景"
  
  # オプション指定
  python llama3_guru_image_cli.py "ポートレート" --width 768 --height 1024 --steps 50
        """
    )
    
    parser.add_argument(
        "request",
        nargs="?",
        help="画像生成のリクエスト（省略時はインタラクティブモード）"
    )
    
    parser.add_argument(
        "--llama-model",
        type=str,
        default="gurubot/llama3-guru-uncensored:latest",
        help="Llama 3モデル名（デフォルト: gurubot/llama3-guru-uncensored:latest）"
    )
    
    parser.add_argument(
        "--sd-model",
        type=str,
        default="runwayml/stable-diffusion-v1-5",
        help="Stable DiffusionモデルID"
    )
    
    parser.add_argument(
        "--style",
        type=str,
        default="detailed",
        help="スタイル（デフォルト: detailed）"
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
        default=30,
        help="推論ステップ数（デフォルト: 30）"
    )
    
    parser.add_argument(
        "--guidance",
        type=float,
        default=7.5,
        help="ガイダンススケール（デフォルト: 7.5）"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="generated_images",
        help="出力ディレクトリ（デフォルト: generated_images）"
    )
    
    parser.add_argument(
        "--no-llama-prompt",
        action="store_true",
        help="Llama 3でプロンプトを生成せず、リクエストを直接使用"
    )
    
    args = parser.parse_args()
    
    # インタラクティブモード
    if not args.request:
        await interactive_mode()
        return
    
    # 直接生成モード
    generator = Llama3GuruImageGenerator(
        llama_model=args.llama_model,
        sd_model_id=args.sd_model
    )
    
    # 接続確認
    if not await generator.check_llama_connection():
        print("❌ Llama 3への接続に失敗しました")
        models = await generator.list_available_models()
        if models:
            print("\n利用可能なモデル:")
            for model in models:
                print(f"  - {model}")
        sys.exit(1)
    
    print("✅ Llama 3への接続成功")
    
    try:
        await generator.generate_image(
            user_request=args.request,
            style=args.style,
            width=args.width,
            height=args.height,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            output_dir=args.output_dir,
            use_llama_prompt=not args.no_llama_prompt
        )
        
        print("\n" + "=" * 60)
        print("✅ 画像生成が完了しました！")
        print(f"画像は '{args.output_dir}' フォルダに保存されています。")
        print("=" * 60)
    
    except KeyboardInterrupt:
        print("\n\n生成が中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        generator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

