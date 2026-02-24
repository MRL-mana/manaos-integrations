"""
Qwen-Image-2512モデルインストールスクリプト
Hugging FaceまたはCivitAIからモデルをダウンロードしてComfyUIにインストール

参考情報:
- Hugging Face: https://huggingface.co/Qwen/Qwen-Image-2512
- ComfyUIワークフロー: https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/
"""

import os
import sys
import requests
from pathlib import Path
try:
    from civitai_integration import CivitAIIntegration
except ImportError:
    CivitAIIntegration = None

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

def main():
    print("=" * 60)
    print("Qwen-Image-2512 インストールスクリプト")
    print("=" * 60)
    print()
    print("参考情報:")
    print("- Hugging Face: https://huggingface.co/Qwen/Qwen-Image-2512")
    print("- ComfyUIワークフロー: https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/")
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
    
    # checkpointsフォルダのパス
    checkpoints_path = os.path.join(comfyui_path, "models", "checkpoints")
    os.makedirs(checkpoints_path, exist_ok=True)
    print(f"   ✅ Checkpointsフォルダ: {checkpoints_path}")
    print()
    
    # CivitAI統合を初期化（オプション）
    civitai = None
    if CivitAIIntegration:
        print("[2] CivitAI統合を初期化中...")
        civitai = CivitAIIntegration()
        print("   ℹ️  CivitAI APIキーが設定されていない場合、検索のみ可能です")
        print("   ダウンロードにはAPIキーまたは手動ダウンロードが必要です")
        print()
    else:
        print("[2] Hugging Faceから直接ダウンロードします...")
        print()
    
    # Hugging Faceから直接ダウンロードを試行
    print("[3] Hugging FaceからQwen-Image-2512をダウンロード中...")
    
    # Hugging Faceのモデル情報
    hf_model_name = "Qwen/Qwen-Image-2512"
    hf_model_url = f"https://huggingface.co/{hf_model_name}"
    
    # ComfyUI用のモデルファイル名（bf16.safetensors形式）
    model_files = [
        "qwen_image_2512_bf16.safetensors",  # ComfyUI用
        "model.safetensors",  # デフォルト
        "pytorch_model.bin",  # フォールバック
    ]
    
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
            
            if safetensors_files:
                print(f"   ✅ {len(safetensors_files)}個のsafetensorsファイルが見つかりました")
                
                # ComfyUI用の推奨ファイルを優先的に探す
                preferred_files = [
                    "qwen_image_2512_bf16.safetensors",  # 高品質版
                    "qwen_image_2512_fp8_e4m3fn.safetensors",  # VRAM節約版
                ]
                
                main_file = None
                file_name = None
                target_folder = "diffusion_models"  # デフォルトはdiffusion_models
                
                # 推奨ファイルを優先
                for preferred in preferred_files:
                    for f in safetensors_files:
                        rfilename = f.get("rfilename", "")
                        if preferred in rfilename:
                            main_file = f
                            file_name = rfilename
                            # ファイル名からフォルダを判断
                            if "text_encoder" in rfilename:
                                target_folder = "text_encoders"
                            elif "vae" in rfilename:
                                target_folder = "vae"
                            elif "lora" in rfilename.lower():
                                target_folder = "loras"
                            break
                    if main_file:
                        break
                
                # 推奨ファイルが見つからない場合、diffusion_modelsフォルダ内の最大ファイルを選択
                if not main_file:
                    diffusion_files = [f for f in safetensors_files 
                                      if "diffusion" in f.get("rfilename", "").lower() 
                                      or "qwen_image" in f.get("rfilename", "").lower()
                                      or ("text_encoder" not in f.get("rfilename", "") 
                                          and "vae" not in f.get("rfilename", "").lower())]
                    if diffusion_files:
                        main_file = max(diffusion_files, key=lambda x: x.get("size", 0))
                        file_name = main_file.get("rfilename", "model.safetensors")
                    else:
                        # フォールバック: 最大のファイルを選択
                        main_file = max(safetensors_files, key=lambda x: x.get("size", 0))
                        file_name = main_file.get("rfilename", "model.safetensors")
                
                file_size = main_file.get("size", 0)
                file_size_gb = file_size / (1024**3) if file_size > 0 else 0
                
                print(f"   選択されたファイル: {file_name}")
                if file_size_gb > 0:
                    print(f"   サイズ: {file_size_gb:.2f} GB")
                print(f"   配置先フォルダ: models/{target_folder}/")
                print()
                
                # ダウンロードURLを構築
                download_url = f"https://huggingface.co/{hf_model_name}/resolve/main/{file_name}"
                
                # 出力パスを構築（サブディレクトリを含む場合も対応）
                target_path = os.path.join(comfyui_path, "models", target_folder)
                os.makedirs(target_path, exist_ok=True)
                
                # ファイル名からディレクトリ部分を除去
                base_file_name = os.path.basename(file_name)
                output_path = os.path.join(target_path, base_file_name)
                if os.path.exists(output_path):
                    print(f"   ⚠️  ファイルが既に存在します: {output_path}")
                    print("   スキップします")
                    print()
                    print("=" * 60)
                    print("✅ インストール完了（既に存在）")
                    print("=" * 60)
                    print()
                    print(f"モデルファイル: {output_path}")
                    print()
                    print("⚠️  注意: これはメインモデルファイルのみです")
                    print("   他の必要なファイルもダウンロードしてください:")
                    print("   - Text Encoder: qwen_2.5_vl_7b_fp8_scaled.safetensors")
                    print("     → models/text_encoders/ に配置")
                    print("   - VAE: qwen_image_vae.safetensors")
                    print("     → models/vae/ に配置")
                    print("   - (オプション) LoRA: Qwen-Image-Lightning-4steps-V1.0.safetensors")
                    print("     → models/loras/ に配置")
                    print()
                    print("次のステップ:")
                    print("1. ComfyUIを起動してください")
                    print("2. ワークフローを読み込んでください:")
                    print("   https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/")
                    print()
                    print("詳細なインストール手順:")
                    print("https://comfyui-wiki.com/ja/tutorial/advanced/image/qwen/qwen-image-2512")
                    print()
                    return 0
                
                # ダウンロード実行
                print("[4] モデルをダウンロード中...")
                print(f"   ダウンロードURL: {download_url}")
                print("   （この処理には時間がかかる場合があります）")
                print()
                
                try:
                    response = requests.get(download_url, stream=True, timeout=300)
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
                                    print(f"\r   進捗: {percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end="")
                    
                    print()  # 改行
                    print("   ✅ ダウンロード完了")
                    print()
                    print("=" * 60)
                    print("✅ インストール完了！")
                    print("=" * 60)
                    print()
                    print(f"モデルファイル: {output_path}")
                    print()
                    print("次のステップ:")
                    print("1. ComfyUIを起動してください")
                    print("2. 必要な他のモデルファイルもダウンロードしてください:")
                    print("   - Text Encoder: qwen_2.5_vl_7b_fp8_scaled.safetensors")
                    print("     → models/text_encoders/ に配置")
                    print("   - VAE: qwen_image_vae.safetensors")
                    print("     → models/vae/ に配置")
                    print("   - (オプション) LoRA: Qwen-Image-Lightning-4steps-V1.0.safetensors")
                    print("     → models/loras/ に配置")
                    print("3. ワークフローを読み込んでください:")
                    print("   https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/")
                    print()
                    print("参考情報:")
                    print(f"- モデルページ: {hf_model_url}")
                    print("- ComfyUIワークフロー: https://comfyanonymous.github.io/ComfyUI_examples/qwen_image/")
                    print("- 詳細手順: https://comfyui-wiki.com/ja/tutorial/advanced/image/qwen/qwen-image-2512")
                    print()
                    return 0
                    
                except Exception as e:
                    print(f"\n   ❌ ダウンロードエラー: {e}")
                    print("   Hugging Faceから手動でダウンロードしてください")
            else:
                print("   ⚠️  safetensorsファイルが見つかりませんでした")
        else:
            print(f"   ⚠️  Hugging Face APIエラー: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Hugging Faceからの取得エラー: {e}")
    
    print()
    print("   ℹ️  Hugging Faceからの自動ダウンロードに失敗しました")
    print("   CivitAIでの検索を試行します...")
    print()
    
    # CivitAIでの検索にフォールバック
    models = []
    
    # CivitAI統合で検索を試行
    if civitai and civitai.is_available():
        try:
            models = civitai.search_models(query="Qwen-Image-2512", limit=10)
        except Exception as e:
            print(f"   ⚠️  CivitAI統合での検索エラー: {e}")
    
    # APIキーなしで直接APIを呼び出す
    if not models:
        try:
            print("   ℹ️  直接APIで検索を試行中...")
            api_url = "https://civitai.com/api/v1/models"
            params = {
                "query": "Qwan-image-2512",
                "limit": 20,
                "sort": "Most Downloaded",
                "types": "Checkpoint"
            }
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                all_models = result.get("items", [])
                # 正確にマッチするモデルを優先
                models = [m for m in all_models if "qwan" in m.get("name", "").lower() and "2512" in m.get("name", "").lower()]
                if not models:
                    # "qwan"と"image"を含むモデル
                    models = [m for m in all_models if "qwan" in m.get("name", "").lower() and "image" in m.get("name", "").lower()]
                if models:
                    print(f"   ✅ {len(models)}件のモデルが見つかりました")
        except Exception as e:
            print(f"   ⚠️  直接API検索エラー: {e}")
    
    # それでも見つからない場合、一般的な検索キーワードで再試行
    if not models:
        print("   ℹ️  'Qwan-image-2512'で見つからないため、'Qwan'で再検索中...")
        try:
            api_url = "https://civitai.com/api/v1/models"
            params = {
                "query": "Qwan",
                "limit": 20,
                "sort": "Most Downloaded",
                "types": "Checkpoint"
            }
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                all_models = result.get("items", [])
                # "2512"を含むモデルをフィルタ
                models = [m for m in all_models if "2512" in m.get("name", "").lower()]
                if not models:
                    # "image"を含むQwanモデルをフィルタ
                    models = [m for m in all_models if "qwan" in m.get("name", "").lower() and "image" in m.get("name", "").lower()]
                if models:
                    print(f"   ✅ {len(models)}件の関連モデルが見つかりました")
        except Exception as e:
            print(f"   ⚠️  再検索エラー: {e}")
    
    # それでも見つからない場合、一般的なQwanモデルを検索
    if not models:
        print("   ℹ️  'Qwan-image-2512'が見つからないため、一般的なQwanモデルを検索中...")
        try:
            api_url = "https://civitai.com/api/v1/models"
            params = {
                "query": "Qwan",
                "limit": 30,
                "sort": "Most Downloaded",
                "types": "Checkpoint"
            }
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                all_models = result.get("items", [])
                # Qwanを含むすべてのモデルを表示
                models = [m for m in all_models if "qwan" in m.get("name", "").lower()]
                if models:
                    print(f"   ✅ {len(models)}件のQwanモデルが見つかりました")
                    print()
                    print("   見つかったモデル:")
                    for i, model in enumerate(models[:10], 1):
                        print(f"   {i}. {model.get('name', 'Unknown')} (ID: {model.get('id')})")
                    print()
                    print("   ⚠️  'Qwan-image-2512'が見つかりませんでした")
                    print("   上記のモデルから選択するか、手動でモデルIDを指定してください")
                    print()
                    print("   手動インストール手順:")
                    print("   1. https://civitai.com にアクセス")
                    print("   2. 'Qwan-image-2512' で検索")
                    print("   3. モデルページのURLからIDを取得（例: /models/12345 → IDは 12345）")
                    print("   4. 以下のコマンドで再実行:")
                    print(f"      python install_qwan_image_2512.py")
                    print()
                    print("   または、モデルを直接ダウンロードして以下に配置:")
                    print(f"   {checkpoints_path}")
                    return 1
        except Exception as e:
            print(f"   ⚠️  検索エラー: {e}")
    
    # それでも見つからない場合
    if not models:
        print("   ❌ モデルが見つかりませんでした")
        print()
        print("   手動インストール手順:")
        print("   1. https://civitai.com にアクセス")
        print("   2. 'Qwan-image-2512' または 'Qwan' で検索")
        print("   3. モデルページのURLからIDを取得（例: /models/12345 → IDは 12345）")
        print("   4. モデルを直接ダウンロードして以下に配置:")
        print(f"   {checkpoints_path}")
        return 1
    
    if not models:
        print("   ❌ モデルが見つかりませんでした")
        print("   別の検索キーワードを試してください")
        return 1
    
    # 最も関連性の高いモデルを選択
    target_model = None
    for model in models:
        name = model.get("name", "").lower()
        if "qwan" in name and "image" in name and "2512" in name:
            target_model = model
            break
    
    if not target_model:
        # 最初の結果を使用
        target_model = models[0]
    
    model_id = target_model.get("id")
    model_name = target_model.get("name", "Unknown")
    
    print(f"   ✅ モデルが見つかりました:")
    print(f"      ID: {model_id}")
    print(f"      名前: {model_name}")
    print()
    
    # モデル詳細を取得
    print("[4] モデル詳細を取得中...")
    model_details = None
    
    # CivitAI統合で取得を試行
    if civitai.is_available():
        model_details = civitai.get_model_details(model_id)
    
    # APIキーなしで直接APIを呼び出す
    if not model_details:
        try:
            api_url = f"https://civitai.com/api/v1/models/{model_id}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                model_details = response.json()
        except Exception as e:
            print(f"   ⚠️  モデル詳細取得エラー: {e}")
    
    if not model_details:
        print("   ❌ モデル詳細の取得に失敗しました")
        print(f"   手動でダウンロードしてください: https://civitai.com/models/{model_id}")
        return 1
    
    # 最新バージョンを取得
    versions = model_details.get("modelVersions", [])
    if not versions:
        print("   ❌ モデルバージョンが見つかりません")
        return 1
    
    latest_version = versions[0]
    version_id = latest_version.get("id")
    version_name = latest_version.get("name", "Unknown")
    
    print(f"   ✅ 最新バージョン: {version_name} (ID: {version_id})")
    
    # ファイル情報を取得
    files = latest_version.get("files", [])
    if not files:
        print("   ❌ ダウンロード可能なファイルが見つかりません")
        return 1
    
    # safetensorsファイルを優先
    target_file = None
    for file in files:
        if file.get("name", "").endswith(".safetensors"):
            target_file = file
            break
    
    if not target_file:
        target_file = files[0]
    
    file_name = target_file.get("name", "model.safetensors")
    file_size_mb = target_file.get("sizeKB", 0) / 1024 if target_file.get("sizeKB") else 0
    
    print(f"   ✅ ダウンロードファイル: {file_name}")
    if file_size_mb > 0:
        print(f"      サイズ: {file_size_mb:.1f} MB")
    print()
    
    # 既存ファイルをチェック
    output_path = os.path.join(checkpoints_path, file_name)
    if os.path.exists(output_path):
        print(f"   ⚠️  ファイルが既に存在します: {output_path}")
        response = input("   上書きしますか？ (y/N): ")
        if response.lower() != "y":
            print("   インストールをキャンセルしました")
            return 0
        print()
    
    # ダウンロード実行
    print("[5] モデルをダウンロード中...")
    print("   （この処理には時間がかかる場合があります）")
    print()
    
    downloaded_path = None
    
    # APIキーがある場合はCivitAI統合を使用
    if civitai.is_available():
        downloaded_path = civitai.download_model(
            model_id=model_id,
            version_id=version_id,
            download_path=output_path
        )
    
    # APIキーがない場合、直接URLからダウンロードを試行
    if not downloaded_path:
        print("   ℹ️  CivitAI APIキーがないため、直接ダウンロードを試行します...")
        
        # ダウンロードURLを取得
        download_url = target_file.get("downloadUrl")
        if not download_url:
            # CivitAIの直接ダウンロードURLを構築
            download_url = f"https://civitai.com/api/download/models/{model_id}"
            if version_id:
                download_url = f"https://civitai.com/api/download/models/{model_id}?type=Model&format=SafeTensor"
        
        if download_url:
            try:
                print(f"   ダウンロードURL: {download_url}")
                print("   ダウンロード中...")
                
                response = requests.get(download_url, stream=True, timeout=300)
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
                                print(f"\r   進捗: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB)", end="")
                
                print()  # 改行
                downloaded_path = output_path
                print("   ✅ ダウンロード完了")
            except Exception as e:
                print(f"\n   ❌ ダウンロードエラー: {e}")
                print()
                print("   手動ダウンロード手順:")
                print(f"   1. https://civitai.com/models/{model_id} にアクセス")
                print(f"   2. モデルをダウンロード")
                print(f"   3. ファイルを {checkpoints_path} に配置")
                print(f"   4. ファイル名: {file_name}")
                return 1
    
    if not downloaded_path:
        print("   ❌ ダウンロードに失敗しました")
        print()
        print("   手動ダウンロード手順:")
        print(f"   1. https://civitai.com/models/{model_id} にアクセス")
        print(f"   2. モデルをダウンロード")
        print(f"   3. ファイルを {checkpoints_path} に配置")
        print(f"   4. ファイル名: {file_name}")
        return 1
    
    print()
    print("=" * 60)
    print("✅ インストール完了！")
    print("=" * 60)
    print()
    print(f"モデルファイル: {downloaded_path}")
    print()
    print("次のステップ:")
    print("1. ComfyUIを起動してください")
    print("2. CheckpointLoaderSimpleノードでモデルを選択できます")
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

