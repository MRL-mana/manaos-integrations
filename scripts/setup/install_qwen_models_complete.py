"""
Qwen-Image-2512 と Qwen-Image-Edit-2511 を一括インストール
huggingface-cliを使用した安定したダウンロード
"""

import os
import sys
import subprocess
from pathlib import Path

# Windowsでのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ComfyUIのパス（デフォルト）
COMFYUI_PATHS = [
    "C:\\ComfyUI",
    os.path.join(os.environ.get("USERPROFILE", ""), "ComfyUI"),
    os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "ComfyUI"),
    "D:\\ComfyUI",
    "E:\\ComfyUI"
]

def find_comfyui_path():
    """ComfyUIのインストールパスを検索"""
    for path in COMFYUI_PATHS:
        if os.path.exists(path) and os.path.exists(os.path.join(path, "main.py")):
            return path
    return None

def check_huggingface_cli():
    """huggingface-cliが利用可能か確認"""
    try:
        # 新しいコマンド hf を試す
        result = subprocess.run(
            ["hf", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass
    
    # フォールバック: huggingface-cli
    try:
        result = subprocess.run(
            ["huggingface-cli", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )
        return result.returncode == 0
    except Exception:
        return False

def install_huggingface_cli():
    """huggingface-cliをインストール"""
    print("   huggingface-cliをインストール中...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "huggingface_hub[cli]"],
            check=True,
            timeout=60
        )
        print("   ✅ インストール完了")
        return True
    except Exception as e:
        print(f"   ❌ インストールエラー: {e}")
        return False

def download_model_with_cli(model_name, target_path, file_patterns=None):
    """huggingface-cliを使用してモデルをダウンロード"""
    print(f"   モデル: {model_name}")
    print(f"   保存先: {target_path}")
    
    # 保存先ディレクトリを作成
    os.makedirs(target_path, exist_ok=True)
    
    # 環境変数を設定（エンコーディング問題を回避）
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    
    # 新しいコマンド hf を優先的に使用
    cmd_base = None
    try:
        subprocess.run(["hf", "--version"], capture_output=True, timeout=2, env=env)
        cmd_base = "hf"
    except Exception:
        cmd_base = "huggingface-cli"
    
    # コマンドを構築
    cmd = [
        cmd_base,
        "download",
        model_name,
        "--local-dir", target_path
    ]
    
    # ファイルパターンを指定する場合
    if file_patterns:
        for pattern in file_patterns:
            cmd.extend(["--include", pattern])
    
    try:
        print("   ダウンロード開始...")
        print(f"   コマンド: {' '.join(cmd)}")
        print()
        
        # プロセスを実行（エラー出力を分離）
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
            errors='replace'  # エンコーディングエラーを回避
        )
        
        # 出力をリアルタイムで表示
        import threading
        
        def read_output(pipe, prefix=""):
            for line in pipe:
                line = line.rstrip()
                if line:
                    print(f"   {prefix}{line}")
        
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, ""))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "[ERR] "))
        
        stdout_thread.start()
        stderr_thread.start()
        
        process.wait()
        
        stdout_thread.join()
        stderr_thread.join()
        
        if process.returncode == 0:
            print("   ✅ ダウンロード完了")
            return True
        else:
            print(f"   ❌ ダウンロード失敗 (終了コード: {process.returncode})")
            return False
            
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def organize_files(comfyui_path, model_name, source_path):
    """ダウンロードしたファイルを適切なフォルダに整理"""
    print(f"   ファイルを整理中: {model_name}")
    
    # ファイルを分類
    diffusion_files = []
    text_encoder_files = []
    vae_files = []
    other_files = []
    
    if not os.path.exists(source_path):
        print(f"   ⚠️  ソースパスが存在しません: {source_path}")
        return
    
    for root, dirs, files in os.walk(source_path):
        for file in files:
            if file.endswith(".safetensors"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_path)
                
                if "diffusion" in rel_path.lower() or "transformer" in rel_path.lower():
                    diffusion_files.append((file_path, file))
                elif "text_encoder" in rel_path.lower() or "encoder" in rel_path.lower():
                    text_encoder_files.append((file_path, file))
                elif "vae" in rel_path.lower():
                    vae_files.append((file_path, file))
                else:
                    other_files.append((file_path, file))
    
    # ファイルを移動
    moved_count = 0
    
    # Diffusionモデル
    if diffusion_files:
        target_dir = os.path.join(comfyui_path, "models", "diffusion_models")
        os.makedirs(target_dir, exist_ok=True)
        for src, filename in diffusion_files:
            dst = os.path.join(target_dir, filename)
            if not os.path.exists(dst):
                try:
                    import shutil
                    shutil.move(src, dst)
                    moved_count += 1
                    print(f"   ✅ {filename} → diffusion_models/")
                except Exception as e:
                    print(f"   ⚠️  {filename} の移動に失敗: {e}")
            else:
                print(f"   ⏭️  {filename} は既に存在します")
    
    # Text Encoder
    if text_encoder_files:
        target_dir = os.path.join(comfyui_path, "models", "text_encoders")
        os.makedirs(target_dir, exist_ok=True)
        for src, filename in text_encoder_files:
            dst = os.path.join(target_dir, filename)
            if not os.path.exists(dst):
                try:
                    import shutil
                    shutil.move(src, dst)
                    moved_count += 1
                    print(f"   ✅ {filename} → text_encoders/")
                except Exception as e:
                    print(f"   ⚠️  {filename} の移動に失敗: {e}")
            else:
                print(f"   ⏭️  {filename} は既に存在します")
    
    # VAE
    if vae_files:
        target_dir = os.path.join(comfyui_path, "models", "vae")
        os.makedirs(target_dir, exist_ok=True)
        for src, filename in vae_files:
            dst = os.path.join(target_dir, filename)
            if not os.path.exists(dst):
                try:
                    import shutil
                    shutil.move(src, dst)
                    moved_count += 1
                    print(f"   ✅ {filename} → vae/")
                except Exception as e:
                    print(f"   ⚠️  {filename} の移動に失敗: {e}")
            else:
                print(f"   ⏭️  {filename} は既に存在します")
    
    print(f"   ✅ {moved_count}個のファイルを整理しました")

def main():
    print("=" * 60)
    print("Qwen-Image-2512 & Qwen-Image-Edit-2511 一括インストール")
    print("=" * 60)
    print()
    
    # ComfyUIのパスを検索
    print("[1] ComfyUIのインストール場所を検索中...")
    comfyui_path = find_comfyui_path()
    
    if not comfyui_path:
        print("❌ ComfyUIが見つかりません")
        print("   以下のパスを確認してください:")
        for path in COMFYUI_PATHS:
            print(f"   - {path}")
        return 1
    
    print(f"   ✅ ComfyUIが見つかりました: {comfyui_path}")
    print()
    
    # huggingface-cliの確認
    print("[2] huggingface-cliの確認...")
    if not check_huggingface_cli():
        print("   huggingface-cliが見つかりません")
        if not install_huggingface_cli():
            print("   ❌ huggingface-cliのインストールに失敗しました")
            return 1
    else:
        print("   ✅ huggingface-cliが利用可能です")
    print()
    
    # 一時ダウンロードディレクトリ
    temp_dir = os.path.join(comfyui_path, "models", "_temp_downloads")
    os.makedirs(temp_dir, exist_ok=True)
    
    # モデルリスト
    models = [
        {
            "name": "Qwen/Qwen-Image-2512",
            "display_name": "Qwen-Image-2512",
            "temp_path": os.path.join(temp_dir, "qwen-image-2512")
        },
        {
            "name": "Qwen/Qwen-Image-Edit-2511",
            "display_name": "Qwen-Image-Edit-2511",
            "temp_path": os.path.join(temp_dir, "qwen-image-edit-2511")
        }
    ]
    
    # 各モデルをダウンロード
    success_count = 0
    for i, model in enumerate(models, 1):
        print(f"[{i+2}/{len(models)+2}] {model['display_name']} をダウンロード中...")
        print()
        
        if download_model_with_cli(
            model["name"],
            model["temp_path"],
            file_patterns=["*.safetensors"]
        ):
            print()
            organize_files(comfyui_path, model["display_name"], model["temp_path"])
            success_count += 1
        else:
            print(f"   ❌ {model['display_name']} のダウンロードに失敗しました")
        
        print()
    
    # 一時ディレクトリをクリーンアップ
    print(f"[{len(models)+3}] クリーンアップ中...")
    try:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("   ✅ 一時ファイルを削除しました")
    except Exception as e:
        print(f"   ⚠️  クリーンアップエラー: {e}")
    
    print()
    print("=" * 60)
    if success_count == len(models):
        print("✅ すべてのインストールが完了しました！")
        print("=" * 60)
        print()
        print("次のステップ:")
        print("1. ComfyUIを起動してください")
        print("2. ワークフローを読み込んでください:")
        print("   - Qwen-Image-2512: https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/")
        print()
        return 0
    else:
        print(f"⚠️  {success_count}/{len(models)} 個のモデルがインストールされました")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nインストールがキャンセルされました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

