"""
LTX-2モデルとGemmaモデルがインストールされたら、
ワークフローのモデル名を自動的に更新するスクリプト
"""

import sys
import os
import re
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

# ComfyUIパスを環境変数から取得（デフォルト: C:/ComfyUI）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
CHECKPOINTS_PATH = COMFYUI_PATH / "models" / "checkpoints"
TEXT_ENCODERS_PATH = COMFYUI_PATH / "models" / "text_encoders"
LTX_VIDEO_PATH = CHECKPOINTS_PATH / "LTX-Video"
WORKFLOW_FILE = Path(__file__).parent / "ltx2_video_integration.py"


def find_ltx2_model():
    """LTX-2モデルを探す"""
    # checkpointsディレクトリを確認
    pattern = "*ltx-2-19b-distilled*.safetensors"
    models = list(CHECKPOINTS_PATH.glob(pattern))
    if models:
        return models[0].name

    # LTX-Videoディレクトリを確認
    if LTX_VIDEO_PATH.exists():
        models = list(LTX_VIDEO_PATH.glob(pattern))
        if models:
            return models[0].name

    return None


def find_gemma_model():
    """Gemmaモデルを探す"""
    gemma_dir = TEXT_ENCODERS_PATH / "gemma-3-12b-it-qat-q4_0-unquantized"
    if gemma_dir.exists():
        # モデルファイルを探す
        model_files = list(gemma_dir.rglob("*.safetensors"))
        if model_files:
            # 最初のモデルファイルの親ディレクトリ名を返す
            return gemma_dir.name

    # 他のGemmaディレクトリも確認
    gemma_dirs = list(TEXT_ENCODERS_PATH.glob("*gemma*"))
    for gemma_dir in gemma_dirs:
        model_files = list(gemma_dir.rglob("*.safetensors"))
        if model_files:
            return gemma_dir.name

    return None


def update_workflow_file(ltx2_model_name, gemma_model_name):
    """ワークフローファイルを更新"""
    if not WORKFLOW_FILE.exists():
        print(f"❌ ワークフローファイルが見つかりません: {WORKFLOW_FILE}")
        return False

    print("\n[3] ワークフローファイルを更新中...")
    print(f"   ファイル: {WORKFLOW_FILE}")

    try:
        with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # LTX-2モデル名を更新
        if ltx2_model_name:
            # CheckpointLoaderSimpleのckpt_nameを更新
            pattern1 = r'"ckpt_name":\s*"realisian_v60\.safetensors"\s*#.*'
            content = re.sub(
                pattern1,
                f'"ckpt_name": "{ltx2_model_name}"',
                content
            )

            # LowVRAMAudioVAELoaderのckpt_nameを更新
            content = re.sub(
                pattern1,
                f'"ckpt_name": "{ltx2_model_name}"',
                content
            )

            # LTXVGemmaCLIPModelLoaderのltxv_pathを更新
            pattern2 = r'"ltxv_path":\s*"realisian_v60\.safetensors"\s*#.*'
            content = re.sub(
                pattern2,
                f'"ltxv_path": "{ltx2_model_name}"',
                content
            )

        # Gemmaモデル名を更新
        if gemma_model_name:
            # LTXVGemmaCLIPModelLoaderのgemma_pathを更新
            # 注意: 実際のファイル名を確認する必要があります
            # ここではディレクトリ名を使用しますが、
            # 実際のファイル名に合わせて調整が必要です
            pattern3 = (
                r'"gemma_path":\s*"model-00001-of-00004\.safetensors"'
                r'\s*#.*'
            )
            content = re.sub(
                pattern3,
                f'"gemma_path": "{gemma_model_name}"',
                content
            )

        # 変更があった場合のみファイルを更新
        if content != original_content:
            with open(WORKFLOW_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
            print("   ✅ ワークフローファイルを更新しました")
            return True
        else:
            print("   ℹ️  更新が必要な箇所が見つかりませんでした")
            return False

    except Exception as e:
        print(f"   ❌ エラーが発生しました: {e}")
        return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("LTX-2ワークフローのモデル名を自動更新")
    print("=" * 60)
    
    # LTX-2モデルを探す
    print("\n[1] LTX-2モデルを検索中...")
    ltx2_model_name = find_ltx2_model()
    if ltx2_model_name:
        print(f"   ✅ 見つかりました: {ltx2_model_name}")
    else:
        print("   ⚠️  LTX-2モデルが見つかりません")
        msg = "   ダウンロードが完了するまで待つか、手動でダウンロード"
        print(f"{msg}してください")

    # Gemmaモデルを探す
    print("\n[2] Gemmaモデルを検索中...")
    gemma_model_name = find_gemma_model()
    if gemma_model_name:
        print(f"   ✅ 見つかりました: {gemma_model_name}")
    else:
        print("   ⚠️  Gemmaモデルが見つかりません")
        msg = "   ダウンロードが完了するまで待つか、手動でダウンロード"
        print(f"{msg}してください")

    # ワークフローファイルを更新
    if ltx2_model_name or gemma_model_name:
        success = update_workflow_file(ltx2_model_name, gemma_model_name)
        if success:
            print("\n✅ ワークフローの更新が完了しました！")
            print("\n次のステップ:")
            print("1. ComfyUIを再起動")
            script = "generate_mana_mufufu_ltx2_video.py"
            print(f"2. 動作確認: python {script}")
        else:
            print("\n⚠️  ワークフローの更新に問題がありました")
    else:
        msg1 = "\n⚠️  モデルが見つからないため、"
        msg2 = "ワークフローを更新できませんでした"
        print(f"{msg1}{msg2}")
        print("モデルのダウンロードが完了してから、再度実行してください:")
        script = "update_ltx2_workflow_models.py"
        print(f"   python {script}")


if __name__ == "__main__":
    main()
