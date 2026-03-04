#!/usr/bin/env python3
"""
保管・削除ポリシーの自動化

保持期間ルール:
- Rawログ（会話等）: 90日で自動削除
- 要約: 無期限
- 監査ログ: 1年
- "法的ホールド"フラグで削除停止
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MEMORY_DIR = Path("/root/.mana_memory")
DB_PATH = MEMORY_DIR / "hot_memory.db"
AUDIT_DB_PATH = MEMORY_DIR / "memory_audit.db"
OBSIDIAN_VAULT = Path("/root/Obsidian/ManaOS_Chronicle")


class RetentionPolicy:
    """保管・削除ポリシー"""

    def __init__(self):
        self.raw_log_retention_days = 90
        self.audit_log_retention_days = 365
        self.legal_hold_tag = "legal_hold"

    def apply_retention_policy(self, dry_run: bool = False) -> Dict:
        """保持期間ポリシーを適用"""
        results = {
            "raw_logs_deleted": 0,
            "audit_logs_deleted": 0,
            "legal_hold_protected": 0,
            "dry_run": dry_run
        }

        # 1. Rawログ（会話）の削除（90日以上）
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(DB_PATH))
                cur = conn.cursor()

                cutoff_date = (datetime.now() - timedelta(days=self.raw_log_retention_days)).isoformat()

                # 法的ホールドフラグをチェック
                cur.execute("""
                    SELECT id, metadata FROM memories
                    WHERE created_at < ?
                    AND (metadata IS NULL OR metadata NOT LIKE ?)
                """, (cutoff_date, f'%{self.legal_hold_tag}%'))

                to_delete = cur.fetchall()

                if not dry_run:
                    for memory_id, metadata in to_delete:
                        cur.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                    conn.commit()
                    results["raw_logs_deleted"] = len(to_delete)
                else:
                    results["raw_logs_deleted"] = len(to_delete)

                # 法的ホールド保護されたレコード数
                cur.execute("""
                    SELECT COUNT(*) FROM memories
                    WHERE created_at < ?
                    AND metadata LIKE ?
                """, (cutoff_date, f'%{self.legal_hold_tag}%'))
                results["legal_hold_protected"] = cur.fetchone()[0]

                conn.close()
            except Exception as e:
                logger.error(f"Rawログ削除エラー: {e}")

        # 2. 監査ログの削除（1年以上）
        if AUDIT_DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(AUDIT_DB_PATH))
                cur = conn.cursor()

                cutoff_date = (datetime.now() - timedelta(days=self.audit_log_retention_days)).isoformat()

                cur.execute("SELECT COUNT(*) FROM memory_audit WHERE created_at < ?", (cutoff_date,))
                count = cur.fetchone()[0]

                if not dry_run:
                    cur.execute("DELETE FROM memory_audit WHERE created_at < ?", (cutoff_date,))
                    conn.commit()
                    results["audit_logs_deleted"] = count
                else:
                    results["audit_logs_deleted"] = count

                conn.close()
            except Exception as e:
                logger.error(f"監査ログ削除エラー: {e}")

        return results

    def set_legal_hold(self, memory_id: int, hold: bool = True) -> bool:
        """法的ホールドフラグを設定"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()

            # 現在のメタデータを取得
            cur.execute("SELECT metadata FROM memories WHERE id = ?", (memory_id,))
            row = cur.fetchone()

            if row:
                metadata = json.loads(row[0]) if row[0] else {}

                if hold:
                    if 'tags' not in metadata:
                        metadata['tags'] = []
                    if self.legal_hold_tag not in metadata['tags']:
                        metadata['tags'].append(self.legal_hold_tag)
                else:
                    if 'tags' in metadata and self.legal_hold_tag in metadata['tags']:
                        metadata['tags'].remove(self.legal_hold_tag)

                cur.execute("UPDATE memories SET metadata = ? WHERE id = ?",
                          (json.dumps(metadata, ensure_ascii=False), memory_id))
                conn.commit()
                conn.close()

                logger.info(f"法的ホールド設定: memory_id={memory_id}, hold={hold}")
                return True
            else:
                logger.warning(f"記憶が見つかりません: memory_id={memory_id}")
                return False
        except Exception as e:
            logger.error(f"法的ホールド設定エラー: {e}")
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description='保管・削除ポリシー')
    parser.add_argument('--dry-run', action='store_true', help='ドライラン（削除しない）')
    parser.add_argument('--legal-hold', type=int, help='法的ホールド設定（memory_id）')
    parser.add_argument('--release-hold', type=int, help='法的ホールド解除（memory_id）')
    args = parser.parse_args()

    policy = RetentionPolicy()

    if args.legal_hold:
        policy.set_legal_hold(args.legal_hold, hold=True)
    elif args.release_hold:
        policy.set_legal_hold(args.release_hold, hold=False)
    else:
        results = policy.apply_retention_policy(dry_run=args.dry_run)
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()








