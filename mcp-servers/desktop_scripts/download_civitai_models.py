"""
Civitaiモデルダウンロードスクリプト
指定されたCivitaiモデルをダウンロードします
"""
# type: ignore
# @noqa
# noqa: F401

import requests
import os
import json
import sys
from pathlib import Path
from typing import Optional
import time

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class CivitaiModelDownloader:
    """Civitaiモデルダウンローダー"""
    
    def __init__(self, output_dir: str = "models"):
        """
        初期化
        
        Args:
            output_dir: モデル保存ディレクトリ
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_base = "https://civitai.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def get_model_info(self, model_id: str) -> Optional[dict]:
        """
        モデル情報を取得
        
        Args:
            model_id: CivitaiモデルID
            
        Returns:
            モデル情報の辞書
        """
        try:
            url = f"{self.api_base}/models/{model_id}"
            print(f"モデル情報を取得中: {model_id}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"モデル情報の取得に失敗: {e}")
            return None
    
    def get_latest_version(self, model_info: dict) -> Optional[dict]:
        """
        最新バージョンを取得
        
        Args:
            model_info: モデル情報
            
        Returns:
            最新バージョン情報
        """
        if not model_info or "modelVersions" not in model_info:
            return None
        
        # 最新バージョンを取得（通常は最初の要素）
        versions = model_info["modelVersions"]
        if not versions:
            return None
        
        # 最新のバージョンを取得（publishedAtでソート）
        latest = max(versions, key=lambda v: v.get("publishedAt", ""))
        return latest
    
    def download_file(self, url: str, filepath: Path, chunk_size: int = 8192) -> bool:
        """
        ファイルをダウンロード
        
        Args:
            url: ダウンロードURL
            filepath: 保存先パス
            chunk_size: チャンクサイズ
            
        Returns:
            成功したかどうか
        """
        try:
            print(f"ダウンロード開始: {filepath.name}")
            response = self.session.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r進捗: {percent:.1f}% ({downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB)", end="")
            
            print(f"\nダウンロード完了: {filepath.name}")
            return True
        except Exception as e:
            print(f"\nダウンロード失敗: {e}")
            if filepath.exists():
                filepath.unlink()
            return False
    
    def download_model(self, model_id: str, version_id: Optional[str] = None) -> bool:
        """
        モデルをダウンロード
        
        Args:
            model_id: CivitaiモデルID
            version_id: バージョンID（Noneの場合は最新版）
            
        Returns:
            成功したかどうか
        """
        # モデル情報を取得
        model_info = self.get_model_info(model_id)
        if not model_info:
            return False
        
        model_name = model_info.get("name", f"model_{model_id}")
        print(f"\nモデル名: {model_name}")
        
        # バージョン情報を取得
        if version_id:
            version = next(
                (v for v in model_info.get("modelVersions", []) if str(v.get("id")) == str(version_id)),
                None
            )
        else:
            version = self.get_latest_version(model_info)
        
        if not version:
            print("バージョン情報が見つかりません")
            return False
        
        version_name = version.get("name", "unknown")
        print(f"バージョン: {version_name}")
        
        # ファイル情報を取得
        files = version.get("files", [])
        if not files:
            print("ダウンロード可能なファイルが見つかりません")
            return False
        
        # メインファイルを取得（通常は.safetensorsまたは.ckpt）
        main_file = None
        for file in files:
            file_type = file.get("type", "").lower()
            if file_type in ["model", "pruned model"]:
                main_file = file
                break
        
        if not main_file:
            main_file = files[0]  # 最初のファイルを使用
        
        file_name = main_file.get("name", "model.safetensors")
        download_url = main_file.get("downloadUrl")
        
        if not download_url:
            print("ダウンロードURLが見つかりません")
            return False
        
        # ファイル名を安全にする
        safe_model_name = "".join(c for c in model_name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_file_name = f"{safe_model_name}_{version_name}_{file_name}"
        safe_file_name = "".join(c for c in safe_file_name if c.isalnum() or c in (" ", "-", "_", ".")).strip()
        
        filepath = self.output_dir / safe_file_name
        
        # 既に存在する場合はサイズを確認
        if filepath.exists():
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            # 100MB未満の場合は破損とみなして再ダウンロード
            if file_size_mb < 100:
                print(f"破損ファイルを検出（{file_size_mb:.2f}MB）。再ダウンロードします...")
                try:
                    filepath.unlink()
                except:
                    pass
            else:
                print(f"既にダウンロード済み: {filepath.name} ({file_size_mb:.2f}MB)")
                return True
        
        # ダウンロード実行
        success = self.download_file(download_url, filepath)
        
        if success:
            print(f"保存先: {filepath}")
            # メタデータを保存
            metadata_path = filepath.with_suffix(".json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump({
                    "model_id": model_id,
                    "model_name": model_name,
                    "version_id": version.get("id"),
                    "version_name": version_name,
                    "file_info": main_file
                }, f, indent=2, ensure_ascii=False)
        
        return success


def main():
    """メイン関数"""
    # ダウンロードするモデルID
    models = [
        {
            "id": "43331",  # majicMIX realistic
            "name": "majicMIX realistic"
        },
        {
            "id": "2661",  # uber-realistic-porn-merge-urpm-sd15
            "name": "uber-realistic-porn-merge-urpm-sd15"
        },
        {
            "id": "443821",  # CyberRealistic Pony
            "name": "CyberRealistic Pony"
        }
    ]
    
    # 出力ディレクトリ（Stable Diffusion WebUIのmodels/Stable-diffusion/を探す）
    possible_paths = [
        Path("models"),
        Path.home() / "stable-diffusion-webui" / "models" / "Stable-diffusion",
        Path("C:/stable-diffusion-webui/models/Stable-diffusion"),
        Path("C:/AI/models"),
    ]
    
    output_dir = None
    for path in possible_paths:
        if path.exists() or path.parent.exists():
            output_dir = path
            break
    
    if not output_dir:
        output_dir = Path("models")
        output_dir.mkdir(exist_ok=True)
        print(f"モデル保存先: {output_dir.absolute()}")
    
    print(f"モデル保存先: {output_dir.absolute()}")
    print("=" * 60)
    
    downloader = CivitaiModelDownloader(output_dir=str(output_dir))
    
    results = []
    for model in models:
        print(f"\n{'=' * 60}")
        print(f"モデル: {model['name']} (ID: {model['id']})")
        print("=" * 60)
        
        success = downloader.download_model(model["id"])
        results.append({
            "name": model["name"],
            "id": model["id"],
            "success": success
        })
        
        # 次のダウンロード前に少し待機
        if success:
            time.sleep(2)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("ダウンロード結果")
    print("=" * 60)
    for result in results:
        status = "✓ 成功" if result["success"] else "✗ 失敗"
        print(f"{result['name']}: {status}")
    
    print(f"\nモデル保存先: {output_dir.absolute()}")


if __name__ == "__main__":
    main()

