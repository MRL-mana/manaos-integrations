#!/usr/bin/env python3
"""
ムフフ画像生成システム - CPU専用版
CPUモードで確実に動作する軽量画像生成システム
"""

import json
import os
from pathlib import Path
from datetime import datetime
import torch
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
import random
import sqlite3

class MufufuCPUGenerator:
    def __init__(self, force_cpu=True):
        """CPU専用画像生成システム初期化"""
        # CPUモードに強制
        self.device = "cpu"
        # 出力先を環境変数またはデフォルトから取得
        output_dir_env = os.environ.get('MUFUFU_OUTPUT_DIR', '/root/trinity_workspace/generated_images')
        self.output_dir = Path(output_dir_env)
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # パーミッションエラーの場合は /home/mana/storage500/generated_images を使用
            self.output_dir = Path("/home/mana/storage500/generated_images")
            self.output_dir.mkdir(parents=True, exist_ok=True)

        # ムフフ画像用プロンプト
        self.mufufu_prompts = {
            "clear_beautiful": [
                "a beautiful clear girl, innocent expression, soft smile, high quality, detailed, anime style",
                "cute girl with pure eyes, gentle smile, clear skin, beautiful hair, high quality, anime art",
                "innocent beautiful girl, shy expression, soft lighting, high quality, detailed illustration"
            ],
            "cute_kawaii": [
                "super cute kawaii girl, big eyes, adorable expression, soft colors, high quality",
                "lovely cute girl, sweet smile, fluffy hair, pastel colors, high quality, anime style",
                "adorable kawaii character, innocent face, cute outfit, high quality, detailed illustration"
            ],
            "elegant_style": [
                "elegant beautiful woman, sophisticated style, graceful pose, high quality, detailed",
                "refined beautiful girl, classy outfit, gentle expression, high quality, anime style"
            ],
            # NSFWプロンプト（顔の品質最優先版 - 前と同じ品質を保つ）
            "nsfw_sexy": [
                "beautiful nude girl, perfect face, detailed facial features, clear skin, symmetrical face, beautiful eyes, perfect body, sensual pose, erotic expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "gorgeous naked woman, perfect face, detailed facial features, clear skin, beautiful eyes, attractive body, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "sexy nude girl, perfect face, detailed facial features, clear skin, beautiful eyes, perfect figure, erotic pose, sensual expression, high quality, detailed art, realistic, masterpiece, best quality, ultra detailed, perfect anatomy"
            ],
            "nsfw_alluring": [
                "beautiful topless girl, perfect face, detailed facial features, clear skin, beautiful eyes, perfect breasts, sensual pose, erotic expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "gorgeous naked woman, perfect face, detailed facial features, clear skin, beautiful eyes, attractive figure, seductive pose, alluring expression, high quality, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "sexy nude girl, perfect face, detailed facial features, clear skin, beautiful eyes, perfect body, erotic pose, sensual expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy"
            ],
            "nsfw_erotic": [
                "beautiful nude woman, perfect face, detailed facial features, clear skin, beautiful eyes, perfect body, erotic pose, sensual expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "gorgeous naked girl, perfect face, detailed facial features, clear skin, beautiful eyes, attractive figure, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "sexy nude woman, perfect face, detailed facial features, clear skin, beautiful eyes, perfect body, erotic pose, sensual expression, high quality, detailed art, realistic, masterpiece, best quality, ultra detailed, perfect anatomy"
            ],
            "nsfw_fellatio": [
                "beautiful girl performing fellatio, perfect face, detailed facial features, clear skin, beautiful eyes, erotic expression, sensual pose, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "gorgeous woman giving oral sex, perfect face, detailed facial features, clear skin, beautiful eyes, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "sexy girl oral sex, perfect face, detailed facial features, clear skin, beautiful eyes, erotic pose, sensual expression, high quality, detailed art, realistic, masterpiece, best quality, ultra detailed, perfect anatomy"
            ],
            "nsfw_ecchi": [
                "beautiful girl, perfect face, detailed facial features, clear skin, beautiful eyes, revealing outfit, erotic pose, sensual expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "gorgeous woman, perfect face, detailed facial features, clear skin, beautiful eyes, sexy lingerie, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy",
                "sexy girl, perfect face, detailed facial features, clear skin, beautiful eyes, provocative pose, erotic expression, high quality, detailed art, realistic, masterpiece, best quality, ultra detailed, perfect anatomy"
            ]
        }

        # ネガティブプロンプト（顔崩れ防止最強化版 - 前と同じ設定）
        self.negative_prompt = "bad quality, low resolution, blurry, distorted, ugly, deformed, bad anatomy, bad face, deformed face, ugly face, bad facial features, distorted face, asymmetrical face, blurry face, low quality face, violence, blood, gore, scary, horror, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username"
        self.nsfw_negative_prompt = "bad quality, low resolution, blurry, distorted, ugly, deformed, bad anatomy, bad face, deformed face, ugly face, bad facial features, distorted face, asymmetrical face, blurry face, low quality face, violence, blood, gore, scary, horror, monster, demon, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username"

        # 利用可能なモデル（CPUで動作確認済みのもの）
        self.available_models = {
            "majicMIX realistic v7": "/mnt/c/mana_workspace/storage500/civitai_models/majicmixRealistic_v7.safetensors",
            "majicMIX lux v3": "/mnt/c/mana_workspace/storage500/civitai_models/majicmixLux_v3.safetensors",
            "majicMIX realistic 麦橘写实_43331": "/mnt/c/mana_workspace/storage500/model_downloads/majicMIX realistic 麦橘写实_43331.safetensors",
            "majicMIX lux 麦橘辉耀_56967": "/mnt/c/mana_workspace/storage500/model_downloads/majicMIX lux 麦橘辉耀_56967.safetensors"
        }

        # SDXLモデル（顔の品質が良い）
        # 利用可能なSDXLモデルのみ使用
        # os は既にインポート済み
        self.sdxl_models = {}

        # Dreamshaper XL Lightning（確認済み）
        dreamshaper_path = "/mnt/storage500/civitai_models/dreamshaperXL_lightningInpaint.safetensors"
        if os.path.exists(dreamshaper_path):
            self.sdxl_models["Dreamshaper XL Lightning"] = dreamshaper_path

        # SDXL Base 1.0（存在確認）
        sdxl_base_paths = [
            "/mnt/storage500/ComfyUI/models/checkpoints/sdxl-base-1.0.safetensors",
            "/mnt/storage/model_cache/sdxl-base-1.0.safetensors"
        ]
        for path in sdxl_base_paths:
            if os.path.exists(path) or os.path.islink(path):
                # シンボリックリンクを解決
                if os.path.islink(path):
                    actual_path = os.readlink(path)
                    if not os.path.isabs(actual_path):
                        actual_path = os.path.join(os.path.dirname(path), actual_path)
                    if os.path.exists(actual_path):
                        self.sdxl_models["SDXL Base 1.0"] = actual_path
                        break
                elif os.path.exists(path):
                    self.sdxl_models["SDXL Base 1.0"] = path
                    break

        self.use_sdxl = False  # SDXL使用フラグ

        self.current_model = None
        self.pipeline = None

        print("🎨 ムフフ画像生成システム - CPU専用版")
        print("=" * 50)
        print(f"🔧 デバイス: {self.device} (強制)")
        print(f"📁 出力ディレクトリ: {self.output_dir}")
        print(f"🎯 利用可能モデル数: {len(self.available_models)}")
        print("✅ CPU専用画像生成システム初期化完了")

    def load_model_sdxl(self, model_path, model_name):
        """SDXLモデル読み込み（CPU最適化版・メモリ節約）"""
        print(f"📥 SDXLモデル読み込み中: {model_name}")
        print(f"📁 パス: {model_path}")

        try:
            print("   🔧 CPU最適化設定中（メモリ節約モード）...")
            print("   🎨 SDXLパイプラインを使用")

            # メモリ節約のため、低メモリモードで読み込み
            import gc
            gc.collect()

            # SDXLモデル読み込み（メモリ節約設定）
            # シンボリックリンクを解決
            import os
            if os.path.islink(model_path):
                actual_path = os.readlink(model_path)
                if not os.path.isabs(actual_path):
                    actual_path = os.path.join(os.path.dirname(model_path), actual_path)
                model_path = actual_path

            # ファイルが存在するか確認
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"SDXLモデルファイルが見つかりません: {model_path}")

            self.pipeline = StableDiffusionXLPipeline.from_single_file(
                model_path,
                torch_dtype=torch.float32,  # CPUではfloat32必須
            )

            # CPUに移動
            self.pipeline = self.pipeline.to(self.device)

            # CPU最適化設定（メモリ節約）
            self.pipeline.enable_attention_slicing(slice_size="max")  # 最大スライスサイズでメモリ節約
            self.pipeline.enable_vae_slicing()  # VAEスライシングでメモリ節約
            self.pipeline.enable_vae_tiling()  # VAEタイリングでメモリ節約

            # メモリクリア
            gc.collect()

            self.current_model = model_name
            self.use_sdxl = True
            print(f"✅ SDXLモデル読み込み完了: {model_name}")
            print("   💡 CPU最適化設定完了（attention_slicing, vae_slicing, vae_tiling）")

        except Exception as e:
            print(f"❌ SDXLモデル読み込みエラー: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def load_model(self, model_name):
        """モデル読み込み（CPU最適化版）"""
        if model_name not in self.available_models:
            raise ValueError(f"モデル '{model_name}' が見つかりません")

        model_path = self.available_models[model_name]

        print(f"📥 モデル読み込み中: {model_name}")
        print(f"📁 パス: {model_path}")

        try:
            # CPUモード用の設定
            print("   🔧 CPU最適化設定中...")

            # 通常のSD 1.5モデル読み込み（SDXLはload_model_sdxlを使用）
            self.pipeline = StableDiffusionPipeline.from_single_file(
                model_path,
                torch_dtype=torch.float32,  # CPUではfloat32必須
                safety_checker=None,
                requires_safety_checker=False
            )
            self.use_sdxl = False

            # CPUに移動
            self.pipeline = self.pipeline.to(self.device)

            # CPU最適化設定（メモリ節約強化）
            self.pipeline.enable_attention_slicing(slice_size="max")  # 最大スライスサイズでメモリ節約
            self.pipeline.enable_vae_slicing()  # VAEスライシングでメモリ節約
            self.pipeline.enable_vae_tiling()  # VAEタイリングでメモリ節約
            # enable_sequential_cpu_offload()はacceleratorが必要なためCPUでは使用不可

            self.current_model = model_name
            print(f"✅ モデル読み込み完了: {model_name}")
            print("   💡 CPU最適化設定完了（attention_slicing）")

        except Exception as e:
            print(f"❌ モデル読み込みエラー: {str(e)}")
            raise

    def generate_mufufu_image(self, style="clear_beautiful", size="square", num_inference_steps=35):
        """ムフフ画像生成（高品質CPUモード）"""
        if not self.pipeline:
            raise ValueError("モデルが読み込まれていません")

        # プロンプト選択
        if style in self.mufufu_prompts:
            prompt = random.choice(self.mufufu_prompts[style])
        else:
            prompt = random.choice(self.mufufu_prompts["clear_beautiful"])

        # NSFWスタイルの場合は専用のネガティブプロンプトを使用
        is_nsfw = style.startswith("nsfw_")
        negative_prompt = self.nsfw_negative_prompt if is_nsfw else self.negative_prompt

        # サイズ設定（SDXLの場合は768、SD 1.5の場合は512）
        if self.use_sdxl:
            # SDXLは768に縮小（メモリ節約）
            size_presets = {
                "square": (768, 768),
                "portrait": (768, 1024),
                "landscape": (1024, 768)
            }
        else:
            # SD 1.5は高品質のため少し大きめに（顔の品質向上）
            size_presets = {
                "square": (512, 512),
                "portrait": (512, 768),  # ポートレートは顔を大きく表示
                "landscape": (768, 512)
            }
        width, height = size_presets.get(size, (512, 512) if not self.use_sdxl else (768, 768))

        print("🎨 ムフフ画像生成開始（高品質CPUモード）")
        print(f"   モデル: {self.current_model}")
        print(f"   スタイル: {style}")
        print(f"   プロンプト: {prompt[:60]}...")
        print(f"   サイズ: {width}x{height}")
        print(f"   ステップ数: {num_inference_steps}")
        print("   ⏳ 高品質設定のため時間がかかりますが、前と同じ品質になります...")

        try:
            # 画像生成（高品質設定）
            import gc
            gc.collect()  # 生成前にメモリクリア

            if self.use_sdxl:
                # SDXL用のパラメータ（メモリ節約）
                image = self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=7.0,  # SDXLは7.0が最適
                    generator=torch.Generator(device=self.device).manual_seed(random.randint(0, 2**32))
                ).images[0]
                # メモリクリア
                gc.collect()
            else:
                # SD 1.5用のパラメータ
                image = self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=8.5,  # SD 1.5は8.5が最適
                    generator=torch.Generator(device=self.device).manual_seed(random.randint(0, 2**32))
                ).images[0]
                # 生成後にメモリクリア
                gc.collect()

            # ファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mufufu_cpu_{style}_{timestamp}.png"
            filepath = self.output_dir / filename

            # 画像保存
            image.save(filepath)

            print("✅ ムフフ画像生成完了！")
            print(f"   📁 保存先: {filepath}")

            # 顔修正を実行（NSFW画像でも顔の品質を保つ）
            try:
                fixed_filepath = self.fix_face(filepath)
                if fixed_filepath and fixed_filepath != filepath:
                    print("   ✨ 顔修正完了！")
                    filepath = fixed_filepath
            except Exception as e:
                print(f"   ⚠️  顔修正スキップ（エラー）: {e}")

            # 自動的にギャラリーに登録
            self.register_to_gallery(filepath, prompt, style, width, height, num_inference_steps)

            return str(filepath)

        except Exception as e:
            print(f"❌ 画像生成エラー: {str(e)}")
            raise

    def generate_mufufu_collection(self, count=3, style=None):
        """ムフフ画像コレクション生成"""
        print(f"🎨 ムフフ画像コレクション生成開始！({count}枚)")
        print("=" * 60)

        results = []
        styles = list(self.mufufu_prompts.keys())

        # 最初のモデルを読み込み
        if not self.pipeline:
            first_model = list(self.available_models.keys())[0]
            self.load_model(first_model)

        for i in range(count):
            print(f"\n📸 {i+1}/{count} 枚目生成中...")

            # スタイル選択
            if style:
                selected_style = style
            else:
                selected_style = random.choice(styles)

            size = random.choice(["square", "portrait"])

            try:
                result = self.generate_mufufu_image(
                    style=selected_style,
                    size=size,
                    num_inference_steps=35  # 高品質設定
                )
                if result:
                    results.append(result)
                    print(f"   ✅ {i+1}枚目完了")
            except Exception as e:
                print(f"   ❌ {i+1}枚目失敗: {str(e)}")

        print("\n🎉 ムフフ画像コレクション生成完了！")
        print(f"✅ 成功: {len(results)}/{count} 枚")
        print(f"📁 保存先: {self.output_dir}")

        return results

    def fix_face(self, image_path):
        """顔修正（inpainting） - NSFW画像でも顔の品質を保つ"""
        try:
            # 顔修正APIを使用（軽量）
            import requests
            import time

            # ギャラリーAPIの顔修正機能を使用
            api_url = "http://localhost:5559/api/enhance"

            # 画像を読み込んでbase64エンコード
            from PIL import Image
            import base64
            import io

            img = Image.open(image_path)
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # 顔修正リクエスト
            payload = {
                "image_path": str(image_path),
                "enhancement_type": "face",
                "face_prompt": "beautiful face, perfect face, detailed facial features, clear skin, beautiful eyes, symmetrical face, high quality"
            }

            try:
                response = requests.post(api_url, json=payload, timeout=300)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("output_path"):
                        fixed_path = result["output_path"]
                        if Path(fixed_path).exists():
                            print(f"   ✨ 顔修正完了: {fixed_path}")
                            return fixed_path
            except Exception as api_error:
                print(f"   ⚠️  API顔修正エラー: {api_error}")

            # APIが使えない場合は、プロンプト最適化で対応
            # 元の画像をそのまま返す（プロンプトで改善済み）
            return image_path

        except Exception as e:
            print(f"   ⚠️  顔修正エラー: {e}")
            return image_path

    def register_to_gallery(self, filepath, prompt, style, width, height, num_steps):
        """生成した画像をギャラリーに自動登録"""
        try:
            db_path = "/root/mufufu_gallery.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            filename = Path(filepath).name
            file_size_mb = Path(filepath).stat().st_size / (1024 * 1024)
            image_url = f"/images/{filename}"

            cursor.execute('''
                INSERT OR IGNORE INTO images (
                    filename, model_name, prompt, negative_prompt,
                    size_preset, num_steps, guidance_scale,
                    file_size_mb, image_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                self.current_model or "majicMIX realistic 麦橘写实_43331",
                prompt,
                self.negative_prompt,
                f"{width}x{height}",
                num_steps,
                7.5,
                file_size_mb,
                image_url
            ))

            conn.commit()
            conn.close()
            print(f"   ✅ ギャラリーに登録完了")
        except Exception as e:
            print(f"   ⚠️  ギャラリー登録エラー（画像は保存済み）: {e}")

    def quick_test(self, model_name=None, style="clear_beautiful"):
        """クイックテスト（1枚生成）"""
        if not model_name:
            model_name = list(self.available_models.keys())[0]

        print(f"🎨 クイックテスト開始: {model_name}")
        print(f"   スタイル: {style}")

        try:
            # モデル読み込み
            self.load_model(model_name)

            # 画像生成（高品質設定）
            filepath = self.generate_mufufu_image(style, "square", 35)

            print(f"✅ クイックテスト完了: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ クイックテスト失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """メイン関数"""
    import sys

    print("🎨 ムフフ画像生成システム - CPU専用版")
    print("=" * 60)

    generator = MufufuCPUGenerator()

    # コマンドライン引数処理
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "test":
            # クイックテスト
            model_name = sys.argv[2] if len(sys.argv) > 2 else None
            generator.quick_test(model_name)

        elif command == "generate":
            # 単体生成
            style = sys.argv[2] if len(sys.argv) > 2 else "clear_beautiful"
            model_name = sys.argv[3] if len(sys.argv) > 3 else None

            if model_name:
                generator.load_model(model_name)
            else:
                generator.load_model(list(generator.available_models.keys())[0])

            generator.generate_mufufu_image(style=style)

        elif command == "collection":
            # コレクション生成
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            style = sys.argv[3] if len(sys.argv) > 3 else None

            generator.generate_mufufu_collection(count=count, style=style)

        elif command == "nsfw":
            # NSFW画像生成
            style = sys.argv[2] if len(sys.argv) > 2 else "nsfw_sexy"
            count = int(sys.argv[3]) if len(sys.argv) > 3 else 1

            if not generator.pipeline:
                generator.load_model(list(generator.available_models.keys())[0])

            if count == 1:
                generator.generate_mufufu_image(style=style, size="square", num_inference_steps=20)
            else:
                nsfw_styles = [s for s in generator.mufufu_prompts.keys() if s.startswith("nsfw_")]
                import gc
                for i in range(count):
                    selected_style = style if style.startswith("nsfw_") else random.choice(nsfw_styles)
                    print(f"\n📸 {i+1}/{count} 枚目生成中（NSFW）...")
                    try:
                        generator.generate_mufufu_image(style=selected_style, size="square", num_inference_steps=20)
                        # 各画像生成後にメモリクリア
                        gc.collect()
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception as e:
                        print(f"   ⚠️  {i+1}枚目生成失敗: {e}")
                        print("   💡 メモリクリアして続行...")
                        gc.collect()
                        continue

        else:
            print("❌ 不明なコマンド")
            print("使い方:")
            print("  python mufufu_cpu_generator.py test [モデル名]")
            print("  python mufufu_cpu_generator.py generate [スタイル] [モデル名]")
            print("  python mufufu_cpu_generator.py collection [枚数] [スタイル]")
    else:
        # デフォルト: クイックテスト
        print("\n💡 デフォルトでクイックテストを実行します")
        generator.quick_test()

        print("\n📝 使い方:")
        print("  python mufufu_cpu_generator.py test [モデル名]")
        print("  python mufufu_cpu_generator.py generate [スタイル] [モデル名]")
        print("  python mufufu_cpu_generator.py collection [枚数] [スタイル]")
        print("  python mufufu_cpu_generator.py nsfw [スタイル] [枚数]")
        print("\n🎭 利用可能なスタイル:")
        print("  【通常】")
        for style in ["clear_beautiful", "cute_kawaii", "elegant_style"]:
            print(f"    - {style}")
        print("  【NSFW】")
        for style in ["nsfw_sexy", "nsfw_alluring", "nsfw_erotic", "nsfw_fellatio", "nsfw_ecchi"]:
            print(f"    - {style}")


if __name__ == "__main__":
    main()

