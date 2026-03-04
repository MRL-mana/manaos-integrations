#!/usr/bin/env python3
"""
Google Drive連携ヘルパー
スクリーンショット・録画の自動アップロード
"""

import os
import logging
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

# Google Drive APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveHelper:
    def __init__(self, credentials_path='/root/credentials.json', token_path='/root/token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.folder_id = None
        
    def authenticate(self):
        """Google Drive認証"""
        creds = None
        
        # トークンファイルが存在する場合は読み込む
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.error(f"Token load error: {e}")
        
        # 認証情報が無効または存在しない場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Token refresh error: {e}")
                    return False
            else:
                # 認証フローは手動で実行する必要がある
                logger.warning("Google Drive credentials not found or invalid")
                return False
        
        # サービスを構築
        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Google Drive認証成功")
            return True
        except Exception as e:
            logger.error(f"Google Drive service build error: {e}")
            return False
    
    def create_folder_if_not_exists(self, folder_name='ManaOS Screenshots'):
        """フォルダが存在しない場合は作成"""
        if not self.service:
            return None
        
        try:
            # フォルダを検索
            results = self.service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                self.folder_id = items[0]['id']
                logger.info(f"既存フォルダを使用: {folder_name} (ID: {self.folder_id})")
                return self.folder_id
            
            # フォルダを作成
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            self.folder_id = folder.get('id')
            logger.info(f"新しいフォルダを作成: {folder_name} (ID: {self.folder_id})")
            return self.folder_id
            
        except Exception as e:
            logger.error(f"Folder creation error: {e}")
            return None
    
    def upload_file(self, file_path, folder_id=None, description=''):
        """ファイルをGoogle Driveにアップロード"""
        if not self.service:
            logger.warning("Google Drive service not initialized")
            return None
        
        try:
            filename = os.path.basename(file_path)
            
            file_metadata = {
                'name': filename,
                'description': description or f'Uploaded from ManaOS at {datetime.now().isoformat()}'
            }
            
            # フォルダIDが指定されている場合
            if folder_id or self.folder_id:
                file_metadata['parents'] = [folder_id or self.folder_id]
            
            # MIMEタイプを推測
            if file_path.endswith('.png') or file_path.endswith('.jpg'):
                mimetype = 'image/png' if file_path.endswith('.png') else 'image/jpeg'
            elif file_path.endswith('.mp4'):
                mimetype = 'video/mp4'
            else:
                mimetype = 'application/octet-stream'
            
            media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            logger.info(f"✅ Google Driveにアップロード完了: {filename} (ID: {file.get('id')})")
            
            return {
                'id': file.get('id'),
                'name': file.get('name'),
                'link': file.get('webViewLink')
            }
            
        except Exception as e:
            logger.error(f"File upload error: {e}")
            return None
    
    def upload_screenshot(self, file_path):
        """スクリーンショットをアップロード"""
        # スクリーンショット用フォルダを確保
        if not self.folder_id:
            self.create_folder_if_not_exists('ManaOS Screenshots')
        
        return self.upload_file(
            file_path,
            description=f'Screenshot taken at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )
    
    def upload_recording(self, file_path):
        """録画をアップロード"""
        # 録画用フォルダを確保
        if not self.folder_id:
            self.create_folder_if_not_exists('ManaOS Recordings')
        
        return self.upload_file(
            file_path,
            description=f'Screen recording from {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )

# グローバルインスタンス
drive_helper = GoogleDriveHelper()

