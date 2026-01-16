"""
環境変数でトークンを設定してGemmaモデルをダウンロードするスクリプト
"""

import os
import sys
from pathlib import Path
import io

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )

try:
    from huggingface_hub import snapshot_download, HfApi
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  huggingface_hubがインストールされていません")
    print("インストール: pip install huggingface_hub")
    sys.exit(1)

# ComfyUIパスを環境変数から取得（デフォルト: C:/ComfyUI）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
TEXT_ENCODERS_PATH = COMFYUI_PATH / "models" / "text_encoders"
GEMMA_DIR = TEXT_ENCODERS_PATH / "gemma-3-12b-it-qat-q4_0-unquantized"


def check_auth():
    """認証状態を確認"""
    print("\n[認証状態の確認]")
    
    # 環境変数からトークンを確認
    token = os.getenv("HF_TOKEN")
    if token:
        print("   ✅ 環境変数HF_TOKENが設定されています")
        os.environ["HF_TOKEN"] = token
        return True
    
    # APIで認証状態を確認
    try:
        api = HfApi()
        user = api.whoami()
        if user:
            print(f"   ✅ 認証済み: {user.get('name', 'Unknown')}")
            return True
    except Exception as e:
        print(f"   ⚠️  認証状態の確認に失敗: {e}")
    
    print("   ⚠️  認証されていません")
    print("")
    print("   認証方法:")
    print("   1. 環境変数でトークンを設定:")
    print('      $env:HF_TOKEN = "your_token_here"')
    print("")
    print("   2. または、hf auth login を実行")
    return False


def download_gemma_model():
    """Gemmaモデルをダウンロード"""
    print("\n[Gemmaモデルのダウンロード]")
    
    GEMMA_DIR.mkdir(parents=True, exist_ok=True)
    
    # モデルファイルのサイズを確認
    model_files = list(GEMMA_DIR.glob("model-*.safetensors"))
    if model_files:
        total_size = sum(f.stat().st_size for f in model_files)
        total_size_gb = total_size / (1024**3)
        print(f"   現在のモデルファイル: {len(model_files)}個")
        print(f"   合計サイズ: {total_size_gb:.2f} GB")
        
        # 各ファイルのサイズを確認
        for f in model_files:
            size_gb = f.stat().st_size / (1024**3)
            if size_gb < 0.1:  # 0.1GB未満は不完全と判断
                print(f"   ⚠️  {f.name}: {size_gb:.2f} GB (不完全)")
            else:
                print(f"   ✅ {f.name}: {size_gb:.2f} GB")
        
        # 完全なモデルは各ファイルが数GBになるはず
        if total_size_gb > 20:  # 20GB以上あれば完全と判断
            print("   ✅ Gemmaモデルは完全です")
            return True
        else:
            msg = f"   ⚠️  Gemmaモデルが不完全です（合計{total_size_gb:.2f}GB）"
            print(msg)
            print("   完全なダウンロードを実行します...")
    else:
        print("   ⚠️  Gemmaモデルファイルが見つかりません")
        print("   完全なダウンロードを実行します...")

    print("")
    print("   [1] google/gemma-3-12b-itから完全ダウンロードを試行...")
    print("   これには時間がかかります（約24GB）...")
    print(f"   ダウンロード先: {GEMMA_DIR}")
    print("")

    try:
        # 完全ダウンロードを試行（既存ファイルはスキップ）
        snapshot_download(
            repo_id="google/gemma-3-12b-it",
            local_dir=str(GEMMA_DIR),
            ignore_patterns=["*.md", "*.txt", ".git*"],
            resume_download=True  # 中断されたダウンロードを再開
        )

        # ダウンロード後の確認
        model_files_after = list(GEMMA_DIR.glob("model-*.safetensors"))
        total_size_after = sum(f.stat().st_size for f in model_files_after)
        total_size_gb_after = total_size_after / (1024**3)

        print("   ✅ ダウンロード完了")
        print(f"   モデルファイル数: {len(model_files_after)}個")
        print(f"   合計サイズ: {total_size_gb_after:.2f} GB")

        # tokenizer.modelの存在を確認
        tokenizer_path = GEMMA_DIR / "tokenizer.model"
        if tokenizer_path.exists():
            print("   tokenizer.model: ✅")
        else:
            print("   ⚠️  tokenizer.modelが見つかりません")
        
        if total_size_gb_after > 20:
            return True
        else:
            print(f"   ⚠️  ダウンロードが不完全です（合計{total_size_gb_after:.2f}GB）")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "restricted" in error_msg.lower():
            print(f"   ❌ アクセス権限がありません")
            print("")
            print("   以下の手順を実行してください:")
            print("   1. https://huggingface.co/google/gemma-3-12b-it にアクセス")
            print("   2. 「Request access」をクリックしてアクセス申請")
            print("   3. アクセスが承認されるまで待つ")
            print("   4. 認証を確認: hf auth whoami")
            print("   5. このスクリプトを再実行")
        else:
            print(f"   ❌ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
        return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("Gemmaモデルのダウンロード（トークン使用）")
    print("=" * 60)
    print("")

    # ComfyUIパスの確認
    if not COMFYUI_PATH.exists():
        print(f"❌ ComfyUIが見つかりません: {COMFYUI_PATH}")
        sys.exit(1)

    print(f"✅ ComfyUIパス: {COMFYUI_PATH}")

    # 認証状態の確認
    if not check_auth():
        print("")
        print("⚠️  認証が必要です")
        print("")
        print("環境変数でトークンを設定してください:")
        print('  $env:HF_TOKEN = "your_token_here"')
        print("")
        print("または、hf auth login を実行してください")
        sys.exit(1)

    # Gemmaモデルのダウンロード
    success = download_gemma_model()

    print("")
    print("=" * 60)
    if success:
        print("✅ ダウンロード完了！")
    else:
        print("⚠️  ダウンロードに失敗しました")
    print("=" * 60)
    print("")

    if success:
        print("次のステップ:")
        print("1. モデルの確認: python check_ltx2_models.py")
        print("2. ComfyUIを再起動")
        script = "generate_mana_mufufu_ltx2_video.py"
        print(f"3. 動画生成を試行: python {script}")


if __name__ == "__main__":
    main()
