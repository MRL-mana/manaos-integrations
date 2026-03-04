#!/usr/bin/env python3
"""
Advanced Model Downloader
WAN 2.2, SDXL, Fast Models の一括ダウンロードシステム
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
import time
import subprocess

class AdvancedModelDownloader:
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
        
        # モデル定義
        self.target_models = {
            "wan_2_2": {
                "name": "WAN 2.2",
                "search_terms": ["wan", "waifu diffusion 2.2", "anime"],
                "size_gb": 2.0,
                "priority": 1
            },
            "sdxl": {
                "name": "Stable Diffusion XL",
                "search_terms": ["sdxl", "stable diffusion xl", "realistic"],
                "size_gb": 6.0,
                "priority": 2
            },
            "fast": {
                "name": "Fast Models",
                "search_terms": ["tinysd", "fast", "lightweight", "small"],
                "size_gb": 0.5,
                "priority": 3
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
    
    def search_models(self, search_terms, limit=10):
        """モデル検索"""
        try:
            url = f"{self.base_url}/models"
            params = {
                "query": " ".join(search_terms),
                "limit": limit,
                "sort": "Most Downloaded"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ 検索エラー: {str(e)}")
            return None
    
    def find_best_model(self, model_type):
        """最適なモデルを検索"""
        model_info = self.target_models[model_type]
        search_terms = model_info["search_terms"]
        
        print(f"🔍 {model_info['name']} を検索中...")
        
        search_results = self.search_models(search_terms)
        if not search_results or not search_results.get('items'):
            print(f"❌ {model_info['name']} が見つかりません")
            return None
        
        # 最適なモデルを選択
        best_model = None
        best_score = 0
        
        for model in search_results['items']:
            # スコア計算
            score = 0
            
            # ダウンロード数
            download_count = model.get('stats', {}).get('downloadCount', 0)
            score += min(download_count / 10000, 10)  # 最大10点
            
            # 評価
            thumbs_up = model.get('stats', {}).get('thumbsUpCount', 0)
            score += min(thumbs_up / 1000, 5)  # 最大5点
            
            # 名前の一致度
            name_lower = model.get('name', '').lower()
            for term in search_terms:
                if term.lower() in name_lower:
                    score += 2
            
            # サイズの適切性
            model_versions = model.get('modelVersions', [])
            if model_versions:
                # 最初のバージョンのファイルサイズをチェック
                files = model_versions[0].get('files', [])
                if files:
                    file_size = files[0].get('sizeKB', 0) / (1024 * 1024)  # GB
                    target_size = model_info["size_gb"]
                    size_diff = abs(file_size - target_size)
                    score += max(0, 5 - size_diff)  # サイズが近いほど高スコア
            
            if score > best_score:
                best_score = score
                best_model = model
        
        if best_model:
            print(f"✅ 最適なモデル発見: {best_model['name']}")
            print(f"   ダウンロード数: {best_model.get('stats', {}).get('downloadCount', 0):,}")
            print(f"   評価: {best_model.get('stats', {}).get('thumbsUpCount', 0):,}")
            print(f"   スコア: {best_score:.1f}")
        
        return best_model
    
    def download_model(self, model_id, model_name):
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
                "stats": model_data.get('stats', {})
            }
            
            info_path = output_path.with_suffix('.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(model_info, f, ensure_ascii=False, indent=2)
            
            print(f"📄 モデル情報保存: {info_path}")
            return True
            
        except Exception as e:
            print(f"❌ ダウンロードエラー: {str(e)}")
            return False
    
    def download_all_models(self):
        """全モデルをダウンロード"""
        print("🚀 Advanced Model Downloader 起動")
        print("=" * 60)
        
        results = {}
        
        # 優先度順でダウンロード
        sorted_models = sorted(
            self.target_models.items(),
            key=lambda x: x[1]['priority']
        )
        
        for model_key, model_info in sorted_models:
            print(f"\n{'='*60}")
            print(f"📥 {model_info['name']} ダウンロード開始")
            print(f"{'='*60}")
            
            # 最適なモデルを検索
            best_model = self.find_best_model(model_key)
            if not best_model:
                print(f"❌ {model_info['name']} の検索に失敗")
                results[model_key] = False
                continue
            
            # モデルをダウンロード
            success = self.download_model(
                best_model['id'],
                model_info['name']
            )
            
            results[model_key] = success
            
            if success:
                print(f"✅ {model_info['name']} ダウンロード完了")
            else:
                print(f"❌ {model_info['name']} ダウンロード失敗")
            
            # レート制限対策
            print("⏳ 待機中...")
            time.sleep(3)
        
        # 結果サマリー
        print(f"\n🎉 ダウンロード完了サマリー")
        print("=" * 60)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        for model_key, success in results.items():
            model_name = self.target_models[model_key]['name']
            status = "✅ 成功" if success else "❌ 失敗"
            print(f"  {model_name}: {status}")
        
        print(f"\n📊 結果: {success_count}/{total_count} 成功")
        
        if success_count == total_count:
            print("🎉 全モデルのダウンロードが完了しました！")
        else:
            print("⚠️ 一部のモデルのダウンロードに失敗しました")
        
        return results


def main():
    """メイン関数"""
    downloader = AdvancedModelDownloader()
    downloader.download_all_models()


if __name__ == "__main__":
    main()


