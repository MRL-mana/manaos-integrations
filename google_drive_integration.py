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
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    import io
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    MediaIoBaseDownload = None
    io = None

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
                self.creds = Credentials.from_authorized_user_file(
                    str(self.token_path), self.SCOPES
                )
            
            # トークンが無効または存在しない場合、再認証
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        error_msg = f"認証情報ファイルが見つかりません: {self.credentials_path}"
                        self.logger.warning(error_msg)
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
        file_name: Optional[str] = None,
        overwrite: bool = False
    ) -> Optional[str]:
        """
        ファイルをアップロード
        
        Args:
            file_path: アップロードするファイルのパス
            folder_id: フォルダIDまたはパス（オプション）
            file_name: ファイル名（オプション、デフォルトは元のファイル名）
            overwrite: 上書きするかどうか
            
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
            
            final_name = file_name or file_path_obj.name
            
            # フォルダIDがパスの場合は解決
            target_folder_id = folder_id
            if folder_id and "/" in folder_id:
                target_folder_id = self._resolve_path_to_id(folder_id)
            
            # 上書きチェック
            if overwrite and target_folder_id:
                query = f"name='{final_name}' and '{target_folder_id}' in parents and trashed=false"
                results = self.service.files().list(q=query, fields="files(id)").execute()
                existing_files = results.get('files', [])
                
                if existing_files:
                    # 既存ファイルを更新
                    file_id = existing_files[0]['id']
                    media = MediaFileUpload(str(file_path_obj), resumable=True)
                    updated_file = self.service.files().update(
                        fileId=file_id,
                        media_body=media,
                        fields='id'
                    ).execute()
                    self.logger.info(f"ファイル更新完了: {final_name} (ID: {file_id})")
                    return file_id

            file_metadata = {
                'name': final_name
            }
            
            if target_folder_id:
                file_metadata['parents'] = [target_folder_id]
            
            media = MediaFileUpload(
                str(file_path_obj),
                resumable=True
            )
            
            timeout = self.get_timeout("file_upload")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            self.logger.info(f"ファイルアップロード完了: {final_name} (ID: {file.get('id')})")
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
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"folder_id": folder_id, "action": "list_files"},
                user_message="ファイル一覧の取得に失敗しました"
            )
            self.logger.error(f"ファイル一覧取得エラー: {error.message}")
            return []


    def download_file(
        self,
        file_id: str,
        output_path: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Optional[str]:
        """
        ファイルをダウンロード
        
        Args:
            file_id: ファイルIDまたはGoogle Drive URL
            output_path: 保存先パス（オプション、デフォルトはファイル名）
            mime_type: MIMEタイプ（オプション、PDFエクスポートなどに使用）
            
        Returns:
            保存先パス（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            # URLからファイルIDを抽出
            if "/" in file_id:
                # Google Drive URLの場合
                if "drive.google.com" in file_id:
                    if "/file/d/" in file_id:
                        file_id = file_id.split("/file/d/")[1].split("/")[0]
                    elif "id=" in file_id:
                        file_id = file_id.split("id=")[1].split("&")[0]
            
            # ファイル情報を取得
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType'
            ).execute()
            
            file_name = file_metadata.get('name', 'downloaded_file')
            file_mime_type = file_metadata.get('mimeType', '')
            
            # 出力パスを決定
            if output_path:
                output_file = Path(output_path)
            else:
                output_file = Path(file_name)
            
            # Google Workspaceファイル（Google Docs、Sheets、Slidesなど）の場合はエクスポート
            if file_mime_type.startswith('application/vnd.google-apps.'):
                export_mime_type = mime_type
                if not export_mime_type:
                    # デフォルトのエクスポート形式を決定
                    if 'document' in file_mime_type:
                        export_mime_type = 'application/pdf'
                        if not output_file.suffix:
                            output_file = output_file.with_suffix('.pdf')
                    elif 'spreadsheet' in file_mime_type:
                        export_mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        if not output_file.suffix:
                            output_file = output_file.with_suffix('.xlsx')
                    elif 'presentation' in file_mime_type:
                        export_mime_type = 'application/pdf'
                        if not output_file.suffix:
                            output_file = output_file.with_suffix('.pdf')
                    else:
                        export_mime_type = 'application/pdf'
                
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType=export_mime_type
                )
            else:
                # 通常のファイルは直接ダウンロード
                request = self.service.files().get_media(fileId=file_id)
            
            # ファイルをダウンロード
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        self.logger.debug(f"ダウンロード進捗: {int(status.progress() * 100)}%")
            
            self.logger.info(f"ファイルダウンロード完了: {file_name} -> {output_file}")
            return str(output_file)
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"file_id": file_id, "action": "download_file"},
                user_message="ファイルのダウンロードに失敗しました"
            )
            self.logger.error(f"ダウンロードエラー: {error.message}")
            return None
    

    def _resolve_path_to_id(self, path_str: str) -> Optional[str]:
        """パス文字列をフォルダIDに解決（存在しない場合は作成）"""
        if not self.is_available():
            return None
            
        try:
            parts = path_str.strip("/").split("/")
            parent_id = 'root'
            
            for part in parts:
                if not part: continue
                
                # フォルダを検索
                query = f"mimeType='application/vnd.google-apps.folder' and name='{part}' and '{parent_id}' in parents and trashed=false"
                results = self.service.files().list(q=query, fields="files(id)").execute()
                files = results.get('files', [])
                
                if not files:
                    # 作成
                    metadata = {
                        'name': part,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [parent_id]
                    }
                    created = self.service.files().create(body=metadata, fields='id').execute()
                    parent_id = created.get('id')
                else:
                    parent_id = files[0]['id']
            
            return parent_id
            
        except Exception as e:
            self.logger.error(f"パス解決エラー ({path_str}): {e}")
            return None
