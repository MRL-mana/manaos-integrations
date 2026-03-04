#!/usr/bin/env python3
"""
Trinity v2.1 データベースクリーンアップスクリプト

機能:
- 重複タスクの削除
- VACUUM実行（データベース最適化）
- ANALYZE実行（統計情報更新）
- インデックス最適化

実行: python3 cleanup_v21.py
"""

import sys
from pathlib import Path

# パス設定
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    logger.info("🧹 Trinity v2.1 クリーンアップ開始")
    
    db = DatabaseManager()
    
    # 1. 重複タスクの特定と削除
    logger.info("📋 重複タスクを検索中...")
    
    duplicates = db.conn.execute("""
        SELECT id, title FROM tasks 
        WHERE title LIKE 'Minaからの依頼: タスク AUTO-%'
        AND status = 'in_progress'
    """).fetchall()
    
    logger.info(f"🔍 重複タスク: {len(duplicates)}件 検出")
    
    if duplicates:
        # 削除実行
        deleted_count = 0
        for task in duplicates:
            try:
                db.conn.execute("DELETE FROM tasks WHERE id = ?", (task[0],))
                deleted_count += 1
                logger.info(f"  ✅ 削除: {task[0][:20]}...")
            except Exception as e:
                logger.error(f"  ❌ 削除失敗 {task[0]}: {e}")
        
        db.conn.commit()
        logger.info(f"✅ {deleted_count}件の重複タスク削除完了")
    else:
        logger.info("✨ 重複タスクなし")
    
    # 2. VACUUM実行（データベース最適化）
    logger.info("🗜️  VACUUM実行中...")
    try:
        # 現在のDBサイズを取得
        before_size = Path(db.db_path).stat().st_size / 1024 / 1024  # MB
        logger.info(f"  現在のDBサイズ: {before_size:.2f} MB")
        
        db.conn.execute("VACUUM")
        
        after_size = Path(db.db_path).stat().st_size / 1024 / 1024  # MB
        saved = before_size - after_size
        logger.info(f"  最適化後: {after_size:.2f} MB")
        logger.info(f"  削減: {saved:.2f} MB ({saved/before_size*100:.1f}%)")
        logger.info("✅ VACUUM完了")
    except Exception as e:
        logger.error(f"❌ VACUUM失敗: {e}")
    
    # 3. ANALYZE実行（統計情報更新）
    logger.info("📊 ANALYZE実行中...")
    try:
        db.conn.execute("ANALYZE")
        logger.info("✅ ANALYZE完了（統計情報更新）")
    except Exception as e:
        logger.error(f"❌ ANALYZE失敗: {e}")
    
    # 4. インデックス最適化確認
    logger.info("🔧 インデックス最適化中...")
    try:
        db.conn.execute("PRAGMA optimize")
        logger.info("✅ インデックス最適化完了")
    except Exception as e:
        logger.error(f"❌ インデックス最適化失敗: {e}")
    
    # 5. 最終統計
    logger.info("\n📊 最終統計:")
    
    total_tasks = db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    logger.info(f"  総タスク数: {total_tasks}")
    
    by_status = db.conn.execute("""
        SELECT status, COUNT(*) 
        FROM tasks 
        GROUP BY status
    """).fetchall()
    
    for status, count in by_status:
        logger.info(f"    {status}: {count}件")
    
    db.close()
    
    logger.info("\n✅ Trinity v2.1 クリーンアップ完了！")
    logger.info("🚀 データベースが最適化されました")


if __name__ == '__main__':
    main()

