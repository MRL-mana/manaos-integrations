#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📋 File Secretary - Organizer Worker
タグ推定・alias生成・整理実行
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from manaos_logger import get_logger
from file_secretary_schemas import FileRecord, FileStatus, AuditAction
from file_secretary_db import FileSecretaryDB

logger = get_logger(__name__)

# 記憶機能統合（オプション）
try:
    from memory_unified import UnifiedMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("UnifiedMemoryが利用できません。記憶機能は無効です。")


class FileOrganizer:
    """ファイル整理ワーカー"""
    
    def __init__(self, db: FileSecretaryDB, ollama_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:14b", use_memory: bool = True):
        """
        初期化
        
        Args:
            db: FileSecretaryDBインスタンス
            ollama_url: Ollama API URL
            model: 使用するLLMモデル
            use_memory: 記憶機能を使用するか
        """
        self.db = db
        self.ollama_url = ollama_url
        self.model = model
        self.use_memory = use_memory and MEMORY_AVAILABLE
        
        # 記憶機能の初期化
        self.memory = None
        if self.use_memory:
            try:
                self.memory = UnifiedMemory()
                logger.info("✅ File Secretary: 記憶機能を有効化しました")
            except Exception as e:
                logger.warning(f"⚠️ 記憶機能の初期化エラー: {e}")
                self.memory = None
    
    def _infer_tags_simple(self, file_record: FileRecord) -> List[str]:
        """
        シンプルなタグ推定（キーワードベース）
        
        Args:
            file_record: FileRecord
            
        Returns:
            タグリスト
        """
        tags = []
        name_lower = file_record.original_name.lower()
        
        # キーワードマッピング
        keyword_map = {
            "日報": ["日報", "daily", "report", "レポート"],
            "クーポン": ["クーポン", "coupon", "割引"],
            "洗車": ["洗車", "car", "車"],
            "実績": ["実績", "achievement", "result"],
            "データ": ["data", "データ", "excel", "xlsx"],
            "画像": ["image", "画像", "photo", "写真"],
            "PDF": ["pdf", "document", "文書"]
        }
        
        for tag, keywords in keyword_map.items():
            if any(keyword in name_lower for keyword in keywords):
                tags.append(tag)
        
        # ファイルタイプから推測
        if file_record.type:
            if file_record.type.value == "pdf":
                tags.append("PDF")
            elif file_record.type.value == "image":
                tags.append("画像")
            elif file_record.type.value == "xlsx":
                tags.append("データ")
        
        return list(set(tags))  # 重複除去
    
    def _infer_tags_llm(self, file_record: FileRecord) -> List[str]:
        """
        LLMでタグ推定（将来拡張用）
        
        Args:
            file_record: FileRecord
            
        Returns:
            タグリスト
        """
        # Phase1ではシンプル版を使用
        return self._infer_tags_simple(file_record)
    
    def _generate_alias_name(self, file_record: FileRecord, tags: List[str]) -> str:
        """
        alias_nameを生成
        
        フォーマット: YYYY-MM-DD_タグ1_タグ2_元ファイル名
        
        Args:
            file_record: FileRecord
            tags: タグリスト
            
        Returns:
            alias_name
        """
        # 日付（ファイル作成日または今日）
        date_str = datetime.now().strftime("%Y-%m-%d")
        if file_record.file_created_at:
            try:
                file_date = datetime.fromisoformat(file_record.file_created_at.replace("Z", "+00:00"))
                date_str = file_date.strftime("%Y-%m-%d")
            except Exception:
                pass
        
        # タグ部分
        tag_part = "_".join(tags[:3]) if tags else "その他"
        
        # 元ファイル名（拡張子付き）
        original_name = file_record.original_name
        
        # 組み立て
        alias = f"{date_str}_{tag_part}_{original_name}"
        
        # 長すぎる場合は切り詰め
        if len(alias) > 200:
            name_part = original_name[:50]
            alias = f"{date_str}_{tag_part}_{name_part}"
        
        return alias
    
    def organize_files(
        self,
        file_ids: List[str],
        thread_ref: Optional[str] = None,
        user: Optional[str] = None,
        auto_tag: bool = True,
        auto_alias: bool = True
    ) -> Dict[str, Any]:
        """
        ファイルを整理
        
        Args:
            file_ids: ファイルIDリスト（空の場合はthread_refから自動判定）
            thread_ref: SlackスレッドID
            user: ユーザーID
            auto_tag: 自動タグ付け
            auto_alias: 自動alias生成
            
        Returns:
            整理結果
        """
        # 対象ファイルを決定
        if not file_ids and thread_ref:
            # スレッド参照から取得
            file_records = self.db.get_files_by_thread(thread_ref)
        elif file_ids:
            # 指定されたIDから取得
            file_records = [self.db.get_file_record(fid) for fid in file_ids]
            file_records = [fr for fr in file_records if fr]  # Noneを除去
        else:
            # 最新3件を取得
            file_records = self.db.get_candidates(limit=3)
        
        if not file_records:
            return {
                "status": "error",
                "error": "整理対象のファイルが見つかりませんでした"
            }
        
        organized_files = []
        
        for file_record in file_records:
            try:
                # タグ推定（LLM優先、フォールバックでキーワードベース）
                if auto_tag:
                    # Ollamaが利用可能かチェック
                    try:
                        import httpx
                        check_response = httpx.get(f"{self.ollama_url}/api/tags", timeout=2.0)
                        use_llm = check_response.status_code == 200
                    except Exception:
                        use_llm = False
                    
                    if use_llm:
                        tags = self._infer_tags_llm(file_record)
                    else:
                        tags = self._infer_tags_simple(file_record)
                    file_record.tags = tags
                else:
                    tags = file_record.tags
                
                # alias生成
                if auto_alias:
                    alias_name = self._generate_alias_name(file_record, tags)
                    file_record.alias_name = alias_name
                
                # ステータス更新
                file_record.status = FileStatus.ARCHIVED
                
                # 監査ログ追加
                file_record.add_audit_log(
                    AuditAction.ARCHIVED,
                    user=user or "system",
                    details={
                        "tags": tags,
                        "alias_name": file_record.alias_name,
                        "thread_ref": thread_ref
                    }
                )
                
                # データベース更新
                if self.db.update_file_record(file_record):
                    organized_files.append({
                        "id": file_record.id,
                        "original_name": file_record.original_name,
                        "alias_name": file_record.alias_name,
                        "tags": file_record.tags,
                        "status": file_record.status.value
                    })
                    logger.info(f"✅ ファイル整理完了: {file_record.original_name} → {file_record.alias_name}")
                else:
                    logger.error(f"❌ ファイル整理失敗: {file_record.original_name}")
                    
            except Exception as e:
                logger.error(f"❌ ファイル整理エラー: {file_record.original_name} - {e}")
        
        return {
            "status": "success",
            "organized_count": len(organized_files),
            "files": organized_files
        }
    
    def restore_files(
        self,
        file_ids: Optional[List[str]] = None,
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ファイルを復元（INBOXに戻す）
        
        Args:
            file_ids: ファイルIDリスト（空の場合は直近の整理操作を復元）
            user: ユーザーID
            
        Returns:
            復元結果
        """
        # 対象ファイルを決定
        if file_ids:
            file_records = [self.db.get_file_record(fid) for fid in file_ids]
            file_records = [fr for fr in file_records if fr]
        else:
            # 直近のarchivedファイルを取得（最新5件）
            file_records = self.db.get_files_by_status(FileStatus.ARCHIVED, limit=5)
        
        if not file_records:
            return {
                "status": "error",
                "error": "復元対象のファイルが見つかりませんでした"
            }
        
        restored_files = []
        
        for file_record in file_records:
            try:
                # ステータスをINBOXに戻す
                old_status = file_record.status
                file_record.status = FileStatus.INBOX
                
                # 監査ログ追加
                file_record.add_audit_log(
                    AuditAction.RESTORED,
                    user=user or "system",
                    details={
                        "restored_from": old_status.value
                    }
                )
                
                # データベース更新
                if self.db.update_file_record(file_record):
                    restored_files.append({
                        "id": file_record.id,
                        "original_name": file_record.original_name,
                        "alias_name": file_record.alias_name,
                        "status": file_record.status.value,
                        "restored_from": old_status.value
                    })
                    logger.info(f"✅ ファイル復元完了: {file_record.original_name}")
                else:
                    logger.error(f"❌ ファイル復元失敗: {file_record.original_name}")
                    
            except Exception as e:
                logger.error(f"❌ ファイル復元エラー: {file_record.original_name} - {e}")
        
        return {
            "status": "success",
            "restored_count": len(restored_files),
            "files": restored_files
        }


