"""
CivitAI API統合モジュール
既存のdownload_civitai_models.pyを拡張
"""

import requests
import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime


class CivitAIIntegration:
    """CivitAI統合クラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: CivitAI APIキー（オプション）
        """
        self.api_base = "https://civitai.com/api/v1"
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}"
            })
    
    def is_available(self) -> bool:
        """
        CivitAIが利用可能かチェック
        
        Returns:
            利用可能な場合True（APIキーが設定されている場合）
        """
        # APIキーが設定されていれば利用可能とする
        # 実際の接続テストは行わない（無料APIなので）
        return self.api_key is not None and len(self.api_key) > 0
    
    def search_models(
        self,
        query: str = "",
        limit: int = 20,
        model_type: Optional[str] = None,
        sort: str = "Most Downloaded"
    ) -> List[Dict[str, Any]]:
        """
        モデルを検索
        
        Args:
            query: 検索クエリ
            limit: 取得数
            model_type: モデルタイプ（Checkpoint, LoRA, etc.）
            sort: ソート方法
            
        Returns:
            モデル情報のリスト
        """
        try:
            params = {
                "limit": limit,
                "sort": sort
            }
            
            if query:
                params["query"] = query
            
            if model_type:
                params["types"] = model_type
            
            response = self.session.get(
                f"{self.api_base}/models",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("items", [])
            
        except Exception as e:
            print(f"モデル検索エラー: {e}")
            return []
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        モデル情報を取得
        
        Args:
            model_id: モデルID
            
        Returns:
            モデル情報の辞書
        """
        try:
            response = self.session.get(
                f"{self.api_base}/models/{model_id}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"モデル情報取得エラー: {e}")
            return None
    
    def get_model_versions(self, model_id: str) -> List[Dict[str, Any]]:
        """
        モデルのバージョン一覧を取得
        
        Args:
            model_id: モデルID
            
        Returns:
            バージョン情報のリスト
        """
        model_info = self.get_model_info(model_id)
        if not model_info:
            return []
        
        return model_info.get("modelVersions", [])
    
    def get_latest_version(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        最新バージョンを取得
        
        Args:
            model_id: モデルID
            
        Returns:
            最新バージョン情報
        """
        versions = self.get_model_versions(model_id)
        if not versions:
            return None
        
        # 最新のバージョンを取得（publishedAtでソート）
        latest = max(versions, key=lambda v: v.get("publishedAt", ""))
        return latest
    
    def get_download_url(self, model_id: str, version_id: Optional[str] = None) -> Optional[str]:
        """
        ダウンロードURLを取得
        
        Args:
            model_id: モデルID
            version_id: バージョンID（Noneの場合は最新版）
            
        Returns:
            ダウンロードURL
        """
        if version_id:
            versions = self.get_model_versions(model_id)
            version = next(
                (v for v in versions if str(v.get("id")) == str(version_id)),
                None
            )
        else:
            version = self.get_latest_version(model_id)
        
        if not version:
            return None
        
        files = version.get("files", [])
        if not files:
            return None
        
        # メインファイルを取得
        main_file = None
        for file in files:
            file_type = file.get("type", "").lower()
            if file_type in ["model", "pruned model"]:
                main_file = file
                break
        
        if not main_file:
            main_file = files[0]
        
        return main_file.get("downloadUrl")
    
    def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        """
        モデルの統計情報を取得
        
        Args:
            model_id: モデルID
            
        Returns:
            統計情報の辞書
        """
        model_info = self.get_model_info(model_id)
        if not model_info:
            return {}
        
        return {
            "model_id": model_id,
            "name": model_info.get("name"),
            "description": model_info.get("description", "")[:200],
            "download_count": model_info.get("downloadCount", 0),
            "rating": model_info.get("rating", 0),
            "rating_count": model_info.get("ratingCount", 0),
            "version_count": len(model_info.get("modelVersions", [])),
            "tags": [tag.get("name") for tag in model_info.get("tags", [])],
            "created_at": model_info.get("createdAt"),
            "updated_at": model_info.get("updatedAt")
        }
    
    def search_by_tags(self, tags: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """
        タグでモデルを検索
        
        Args:
            tags: タグのリスト
            limit: 取得数
            
        Returns:
            モデル情報のリスト
        """
        try:
            params = {
                "limit": limit,
                "tags": ",".join(tags)
            }
            
            response = self.session.get(
                f"{self.api_base}/models",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("items", [])
            
        except Exception as e:
            print(f"タグ検索エラー: {e}")
            return []


def main():
    """テスト用メイン関数"""
    civitai = CivitAIIntegration()
    
    print("CivitAI統合テスト")
    print("=" * 50)
    
    # モデル検索
    print("\n人気モデルを検索中...")
    models = civitai.search_models(query="realistic", limit=5)
    print(f"検索結果: {len(models)}件")
    
    for model in models[:3]:
        print(f"  - {model.get('name')} (ID: {model.get('id')})")
        print(f"    ダウンロード数: {model.get('downloadCount', 0)}")
    
    # モデル情報取得
    if models:
        model_id = models[0].get('id')
        print(f"\nモデル情報を取得中: {model_id}...")
        stats = civitai.get_model_stats(str(model_id))
        print(f"  名前: {stats.get('name')}")
        print(f"  ダウンロード数: {stats.get('download_count')}")
        print(f"  評価: {stats.get('rating')}/5 ({stats.get('rating_count')}件)")


if __name__ == "__main__":
    main()




