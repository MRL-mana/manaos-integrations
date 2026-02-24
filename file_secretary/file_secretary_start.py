#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 File Secretary - 起動スクリプト
Phase1の全サービスを起動
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from manaos_logger import get_logger, get_service_logger
from file_secretary_db import FileSecretaryDB
from file_secretary_indexer import FileIndexer
from file_secretary_schemas import FileSource

logger = get_service_logger("file-secretary-start")


def main():
    """メイン処理"""
    logger.info("🚀 File Secretary Phase1 起動中...")
    
    # データベース初期化
    db_path = os.getenv("FILE_SECRETARY_DB_PATH", "file_secretary.db")
    db = FileSecretaryDB(db_path)
    logger.info("✅ データベース初期化完了")
    
    # INBOX監視開始（母艦）
    # Windows環境を考慮してデフォルトパスを設定
    default_inbox = str(Path(__file__).parent / "00_INBOX")
    inbox_path = os.getenv("INBOX_PATH", default_inbox)
    if not Path(inbox_path).exists():
        logger.warning(f"⚠️ INBOXパスが存在しません: {inbox_path}")
        logger.info(f"📁 INBOXパスを作成します: {inbox_path}")
        Path(inbox_path).mkdir(parents=True, exist_ok=True)
    
    indexer = FileIndexer(db, FileSource.MOTHER, inbox_path)
    indexer.start_watching()
    logger.info(f"✅ ファイル監視開始: {inbox_path}")
    
    # 既存ファイルをインデックス
    logger.info("📂 既存ファイルをインデックス中...")
    indexed_count = indexer.index_directory()
    logger.info(f"✅ {indexed_count}件のファイルをインデックスしました")
    
    logger.info("✅ File Secretary Phase1 起動完了")
    logger.info("📌 File Secretary APIは別途起動してください: python file_secretary_api.py")
    
    # 監視を継続
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("⏹️ 停止シグナルを受信しました")
        indexer.stop_watching()
        db.close()
        logger.info("✅ File Secretary Phase1 停止完了")


if __name__ == '__main__':
    main()


