#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📄 File Secretary - データモデル定義
FileRecordとAuditLogEntryのスキーマ
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class FileSource(str, Enum):
    """ファイルソース"""
    MOTHER = "mother"
    DRIVE = "drive"
    X280 = "x280"


class FileType(str, Enum):
    """ファイルタイプ"""
    PDF = "pdf"
    IMAGE = "image"
    XLSX = "xlsx"
    DOCX = "docx"
    MD = "md"
    TXT = "txt"
    OTHER = "other"


class FileStatus(str, Enum):
    """ファイルステータス"""
    INBOX = "inbox"
    TRIAGED = "triaged"
    DONE = "done"
    ARCHIVED = "archived"


class AuditAction(str, Enum):
    """監査ログアクション"""
    CREATED = "created"
    TRIAGED = "triaged"
    TAGGED = "tagged"
    RENAMED = "renamed"
    ARCHIVED = "archived"
    RESTORED = "restored"


@dataclass
class AuditLogEntry:
    """監査ログエントリ"""
    timestamp: str  # ISO 8601
    action: AuditAction
    user: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "timestamp": self.timestamp,
            "action": self.action.value,
            "user": self.user,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogEntry":
        """辞書から作成"""
        return cls(
            timestamp=data["timestamp"],
            action=AuditAction(data["action"]),
            user=data.get("user"),
            details=data.get("details", {})
        )


@dataclass
class FileRecord:
    """ファイルレコード"""
    id: str
    source: FileSource
    path: str
    original_name: str
    created_at: str  # ISO 8601
    status: FileStatus
    modified_at: Optional[str] = None  # ISO 8601
    file_created_at: Optional[str] = None  # ISO 8601
    type: Optional[FileType] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    alias_name: Optional[str] = None
    summary: Optional[str] = None
    ocr_text_ref: Optional[str] = None
    thread_ref: Optional[str] = None
    audit_log: List[AuditLogEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換（JSON用）"""
        return {
            "id": self.id,
            "source": self.source.value,
            "path": self.path,
            "original_name": self.original_name,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "file_created_at": self.file_created_at,
            "type": self.type.value if self.type else None,
            "size": self.size,
            "hash": self.hash,
            "status": self.status.value,
            "tags": self.tags,
            "alias_name": self.alias_name,
            "summary": self.summary,
            "ocr_text_ref": self.ocr_text_ref,
            "thread_ref": self.thread_ref,
            "audit_log": [entry.to_dict() for entry in self.audit_log],
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileRecord":
        """辞書から作成"""
        return cls(
            id=data["id"],
            source=FileSource(data["source"]),
            path=data["path"],
            original_name=data["original_name"],
            created_at=data["created_at"],
            status=FileStatus(data["status"]),
            modified_at=data.get("modified_at"),
            file_created_at=data.get("file_created_at"),
            type=FileType(data["type"]) if data.get("type") else None,
            size=data.get("size"),
            hash=data.get("hash"),
            tags=data.get("tags", []),
            alias_name=data.get("alias_name"),
            summary=data.get("summary"),
            ocr_text_ref=data.get("ocr_text_ref"),
            thread_ref=data.get("thread_ref"),
            audit_log=[AuditLogEntry.from_dict(entry) for entry in data.get("audit_log", [])],
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "FileRecord":
        """JSON文字列から作成"""
        return cls.from_dict(json.loads(json_str))
    
    def add_audit_log(self, action: AuditAction, user: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """監査ログを追加"""
        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            action=action,
            user=user,
            details=details or {}
        )
        self.audit_log.append(entry)























