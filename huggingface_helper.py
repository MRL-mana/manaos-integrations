"""
Hugging Face統合ヘルパー
Hugging Face Hubとの統合を提供
"""

from manaos_logger import get_logger
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = get_logger(__name__)
try:
    from huggingface_hub import HfApi, snapshot_download
    from huggingface_hub.utils import HfHubHTTPError
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    logger.warning("huggingface_hubライブラリが利用できません。pip install huggingface_hub を実行してください。")


class HuggingFaceHelper:
    """Hugging Face統合ヘルパー"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初期化
        
        Args:
            token: Hugging Face APIトークン（オプション）
        """
        if not HF_HUB_AVAILABLE:
            raise ImportError("huggingface_hubライブラリが必要です。pip install huggingface_hub を実行してください。")
        
        self.api = HfApi(token=token)
        self.token = token
        logger.info("HuggingFaceHelperを初期化しました")
    
    def search_models(
        self,
        query: str,
        task: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        モデルを検索
        
        Args:
            query: 検索クエリ
            task: タスクタイプ（例: "text-to-image"）
            limit: 取得件数
        
        Returns:
            モデル情報のリスト
        """
        try:
            models = self.api.list_models(
                search=query,
                task=task,
                limit=limit
            )
            
            results = []
            for model in models:
                results.append({
                    "id": model.id,
                    "author": model.author,
                    "downloads": model.downloads,
                    "likes": model.likes,
                    "tags": model.tags,
                    "pipeline_tag": model.pipeline_tag
                })
            
            logger.info(f"モデル検索完了: {len(results)}件")
            return results
            
        except Exception as e:
            logger.error(f"モデル検索エラー: {e}")
            return []
    
    def download_model(
        self,
        model_id: str,
        cache_dir: Optional[str] = None
    ) -> Optional[Path]:
        """
        モデルをダウンロード
        
        Args:
            model_id: モデルID
            cache_dir: キャッシュディレクトリ
        
        Returns:
            ダウンロード先のパス（失敗時はNone）
        """
        try:
            logger.info(f"モデルをダウンロード: {model_id}")
            
            download_path = snapshot_download(
                repo_id=model_id,
                cache_dir=cache_dir,
                token=self.token
            )
            
            logger.info(f"ダウンロード完了: {download_path}")
            return Path(download_path)
            
        except Exception as e:
            logger.error(f"モデルダウンロードエラー: {e}")
            return None
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        モデル情報を取得
        
        Args:
            model_id: モデルID
        
        Returns:
            モデル情報（失敗時はNone）
        """
        try:
            model_info = self.api.model_info(model_id)
            
            return {
                "id": model_info.id,
                "author": model_info.author,
                "downloads": model_info.downloads,
                "likes": model_info.likes,
                "tags": model_info.tags,
                "pipeline_tag": model_info.pipeline_tag,
                "siblings": [sibling.rfilename for sibling in model_info.siblings]
            }
            
        except Exception as e:
            logger.error(f"モデル情報取得エラー: {e}")
            return None


# 使用例
if __name__ == "__main__":
    helper = HuggingFaceHelper()
    
    # モデル検索
    models = helper.search_models("stable-diffusion", task="text-to-image", limit=5)
    for model in models:
        print(f"モデル: {model['id']} (ダウンロード数: {model['downloads']})")
