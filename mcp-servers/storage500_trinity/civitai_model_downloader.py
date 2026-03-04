#!/usr/bin/env python3
"""
CivitAI Model Downloader
マナのお気に入りモデルをダウンロードして使用するツール
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
import time

class CivitAIModelDownloader:
    def __init__(self):
        self.models_dir = Path("/root/civitai_models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # API設定
        self.api_key = self._load_api_key()
        self.base_url = "https://civitai.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _load_api_key(self):
        """APIキーを読み込み"""
        env_file = Path("/root/.mana_vault/civitai_api.env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith("CIVITAI_API_KEY="):
                        return line.split("=", 1)[1].strip()
        return None
    
    def download_model(self, model_id, version_id=None):
        """モデルをダウンロード"""
        try:
            # モデル詳細を取得
            model_url = f"{self.base_url}/models/{model_id}"
            response = requests.get(model_url, headers=self.headers)
            response.raise_for_status()
            model_data = response.json()
            
            print(f"📥 モデル情報取得: {model_data['name']}")
            
            # バージョン選択
            if version_id is None:
                # 最新バージョンを使用
                version = model_data['modelVersions'][0]
            else:
                # 指定されたバージョンを検索
                version = None
                for v in model_data['modelVersions']:
                    if v['id'] == version_id:
                        version = v
                        break
                
                if version is None:
                    print(f"❌ バージョン {version_id} が見つかりません")
                    return False
            
            print(f"📦 ダウンロード対象: {version['name']}")
            
            # ファイル情報を取得
            files = version.get('files', [])
            if not files:
                print("❌ ダウンロード可能なファイルがありません")
                return False
            
            # メインファイルを選択（通常は.safetensorsまたは.ckpt）
            main_file = None
            for file_info in files:
                if file_info.get('type') == 'Model':
                    main_file = file_info
                    break
            
            if main_file is None:
                main_file = files[0]  # 最初のファイルを使用
            
            # ダウンロードURLを取得
            download_url = main_file.get('downloadUrl')
            if not download_url:
                print("❌ ダウンロードURLが取得できません")
                return False
            
            # ファイル名を決定
            filename = main_file.get('name', f"model_{model_id}.safetensors")
            output_path = self.models_dir / filename
            
            print(f"⬇️ ダウンロード開始: {filename}")
            print(f"📁 保存先: {output_path}")
            
            # ダウンロード実行
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r📊 進捗: {progress:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print(f"\n✅ ダウンロード完了: {output_path}")
            
            # モデル情報を保存
            model_info = {
                "id": model_id,
                "name": model_data['name'],
                "type": model_data['type'],
                "version": version['name'],
                "version_id": version['id'],
                "base_model": version.get('baseModel', 'SD 1.5'),
                "filename": filename,
                "downloaded_at": datetime.now().isoformat(),
                "description": model_data.get('description', ''),
                "tags": model_data.get('tags', [])
            }
            
            info_path = output_path.with_suffix('.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(model_info, f, ensure_ascii=False, indent=2)
            
            print(f"📄 モデル情報保存: {info_path}")
            return True
            
        except Exception as e:
            print(f"❌ ダウンロードエラー: {str(e)}")
            return False
    
    def download_favorites(self, limit=5):
        """お気に入りモデルをダウンロード"""
        try:
            # お気に入りを取得
            favorites_url = f"{self.base_url}/models"
            params = {
                "favorites": "true",
                "limit": limit,
                "sort": "Highest Rated"
            }
            
            response = requests.get(favorites_url, headers=self.headers, params=params)
            response.raise_for_status()
            favorites_data = response.json()
            
            items = favorites_data.get('items', [])
            print(f"📋 お気に入りモデル: {len(items)}件")
            
            downloaded_count = 0
            for i, model in enumerate(items, 1):
                print(f"\n{'='*60}")
                print(f"📥 {i}/{len(items)}: {model['name']}")
                print(f"🆔 ID: {model['id']}")
                print(f"📊 ダウンロード数: {model['stats']['downloadCount']:,}")
                
                if self.download_model(model['id']):
                    downloaded_count += 1
                    print(f"✅ 成功: {model['name']}")
                else:
                    print(f"❌ 失敗: {model['name']}")
                
                # レート制限対策
                if i < len(items):
                    print("⏳ 待機中...")
                    time.sleep(2)
            
            print(f"\n🎉 ダウンロード完了: {downloaded_count}/{len(items)}件")
            return downloaded_count
            
        except Exception as e:
            print(f"❌ お気に入り取得エラー: {str(e)}")
            return 0
    
    def list_downloaded_models(self):
        """ダウンロード済みモデル一覧"""
        models = []
        
        for model_file in self.models_dir.glob("*.safetensors"):
            info_file = model_file.with_suffix('.json')
            if info_file.exists():
                with open(info_file, 'r', encoding='utf-8') as f:
                    model_info = json.load(f)
                    models.append(model_info)
        
        return models
    
    def print_downloaded_models(self):
        """ダウンロード済みモデル表示"""
        models = self.list_downloaded_models()
        
        if not models:
            print("📭 ダウンロード済みモデルがありません")
            return
        
        print(f"📦 ダウンロード済みモデル: {len(models)}件")
        print("=" * 80)
        
        for i, model in enumerate(models, 1):
            print(f"\n{i}. {model['name']}")
            print(f"   🆔 ID: {model['id']}")
            print(f"   📦 バージョン: {model['version']}")
            print(f"   🏷️ タイプ: {model['type']}")
            print(f"   🎯 ベースモデル: {model['base_model']}")
            print(f"   📁 ファイル: {model['filename']}")
            print(f"   📅 ダウンロード日: {model['downloaded_at'][:10]}")
            print(f"   🏷️ タグ: {', '.join(model['tags'][:5])}")


def main():
    """メイン関数"""
    downloader = CivitAIModelDownloader()
    
    print("🎨 CivitAI Model Downloader for Trinity")
    print("=" * 60)
    
    # ダウンロード済みモデル一覧
    print("📦 現在のダウンロード済みモデル:")
    downloader.print_downloaded_models()
    
    print(f"\n🚀 マナのお気に入りモデルをダウンロードしますか？")
    print("📥 上位5件のモデルをダウンロード中...")
    
    # お気に入りモデルをダウンロード
    downloaded_count = downloader.download_favorites(limit=5)
    
    if downloaded_count > 0:
        print(f"\n🎉 ダウンロード完了: {downloaded_count}件")
        print("📦 更新されたモデル一覧:")
        downloader.print_downloaded_models()
    else:
        print("❌ ダウンロードに失敗しました")


if __name__ == "__main__":
    main()


