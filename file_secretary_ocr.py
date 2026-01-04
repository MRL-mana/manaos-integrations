#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 File Secretary - OCR統合
条件付きOCR実行とテキスト保存
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from manaos_logger import get_logger
from file_secretary_schemas import FileRecord, FileType, AuditAction
from file_secretary_db import FileSecretaryDB

logger = get_logger(__name__)

# OCR統合をインポート
try:
    from ocr_multi_provider import MultiProviderOCR
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR統合モジュールが見つかりません")


class FileSecretaryOCR:
    """ファイル秘書OCR統合"""
    
    def __init__(self, db: FileSecretaryDB, ocr_provider: str = "tesseract"):
        """
        初期化
        
        Args:
            db: FileSecretaryDBインスタンス
            ocr_provider: OCRプロバイダー（tesseract/google/microsoft/amazon）
        """
        self.db = db
        self.ocr_provider = ocr_provider
        self.ocr_engine = None
        
        if OCR_AVAILABLE:
            try:
                self.ocr_engine = MultiProviderOCR()
                available_providers = self.ocr_engine.get_available_providers()
                if ocr_provider not in available_providers:
                    logger.warning(f"⚠️ OCRプロバイダー '{ocr_provider}' が利用できません。利用可能: {available_providers}")
                    if available_providers:
                        self.ocr_provider = available_providers[0]
                        logger.info(f"✅ OCRプロバイダーを '{self.ocr_provider}' に変更")
                logger.info(f"✅ OCR統合初期化完了: {self.ocr_provider}")
            except Exception as e:
                logger.error(f"❌ OCR統合初期化エラー: {e}")
    
    def should_run_ocr(self, file_record: FileRecord) -> bool:
        """
        OCRを実行すべきか判定
        
        条件:
        - PDFまたは画像ファイル
        - タグに「日報」が含まれる、またはocr_text_refが未設定
        
        Args:
            file_record: FileRecord
            
        Returns:
            OCRを実行すべきかどうか
        """
        # PDFまたは画像のみ
        if file_record.type not in [FileType.PDF, FileType.IMAGE]:
            return False
        
        # 既にOCR済みならスキップ
        if file_record.ocr_text_ref:
            return False
        
        # タグに「日報」が含まれる場合は優先
        if "日報" in file_record.tags:
            return True
        
        # その他のPDF/画像も実行（設定で制御可能）
        return True
    
    def _save_ocr_text(self, file_record: FileRecord, ocr_text: str) -> str:
        """
        OCRテキストをファイルに保存
        
        Args:
            file_record: FileRecord
            ocr_text: OCRテキスト
            
        Returns:
            保存先パス
        """
        ocr_dir = Path(os.getenv("OCR_TEXT_DIR", "ocr_texts"))
        ocr_dir.mkdir(parents=True, exist_ok=True)
        
        ocr_file = ocr_dir / f"{file_record.id}.txt"
        ocr_file.write_text(ocr_text, encoding='utf-8')
        
        return str(ocr_file)
    
    def run_ocr(self, file_record: FileRecord) -> Optional[str]:
        """
        OCRを実行
        
        Args:
            file_record: FileRecord
            
        Returns:
            OCRテキストへの参照パスまたはNone
        """
        if not self.should_run_ocr(file_record):
            return None
        
        if not self.ocr_engine:
            logger.warning("⚠️ OCRエンジンが利用できません")
            return None
        
        try:
            # ファイルパスを取得
            file_path = file_record.path
            
            # Google Driveの場合はダウンロードが必要
            if file_path.startswith("gdrive://"):
                # Google Driveからダウンロード（簡易版：実装は省略）
                logger.warning("⚠️ Google DriveファイルのOCRは未実装です")
                return None
            
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.warning(f"⚠️ ファイルが存在しません: {file_path}")
                return None
            
            # OCR実行
            logger.info(f"🔍 OCR実行中: {file_record.original_name}")
            ocr_result = self.ocr_engine.recognize(str(file_path_obj), provider=self.ocr_provider)
            
            if not ocr_result or not ocr_result.get("text"):
                logger.warning(f"⚠️ OCR結果が空です: {file_record.original_name}")
                return None
            
            ocr_text = ocr_result.get("text", "")
            
            # OCRテキストを保存
            ocr_ref = self._save_ocr_text(file_record, ocr_text)
            
            # FileRecordを更新
            file_record.ocr_text_ref = ocr_ref
            file_record.add_audit_log(
                AuditAction.TAGGED,
                user="system",
                details={"action": "ocr", "provider": self.ocr_provider}
            )
            
            if self.db.update_file_record(file_record):
                logger.info(f"✅ OCR完了: {file_record.original_name} ({len(ocr_text)}文字)")
                return ocr_ref
            else:
                logger.error(f"❌ OCR結果の保存に失敗: {file_record.original_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ OCR実行エラー: {file_record.original_name} - {e}")
            return None
    
    def get_ocr_text(self, file_record: FileRecord) -> Optional[str]:
        """
        OCRテキストを取得
        
        Args:
            file_record: FileRecord
            
        Returns:
            OCRテキストまたはNone
        """
        if not file_record.ocr_text_ref:
            return None
        
        try:
            ocr_path = Path(file_record.ocr_text_ref)
            if ocr_path.exists():
                return ocr_path.read_text(encoding='utf-8')
            else:
                logger.warning(f"⚠️ OCRテキストファイルが存在しません: {ocr_path}")
                return None
        except Exception as e:
            logger.error(f"❌ OCRテキスト読み込みエラー: {e}")
            return None
    
    def search_in_ocr_text(self, query: str, file_records: list) -> list:
        """
        OCRテキスト内を検索
        
        Args:
            query: 検索クエリ
            file_records: FileRecordリスト
            
        Returns:
            マッチしたFileRecordリスト
        """
        matched = []
        query_lower = query.lower()
        
        for file_record in file_records:
            if not file_record.ocr_text_ref:
                continue
            
            ocr_text = self.get_ocr_text(file_record)
            if ocr_text and query_lower in ocr_text.lower():
                matched.append(file_record)
        
        return matched

