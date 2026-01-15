#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR統合テスト
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_ocr import FileSecretaryOCR
from file_secretary_schemas import FileRecord, FileType, FileStatus, FileSource
from datetime import datetime

def main():
    print("=== OCR統合テスト ===\n")
    
    # データベース接続
    db = FileSecretaryDB('file_secretary.db')
    
    # OCRエンジン初期化
    print("OCRエンジン初期化中...")
    ocr_engine = FileSecretaryOCR(db)
    
    if not ocr_engine.ocr_engine:
        print("⚠️ OCRエンジンが利用できません")
        print("   設定が必要:")
        print("   - Tesseract OCRのインストール")
        print("   - またはGoogle Cloud Vision APIの設定")
        return
    
    print(f"✅ OCRエンジン利用可能: {ocr_engine.ocr_provider}\n")
    
    # テスト用FileRecord作成（PDF/画像タイプ）
    print("テスト用FileRecord作成中...")
    test_file_record = FileRecord(
        id="test_ocr_file_001",
        source=FileSource.MOTHER,
        path="test_file.pdf",
        original_name="test_file.pdf",
        created_at=datetime.now().isoformat(),
        status=FileStatus.TRIAGED,
        type=FileType.PDF,
        tags=["日報"]  # OCR実行条件を満たす
    )
    
    # OCR実行判定テスト
    print("\nOCR実行判定テスト:")
    should_run = ocr_engine.should_run_ocr(test_file_record)
    print(f"  PDF + 日報タグ: {should_run}")
    
    test_file_record.type = FileType.IMAGE
    should_run = ocr_engine.should_run_ocr(test_file_record)
    print(f"  IMAGE + 日報タグ: {should_run}")
    
    test_file_record.tags = []
    should_run = ocr_engine.should_run_ocr(test_file_record)
    print(f"  IMAGE + タグなし: {should_run}")
    
    test_file_record.type = FileType.TXT
    should_run = ocr_engine.should_run_ocr(test_file_record)
    print(f"  TXT: {should_run}")
    
    # OCRテキスト検索テスト（モック）
    print("\nOCRテキスト検索テスト（モック）:")
    test_records = [
        FileRecord(
            id="test1",
            source=FileSource.MOTHER,
            path="test1.pdf",
            original_name="test1.pdf",
            created_at=datetime.now().isoformat(),
            status=FileStatus.TRIAGED,
            type=FileType.PDF,
            ocr_text_ref="ocr_texts/test1.txt"
        )
    ]
    
    # OCRテキストファイルを作成（テスト用）
    ocr_dir = Path("ocr_texts")
    ocr_dir.mkdir(exist_ok=True)
    test_ocr_file = ocr_dir / "test1.txt"
    test_ocr_file.write_text("これはテスト用のOCRテキストです。日報の内容が含まれています。", encoding='utf-8')
    
    matched = ocr_engine.search_in_ocr_text("日報", test_records)
    print(f"  検索クエリ: \"日報\"")
    print(f"  マッチ数: {len(matched)}")
    if matched:
        print(f"  マッチしたファイル: {matched[0].original_name}")
    
    db.close()

if __name__ == '__main__':
    main()






















