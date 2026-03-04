#!/usr/bin/env python3
"""
監査DBのマイグレーション
ハッシュ連鎖対応のため、prev_hashとchain_hashカラムを追加
"""

import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIT_DB_PATH = Path("/root/.mana_memory/memory_audit.db")


def migrate_audit_db():
    """監査DBをマイグレーション"""
    if not AUDIT_DB_PATH.exists():
        logger.info("監査DBが存在しません。新規作成されます。")
        return True

    try:
        conn = sqlite3.connect(str(AUDIT_DB_PATH))
        cur = conn.cursor()

        # 既存のカラムを確認
        cur.execute("PRAGMA table_info(memory_audit)")
        columns = [row[1] for row in cur.fetchall()]

        # prev_hashカラムが存在しない場合は追加
        if 'prev_hash' not in columns:
            logger.info("prev_hashカラムを追加中...")
            conn.execute("ALTER TABLE memory_audit ADD COLUMN prev_hash TEXT")
            logger.info("✅ prev_hashカラム追加完了")

        # chain_hashカラムが存在しない場合は追加
        if 'chain_hash' not in columns:
            logger.info("chain_hashカラムを追加中...")
            conn.execute("ALTER TABLE memory_audit ADD COLUMN chain_hash TEXT")
            logger.info("✅ chain_hashカラム追加完了")

            # 既存レコードのchain_hashを計算（オプション）
            # 既存データは後から計算する必要がある
            logger.info("既存レコードのchain_hashは後で計算されます")

        # インデックスを追加（存在しない場合）
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chain_hash ON memory_audit(chain_hash)")
        except Exception as e:
            pass

        conn.commit()
        conn.close()

        logger.info("✅ 監査DBマイグレーション完了")
        return True
    except Exception as e:
        logger.error(f"マイグレーションエラー: {e}")
        return False


if __name__ == '__main__':
    migrate_audit_db()








