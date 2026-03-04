#!/usr/bin/env python3
"""
Trinity v2.1 自動メンテナンススクリプト

定期的に実行してシステムを最適な状態に保つ

機能:
- タスク履歴の自動クリーンアップ（100件のみ保持）
- 古いログの削除（7日以上）
- キャッシュのリフレッシュ
- RAGインデックス更新
- 統計レポート生成

実行: python3 auto_maintenance.py
Cron設定: 0 3 * * * python3 /root/trinity_workspace/scripts/auto_maintenance.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from datetime import datetime
import logging
import os

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/root/trinity_workspace/logs/auto_maintenance.log')
    ]
)
logger = logging.getLogger(__name__)


def cleanup_task_history():
    """タスク履歴クリーンアップ（最新100件のみ保持）"""
    logger.info("🗑️  タスク履歴クリーンアップ開始...")
    
    db = DatabaseManager()
    
    try:
        # 削除前の件数
        before = db.conn.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
        
        # 最新100件以外を削除
        db.conn.execute("""
            DELETE FROM task_history 
            WHERE id NOT IN (
                SELECT id FROM task_history 
                ORDER BY changed_at DESC 
                LIMIT 100
            )
        """)
        db.conn.commit()
        
        # 削除後の件数
        after = db.conn.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
        deleted = before - after
        
        logger.info(f"✅ {deleted}件の古い履歴を削除（{before} → {after}）")
        
        # VACUUM実行
        logger.info("🗜️  VACUUM実行中...")
        db.conn.execute("VACUUM")
        logger.info("✅ VACUUM完了")
        
    except Exception as e:
        logger.error(f"❌ クリーンアップ失敗: {e}")
    finally:
        db.close()


def cleanup_old_logs():
    """古いログファイル削除（7日以上）"""
    logger.info("📄 古いログファイル削除...")
    
    log_dir = Path('/root/trinity_workspace/logs')
    deleted_count = 0
    
    for log_file in log_dir.glob('*.log'):
        try:
            # 最終更新から7日以上
            mtime = log_file.stat().st_mtime
            age_days = (datetime.now().timestamp() - mtime) / 86400
            
            if age_days > 7 and log_file.stat().st_size > 100 * 1024 * 1024:  # 100MB以上
                log_file.unlink()
                deleted_count += 1
                logger.info(f"  削除: {log_file.name}")
        
        except Exception as e:
            logger.warning(f"⚠️  削除失敗 ({log_file}): {e}")
    
    logger.info(f"✅ {deleted_count}件の古いログを削除")


def refresh_cache():
    """キャッシュリフレッシュ"""
    logger.info("🔥 キャッシュリフレッシュ...")
    
    try:
        from core.db_manager_cached import CachedDatabaseManager
        
        db = CachedDatabaseManager()
        db.warm_cache()
        db.close()
        
        logger.info("✅ キャッシュリフレッシュ完了")
    
    except Exception as e:
        logger.error(f"❌ キャッシュリフレッシュ失敗: {e}")


def update_rag_index():
    """RAGインデックス更新"""
    logger.info("🔍 RAGインデックス更新...")
    
    try:
        from ai.rag_enhanced import rag
        
        if rag:
            count = rag.import_from_files(
                '/root/trinity_workspace/docs',
                extensions=['.md', '.txt']
            )
            logger.info(f"✅ {count}件のドキュメントをインデックス化")
        else:
            logger.warning("⚠️  RAG未初期化")
    
    except Exception as e:
        logger.error(f"❌ RAGインデックス更新失敗: {e}")


def generate_report():
    """統計レポート生成"""
    logger.info("📊 統計レポート生成...")
    
    db = DatabaseManager()
    
    try:
        # タスク統計
        all_tasks = db.get_tasks()
        by_status = {}
        for task in all_tasks:
            status = task['status']
            by_status[status] = by_status.get(status, 0) + 1
        
        # DBサイズ
        db_size = os.path.getsize('/root/trinity_workspace/shared/tasks.db') / 1024 / 1024
        
        # ディスク使用率
        import shutil
        usage = shutil.disk_usage('/')
        disk_percent = (usage.used / usage.total) * 100
        disk_free = usage.free / 1024**3
        
        # レポート生成
        report = f"""
# Trinity v2.1 メンテナンスレポート

**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## タスク統計
- 総タスク数: {len(all_tasks)}
"""
        
        for status, count in by_status.items():
            report += f"- {status}: {count}件\n"
        
        report += f"""
## システム情報
- データベースサイズ: {db_size:.2f} MB
- ディスク使用率: {disk_percent:.1f}%
- ディスク空き容量: {disk_free:.1f} GB

## メンテナンス状態
✅ すべてのメンテナンスタスクが完了しました

---
"""
        
        # レポート保存
        report_path = f'/root/trinity_workspace/reports/maintenance_{datetime.now().strftime("%Y%m%d")}.md'
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"✅ レポート生成: {report_path}")
        
        # コンソール出力
        print(report)
    
    except Exception as e:
        logger.error(f"❌ レポート生成失敗: {e}")
    finally:
        db.close()


def main():
    """メインメンテナンス実行"""
    logger.info("🚀 Trinity v2.1 自動メンテナンス開始")
    logger.info("="*60)
    
    # 1. タスク履歴クリーンアップ
    cleanup_task_history()
    
    # 2. 古いログ削除
    cleanup_old_logs()
    
    # 3. キャッシュリフレッシュ
    refresh_cache()
    
    # 4. RAGインデックス更新
    update_rag_index()
    
    # 5. レポート生成
    generate_report()
    
    logger.info("="*60)
    logger.info("✅ Trinity v2.1 自動メンテナンス完了！")


if __name__ == '__main__':
    main()

