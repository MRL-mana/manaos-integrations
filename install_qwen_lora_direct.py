"""
Qwen-Image-Lightning LoRAを直接ダウンロード
"""

import os
import sys
import subprocess
from pathlib import Path

# Windowsでのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def main():
    print("=" * 60)
    print("Qwen-Image-Lightning LoRA インストール")
    print("=" * 60)
    print()
    
    # ComfyUIのパス
    comfyui_path = "C:\\ComfyUI"
    if not os.path.exists(comfyui_path):
        print("❌ ComfyUIが見つかりません")
        return 1
    
    lora_path = os.path.join(comfyui_path, "models", "loras")
    os.makedirs(lora_path, exist_ok=True)
    
    print(f"[1] LoRA保存先: {lora_path}")
    print()
    
    # 環境変数を設定
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    
    # コマンドベースを決定
    cmd_base = None
    try:
        subprocess.run(["hf", "--version"], capture_output=True, timeout=2, env=env)
        cmd_base = "hf"
    except:
        cmd_base = "huggingface-cli"
    
    print(f"[2] 使用コマンド: {cmd_base}")
    print()
    
    # LoRAモデルをダウンロード
    model_name = "lightx2v/Qwen-Image-2512-Lightning"
    temp_dir = os.path.join(comfyui_path, "models", "_temp_lora")
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"[3] LoRAモデルをダウンロード中...")
    print(f"    モデル: {model_name}")
    print(f"    一時保存先: {temp_dir}")
    print()
    
    cmd = [
        cmd_base,
        "download",
        model_name,
        "--local-dir", temp_dir,
        "--include", "*.safetensors"
    ]
    
    try:
        print("    ダウンロード開始...")
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
                if line and ("Download" in line or "Fetching" in line or "complete" in line.lower() or "%" in line):
                    print(f"    {prefix}{line[:120]}")
        
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, ""))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "[INFO] "))
        
        stdout_thread.start()
        stderr_thread.start()
        
        process.wait()
        
        stdout_thread.join()
        stderr_thread.join()
        
        if process.returncode == 0:
            print()
            print("    ✅ ダウンロード完了")
        else:
            print()
            print(f"    ❌ ダウンロード失敗 (終了コード: {process.returncode})")
            return 1
    except Exception as e:
        print(f"    ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # ファイルを移動
    print()
    print("[4] ファイルを整理中...")
    moved_count = 0
    
    if os.path.exists(temp_dir):
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".safetensors"):
                    src = os.path.join(root, file)
                    dst = os.path.join(lora_path, file)
                    if not os.path.exists(dst):
                        try:
                            import shutil
                            shutil.move(src, dst)
                            moved_count += 1
                            file_size_mb = os.path.getsize(dst) / 1024 / 1024
                            print(f"    ✅ {file} → loras/ ({file_size_mb:.2f} MB)")
                        except Exception as e:
                            print(f"    ⚠️  {file} の移動に失敗: {e}")
                    else:
                        print(f"    ⏭️  {file} は既に存在します")
    
    # 一時ディレクトリをクリーンアップ
    print()
    print("[5] クリーンアップ中...")
    try:
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("    ✅ 一時ファイルを削除しました")
    except Exception as e:
        print(f"    ⚠️  クリーンアップエラー: {e}")
    
    print()
    print("=" * 60)
    if moved_count > 0:
        print(f"✅ LoRAファイル {moved_count}個をインストールしました！")
    else:
        print("⚠️  移動したファイルがありません")
    print("=" * 60)
    print()
    
    # 最終確認
    lora_files = [f for f in os.listdir(lora_path) if "qwen" in f.lower() or "lightning" in f.lower()]
    if lora_files:
        print("インストール済みLoRAファイル:")
        for f in lora_files:
            file_path = os.path.join(lora_path, f)
            file_size_mb = os.path.getsize(file_path) / 1024 / 1024
            print(f"  - {f} ({file_size_mb:.2f} MB)")
    else:
        print("⚠️  LoRAファイルが見つかりません")
    
    return 0 if moved_count > 0 else 1

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
