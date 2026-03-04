#!/usr/bin/env python3
"""
Advanced CivitAI Downloader
マナのお気に入りモデルを一括ダウンロード
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
import time
import subprocess

class AdvancedCivitAIDownloader:
    def __init__(self):
        self.models_dir = Path("/mnt/storage500/civitai_models")  # 追加ストレージに保存
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # API設定
        self.api_key = self._load_api_key()
        self.base_url = "https://civitai.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # マナのお気に入りモデル定義
        self.mana_favorites = {
            "anime_models": {
                "name": "アニメ・イラスト系",
                "search_terms": ["anime", "waifu", "manga", "illustration", "2d"],
                "size_gb": 2.0,
                "priority": 1
            },
            "realistic_models": {
                "name": "リアル系",
                "search_terms": ["realistic", "photorealistic", "portrait", "real"],
                "size_gb": 3.0,
                "priority": 2
            },
            "artistic_models": {
                "name": "アート系",
                "search_terms": ["art", "painting", "artistic", "style", "artwork"],
                "size_gb": 1.5,
                "priority": 3
            },
            "character_models": {
                "name": "キャラクター系",
                "search_terms": ["character", "person", "face", "portrait"],
                "size_gb": 1.0,
                "priority": 4
            },
            "style_models": {
                "name": "スタイル系",
                "search_terms": ["style", "lora", "embedding", "hypernetwork"],
                "size_gb": 0.5,
                "priority": 5
            }
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
    
    def search_models_by_category(self, category_key, limit=5):
        """カテゴリ別モデル検索"""
        category = self.mana_favorites[category_key]
        search_terms = category["search_terms"]
        
        print(f"🔍 {category['name']} モデル検索中...")
        
        try:
            url = f"{self.base_url}/models"
            params = {
                "query": " ".join(search_terms),
                "limit": limit,
                "sort": "Most Downloaded",
                "types": "Checkpoint"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ 検索エラー: {str(e)}")
            return None
    
    def find_best_models(self, category_key):
        """カテゴリ別最適モデル検索"""
        category = self.mana_favorites[category_key]
        search_results = self.search_models_by_category(category_key)
        
        if not search_results or not search_results.get('items'):
            print(f"❌ {category['name']} モデルが見つかりません")
            return []
        
        # 最適なモデルを選択
        best_models = []
        
        for model in search_results['items'][:3]:  # 上位3つ
            # スコア計算
            score = 0
            
            # ダウンロード数
            download_count = model.get('stats', {}).get('downloadCount', 0)
            score += min(download_count / 10000, 10)
            
            # 評価
            thumbs_up = model.get('stats', {}).get('thumbsUpCount', 0)
            score += min(thumbs_up / 1000, 5)
            
            # 名前の一致度
            name_lower = model.get('name', '').lower()
            for term in category["search_terms"]:
                if term.lower() in name_lower:
                    score += 2
            
            if score > 5:  # 最低スコア
                best_models.append({
                    "model": model,
                    "score": score,
                    "category": category_key
                })
        
        # スコア順でソート
        best_models.sort(key=lambda x: x['score'], reverse=True)
        
        return best_models
    
    def download_model(self, model_id, model_name, category):
        """モデルをダウンロード"""
        try:
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
                "category": category
            }
            
            info_path = output_path.with_suffix('.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(model_info, f, ensure_ascii=False, indent=2)
            
            print(f"📄 モデル情報保存: {info_path}")
            return True
            
        except Exception as e:
            print(f"❌ ダウンロードエラー: {str(e)}")
            return False
    
    def download_all_categories(self):
        """全カテゴリのモデルをダウンロード"""
        print("🚀 Advanced CivitAI Downloader - マナのお気に入りモデル")
        print("=" * 80)
        
        results = {}
        
        # カテゴリ別ダウンロード
        for category_key, category_info in self.mana_favorites.items():
            print(f"\n{'='*80}")
            print(f"📥 {category_info['name']} モデルダウンロード開始")
            print(f"{'='*80}")
            
            # 最適なモデルを検索
            best_models = self.find_best_models(category_key)
            
            if not best_models:
                print(f"❌ {category_info['name']} の検索に失敗")
                results[category_key] = []
                continue
            
            category_results = []
            for i, model_info in enumerate(best_models[:2], 1):  # 各カテゴリから2つまで
                model = model_info['model']
                print(f"\n📦 {i}. {model['name']} (スコア: {model_info['score']:.1f})")
                
                # モデルをダウンロード
                success = self.download_model(
                    model['id'],
                    model['name'],
                    category_key
                )
                
                category_results.append({
                    "name": model['name'],
                    "success": success,
                    "score": model_info['score']
                })
                
                if success:
                    print(f"✅ {model['name']} ダウンロード完了")
                else:
                    print(f"❌ {model['name']} ダウンロード失敗")
                
                # レート制限対策
                print("⏳ 待機中...")
                time.sleep(3)
            
            results[category_key] = category_results
        
        # 結果サマリー
        print(f"\n🎉 ダウンロード完了サマリー")
        print("=" * 80)
        
        total_success = 0
        total_attempts = 0
        
        for category_key, category_results in results.items():
            category_name = self.mana_favorites[category_key]['name']
            success_count = sum(1 for result in category_results if result['success'])
            total_count = len(category_results)
            
            print(f"\n📁 {category_name}:")
            for result in category_results:
                status = "✅ 成功" if result['success'] else "❌ 失敗"
                print(f"  {result['name']}: {status}")
            
            total_success += success_count
            total_attempts += total_count
        
        print(f"\n📊 総合結果: {total_success}/{total_attempts} 成功")
        
        if total_success == total_attempts:
            print("🎉 全モデルのダウンロードが完了しました！")
        else:
            print("⚠️ 一部のモデルのダウンロードに失敗しました")
        
        return results
    
    def list_downloaded_models(self):
        """ダウンロード済みモデル一覧"""
        print("📦 ダウンロード済みモデル一覧")
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
            category_name = self.mana_favorites.get(category, {}).get('name', category)
            print(f"\n📁 {category_name} ({len(model_list)}個):")
            
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
    downloader = AdvancedCivitAIDownloader()
    
    print("🎨 Advanced CivitAI Downloader - マナのお気に入りモデル")
    print("=" * 80)
    
    # ダウンロード済みモデル一覧
    downloader.list_downloaded_models()
    
    # 全カテゴリダウンロード
    downloader.download_all_categories()
    
    # 最終結果表示
    downloader.list_downloaded_models()


if __name__ == "__main__":
    main()


