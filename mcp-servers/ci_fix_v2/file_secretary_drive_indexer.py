#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📂 File Secretary - Google Drive Indexer
Google Drive INBOX監視とFileRecord作成
"""

import os
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from manaos_logger import get_logger, get_service_logger
from file_secretary_schemas import FileRecord, FileSource, FileStatus, FileType, AuditAction
from file_secretary_db import FileSecretaryDB

logger = get_service_logger("file-secretary-drive-indexer")

# Google Drive統合をインポート
try:
    from google_drive_integration import GoogleDriveIntegration
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    logger.warning("Google Drive統合モジュールが見つかりません")


class GoogleDriveIndexer:
    """Google Driveインデクサー"""
    
    def __init__(self, db: FileSecretaryDB, drive_folder_name: str = "INBOX"):
        """
        初期化
        
        Args:
            db: FileSecretaryDBインスタンス
            drive_folder_name: Google Drive内のINBOXフォルダ名
        """
        self.db = db
        self.drive_folder_name = drive_folder_name
        self.drive_integration = None
        self.drive_folder_id = None
        
        if GOOGLE_DRIVE_AVAILABLE:
            credentials_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS", "credentials.json")
            token_path = os.getenv("GOOGLE_DRIVE_TOKEN", "token.json")
            
            try:
                self.drive_integration = GoogleDriveIntegration(
                    credentials_path=credentials_path,
                    token_path=token_path
                )
                if self.drive_integration.is_available():
                    self.drive_folder_id = self._find_or_create_folder(drive_folder_name)
                    logger.info(f"✅ Google Drive統合初期化完了: {drive_folder_name}")
                else:
                    logger.warning("⚠️ Google Drive認証に失敗しました")
            except Exception as e:
                logger.error(f"❌ Google Drive統合初期化エラー: {e}")
    
    def _find_or_create_folder(self, folder_name: str) -> Optional[str]:
        """
        Google Driveフォルダを検索または作成
        
        Args:
            folder_name: フォルダ名
            
        Returns:
            フォルダIDまたはNone
        """
        if not self.drive_integration or not self.drive_integration.is_available():
            return None
        
        try:
            # 既存フォルダを検索
            service = self.drive_integration.service
            results = service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name)"
            ).execute()
            
            items = results.get('files', [])
            if items:
                return items[0]['id']
            
            # フォルダが存在しない場合は作成
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            logger.info(f"✅ Google Driveフォルダ作成: {folder_name} ({folder.get('id')})")
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"❌ Google Driveフォルダ検索/作成エラー: {e}")
            return None
    
    def _get_file_type_from_mime(self, mime_type: str) -> Optional[FileType]:
        """MIMEタイプからFileTypeを判定"""
        mime_lower = mime_type.lower()
        
        if 'pdf' in mime_lower:
            return FileType.PDF
        elif 'image' in mime_lower:
            return FileType.IMAGE
        elif 'spreadsheet' in mime_lower or 'excel' in mime_lower:
            return FileType.XLSX
        elif 'document' in mime_lower or 'word' in mime_lower:
            return FileType.DOCX
        elif 'text/plain' in mime_lower:
            return FileType.TXT
        elif 'markdown' in mime_lower:
            return FileType.MD
        else:
            return FileType.OTHER
    
    def _download_file(self, file_id: str) -> Optional[Path]:
        """
        Google Driveからファイルを一時ダウンロード
        
        Args:
            file_id: Google DriveファイルID
            
        Returns:
            一時ファイルパスまたはNone
        """
        if not self.drive_integration or not self.drive_integration.is_available():
            return None
        
        try:
            service = self.drive_integration.service
            
            # ファイルメタデータ取得
            file_metadata = service.files().get(fileId=file_id).execute()
            file_name = file_metadata.get('name', 'unknown')
            
            # 一時ファイルにダウンロード
            request = service.files().get_media(fileId=file_id)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix)
            temp_path = Path(temp_file.name)
            
            with open(temp_path, 'wb') as f:
                downloader = request
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.debug(f"ダウンロード進捗: {int(status.progress() * 100)}%")
            
            return temp_path
            
        except Exception as e:
            logger.error(f"❌ Google Driveファイルダウンロードエラー: {e}")
            return None
    
    def _calculate_hash_from_drive(self, file_id: str) -> Optional[str]:
        """
        Google Driveファイルのハッシュを計算（ダウンロードして）
        
        Args:
            file_id: Google DriveファイルID
            
        Returns:
            SHA256ハッシュまたはNone
        """
        temp_path = self._download_file(file_id)
        if not temp_path:
            return None
        
        try:
            sha256 = hashlib.sha256()
            with open(temp_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"❌ ハッシュ計算エラー: {e}")
            return None
        finally:
            # 一時ファイル削除
            if temp_path.exists():
                temp_path.unlink()
    
    def list_drive_files(self) -> List[Dict[str, Any]]:
        """
        Google Drive INBOXフォルダ内のファイル一覧を取得
        
        Returns:
            ファイル情報リスト
        """
        if not self.drive_integration or not self.drive_integration.is_available() or not self.drive_folder_id:
            return []
        
        try:
            service = self.drive_integration.service
            
            # フォルダ内のファイルを検索
            query = f"'{self.drive_folder_id}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime)",
                orderBy="createdTime desc"
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append({
                    'id': item['id'],
                    'name': item['name'],
                    'mime_type': item.get('mimeType', ''),
                    'size': int(item.get('size', 0)),
                    'created_time': item.get('createdTime', ''),
                    'modified_time': item.get('modifiedTime', '')
                })
            
            return files
            
        except Exception as e:
            logger.error(f"❌ Google Driveファイル一覧取得エラー: {e}")
            return []
    
    def index_drive_file(self, file_id: str, force: bool = False) -> Optional[FileRecord]:
        """
        Google Driveファイルをインデックス
        
        Args:
            file_id: Google DriveファイルID
            force: 強制再インデックス
            
        Returns:
            FileRecordまたはNone
        """
        if not self.drive_integration or not self.drive_integration.is_available():
            return None
        
        try:
            service = self.drive_integration.service
            
            # ファイルメタデータ取得
            file_metadata = service.files().get(fileId=file_id).execute()
            file_name = file_metadata.get('name', 'unknown')
            mime_type = file_metadata.get('mimeType', '')
            size = int(file_metadata.get('size', 0))
            created_time = file_metadata.get('createdTime', '')
            modified_time = file_metadata.get('modifiedTime', '')
            
            # ハッシュ計算（重複検知用）
            file_hash = self._calculate_hash_from_drive(file_id)
            if not file_hash:
                return None
            
            # 既存レコードをチェック
            existing = self.db.get_file_record(file_hash)
            if existing and not force:
                logger.info(f"⏭️ 既存ファイルをスキップ: {file_name}")
                return existing
            
            # 日時変換
            try:
                created_dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                created_at = created_dt.isoformat()
            except Exception:
                created_at = datetime.now().isoformat()
            
            try:
                modified_dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                modified_at = modified_dt.isoformat()
            except Exception:
                modified_at = None
            
            # FileRecord作成
            file_record = FileRecord(
                id=file_hash,
                source=FileSource.DRIVE,
                path=f"gdrive://{file_id}",  # Google Driveの仮想パス
                original_name=file_name,
                created_at=created_at,
                status=FileStatus.TRIAGED,
                modified_at=modified_at,
                file_created_at=created_at,
                type=self._get_file_type_from_mime(mime_type),
                size=size,
                hash=file_hash,
                tags=[],
                alias_name=None,
                summary=None,
                ocr_text_ref=None,
                thread_ref=None,
                audit_log=[],
                metadata={
                    "drive_file_id": file_id,
                    "drive_mime_type": mime_type
                }
            )
            
            # 監査ログ追加
            file_record.add_audit_log(
                AuditAction.CREATED,
                user="system",
                details={"source": "google_drive", "file_id": file_id}
            )
            
            # データベースに保存
            if self.db.create_file_record(file_record):
                logger.info(f"✅ Google Driveファイルインデックス完了: {file_name} ({file_record.id[:8]}...)")
                return file_record
            else:
                logger.error(f"❌ Google Driveファイルインデックス失敗: {file_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Google Driveファイルインデックスエラー: {file_id} - {e}")
            return None
    
    def index_drive_folder(self) -> int:
        """
        Google Drive INBOXフォルダ内の全ファイルをインデックス
        
        Returns:
            インデックスしたファイル数
        """
        files = self.list_drive_files()
        count = 0
        
        for file_info in files:
            if self.index_drive_file(file_info['id']):
                count += 1
        
        logger.info(f"✅ Google Driveフォルダインデックス完了: {count}件")
        return count
    
    def watch_drive_folder(self, interval_seconds: int = 300):
        """
        Google Driveフォルダを定期監視（ポーリング）
        
        Args:
            interval_seconds: 監視間隔（秒）
        """
        import time
        
        logger.info(f"👀 Google Drive監視開始: {self.drive_folder_name} (間隔: {interval_seconds}秒)")
        
        last_file_ids = set()
        
        try:
            while True:
                # 現在のファイル一覧取得
                current_files = self.list_drive_files()
                current_file_ids = {f['id'] for f in current_files}
                
                # 新規ファイルを検出
                new_file_ids = current_file_ids - last_file_ids
                for file_id in new_file_ids:
                    file_info = next((f for f in current_files if f['id'] == file_id), None)
                    if file_info:
                        logger.info(f"📄 新規ファイル検出: {file_info['name']}")
                        self.index_drive_file(file_id)
                
                last_file_ids = current_file_ids
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Google Drive監視停止")






















