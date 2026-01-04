"""
Google Drive API統合モジュール
バックアップ自動化とファイル管理
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
    print("Google Drive APIライブラリがインストールされていません。")
    print("インストール: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


class GoogleDriveIntegration:
    """Google Drive統合クラス"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
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
        
        if GOOGLE_DRIVE_AVAILABLE:
            self._authenticate()
    
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
                self.creds = Credentials.from_authorized_user_file(
                    str(self.token_path), self.SCOPES
                )
            
            # トークンが無効または存在しない場合、再認証
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        print(f"認証情報ファイルが見つかりません: {self.credentials_path}")
                        print("Google Cloud Consoleから認証情報をダウンロードしてください。")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            
            # サービスを構築
            self.service = build('drive', 'v3', credentials=self.creds)
            return True
            
        except Exception as e:
            print(f"認証エラー: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Google Driveが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        return GOOGLE_DRIVE_AVAILABLE and self.service is not None
    
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
            folder_id: アップロード先フォルダID（オプション）
            file_name: アップロード後のファイル名（オプション）
            
        Returns:
            ファイルID（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                print(f"ファイルが見つかりません: {file_path}")
                return None
            
            file_metadata = {
                'name': file_name or file_path_obj.name
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(
                str(file_path_obj),
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            print(f"アップロード完了: {file.get('id')}")
            return file.get('id')
            
        except HttpError as e:
            print(f"アップロードエラー: {e}")
            return None
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        フォルダを作成
        
        Args:
            folder_name: フォルダ名
            parent_folder_id: 親フォルダID（オプション）
            
        Returns:
            フォルダID（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            file = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            print(f"フォルダ作成完了: {file.get('id')}")
            return file.get('id')
            
        except HttpError as e:
            print(f"フォルダ作成エラー: {e}")
            return None
    
    def list_files(self, folder_id: Optional[str] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        ファイル一覧を取得
        
        Args:
            folder_id: フォルダID（オプション、Noneでルート）
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
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as e:
            print(f"ファイル一覧取得エラー: {e}")
            return []
    
    def backup_directory(
        self,
        local_dir: str,
        drive_folder_name: str = "ManaOS_Backup",
        parent_folder_id: Optional[str] = None
    ) -> bool:
        """
        ディレクトリをバックアップ
        
        Args:
            local_dir: バックアップするローカルディレクトリ
            drive_folder_name: Drive上のフォルダ名
            parent_folder_id: 親フォルダID（オプション）
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            # バックアップフォルダを作成（日時付き）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder_name = f"{drive_folder_name}_{timestamp}"
            backup_folder_id = self.create_folder(backup_folder_name, parent_folder_id)
            
            if not backup_folder_id:
                return False
            
            # ファイルをアップロード
            local_path = Path(local_dir)
            uploaded_count = 0
            
            for file_path in local_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(local_path)
                    print(f"アップロード中: {relative_path}")
                    
                    file_id = self.upload_file(str(file_path), backup_folder_id)
                    if file_id:
                        uploaded_count += 1
            
            print(f"バックアップ完了: {uploaded_count}ファイル")
            return True
            
        except Exception as e:
            print(f"バックアップエラー: {e}")
            return False


def main():
    """テスト用メイン関数"""
    drive = GoogleDriveIntegration()
    
    if not drive.is_available():
        print("Google Drive APIが利用できません。")
        print("認証情報ファイルを設定してください。")
        return
    
    print("Google Drive統合テスト")
    print("=" * 50)
    
    # ファイル一覧を取得
    files = drive.list_files(max_results=10)
    print(f"\nファイル数: {len(files)}")
    for file in files[:5]:
        print(f"  - {file.get('name')} ({file.get('id')})")


if __name__ == "__main__":
    main()





















