#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📂 File Secretary - Indexer Worker
ファイル監視とFileRecord作成
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from manaos_logger import get_logger
from file_secretary_schemas import FileRecord, FileSource, FileStatus, FileType, AuditAction
from file_secretary_db import FileSecretaryDB

logger = get_logger(__name__)


class FileIndexerHandler(FileSystemEventHandler):
    """ファイル監視ハンドラー"""
    
    def __init__(self, indexer: "FileIndexer"):
        """
        初期化
        
        Args:
            indexer: FileIndexerインスタンス
        """
        self.indexer = indexer
        self.debounce_time = 2.0  # 2秒のデバウンス
        self.pending_files = {}
    
    def on_created(self, event):
        """ファイル作成時の処理"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.is_file():
            self._handle_file(file_path)
    
    def on_modified(self, event):
        """ファイル変更時の処理"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.is_file():
            # 作成イベントと区別するため、少し待つ
            import time
            time.sleep(0.5)
            self._handle_file(file_path)
    
    def _handle_file(self, file_path: Path):
        """ファイルを処理"""
        try:
            # デバウンス処理
            current_time = datetime.now().timestamp()
            if file_path in self.pending_files:
                last_time = self.pending_files[file_path]
                if current_time - last_time < self.debounce_time:
                    return
            
            self.pending_files[file_path] = current_time
            
            # ファイルが完全に書き込まれるまで待つ
            import time
            time.sleep(1)
            
            if file_path.exists() and file_path.is_file():
                self.indexer.index_file(file_path)
        except Exception as e:
            logger.error(f"❌ ファイル処理エラー: {file_path} - {e}")


class FileIndexer:
    """ファイルインデクサー"""
    
    def __init__(self, db: FileSecretaryDB, source: FileSource, watch_path: str):
        """
        初期化
        
        Args:
            db: FileSecretaryDBインスタンス
            source: ファイルソース
            watch_path: 監視パス
        """
        self.db = db
        self.source = source
        self.watch_path = Path(watch_path)
        self.observer = None
        
        if not self.watch_path.exists():
            logger.warning(f"⚠️ 監視パスが存在しません: {self.watch_path}")
            self.watch_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_type(self, file_path: Path) -> Optional[FileType]:
        """ファイルタイプを判定"""
        ext = file_path.suffix.lower()
        
        type_map = {
            ".pdf": FileType.PDF,
            ".png": FileType.IMAGE,
            ".jpg": FileType.IMAGE,
            ".jpeg": FileType.IMAGE,
            ".gif": FileType.IMAGE,
            ".xlsx": FileType.XLSX,
            ".xls": FileType.XLSX,
            ".docx": FileType.DOCX,
            ".doc": FileType.DOCX,
            ".md": FileType.MD,
            ".txt": FileType.TXT
        }
        
        return type_map.get(ext, FileType.OTHER)
    
    def _calculate_hash(self, file_path: Path) -> Optional[str]:
        """ファイルのSHA256ハッシュを計算"""
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"❌ ハッシュ計算エラー: {file_path} - {e}")
            return None
    
    def _get_file_stats(self, file_path: Path) -> Dict[str, Any]:
        """ファイル統計情報を取得"""
        try:
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "file_created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
        except Exception as e:
            logger.error(f"❌ ファイル統計取得エラー: {file_path} - {e}")
            return {
                "size": None,
                "modified_at": None,
                "file_created_at": None
            }
    
    def index_file(self, file_path: Path, force: bool = False) -> Optional[FileRecord]:
        """
        ファイルをインデックス
        
        Args:
            file_path: ファイルパス
            force: 強制再インデックス
            
        Returns:
            FileRecordまたはNone
        """
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            
            # ハッシュ計算
            file_hash = self._calculate_hash(file_path)
            if not file_hash:
                return None
            
            # 既存レコードをチェック（重複検知）
            existing = self.db.get_file_record(file_hash)
            if existing and not force:
                logger.info(f"⏭️ 既存ファイルをスキップ: {file_path.name}")
                return existing
            
            # ファイル統計情報
            stats = self._get_file_stats(file_path)
            
            # FileRecord作成
            file_record = FileRecord(
                id=file_hash,  # ハッシュをIDとして使用
                source=self.source,
                path=str(file_path.absolute()),
                original_name=file_path.name,
                created_at=datetime.now().isoformat(),
                status=FileStatus.TRIAGED,  # 自動でtriagedに
                modified_at=stats.get("modified_at"),
                file_created_at=stats.get("file_created_at"),
                type=self._get_file_type(file_path),
                size=stats.get("size"),
                hash=file_hash,
                tags=[],
                alias_name=None,
                summary=None,
                ocr_text_ref=None,
                thread_ref=None,
                audit_log=[],
                metadata={}
            )
            
            # 監査ログ追加
            file_record.add_audit_log(
                AuditAction.CREATED,
                user="system",
                details={"path": str(file_path)}
            )
            
            # データベースに保存
            if self.db.create_file_record(file_record):
                logger.info(f"✅ ファイルインデックス完了: {file_path.name} ({file_record.id[:8]}...)")
                return file_record
            else:
                logger.error(f"❌ ファイルインデックス失敗: {file_path.name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ ファイルインデックスエラー: {file_path} - {e}")
            return None
    
    def index_directory(self, directory: Optional[Path] = None, recursive: bool = True) -> int:
        """
        ディレクトリ内のファイルを一括インデックス
        
        Args:
            directory: ディレクトリパス（Noneの場合はwatch_path）
            recursive: 再帰的に処理するか
            
        Returns:
            インデックスしたファイル数
        """
        target_dir = directory or self.watch_path
        
        if not target_dir.exists():
            logger.warning(f"⚠️ ディレクトリが存在しません: {target_dir}")
            return 0
        
        count = 0
        pattern = "**/*" if recursive else "*"
        
        for file_path in target_dir.glob(pattern):
            if file_path.is_file():
                if self.index_file(file_path):
                    count += 1
        
        logger.info(f"✅ ディレクトリインデックス完了: {count}件")
        return count
    
    def start_watching(self):
        """ファイル監視を開始"""
        if self.observer:
            logger.warning("⚠️ 既に監視中です")
            return
        
        logger.info(f"👀 ファイル監視開始: {self.watch_path}")
        
        self.observer = Observer()
        handler = FileIndexerHandler(self)
        self.observer.schedule(handler, str(self.watch_path), recursive=True)
        self.observer.start()
    
    def stop_watching(self):
        """ファイル監視を停止"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("✅ ファイル監視停止")


