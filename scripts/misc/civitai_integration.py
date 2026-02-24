"""
CivitAI API統合モジュール（改善版）
既存のdownload_civitai_models.pyを拡張
ベースクラスを使用して統一モジュールを活用
"""

import requests
import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

# ベースクラスのインポート
from base_integration import BaseIntegration


class CivitAIIntegration(BaseIntegration):
    """CivitAI統合クラス（改善版）"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初期化

        Args:
            api_key: CivitAI APIキー（オプション、環境変数からも取得可能）
        """
        super().__init__("CivitAI")
        self.api_base = "https://civitai.com/api/v1"
        self.api_key = api_key or os.getenv("CIVITAI_API_KEY")
        self.session = requests.Session()
        # プロキシを無効化
        self.session.proxies = {
            'http': None,
            'https': None
        }
        self.session.headers.update({
            "User-Agent": "ManaOS-CivitAI-Integration/1.0"
        })

        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })

    def _initialize_internal(self) -> bool:
        """
        内部初期化

        Returns:
            初期化成功かどうか
        """
        # CivitAIはAPIキーが設定されていれば利用可能
        if self.api_key:
            self.logger.info("CivitAI統合を初期化しました")
            return True
        else:
            self.logger.warning("CivitAI APIキーが設定されていません")
            return False

    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック

        Returns:
            利用可能かどうか
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
        if not self.is_available():
            self.logger.warning("CivitAI統合が利用できません")
            return []

        try:
            params = {}

            if limit:
                params["limit"] = limit

            # sortパラメータ（APIでは "Highest Rated", "Most Downloaded", "Most Liked", "Most Discussed", "Most Collected", "Most Images", "Newest", "Oldest"）
            if sort:
                # sort値はそのまま使用（スペースありの形式）
                params["sort"] = sort

            if query:
                params["query"] = query

            # typesパラメータ（APIドキュメントでは enum[]: Checkpoint, TextualInversion, Hypernetwork, AestheticGradient, LORA, Controlnet, Poses）
            if model_type:
                # モデルタイプをAPI形式に変換（大文字のLORA）
                type_map = {
                    "LoRA": "LORA",
                    "lora": "LORA",
                    "LORA": "LORA",
                    "Checkpoint": "Checkpoint",
                    "checkpoint": "Checkpoint"
                }
                params["types"] = type_map.get(model_type, model_type)

            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.api_base}/models",
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            models = result.get("items", [])
            self.logger.info(f"モデル検索完了: {len(models)}件")
            return models

        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"query": query, "limit": limit, "action": "search_models"},
                user_message="モデルの検索に失敗しました"
            )
            self.logger.error(f"モデル検索エラー: {error.message}")
            return []

    def get_model_details(self, model_id: int) -> Optional[Dict[str, Any]]:
        """
        モデルの詳細情報を取得

        Args:
            model_id: モデルID

        Returns:
            モデル詳細情報（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None

        try:
            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.api_base}/models/{model_id}",
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"model_id": model_id, "action": "get_model_details"},
                user_message="モデル詳細の取得に失敗しました"
            )
            self.logger.error(f"モデル詳細取得エラー: {error.message}")
            return None

    def download_model(
        self,
        model_id: int,
        version_id: Optional[int] = None,
        download_path: Optional[str] = None
    ) -> Optional[str]:
        """
        モデルをダウンロード

        Args:
            model_id: モデルID
            version_id: バージョンID（オプション）
            download_path: ダウンロード先パス（オプション）

        Returns:
            ダウンロードしたファイルのパス（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None

        try:
            # モデル詳細を取得
            model_details = self.get_model_details(model_id)
            if not model_details:
                return None

            # バージョンを決定
            if not version_id:
                # 最新バージョンを使用
                versions = model_details.get("modelVersions", [])
                if not versions:
                    self.logger.warning("モデルバージョンが見つかりません")
                    return None
                version_id = versions[0].get("id")

            # ダウンロードURLを取得
            version_details = None
            for version in model_details.get("modelVersions", []):
                if version.get("id") == version_id:
                    version_details = version
                    break

            if not version_details:
                self.logger.warning(f"バージョン {version_id} が見つかりません")
                return None

            files = version_details.get("files", [])
            if not files:
                self.logger.warning("ダウンロード可能なファイルが見つかりません")
                return None

            download_url = files[0].get("downloadUrl")
            if not download_url:
                self.logger.warning("ダウンロードURLが見つかりません")
                return None

            # ダウンロード先を決定
            if not download_path:
                download_path = Path("./downloads") / f"model_{model_id}_v{version_id}.safetensors"
            else:
                download_path = Path(download_path)

            download_path.parent.mkdir(parents=True, exist_ok=True)

            # ダウンロード実行
            # downloadUrlは直接アクセス可能なURL（APIキーはセッションヘッダーに含まれている）
            timeout = self.get_timeout("file_download")
            # 新しいセッションを作成してダウンロード（元のセッションのヘッダーを継承）
            download_session = requests.Session()
            download_session.headers.update(self.session.headers)
            response = download_session.get(download_url, stream=True, timeout=timeout)
            response.raise_for_status()

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"モデルダウンロード完了: {download_path}")
            return str(download_path)

        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"model_id": model_id, "version_id": version_id, "action": "download_model"},
                user_message="モデルのダウンロードに失敗しました"
            )
            self.logger.error(f"モデルダウンロードエラー: {error.message}")
            return None

    def get_favorite_models(
        self,
        limit: int = 100,
        model_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        お気に入り（ブックマーク）したモデルを取得

        Args:
            limit: 取得数（最大100）
            model_type: モデルタイプ（Checkpoint, LoRA, etc.）

        Returns:
            お気に入りモデル情報のリスト
        """
        if not self.is_available():
            self.logger.warning("CivitAI統合が利用できません（APIキーが必要です）")
            return []

        if not self.api_key:
            self.logger.warning("お気に入りを取得するにはAPIキーが必要です")
            return []

        try:
            params = {
                "favorites": "true",
                "limit": min(limit, 100)  # 最大100件
            }

            if model_type:
                params["types"] = model_type

            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.api_base}/models",
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            models = result.get("items", [])
            self.logger.info(f"お気に入りモデル取得完了: {len(models)}件")
            return models

        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"limit": limit, "action": "get_favorite_models"},
                user_message="お気に入りモデルの取得に失敗しました"
            )
            self.logger.error(f"お気に入りモデル取得エラー: {error.message}")
            return []

    def get_images(
        self,
        limit: int = 20,
        model_id: Optional[int] = None,
        model_version_id: Optional[int] = None,
        username: Optional[str] = None,
        nsfw: Optional[bool] = None,
        sort: str = "Most Reactions",
        period: str = "AllTime",
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        画像を取得（プロンプト情報含む）

        Args:
            limit: 取得数（最大200）
            model_id: モデルIDでフィルタ
            model_version_id: モデルバージョンIDでフィルタ
            username: ユーザー名でフィルタ
            nsfw: NSFWフラグ
            sort: ソート方法（Most Reactions, Most Comments, Newest）
            period: 期間（AllTime, Year, Month, Week, Day）
            page: ページ番号

        Returns:
            画像情報のリスト（プロンプト、ネガティブプロンプト、モデル情報含む）
        """
        if not self.is_available():
            self.logger.warning("CivitAI統合が利用できません")
            return []

        try:
            params = {
                "limit": min(limit, 200),  # 最大200件
                "sort": sort,
                "period": period,
                "page": page
            }

            if model_id:
                params["modelId"] = model_id
            if model_version_id:
                params["modelVersionId"] = model_version_id
            if username:
                params["username"] = username
            if nsfw is not None:
                params["nsfw"] = str(nsfw).lower()

            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.api_base}/images",
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            images = result.get("items", [])
            self.logger.info(f"画像取得完了: {len(images)}件")
            return images

        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"limit": limit, "model_id": model_id, "action": "get_images"},
                user_message="画像の取得に失敗しました"
            )
            self.logger.error(f"画像取得エラー: {error.message}")
            return []

    def get_image_details(self, image_id: int) -> Optional[Dict[str, Any]]:
        """
        画像の詳細情報を取得（プロンプト情報含む）

        Args:
            image_id: 画像ID

        Returns:
            画像詳細情報（プロンプト、ネガティブプロンプト、モデル情報含む）
        """
        if not self.is_available():
            return None

        try:
            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.api_base}/images/{image_id}",
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"image_id": image_id, "action": "get_image_details"},
                user_message="画像詳細の取得に失敗しました"
            )
            self.logger.error(f"画像詳細取得エラー: {error.message}")
            return None

    def get_creators(
        self,
        username: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        クリエイター一覧を取得

        Args:
            username: ユーザー名でフィルタ
            limit: 取得数

        Returns:
            クリエイター情報のリスト
        """
        if not self.is_available():
            return []

        try:
            params = {"limit": limit}
            if username:
                params["username"] = username

            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.api_base}/creators",
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            creators = result.get("items", [])
            self.logger.info(f"クリエイター取得完了: {len(creators)}件")
            return creators

        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"username": username, "action": "get_creators"},
                user_message="クリエイターの取得に失敗しました"
            )
            self.logger.error(f"クリエイター取得エラー: {error.message}")
            return []
