#!/usr/bin/env python3
"""
CivitAI API Client for Trinity System
マナのお気に入りモデルを取得・管理するツール
"""

import os
import requests
import json
from datetime import datetime
from pathlib import Path

class CivitAIClient:
    def __init__(self, api_key=None):
        """初期化"""
        if api_key is None:
            # .mana_vaultから読み込み
            env_file = Path("/root/.mana_vault/civitai_api.env")
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith("CIVITAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            break
        
        self.api_key = api_key
        self.base_url = "https://civitai.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_favorites(self, limit=100, page=1):
        """
        お気に入りモデルを取得
        """
        url = f"{self.base_url}/models"
        params = {
            "favorites": "true",
            "limit": limit,
            "page": page,
            "sort": "Highest Rated"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"エラー: {e}")
            return None
    
    def get_model_details(self, model_id):
        """
        特定のモデルの詳細を取得
        """
        url = f"{self.base_url}/models/{model_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"エラー: {e}")
            return None
    
    def search_models(self, query, limit=20):
        """
        モデルを検索
        """
        url = f"{self.base_url}/models"
        params = {
            "query": query,
            "limit": limit
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"エラー: {e}")
            return None
    
    def download_model(self, model_version_id, output_dir="/root/civitai_models"):
        """
        モデルをダウンロード
        """
        url = f"{self.base_url}/model-versions/{model_version_id}"
        
        try:
            # モデル情報を取得
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            model_info = response.json()
            
            # ダウンロードURL
            download_url = model_info.get("downloadUrl")
            if not download_url:
                print("ダウンロードURLが見つかりません")
                return False
            
            # 出力ディレクトリを作成
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # ダウンロード
            filename = model_info.get("files", [{}])[0].get("name", "model.safetensors")
            output_path = Path(output_dir) / filename
            
            print(f"ダウンロード中: {filename}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"完了: {output_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"エラー: {e}")
            return False
    
    def save_favorites_to_json(self, output_file="/root/trinity_workspace/shared/civitai_favorites.json"):
        """
        お気に入りをJSONファイルに保存
        """
        favorites = self.get_favorites(limit=100)
        
        if favorites:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # タイムスタンプ追加
            favorites["retrieved_at"] = datetime.now().isoformat()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(favorites, f, ensure_ascii=False, indent=2)
            
            print(f"お気に入りを保存しました: {output_path}")
            print(f"モデル数: {len(favorites.get('items', []))}")
            return True
        
        return False


def main():
    """メイン関数"""
    client = CivitAIClient()
    
    print("=== CivitAI Client for Trinity ===")
    print(f"API接続テスト...")
    
    # お気に入りを取得
    favorites = client.get_favorites(limit=10)
    
    if favorites:
        items = favorites.get("items", [])
        print(f"\n✅ 成功！マナのお気に入り: {len(items)}件")
        
        for i, model in enumerate(items[:5], 1):
            print(f"\n{i}. {model.get('name')}")
            print(f"   ID: {model.get('id')}")
            print(f"   タイプ: {model.get('type')}")
            print(f"   ダウンロード数: {model.get('stats', {}).get('downloadCount', 0):,}")
        
        # JSONに保存
        client.save_favorites_to_json()
    else:
        print("❌ お気に入りを取得できませんでした")


if __name__ == "__main__":
    main()

