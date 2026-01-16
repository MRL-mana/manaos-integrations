"""
LTX-2モデルとGemmaモデルの自動ダウンロードスクリプト
Hugging Face Hubを使用してモデルをダウンロード
"""

import os
import sys
from pathlib import Path

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  huggingface_hubがインストールされていません")
    print("インストール: pip install huggingface_hub")
    sys.exit(1)

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )

# ComfyUIパスを環境変数から取得（デフォルト: C:/ComfyUI）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
CHECKPOINTS_PATH = COMFYUI_PATH / "models" / "checkpoints"
TEXT_ENCODERS_PATH = COMFYUI_PATH / "models" / "text_encoders"
LTX_VIDEO_PATH = CHECKPOINTS_PATH / "LTX-Video"


def check_comfyui_path():
    """ComfyUIパスを確認"""
    if not COMFYUI_PATH.exists():
        print(f"❌ ComfyUIが見つかりません: {COMFYUI_PATH}")
        return False

    main_py = COMFYUI_PATH / "main.py"
    if not main_py.exists():
        print(f"❌ main.pyが見つかりません: {COMFYUI_PATH}")
        return False

    print(f"✅ ComfyUIパス: {COMFYUI_PATH}")
    return True


def create_directories():
    """必要なディレクトリを作成"""
    directories = [
        CHECKPOINTS_PATH,
        TEXT_ENCODERS_PATH,
        LTX_VIDEO_PATH
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ ディレクトリ確認: {directory}")


def download_ltx2_model():
    """LTX-2モデルをダウンロード"""
    print("\n[2] LTX-2モデルの確認...")

    # 既存のモデルを確認
    pattern = "*ltx-2-19b-distilled*.safetensors"
    existing_models = list(CHECKPOINTS_PATH.glob(pattern))
    if existing_models:
        model = existing_models[0]
        size_gb = model.stat().st_size / (1024 ** 3)
        print(f"   ✅ LTX-2モデルが見つかりました: {model.name}")
        print(f"      サイズ: {size_gb:.2f} GB")
        return True

    # LTX-Videoディレクトリも確認
    existing_models = list(LTX_VIDEO_PATH.glob(pattern))
    if existing_models:
        model = existing_models[0]
        size_gb = model.stat().st_size / (1024 ** 3)
        print(f"   ✅ LTX-2モデルが見つかりました: {model.name}")
        print(f"      パス: {model}")
        print(f"      サイズ: {size_gb:.2f} GB")
        return True

    print("   ⚠️  LTX-2モデルが見つかりません")
    print("")
    print("   [2-1] LTX-2 19B Distilledモデルをダウンロード中...")
    print("   これには時間がかかる場合があります（約40GB）...")
    print(f"   ダウンロード先: {LTX_VIDEO_PATH}")
    print("")

    try:
        # 特定のファイルのみをダウンロード
        model_path = hf_hub_download(
            repo_id="Lightricks/LTX-2",
            filename="ltx-2-19b-distilled.safetensors",
            local_dir=str(LTX_VIDEO_PATH),
            local_dir_use_symlinks=False
        )

        if os.path.exists(model_path):
            size_gb = os.path.getsize(model_path) / (1024 ** 3)
            print("   ✅ LTX-2モデルのダウンロードが完了しました")
            print(f"   ファイル: {model_path}")
            print(f"   サイズ: {size_gb:.2f} GB")
            return True
        else:
            print("   ❌ ダウンロードに失敗しました")
            return False

    except Exception as e:
        print(f"   ❌ エラーが発生しました: {e}")
        print("   手動でダウンロードしてください:")
        print("   https://huggingface.co/Lightricks/LTX-2")
        print("   ダウンロード後、以下のパスに配置してください:")
        print(f"   {CHECKPOINTS_PATH}")
        return False


def download_gemma_model():
    """Gemmaモデルをダウンロード（完全版 - tokenizer.modelを含む）"""
    print("\n[3] Gemma 3 Text Encoderモデルの確認...")

    # 既存のモデルを確認
    gemma_dir = TEXT_ENCODERS_PATH / "gemma-3-12b-it-qat-q4_0-unquantized"
    gemma_dir.mkdir(parents=True, exist_ok=True)

    # tokenizer.modelの存在を確認
    tokenizer_path = gemma_dir / "tokenizer.model"
    if tokenizer_path.exists():
        print("   ✅ tokenizer.modelが見つかりました")
        model_files = list(gemma_dir.glob("model-*.safetensors"))
        if model_files:
            print(f"   ✅ Gemmaモデルファイル: {len(model_files)}個")
            return True

    print("   ⚠️  Gemma 3 Text Encoderモデルが不完全です")
    print("")
    print("   [3-1] Gemma 3-12B ITモデルを完全にダウンロード中...")
    print("   これには時間がかかる場合があります（数GB）...")
    print(f"   ダウンロード先: {gemma_dir}")
    print("")

    try:
        # まず、google/gemma-3-12b-itから完全にダウンロード
        msg1 = "   [3-1-1] google/gemma-3-12b-itから完全ダウンロードを試行..."
        print(msg1)
        print("   注意: アクセス権限が必要な場合があります")
        print("   Hugging Face CLIで認証してください: huggingface-cli login")
        print("")

        try:
            ignore_patterns = ["*.md", "*.txt", ".git*", "*.json"]
            downloaded_path = snapshot_download(
                repo_id="google/gemma-3-12b-it",
                local_dir=str(gemma_dir),
                local_dir_use_symlinks=False,
                ignore_patterns=ignore_patterns
            )

            # tokenizer.modelの存在を確認
            if tokenizer_path.exists():
                print("   ✅ Gemmaモデルのダウンロードが完了しました")
                print(f"   パス: {downloaded_path}")
                print("   tokenizer.model: ✅")
                return True
            else:
                msg2 = "   ⚠️  ダウンロードは完了しましたが、"
                msg3 = "tokenizer.modelが見つかりません"
                print(f"{msg2}{msg3}")
        except Exception as e1:
            msg = f"   ⚠️  google/gemma-3-12b-itからのダウンロードに失敗: {e1}"
            print(msg)
            print("   エラー詳細: アクセス権限が必要な可能性があります")
            print("   Hugging Face CLIで認証してください: huggingface-cli login")

        # tokenizer.modelを個別にダウンロード
        print("")
        print("   [3-1-2] tokenizer.modelを個別にダウンロードを試行...")
        try:
            tokenizer_file = hf_hub_download(
                repo_id="google/gemma-3-12b-it",
                filename="tokenizer.model",
                local_dir=str(gemma_dir),
                local_dir_use_symlinks=False
            )

            if os.path.exists(tokenizer_file):
                print("   ✅ tokenizer.modelのダウンロードが完了しました")
                print(f"   パス: {tokenizer_file}")

                # 他の必要なファイルもダウンロード
                print("")
                print("   [3-1-3] その他の必要なファイルをダウンロード...")
                try:
                    # preprocessor_config.json
                    hf_hub_download(
                        repo_id="google/gemma-3-12b-it",
                        filename="preprocessor_config.json",
                        local_dir=str(gemma_dir),
                        local_dir_use_symlinks=False
                    )
                    print("   ✅ preprocessor_config.json: ダウンロード完了")
                except Exception as e3:
                    msg = f"   ⚠️  preprocessor_config.jsonのダウンロードに失敗: {e3}"
                    print(msg)

                return True
        except Exception as e2:
            msg = f"   ⚠️  tokenizer.modelの個別ダウンロードに失敗: {e2}"
            print(msg)
            print("   エラー詳細: アクセス権限が必要な可能性があります")

        print("")
        print("   ⚠️  自動ダウンロードに失敗しました")
        print("")
        print("   手動でダウンロードしてください:")
        print("   1. Hugging Face CLIで認証:")
        print("      huggingface-cli login")
        print("")
        print("   2. または、ブラウザからダウンロード:")
        print("      https://huggingface.co/google/gemma-3-12b-it")
        print("")
        print("   必要なファイル:")
        print("   - tokenizer.model")
        print("   - model-*.safetensors (複数ファイル)")
        print("   - preprocessor_config.json")
        print("")
        print("   ダウンロード後、以下のパスに配置してください:")
        print(f"   {gemma_dir}")
        return False

    except Exception as e:
        print(f"   ❌ エラーが発生しました: {e}")
        print("")
        print("   手動でダウンロードしてください:")
        print("   https://huggingface.co/google/gemma-3-12b-it")
        print("   ダウンロード後、以下のパスに配置してください:")
        print(f"   {gemma_dir}")
        return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("LTX-2モデルとGemmaモデルの自動ダウンロード")
    print("=" * 60)
    print("")

    # ComfyUIパスの確認
    if not check_comfyui_path():
        sys.exit(1)

    # ディレクトリの作成
    create_directories()

    # LTX-2モデルのダウンロード
    ltx2_success = download_ltx2_model()

    # Gemmaモデルのダウンロード
    gemma_success = download_gemma_model()

    print("")
    print("=" * 60)
    print("✅ ダウンロード処理完了！")
    print("=" * 60)
    print("")

    print("次のステップ:")
    print("")
    print("1. モデルが正しく配置されているか確認:")
    ltx2_path1 = f"{CHECKPOINTS_PATH}\\ltx-2-19b-distilled.safetensors"
    print(f"   - LTX-2モデル: {ltx2_path1}")
    ltx2_path2 = f"{LTX_VIDEO_PATH}\\ltx-2-19b-distilled.safetensors"
    print(f"   または: {ltx2_path2}")
    gemma_path = (
        f"{TEXT_ENCODERS_PATH}\\gemma-3-12b-it-qat-q4_0-unquantized\\"
    )
    print(f"   - Gemmaモデル: {gemma_path}")
    print("")
    print("2. ComfyUIを再起動:")
    print("   ComfyUIを再起動して、新しいモデルを認識させてください")
    print("")
    print("3. 動作確認:")
    print("   python generate_mana_mufufu_ltx2_video.py")
    print("")

    if ltx2_success and gemma_success:
        print("✅ すべてのモデルが正常にダウンロードされました！")
    elif ltx2_success or gemma_success:
        print("⚠️  一部のモデルのダウンロードに失敗しました")
    else:
        print("❌ モデルのダウンロードに失敗しました")


if __name__ == "__main__":
    main()
