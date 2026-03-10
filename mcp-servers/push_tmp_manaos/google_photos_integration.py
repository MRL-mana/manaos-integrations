"""
Google Photos API統合モジュール
Google Photosへのアクセスと画像管理
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_PHOTOS_AVAILABLE = True
except ImportError:
    GOOGLE_PHOTOS_AVAILABLE = False
    print("Google Photos APIライブラリがインストールされていません。")
    print("インストール: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


class GooglePhotosIntegration:
    """Google Photos統合クラス"""
    
    # Google Photos Library APIのスコープ
    SCOPES = [
        'https://www.googleapis.com/auth/photoslibrary.readonly',
        'https://www.googleapis.com/auth/photoslibrary.appendonly',
        'https://www.googleapis.com/auth/photoslibrary.sharing'
    ]
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token_photos.json"):
        """
        初期化
        
        Args:
            credentials_path: 認証情報ファイルのパス
            token_path: トークンファイルのパス
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service = None
        self.creds = None
        
        if GOOGLE_PHOTOS_AVAILABLE:
            self._authenticate()
    
    def _authenticate(self) -> bool:
        """
        認証を実行
        
        Returns:
            認証成功時True
        """
        if not GOOGLE_PHOTOS_AVAILABLE:
            return False
        
        try:
            # 既存のトークンを確認
            if self.token_path.exists():
                self.creds = Credentials.from_authorized_user_file(  # type: ignore[possibly-unbound]
                    str(self.token_path), self.SCOPES
                )
            
            # トークンが無効または存在しない場合、再認証
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())  # type: ignore[possibly-unbound]
                else:
                    if not self.credentials_path.exists():
                        print(f"認証情報ファイルが見つかりません: {self.credentials_path}")
                        print("Google Cloud Consoleから認証情報をダウンロードしてください。")
                        print("Google Photos Library APIを有効にする必要があります。")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(  # type: ignore[possibly-unbound]
                        str(self.credentials_path), self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            
            # サービスを構築
            self.service = build('photoslibrary', 'v1', credentials=self.creds, static_discovery=False)  # type: ignore[possibly-unbound]
            return True
            
        except Exception as e:
            print(f"認証エラー: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Google Photosが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        return GOOGLE_PHOTOS_AVAILABLE and self.service is not None
    
    def list_media_items(
        self,
        page_size: int = 25,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        メディアアイテム（写真・動画）の一覧を取得
        
        Args:
            page_size: 1ページあたりの取得数（最大100）
            page_token: ページネーショントークン
        
        Returns:
            メディアアイテムのリストとページトークン
        """
        if not self.is_available():
            return {'mediaItems': [], 'nextPageToken': None}
        
        try:
            body = {
                'pageSize': min(page_size, 100),
            }
            if page_token:
                body['pageToken'] = page_token  # type: ignore
            
            response = self.service.mediaItems().list(**body).execute()  # type: ignore[union-attr]
            return response
            
        except HttpError as e:  # type: ignore[possibly-unbound]
            print(f"メディアアイテム取得エラー: {e}")
            return {'mediaItems': [], 'nextPageToken': None}
    
    def get_all_media_items(self, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        すべてのメディアアイテムを取得
        
        Args:
            max_items: 最大取得数（Noneで全件）
        
        Returns:
            メディアアイテムのリスト
        """
        if not self.is_available():
            return []
        
        all_items = []
        page_token = None
        
        while True:
            response = self.list_media_items(page_size=100, page_token=page_token)
            items = response.get('mediaItems', [])
            all_items.extend(items)
            
            if max_items and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                break
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        
        return all_items
    
    def search_media_items(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page_size: int = 25,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        メディアアイテムを検索
        
        Args:
            filters: フィルター条件（日付範囲、メディアタイプなど）
            page_size: 1ページあたりの取得数
            page_token: ページネーショントークン
        
        Returns:
            検索結果
        """
        if not self.is_available():
            return {'mediaItems': [], 'nextPageToken': None}
        
        try:
            body = {
                'pageSize': min(page_size, 100),
            }
            if filters:
                body['filters'] = filters  # type: ignore
            if page_token:
                body['pageToken'] = page_token  # type: ignore
            
            response = self.service.mediaItems().search(body=body).execute()  # type: ignore[union-attr]
            return response
            
        except HttpError as e:  # type: ignore[possibly-unbound]
            print(f"検索エラー: {e}")
            return {'mediaItems': [], 'nextPageToken': None}
    
    def get_media_item(self, media_item_id: str) -> Optional[Dict[str, Any]]:
        """
        特定のメディアアイテムを取得
        
        Args:
            media_item_id: メディアアイテムID
        
        Returns:
            メディアアイテム情報
        """
        if not self.is_available():
            return None
        
        try:
            response = self.service.mediaItems().get(mediaItemId=media_item_id).execute()  # type: ignore[union-attr]
            return response
        except HttpError as e:  # type: ignore[possibly-unbound]
            print(f"メディアアイテム取得エラー: {e}")
            return None
    
    def list_albums(
        self,
        page_size: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        アルバム一覧を取得
        
        Args:
            page_size: 1ページあたりの取得数
            page_token: ページネーショントークン
        
        Returns:
            アルバムのリスト
        """
        if not self.is_available():
            return {'albums': [], 'nextPageToken': None}
        
        try:
            body = {
                'pageSize': min(page_size, 50),
            }
            if page_token:
                body['pageToken'] = page_token  # type: ignore
            
            response = self.service.albums().list(**body).execute()  # type: ignore[union-attr]
            return response
            
        except HttpError as e:  # type: ignore[possibly-unbound]
            print(f"アルバム取得エラー: {e}")
            return {'albums': [], 'nextPageToken': None}
    
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """
        特定のアルバムを取得
        
        Args:
            album_id: アルバムID
        
        Returns:
            アルバム情報
        """
        if not self.is_available():
            return None
        
        try:
            response = self.service.albums().get(albumId=album_id).execute()  # type: ignore[union-attr]
            return response
        except HttpError as e:  # type: ignore[possibly-unbound]
            print(f"アルバム取得エラー: {e}")
            return None
    
    def get_album_media_items(
        self,
        album_id: str,
        page_size: int = 25,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        アルバム内のメディアアイテムを取得
        
        Args:
            album_id: アルバムID
            page_size: 1ページあたりの取得数
            page_token: ページネーショントークン
        
        Returns:
            メディアアイテムのリスト
        """
        if not self.is_available():
            return {'mediaItems': [], 'nextPageToken': None}
        
        try:
            body = {
                'albumId': album_id,
                'pageSize': min(page_size, 100),
            }
            if page_token:
                body['pageToken'] = page_token
            
            response = self.service.mediaItems().search(body=body).execute()  # type: ignore[union-attr]
            return response
            
        except HttpError as e:  # type: ignore[possibly-unbound]
            print(f"アルバムメディア取得エラー: {e}")
            return {'mediaItems': [], 'nextPageToken': None}


def main():
    """テスト用メイン関数"""
    photos = GooglePhotosIntegration()
    
    if not photos.is_available():
        print("Google Photos APIが利用できません。")
        print("認証情報ファイルを設定してください。")
        print("\n設定手順:")
        print("1. Google Cloud Consoleでプロジェクトを作成")
        print("2. Google Photos Library APIを有効化")
        print("3. OAuth 2.0認証情報を作成（デスクトップアプリ）")
        print("4. credentials.jsonをダウンロードして配置")
        return
    
    print("Google Photos統合テスト")
    print("=" * 50)
    
    # アルバム一覧を取得
    print("\nアルバム一覧:")
    albums_response = photos.list_albums(page_size=10)
    albums = albums_response.get('albums', [])
    print(f"アルバム数: {len(albums)}")
    for album in albums[:5]:
        print(f"  - {album.get('title')} ({album.get('id')})")
    
    # 最近のメディアアイテムを取得
    print("\n最近のメディアアイテム:")
    media_response = photos.list_media_items(page_size=10)
    media_items = media_response.get('mediaItems', [])
    print(f"メディア数: {len(media_items)}")
    for item in media_items[:5]:
        filename = item.get('filename', 'Unknown')
        mime_type = item.get('mimeType', 'Unknown')
        print(f"  - {filename} ({mime_type})")


if __name__ == "__main__":
    main()


















