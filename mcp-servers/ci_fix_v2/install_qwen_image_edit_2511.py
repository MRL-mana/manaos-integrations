"""
Qwen-Image-Edit-2511モデルインストールスクリプト
Hugging FaceからモデルをダウンロードしてComfyUIにインストール

参考情報:
- Hugging Face: https://huggingface.co/Qwen/Qwen-Image-Edit-2511
"""

import os
import sys
import requests
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

def download_file(url, output_path, description=""):
    """ファイルをダウンロード"""
    try:
        print(f"   ダウンロード中: {description}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb_downloaded = downloaded / 1024 / 1024
                        mb_total = total_size / 1024 / 1024
                        print(f"\r      進捗: {percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end="")
        
        print()  # 改行
        return True
    except Exception as e:
        print(f"\n   ❌ ダウンロードエラー: {e}")
        return False

def main():
    print("=" * 60)
    print("Qwen-Image-Edit-2511 インストールスクリプト")
    print("=" * 60)
    print()
    print("参考情報:")
    print("- Hugging Face: https://huggingface.co/Qwen/Qwen-Image-Edit-2511")
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
    
    # Hugging Faceのモデル情報
    hf_model_name = "Qwen/Qwen-Image-Edit-2511"
    hf_model_url = f"https://huggingface.co/{hf_model_name}"
    
    print("[2] Hugging FaceからQwen-Image-Edit-2511の情報を取得中...")
    print(f"   モデルページ: {hf_model_url}")
    print()
    
    # Hugging Face APIでファイル一覧を取得
    try:
        api_url = f"https://huggingface.co/api/models/{hf_model_name}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            model_info = response.json()
            siblings = model_info.get("siblings", [])
            
            # safetensorsファイルを探す
            safetensors_files = [f for f in siblings if f.get("rfilename", "").endswith(".safetensors")]
            
            if not safetensors_files:
                print("   ⚠️  safetensorsファイルが見つかりませんでした")
                print("   モデルがまだ公開されていない可能性があります")
                return 1
            
            print(f"   ✅ {len(safetensors_files)}個のsafetensorsファイルが見つかりました")
            print()
            
            # 必要なファイルを分類
            diffusion_files = []
            text_encoder_files = []
            vae_files = []
            other_files = []
            
            for f in safetensors_files:
                rfilename = f.get("rfilename", "")
                if "diffusion" in rfilename.lower() or "transformer" in rfilename.lower():
                    diffusion_files.append(f)
                elif "text_encoder" in rfilename.lower() or "encoder" in rfilename.lower():
                    text_encoder_files.append(f)
                elif "vae" in rfilename.lower():
                    vae_files.append(f)
                else:
                    other_files.append(f)
            
            # ダウンロードするファイルを決定
            files_to_download = []
            
            # Diffusionモデル（メインモデル）
            if diffusion_files:
                # 最大のファイルを選択（通常がメインモデル）
                main_diffusion = max(diffusion_files, key=lambda x: x.get("size", 0))
                files_to_download.append({
                    "file": main_diffusion,
                    "folder": "diffusion_models",
                    "description": "Diffusionモデル（メイン）"
                })
            
            # Text Encoder
            if text_encoder_files:
                # すべてのtext encoderファイルをダウンロード
                for f in text_encoder_files:
                    files_to_download.append({
                        "file": f,
                        "folder": "text_encoders",
                        "description": f"Text Encoder ({os.path.basename(f.get('rfilename', ''))})"
                    })
            
            # VAE
            if vae_files:
                for f in vae_files:
                    files_to_download.append({
                        "file": f,
                        "folder": "vae",
                        "description": f"VAE ({os.path.basename(f.get('rfilename', ''))})"
                    })
            
            if not files_to_download:
                print("   ⚠️  ダウンロード対象のファイルが見つかりませんでした")
                print("   手動でダウンロードしてください:")
                print(f"   {hf_model_url}")
                return 1
            
            print(f"[3] {len(files_to_download)}個のファイルをダウンロードします")
            print()
            
            downloaded_count = 0
            skipped_count = 0
            
            for i, item in enumerate(files_to_download, 1):
                file_info = item["file"]
                folder = item["folder"]
                description = item["description"]
                
                rfilename = file_info.get("rfilename", "")
                file_size = file_info.get("size", 0)
                file_size_gb = file_size / (1024**3) if file_size > 0 else 0
                
                print(f"[{i}/{len(files_to_download)}] {description}")
                print(f"   ファイル: {rfilename}")
                if file_size_gb > 0:
                    print(f"   サイズ: {file_size_gb:.2f} GB")
                
                # 出力パスを構築
                target_path = os.path.join(comfyui_path, "models", folder)
                os.makedirs(target_path, exist_ok=True)
                
                # ファイル名からディレクトリ部分を除去
                base_file_name = os.path.basename(rfilename)
                output_path = os.path.join(target_path, base_file_name)
                
                # 既存ファイルをチェック
                if os.path.exists(output_path):
                    print(f"   ⚠️  既に存在します: {output_path}")
                    print("   スキップします")
                    skipped_count += 1
                    print()
                    continue
                
                # ダウンロードURLを構築
                download_url = f"https://huggingface.co/{hf_model_name}/resolve/main/{rfilename}"
                
                # ダウンロード実行
                if download_file(download_url, output_path, description):
                    print(f"   ✅ ダウンロード完了: {output_path}")
                    downloaded_count += 1
                else:
                    print(f"   ❌ ダウンロード失敗")
                
                print()
            
            # 結果サマリー
            print("=" * 60)
            print("✅ インストール完了！")
            print("=" * 60)
            print()
            print(f"ダウンロード完了: {downloaded_count}個")
            print(f"スキップ: {skipped_count}個")
            print()
            print("次のステップ:")
            print("1. ComfyUIを起動してください")
            print("2. Qwen-Image-Edit-2511用のワークフローを読み込んでください")
            print()
            print("参考情報:")
            print(f"- モデルページ: {hf_model_url}")
            print()
            
            return 0
            
        else:
            print(f"   ❌ Hugging Face APIエラー: {response.status_code}")
            print(f"   手動でダウンロードしてください: {hf_model_url}")
            return 1
            
    except Exception as e:
        print(f"   ❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("手動インストール手順:")
        print(f"1. {hf_model_url} にアクセス")
        print("2. 必要なファイルをダウンロード")
        print("3. 以下のフォルダに配置:")
        print(f"   {os.path.join(comfyui_path, 'models')}")
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

