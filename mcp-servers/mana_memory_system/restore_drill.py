#!/usr/bin/env python3
"""
復元ドリル（Restore Drill）
バックアップから復元できることを証明するテスト

合格条件:
- RTO（復旧時間） ≤ 10分
- RPO（データ損失許容） ≤ 24時間
- 復元後のデータ完全性（件数・ハッシュ一致）
"""

import sqlite3
import hashlib
import json
import shutil
import tarfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MEMORY_DIR = Path("/root/.mana_memory")
DB_PATH = MEMORY_DIR / "hot_memory.db"
BACKUP_DIR = Path("/root/.mana_memory_backups")
RESTORE_TEST_DIR = Path("/root/.mana_memory/restore_test")
GDRIVE_BACKUP_DIR = Path("/root/Google Drive/ManaMemoryArchive/encrypted_backups")


class RestoreDrill:
    """復元ドリル"""

    def __init__(self):
        self.restore_dir = RESTORE_TEST_DIR
        self.restore_dir.mkdir(parents=True, exist_ok=True)

    def dump_database_info(self, db_path: Path) -> Dict:
        """データベース情報をダンプ"""
        if not db_path.exists():
            return {"db": str(db_path), "count": 0, "ids_hash": None, "exists": False}

        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()

            # 件数取得
            cur.execute("SELECT COUNT(*) FROM memories")
            count = cur.fetchone()[0]

            # IDハッシュ取得
            cur.execute("SELECT GROUP_CONCAT(id, '|') FROM memories ORDER BY id")
            ids_str = cur.fetchone()[0] or ''
            ids_hash = hashlib.sha256(ids_str.encode()).hexdigest() if ids_str else None

            # 重要度分布
            cur.execute("SELECT importance, COUNT(*) FROM memories GROUP BY importance")
            importance_dist = dict(cur.fetchall())

            # カテゴリ分布
            cur.execute("SELECT category, COUNT(*) FROM memories WHERE category IS NOT NULL GROUP BY category")
            category_dist = dict(cur.fetchall())

            conn.close()

            return {
                "db": str(db_path),
                "count": count,
                "ids_hash": ids_hash,
                "importance_dist": importance_dist,
                "category_dist": category_dist,
                "exists": True
            }
        except Exception as e:
            logger.error(f"データベースダンプエラー: {e}")
            return {"db": str(db_path), "error": str(e), "exists": False}

    def find_latest_backup(self) -> Optional[Path]:
        """最新のバックアップを検索"""
        # ローカルバックアップ
        local_backups = list(BACKUP_DIR.glob("hot_memory_*.tar.gz"))
        if local_backups:
            latest = max(local_backups, key=lambda p: p.stat().st_mtime)
            logger.info(f"最新ローカルバックアップ: {latest}")
            return latest

        # Google Driveバックアップ
        if GDRIVE_BACKUP_DIR.exists():
            gdrive_backups = list(GDRIVE_BACKUP_DIR.rglob("hot_memory_*.tar.gz*"))
            if gdrive_backups:
                latest = max(gdrive_backups, key=lambda p: p.stat().st_mtime)
                logger.info(f"最新Google Driveバックアップ: {latest}")
                return latest

        return None

    def decrypt_backup(self, backup_path: Path) -> Optional[Path]:
        """バックアップを復号化"""
        if backup_path.suffix == '.gpg':
            # GPG暗号化ファイル
            decrypted_path = backup_path.with_suffix('')
            try:
                result = subprocess.run(
                    ["gpg", "--decrypt", "--output", str(decrypted_path), str(backup_path)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    logger.info(f"復号化成功: {decrypted_path}")
                    return decrypted_path
                else:
                    logger.error(f"復号化失敗: {result.stderr}")
                    return None
            except Exception as e:
                logger.error(f"復号化エラー: {e}")
                return None
        else:
            # 暗号化されていない
            return backup_path

    def extract_backup(self, backup_path: Path) -> Optional[Path]:
        """バックアップを展開"""
        try:
            extract_dir = self.restore_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)

            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(extract_dir)

            # hot_memory.dbを探す
            db_file = extract_dir / "hot_memory" / "hot_memory.db"
            if not db_file.exists():
                # 別の構造を試す
                db_file = extract_dir.rglob("hot_memory.db")
                db_file = next(db_file, None)

            if db_file and db_file.exists():
                logger.info(f"展開成功: {db_file}")
                return db_file
            else:
                logger.error("hot_memory.dbが見つかりません")
                return None
        except Exception as e:
            logger.error(f"展開エラー: {e}")
            return None

    def restore_database(self, source_db: Path) -> bool:
        """データベースを復元"""
        try:
            restore_db = self.restore_dir / "hot_memory.db"
            shutil.copy2(source_db, restore_db)
            logger.info(f"復元成功: {restore_db}")
            return True
        except Exception as e:
            logger.error(f"復元エラー: {e}")
            return False

    def verify_restore(self) -> Dict:
        """復元の検証"""
        start_time = time.time()

        # 本番DB情報
        production_info = self.dump_database_info(DB_PATH)

        # 復元DB情報
        restore_db = self.restore_dir / "hot_memory.db"
        restore_info = self.dump_database_info(restore_db)

        # 比較
        elapsed_time = time.time() - start_time

        # 合格条件チェック
        count_match = production_info.get("count") == restore_info.get("count")
        hash_match = production_info.get("ids_hash") == restore_info.get("ids_hash")
        rto_ok = elapsed_time <= 600  # 10分以内

        result = {
            "success": count_match and hash_match and rto_ok,
            "elapsed_seconds": elapsed_time,
            "rto_ok": rto_ok,
            "production": production_info,
            "restored": restore_info,
            "count_match": count_match,
            "hash_match": hash_match,
            "timestamp": datetime.now().isoformat()
        }

        return result

    def run_drill(self) -> Dict:
        """復元ドリル実行"""
        logger.info("🔄 復元ドリル開始")
        start_time = time.time()

        # 1. 最新バックアップを検索
        backup_path = self.find_latest_backup()
        if not backup_path:
            return {
                "success": False,
                "error": "バックアップが見つかりません"
            }

        # 2. 復号化（必要に応じて）
        decrypted_path = self.decrypt_backup(backup_path)
        if not decrypted_path:
            return {
                "success": False,
                "error": "復号化失敗"
            }

        # 3. 展開
        extracted_db = self.extract_backup(decrypted_path)
        if not extracted_db:
            return {
                "success": False,
                "error": "展開失敗"
            }

        # 4. 復元
        if not self.restore_database(extracted_db):
            return {
                "success": False,
                "error": "復元失敗"
            }

        # 5. 検証
        verification = self.verify_restore()

        elapsed_time = time.time() - start_time

        result = {
            "success": verification["success"],
            "elapsed_seconds": elapsed_time,
            "rto_ok": elapsed_time <= 600,  # 10分以内
            "verification": verification,
            "backup_path": str(backup_path),
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"✅ 復元ドリル完了: {result['success']}")
        logger.info(f"   経過時間: {elapsed_time:.2f}秒")
        logger.info(f"   RTO: {'✅ OK' if result['rto_ok'] else '❌ NG'}")
        logger.info(f"   件数一致: {'✅' if verification['count_match'] else '❌'}")
        logger.info(f"   ハッシュ一致: {'✅' if verification['hash_match'] else '❌'}")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='復元ドリル')
    parser.add_argument('--verify-only', action='store_true', help='検証のみ（復元はスキップ）')
    args = parser.parse_args()

    drill = RestoreDrill()

    if args.verify_only:
        result = drill.verify_restore()
    else:
        result = drill.run_drill()

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("success"):
        exit(1)


if __name__ == '__main__':
    main()








