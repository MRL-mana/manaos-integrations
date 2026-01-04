#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ File Secretary - データベース管理
SQLiteスキーマとCRUD操作
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from manaos_logger import get_logger
from file_secretary_schemas import FileRecord, FileSource, FileStatus, FileType, AuditLogEntry, AuditAction

logger = get_logger(__name__)


class FileSecretaryDB:
    """ファイル秘書データベース"""
    
    def __init__(self, db_path: str = "file_secretary.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
        """
        self.db_path = Path(db_path)
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """データベース初期化"""
        # タイムアウト設定（データベースロック対策）
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        # WALモード有効化（同時アクセス改善）
        self.conn.execute("PRAGMA journal_mode=WAL")
        
        cursor = self.conn.cursor()
        
        # FileRecordテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_records (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL CHECK(source IN ('mother', 'drive', 'x280')),
                path TEXT NOT NULL,
                original_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT,
                file_created_at TEXT,
                type TEXT CHECK(type IN ('pdf', 'image', 'xlsx', 'docx', 'md', 'txt', 'other')),
                size INTEGER,
                hash TEXT,
                status TEXT NOT NULL CHECK(status IN ('inbox', 'triaged', 'done', 'archived')),
                tags TEXT,
                alias_name TEXT,
                summary TEXT,
                ocr_text_ref TEXT,
                thread_ref TEXT,
                audit_log TEXT,
                metadata TEXT,
                created_at_db TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at_db TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # インデックス
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_records_source ON file_records(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_records_status ON file_records(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_records_thread_ref ON file_records(thread_ref)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_records_hash ON file_records(hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_records_created_at ON file_records(created_at)")
        
        # 全文検索用（FTS5）
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS file_records_fts USING fts5(
                id UNINDEXED,
                original_name,
                alias_name,
                summary,
                tags,
                content='file_records',
                content_rowid='rowid'
            )
        """)
        
        self.conn.commit()
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def create_file_record(self, file_record: FileRecord) -> bool:
        """
        ファイルレコードを作成
        
        Args:
            file_record: FileRecordオブジェクト
            
        Returns:
            成功したかどうか
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO file_records (
                    id, source, path, original_name, created_at,
                    modified_at, file_created_at, type, size, hash,
                    status, tags, alias_name, summary, ocr_text_ref,
                    thread_ref, audit_log, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_record.id,
                file_record.source.value,
                file_record.path,
                file_record.original_name,
                file_record.created_at,
                file_record.modified_at,
                file_record.file_created_at,
                file_record.type.value if file_record.type else None,
                file_record.size,
                file_record.hash,
                file_record.status.value,
                json.dumps(file_record.tags, ensure_ascii=False),
                file_record.alias_name,
                file_record.summary,
                file_record.ocr_text_ref,
                file_record.thread_ref,
                json.dumps([entry.to_dict() for entry in file_record.audit_log], ensure_ascii=False),
                json.dumps(file_record.metadata, ensure_ascii=False)
            ))
            
            # FTS5にも追加
            cursor.execute("""
                INSERT INTO file_records_fts (
                    rowid, original_name, alias_name, summary, tags
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                cursor.lastrowid,
                file_record.original_name,
                file_record.alias_name or "",
                file_record.summary or "",
                json.dumps(file_record.tags, ensure_ascii=False)
            ))
            
            self.conn.commit()
            logger.info(f"✅ ファイルレコード作成: {file_record.id}")
            return True
        except Exception as e:
            logger.error(f"❌ ファイルレコード作成エラー: {e}")
            self.conn.rollback()
            return False
    
    def get_file_record(self, file_id: str) -> Optional[FileRecord]:
        """
        ファイルレコードを取得
        
        Args:
            file_id: ファイルID
            
        Returns:
            FileRecordまたはNone
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_file_record(row)
    
    def update_file_record(self, file_record: FileRecord) -> bool:
        """
        ファイルレコードを更新
        
        Args:
            file_record: FileRecordオブジェクト
            
        Returns:
            成功したかどうか
        """
        try:
            cursor = self.conn.cursor()
            
            # 現在のrowidを取得
            cursor.execute("SELECT rowid FROM file_records WHERE id = ?", (file_record.id,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"File record not found for update: {file_record.id[:16]}...")
                return False
            
            rowid = row[0]
            
            # デバッグ: 更新前の状態を確認
            logger.debug(f"Updating file record: {file_record.id[:16]}..., status: {file_record.status.value}, tags: {file_record.tags}, alias: {file_record.alias_name}")
            
            cursor.execute("""
                UPDATE file_records SET
                    source = ?, path = ?, original_name = ?, created_at = ?,
                    modified_at = ?, file_created_at = ?, type = ?, size = ?, hash = ?,
                    status = ?, tags = ?, alias_name = ?, summary = ?, ocr_text_ref = ?,
                    thread_ref = ?, audit_log = ?, metadata = ?,
                    updated_at_db = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                file_record.source.value,
                file_record.path,
                file_record.original_name,
                file_record.created_at,
                file_record.modified_at,
                file_record.file_created_at,
                file_record.type.value if file_record.type else None,
                file_record.size,
                file_record.hash,
                file_record.status.value,
                json.dumps(file_record.tags, ensure_ascii=False),
                file_record.alias_name,
                file_record.summary,
                file_record.ocr_text_ref,
                file_record.thread_ref,
                json.dumps([entry.to_dict() for entry in file_record.audit_log], ensure_ascii=False),
                json.dumps(file_record.metadata, ensure_ascii=False),
                file_record.id
            ))
            
            # FTS5も更新（rowidが存在する場合のみ）
            try:
                cursor.execute("""
                    UPDATE file_records_fts SET
                        original_name = ?, alias_name = ?, summary = ?, tags = ?
                    WHERE rowid = ?
                """, (
                    file_record.original_name,
                    file_record.alias_name or "",
                    file_record.summary or "",
                    json.dumps(file_record.tags, ensure_ascii=False),
                    rowid
                ))
                fts_updated = cursor.rowcount
                if fts_updated == 0:
                    # FTS5に存在しない場合は挿入
                    logger.debug(f"FTS5 record not found, inserting new record for rowid: {rowid}")
                    cursor.execute("""
                        INSERT INTO file_records_fts (
                            rowid, original_name, alias_name, summary, tags
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        rowid,
                        file_record.original_name,
                        file_record.alias_name or "",
                        file_record.summary or "",
                        json.dumps(file_record.tags, ensure_ascii=False)
                    ))
            except Exception as fts_error:
                # FTS5の更新エラーは無視（メインテーブルの更新は成功）
                logger.warning(f"FTS5 update error (ignored): {fts_error}")
            
            # 更新行数を確認
            rows_updated = cursor.rowcount
            if rows_updated == 0:
                logger.warning(f"No rows updated for file record: {file_record.id[:16]}...")
                self.conn.rollback()
                return False
            
            self.conn.commit()
            logger.info(f"✅ ファイルレコード更新: {file_record.id}")
            return True
        except Exception as e:
            logger.error(f"❌ ファイルレコード更新エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.conn.rollback()
            return False
    
    def get_files_by_thread(self, thread_ref: str) -> List[FileRecord]:
        """
        スレッド参照でファイルレコードを取得
        
        Args:
            thread_ref: SlackスレッドID
            
        Returns:
            FileRecordリスト
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM file_records WHERE thread_ref = ?", (thread_ref,))
        rows = cursor.fetchall()
        
        return [self._row_to_file_record(row) for row in rows]
    
    def get_files_by_status(self, status: FileStatus, source: Optional[FileSource] = None, limit: int = 100) -> List[FileRecord]:
        """
        ステータスでファイルレコードを取得
        
        Args:
            status: ファイルステータス
            source: ソース（オプション）
            limit: 取得上限
            
        Returns:
            FileRecordリスト
        """
        cursor = self.conn.cursor()
        
        if source:
            cursor.execute(
                "SELECT * FROM file_records WHERE status = ? AND source = ? ORDER BY created_at DESC LIMIT ?",
                (status.value, source.value, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM file_records WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status.value, limit)
            )
        
        rows = cursor.fetchall()
        return [self._row_to_file_record(row) for row in rows]
    
    def search_files(self, query: str, limit: int = 10) -> List[FileRecord]:
        """
        全文検索
        
        Args:
            query: 検索クエリ
            limit: 取得上限
            
        Returns:
            FileRecordリスト
        """
        cursor = self.conn.cursor()
        
        # FTS5で検索
        cursor.execute("""
            SELECT fr.* FROM file_records fr
            JOIN file_records_fts fts ON fr.rowid = fts.rowid
            WHERE file_records_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        rows = cursor.fetchall()
        return [self._row_to_file_record(row) for row in rows]
    
    def get_inbox_status(self, source: Optional[FileSource] = None, days_new: int = 1, days_old: int = 7) -> Dict[str, Any]:
        """
        INBOX状況を取得
        
        Args:
            source: ソース（オプション）
            days_new: 新規判定日数
            days_old: 未処理判定日数
            
        Returns:
            状況サマリ
        """
        cursor = self.conn.cursor()
        
        # 新規ファイル数（days_new日以内）
        new_threshold = (datetime.now().timestamp() - days_new * 86400)
        new_date = datetime.fromtimestamp(new_threshold).isoformat()
        
        # 長期未処理（days_old日以上）
        old_threshold = (datetime.now().timestamp() - days_old * 86400)
        old_date = datetime.fromtimestamp(old_threshold).isoformat()
        
        if source:
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE created_at >= ?) as new_count,
                    COUNT(*) FILTER (WHERE created_at < ? AND status IN ('inbox', 'triaged')) as old_count,
                    COUNT(*) FILTER (WHERE created_at < ? AND status IN ('inbox', 'triaged')) as long_term_count
                FROM file_records
                WHERE source = ?
            """, (new_date, old_date, old_date, source.value))
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE created_at >= ?) as new_count,
                    COUNT(*) FILTER (WHERE created_at < ? AND status IN ('inbox', 'triaged')) as old_count,
                    COUNT(*) FILTER (WHERE created_at < ? AND status IN ('inbox', 'triaged')) as long_term_count
                FROM file_records
            """, (new_date, old_date, old_date))
        
        row = cursor.fetchone()
        
        # タイプ別カウント
        if source:
            cursor.execute("""
                SELECT type, COUNT(*) as count
                FROM file_records
                WHERE source = ? AND status IN ('inbox', 'triaged')
                GROUP BY type
            """, (source.value,))
        else:
            cursor.execute("""
                SELECT type, COUNT(*) as count
                FROM file_records
                WHERE status IN ('inbox', 'triaged')
                GROUP BY type
            """)
        
        type_counts = {row[0] or "other": row[1] for row in cursor.fetchall()}
        
        return {
            "new_count": row[0] or 0,
            "old_count": row[1] or 0,
            "long_term_count": row[2] or 0,
            "by_type": type_counts
        }
    
    def get_candidates(self, limit: int = 3) -> List[FileRecord]:
        """
        候補ファイルを取得（最新の未処理ファイル）
        
        Args:
            limit: 取得上限
            
        Returns:
            FileRecordリスト
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM file_records
            WHERE status IN ('inbox', 'triaged')
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [self._row_to_file_record(row) for row in rows]
    
    def _row_to_file_record(self, row: sqlite3.Row) -> FileRecord:
        """行をFileRecordに変換"""
        return FileRecord(
            id=row["id"],
            source=FileSource(row["source"]),
            path=row["path"],
            original_name=row["original_name"],
            created_at=row["created_at"],
            status=FileStatus(row["status"]),
            modified_at=row["modified_at"],
            file_created_at=row["file_created_at"],
            type=FileType(row["type"]) if row["type"] else None,
            size=row["size"],
            hash=row["hash"],
            tags=json.loads(row["tags"] or "[]"),
            alias_name=row["alias_name"],
            summary=row["summary"],
            ocr_text_ref=row["ocr_text_ref"],
            thread_ref=row["thread_ref"],
            audit_log=[AuditLogEntry.from_dict(entry) for entry in json.loads(row["audit_log"] or "[]")],
            metadata=json.loads(row["metadata"] or "{}")
        )
    
    def close(self):
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            logger.info("✅ データベース接続を閉じました")


