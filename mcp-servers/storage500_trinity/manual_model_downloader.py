#!/usr/bin/env python3
"""
Manual Model Downloader
手動でモデルを追加ダウンロード
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
import time

class ManualModelDownloader:
    def __init__(self):
        self.models_dir = Path("/mnt/storage500/civitai_models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # API設定
        self.api_key = self._load_api_key()
        self.base_url = "https://civitai.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 人気モデルIDリスト
        self.popular_models = {
            "anime_models": [
                {"id": 128713, "name": "Anything V5", "type": "Checkpoint"},
                {"id": 4384, "name": "ChilloutMix", "type": "Checkpoint"},
                {"id": 4823, "name": "DreamShaper", "type": "Checkpoint"},
                {"id": 128713, "name": "Anything V4.5", "type": "Checkpoint"},
                {"id": 128713, "name": "Counterfeit V3.0", "type": "Checkpoint"}
            ],
            "realistic_models": [
                {"id": 128713, "name": "Realistic Vision V2.0", "type": "Checkpoint"},
                {"id": 128713, "name": "Deliberate", "type": "Checkpoint"},
                {"id": 128713, "name": "Juggernaut XL", "type": "Checkpoint"},
                {"id": 128713, "name": "Realistic Vision V1.4", "type": "Checkpoint"}
            ],
            "artistic_models": [
                {"id": 128713, "name": "OpenJourney", "type": "Checkpoint"},
                {"id": 128713, "name": "Stable Diffusion 2.1", "type": "Checkpoint"},
                {"id": 128713, "name": "Waifu Diffusion", "type": "Checkpoint"}
            ]
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
    
    def download_model_by_id(self, model_id, model_name):
        """モデルIDでダウンロード"""
        try:
            print(f"📥 モデルダウンロード開始: {model_name} (ID: {model_id})")
            
            # モデル詳細を取得
            model_url = f"{self.base_url}/models/{model_id}"
            response = requests.get(model_url, headers=self.headers)
            response.raise_for_status()
            model_data = response.json()
            
            # 最新バージョンを取得
            version = model_data['modelVersions'][0]
            version_id = version['id']
            
            # バージョン詳細を取得
            version_url = f"{self.base_url}/model-versions/{version_id}"
            response = requests.get(version_url, headers=self.headers)
            response.raise_for_status()
            version_data = response.json()
            
            # メインファイルを選択
            files = version_data.get('files', [])
            if not files:
                print("❌ ダウンロード可能なファイルがありません")
                return False
            
            main_file = None
            for file_info in files:
                if file_info.get('type') == 'Model':
                    main_file = file_info
                    break
            
            if main_file is None:
                main_file = files[0]
            
            # ダウンロードURLを取得
            download_url = main_file.get('downloadUrl')
            if not download_url:
                print("❌ ダウンロードURLが取得できません")
                return False
            
            # ファイル名を決定
            filename = main_file.get('name', f"{model_name}.safetensors")
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
                "version_id": version_id,
                "base_model": version.get('baseModel', 'SD 1.5'),
                "filename": filename,
                "downloaded_at": datetime.now().isoformat(),
                "description": model_data.get('description', ''),
                "tags": model_data.get('tags', []),
                "stats": model_data.get('stats', {}),
                "category": "manual_download"
            }
            
            info_path = output_path.with_suffix('.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(model_info, f, ensure_ascii=False, indent=2)
            
            print(f"📄 モデル情報保存: {info_path}")
            return True
            
        except Exception as e:
            print(f"❌ ダウンロードエラー: {str(e)}")
            return False
    
    def download_popular_models(self):
        """人気モデルをダウンロード"""
        print("🚀 人気モデル一括ダウンロード開始")
        print("=" * 80)
        
        results = {}
        
        for category, models in self.popular_models.items():
            print(f"\n📁 {category} モデルダウンロード開始")
            print("-" * 60)
            
            category_results = []
            for model_info in models[:2]:  # 各カテゴリから2つまで
                model_id = model_info['id']
                model_name = model_info['name']
                
                print(f"\n📦 {model_name} ダウンロード中...")
                
                success = self.download_model_by_id(model_id, model_name)
                category_results.append({
                    "name": model_name,
                    "success": success
                })
                
                if success:
                    print(f"✅ {model_name} ダウンロード完了")
                else:
                    print(f"❌ {model_name} ダウンロード失敗")
                
                # レート制限対策
                print("⏳ 待機中...")
                time.sleep(5)
            
            results[category] = category_results
        
        # 結果サマリー
        print(f"\n🎉 ダウンロード完了サマリー")
        print("=" * 80)
        
        total_success = 0
        total_attempts = 0
        
        for category, category_results in results.items():
            success_count = sum(1 for result in category_results if result['success'])
            total_count = len(category_results)
            
            print(f"\n📁 {category}:")
            for result in category_results:
                status = "✅ 成功" if result['success'] else "❌ 失敗"
                print(f"  {result['name']}: {status}")
            
            total_success += success_count
            total_attempts += total_count
        
        print(f"\n📊 総合結果: {total_success}/{total_attempts} 成功")
        return results
    
    def list_current_models(self):
        """現在のモデル一覧表示"""
        print("📦 現在のモデル一覧")
        print("=" * 60)
        
        if not self.models_dir.exists():
            print("❌ モデルディレクトリが存在しません")
            return
        
        models = {}
        for model_file in self.models_dir.glob("*.safetensors"):
            info_file = model_file.with_suffix('.json')
            
            if info_file.exists():
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        model_info = json.load(f)
                    
                    category = model_info.get('category', 'unknown')
                    if category not in models:
                        models[category] = []
                    
                    models[category].append({
                        "name": model_info['name'],
                        "filename": model_file.name,
                        "size_mb": model_file.stat().st_size / (1024 * 1024),
                        "downloaded_at": model_info.get('downloaded_at', ''),
                        "description": model_info.get('description', '')[:100] + "..." if model_info.get('description') else ""
                    })
                except:
                    pass
        
        for category, model_list in models.items():
            print(f"\n📁 {category} ({len(model_list)}個):")
            
            for model in model_list:
                print(f"  📦 {model['name']}")
                print(f"     ファイル: {model['filename']}")
                print(f"     サイズ: {model['size_mb']:.1f}MB")
                print(f"     ダウンロード日: {model['downloaded_at'][:19] if model['downloaded_at'] else '不明'}")
                if model['description']:
                    print(f"     説明: {model['description']}")
                print()


def main():
    """メイン関数"""
    downloader = ManualModelDownloader()
    
    print("🎨 Manual Model Downloader")
    print("=" * 80)
    
    # 現在のモデル一覧
    downloader.list_current_models()
    
    # 人気モデルダウンロード
    print("\n🚀 人気モデルを追加ダウンロードしますか？")
    print("これにより、より多くのモデルが利用可能になります。")
    
    # 自動実行
    downloader.download_popular_models()
    
    # 最終結果表示
    downloader.list_current_models()


if __name__ == "__main__":
    main()


