"""
Google Drive API統合モジュール（改善版）
バックアップ自動化とファイル管理
ベースクラスを使用して統一モジュールを活用
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
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

# ベースクラスのインポート
from base_integration import BaseIntegration


class GoogleDriveIntegration(BaseIntegration):
    """Google Drive統合クラス（改善版）"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        """
        初期化
        
        Args:
            credentials_path: 認証情報ファイルのパス
            token_path: トークンファイルのパス
        """
        super().__init__("GoogleDrive")
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service = None
        self.creds = None
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not GOOGLE_DRIVE_AVAILABLE:
            self.logger.warning("Google Drive APIライブラリがインストールされていません")
            return False
        
        return self._authenticate()
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return GOOGLE_DRIVE_AVAILABLE and self.service is not None
    
    def _authenticate(self) -> bool:
        """
        認証を実行
        
        Returns:
            認証成功時True
        """
        if not GOOGLE_DRIVE_AVAILABLE:
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
                        error_msg = f"認証情報ファイルが見つかりません: {self.credentials_path}"
                        self.logger.warning(error_msg)
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(  # type: ignore[possibly-unbound]
                        str(self.credentials_path), self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            
            # サービスを構築
            self.service = build('drive', 'v3', credentials=self.creds)  # type: ignore[possibly-unbound]
            self.logger.info("Google Drive認証が完了しました")
            return True
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"credentials_path": str(self.credentials_path), "action": "authenticate"},
                user_message="Google Driveの認証に失敗しました"
            )
            self.logger.error(f"認証エラー: {error.message}")
            return False
    
    def upload_file(
        self,
        file_path: str,
        folder_id: Optional[str] = None,
        file_name: Optional[str] = None
    ) -> Optional[str]:
        """
        ファイルをアップロード
        
        Args:
            file_path: アップロードするファイルのパス
            folder_id: フォルダID（オプション）
            file_name: ファイル名（オプション、デフォルトは元のファイル名）
            
        Returns:
            ファイルID（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                self.logger.warning(f"ファイルが見つかりません: {file_path}")
                return None
            
            file_metadata = {
                'name': file_name or file_path_obj.name
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]  # type: ignore
            
            media = MediaFileUpload(  # type: ignore[possibly-unbound]
                str(file_path_obj),
                resumable=True
            )
            
            timeout = self.get_timeout("file_upload")
            file = self.service.files().create(  # type: ignore[union-attr]
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute(timeout=timeout)
            
            self.logger.info(f"ファイルアップロード完了: {file_path_obj.name} (ID: {file.get('id')})")
            return file.get('id')
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"file_path": file_path, "action": "upload_file"},
                user_message="ファイルのアップロードに失敗しました"
            )
            self.logger.error(f"アップロードエラー: {error.message}")
            return None
    
    def list_files(self, folder_id: Optional[str] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        ファイル一覧を取得
        
        Args:
            folder_id: フォルダID（オプション）
            max_results: 最大取得数
            
        Returns:
            ファイル情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            query = "trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            timeout = self.get_timeout("api_call")
            results = self.service.files().list(  # type: ignore[union-attr]
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute(timeout=timeout)
            
            return results.get('files', [])
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"folder_id": folder_id, "action": "list_files"},
                user_message="ファイル一覧の取得に失敗しました"
            )
            self.logger.error(f"ファイル一覧取得エラー: {error.message}")
            return []






















