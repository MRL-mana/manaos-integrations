"""
Qwen-Image-2512 & Qwen-Image-Edit-2511 のオプションファイルをインストール
VAE、LoRA、その他の必要なファイルをダウンロード
"""

import os
import sys
import subprocess
from pathlib import Path

# Windowsでのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

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

def download_file_with_hf(model_name, file_path, target_path):
    """huggingface-cliを使用して特定のファイルをダウンロード"""
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
    
    cmd = [
        cmd_base,
        "download",
        model_name,
        file_path,
        "--local-dir", target_path
    ]
    
    try:
        print(f"   ダウンロード中: {file_path}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            errors='replace'
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print(f"   ✅ ダウンロード完了")
            return True
        else:
            print(f"   ❌ ダウンロード失敗")
            if stderr:
                print(f"   エラー: {stderr[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return False

def download_model_files(model_name, target_path, file_patterns):
    """モデルから複数ファイルをダウンロード"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    
    cmd_base = None
    try:
        subprocess.run(["hf", "--version"], capture_output=True, timeout=2, env=env)
        cmd_base = "hf"
    except Exception:
        cmd_base = "huggingface-cli"
    
    os.makedirs(target_path, exist_ok=True)
    
    cmd = [
        cmd_base,
        "download",
        model_name,
        "--local-dir", target_path
    ]
    
    for pattern in file_patterns:
        cmd.extend(["--include", pattern])
    
    try:
        print(f"   ダウンロード開始...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            errors='replace'
        )
        
        import threading
        def read_output(pipe, prefix=""):
            for line in pipe:
                line = line.rstrip()
                if line and ("Download" in line or "Fetching" in line or "complete" in line.lower()):
                    print(f"   {prefix}{line[:100]}")
        
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, ""))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "[INFO] "))
        
        stdout_thread.start()
        stderr_thread.start()
        
        process.wait()
        
        stdout_thread.join()
        stderr_thread.join()
        
        if process.returncode == 0:
            print(f"   ✅ ダウンロード完了")
            return True
        else:
            print(f"   ❌ ダウンロード失敗")
            return False
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return False

def organize_vae_files(comfyui_path, source_path):
    """VAEファイルを適切なフォルダに移動"""
    vae_dir = os.path.join(comfyui_path, "models", "vae")
    os.makedirs(vae_dir, exist_ok=True)
    
    moved_count = 0
    if os.path.exists(source_path):
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.endswith(".safetensors") and "vae" in root.lower():
                    src = os.path.join(root, file)
                    dst = os.path.join(vae_dir, file)
                    if not os.path.exists(dst):
                        try:
                            import shutil
                            shutil.move(src, dst)
                            moved_count += 1
                            print(f"   ✅ {file} → vae/")
                        except Exception as e:
                            print(f"   ⚠️  {file} の移動に失敗: {e}")
                    else:
                        print(f"   ⏭️  {file} は既に存在します")
    
    return moved_count

def main():
    print("=" * 60)
    print("Qwen-Image オプションファイル インストール")
    print("=" * 60)
    print()
    
    # ComfyUIのパスを検索
    print("[1] ComfyUIのインストール場所を検索中...")
    comfyui_path = find_comfyui_path()
    
    if not comfyui_path:
        print("❌ ComfyUIが見つかりません")
        return 1
    
    print(f"   ✅ ComfyUIが見つかりました: {comfyui_path}")
    print()
    
    # 一時ダウンロードディレクトリ
    temp_dir = os.path.join(comfyui_path, "models", "_temp_downloads")
    os.makedirs(temp_dir, exist_ok=True)
    
    success_count = 0
    total_tasks = 0
    
    # 1. VAEファイルのダウンロード
    print("[2] VAEファイルをダウンロード中...")
    print()
    
    vae_path = os.path.join(comfyui_path, "models", "vae")
    os.makedirs(vae_path, exist_ok=True)
    
    # Qwen-Image-2512のVAE
    vae_file = "vae/diffusion_pytorch_model.safetensors"
    vae_target = os.path.join(vae_path, "qwen_image_vae.safetensors")
    
    if not os.path.exists(vae_target):
        total_tasks += 1
        temp_vae_dir = os.path.join(temp_dir, "qwen-vae")
        if download_model_files("Qwen/Qwen-Image-2512", temp_vae_dir, ["vae/*.safetensors"]):
            moved = organize_vae_files(comfyui_path, temp_vae_dir)
            if moved > 0:
                success_count += 1
                # ファイル名を変更
                vae_files = [f for f in os.listdir(vae_path) if f.endswith(".safetensors") and "diffusion" in f.lower()]
                if vae_files:
                    old_path = os.path.join(vae_path, vae_files[0])
                    if not os.path.exists(vae_target):
                        os.rename(old_path, vae_target)
                        print(f"   ✅ ファイル名を変更: {vae_files[0]} → qwen_image_vae.safetensors")
        print()
    else:
        print(f"   ⏭️  VAEファイルは既に存在します: {vae_target}")
        print()
    
    # 2. LoRAファイル（4-step Lightning）のダウンロード
    print("[3] LoRAファイル（Qwen-Image-Lightning-4steps）をダウンロード中...")
    print()
    
    lora_path = os.path.join(comfyui_path, "models", "loras")
    os.makedirs(lora_path, exist_ok=True)
    
    lora_file = "Qwen-Image-Lightning-4steps-V1.0.safetensors"
    lora_target = os.path.join(lora_path, lora_file)
    
    if not os.path.exists(lora_target):
        total_tasks += 1
        print("   Hugging Faceから検索中...")
        # Hugging Faceで検索
        lora_model = "lightx2v/Qwen-Image-2512-Lightning"
        temp_lora_dir = os.path.join(temp_dir, "qwen-lora")
        if download_model_files(lora_model, temp_lora_dir, ["*.safetensors"]):
            # ファイルを移動
            if os.path.exists(temp_lora_dir):
                for root, dirs, files in os.walk(temp_lora_dir):
                    for file in files:
                        if file.endswith(".safetensors"):
                            src = os.path.join(root, file)
                            dst = os.path.join(lora_path, file)
                            if not os.path.exists(dst):
                                try:
                                    import shutil
                                    shutil.move(src, dst)
                                    success_count += 1
                                    print(f"   ✅ {file} → loras/")
                                except Exception as e:
                                    print(f"   ⚠️  {file} の移動に失敗: {e}")
        print()
    else:
        print(f"   ⏭️  LoRAファイルは既に存在します: {lora_target}")
        print()
    
    # 3. Text Encoder（FP8版）の確認
    print("[4] Text Encoder（FP8版）の確認...")
    print()
    
    text_encoder_path = os.path.join(comfyui_path, "models", "text_encoders")
    fp8_file = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
    fp8_target = os.path.join(text_encoder_path, fp8_file)
    
    if not os.path.exists(fp8_target):
        print("   ⚠️  FP8版のText Encoderが見つかりません")
        print("   現在のText Encoderで動作しますが、FP8版の方がVRAMを節約できます")
        print("   必要に応じて手動でダウンロードしてください")
        print()
    else:
        print(f"   ✅ FP8版のText Encoderが存在します")
        print()
    
    # クリーンアップ
    print("[5] クリーンアップ中...")
    try:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("   ✅ 一時ファイルを削除しました")
    except Exception as e:
        print(f"   ⚠️  クリーンアップエラー: {e}")
    
    print()
    print("=" * 60)
    if success_count > 0:
        print(f"✅ {success_count}個のオプションファイルをインストールしました！")
    else:
        print("✅ オプションファイルの確認が完了しました")
    print("=" * 60)
    print()
    
    # インストール済みファイルの確認
    print("インストール済みファイル:")
    print()
    
    vae_files = [f for f in os.listdir(vae_path) if "qwen" in f.lower() and f.endswith(".safetensors")]
    if vae_files:
        print(f"  VAE: {len(vae_files)}個")
        for f in vae_files:
            print(f"    - {f}")
    else:
        print("  VAE: 0個")
    
    lora_files = [f for f in os.listdir(lora_path) if "qwen" in f.lower() and f.endswith(".safetensors")]
    if lora_files:
        print(f"  LoRA: {len(lora_files)}個")
        for f in lora_files:
            print(f"    - {f}")
    else:
        print("  LoRA: 0個")
    
    print()
    print("次のステップ:")
    print("1. ComfyUIを起動してください")
    print("2. ワークフローを読み込んでください")
    print()
    
    return 0

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
