#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary バックアップ・復旧機能
データベースと設定ファイルのバックアップ・復旧
"""

import sys
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from manaos_logger import get_logger

logger = get_logger(__name__)


class FileSecretaryBackup:
    """File Secretaryバックアップシステム"""
    
    def __init__(self, backup_dir: str = "backups"):
        """
        初期化
        
        Args:
            backup_dir: バックアップディレクトリ
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_database(self, db_path: str = "file_secretary.db") -> Optional[str]:
        """
        データベースバックアップ
        
        Args:
            db_path: データベースファイルパス
            
        Returns:
            バックアップファイルパス
        """
        db_file = Path(db_path)
        if not db_file.exists():
            logger.error(f"データベースファイルが見つかりません: {db_path}")
            return None
        
        # バックアップファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"file_secretary_{timestamp}.db"
        
        try:
            # データベースファイルをコピー
            shutil.copy2(db_file, backup_file)
            
            # WALファイルもコピー（存在する場合）
            wal_file = Path(f"{db_path}-wal")
            if wal_file.exists():
                shutil.copy2(wal_file, self.backup_dir / f"file_secretary_{timestamp}.db-wal")
            
            shm_file = Path(f"{db_path}-shm")
            if shm_file.exists():
                shutil.copy2(shm_file, self.backup_dir / f"file_secretary_{timestamp}.db-shm")
            
            logger.info(f"✅ データベースバックアップ完了: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"❌ データベースバックアップエラー: {e}")
            return None
    
    def restore_database(self, backup_file: str, db_path: str = "file_secretary.db") -> bool:
        """
        データベース復旧
        
        Args:
            backup_file: バックアップファイルパス
            db_path: 復旧先データベースファイルパス
            
        Returns:
            成功したかどうか
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            logger.error(f"バックアップファイルが見つかりません: {backup_file}")
            return False
        
        db_file = Path(db_path)
        
        try:
            # 既存のデータベースファイルをバックアップ（念のため）
            if db_file.exists():
                old_backup = self.backup_dir / f"file_secretary_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(db_file, old_backup)
                logger.info(f"既存データベースをバックアップ: {old_backup}")
            
            # バックアップから復旧
            shutil.copy2(backup_path, db_file)
            
            # WALファイルも復旧（存在する場合）
            wal_backup = Path(f"{backup_file}-wal")
            if wal_backup.exists():
                shutil.copy2(wal_backup, Path(f"{db_path}-wal"))
            
            shm_backup = Path(f"{backup_file}-shm")
            if shm_backup.exists():
                shutil.copy2(shm_backup, Path(f"{db_path}-shm"))
            
            logger.info(f"✅ データベース復旧完了: {db_path}")
            return True
        except Exception as e:
            logger.error(f"❌ データベース復旧エラー: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        バックアップ一覧取得
        
        Returns:
            バックアップ情報リスト
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("file_secretary_*.db"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "file": str(backup_file.name),
                "path": str(backup_file),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return backups
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        古いバックアップを削除
        
        Args:
            keep_count: 保持するバックアップ数
            
        Returns:
            削除したバックアップ数
        """
        backups = sorted(self.backup_dir.glob("file_secretary_*.db"), reverse=True)
        
        if len(backups) <= keep_count:
            return 0
        
        deleted_count = 0
        for backup_file in backups[keep_count:]:
            try:
                backup_file.unlink()
                # 関連ファイルも削除
                wal_file = Path(f"{backup_file}-wal")
                if wal_file.exists():
                    wal_file.unlink()
                shm_file = Path(f"{backup_file}-shm")
                if shm_file.exists():
                    shm_file.unlink()
                deleted_count += 1
                logger.info(f"古いバックアップを削除: {backup_file.name}")
            except Exception as e:
                logger.error(f"バックアップ削除エラー: {e}")
        
        return deleted_count


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='File Secretary バックアップ・復旧')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup'],
                       help='実行するアクション')
    parser.add_argument('--backup-file', help='復旧するバックアップファイル（restore時）')
    parser.add_argument('--db-path', default='file_secretary.db',
                       help='データベースファイルパス')
    parser.add_argument('--backup-dir', default='backups',
                       help='バックアップディレクトリ')
    parser.add_argument('--keep', type=int, default=10,
                       help='保持するバックアップ数（cleanup時）')
    
    args = parser.parse_args()
    
    backup = FileSecretaryBackup(backup_dir=args.backup_dir)
    
    if args.action == 'backup':
        result = backup.backup_database(db_path=args.db_path)
        if result:
            print(f"✅ バックアップ完了: {result}")
        else:
            print("❌ バックアップ失敗")
            sys.exit(1)
    
    elif args.action == 'restore':
        if not args.backup_file:
            print("❌ --backup-file を指定してください")
            sys.exit(1)
        
        if backup.restore_database(args.backup_file, db_path=args.db_path):
            print(f"✅ 復旧完了: {args.db_path}")
        else:
            print("❌ 復旧失敗")
            sys.exit(1)
    
    elif args.action == 'list':
        backups = backup.list_backups()
        print(f"\nバックアップ一覧 ({len(backups)}件):")
        for b in backups:
            print(f"  {b['file']}")
            print(f"    サイズ: {b['size_mb']}MB")
            print(f"    作成日時: {b['created_at']}")
    
    elif args.action == 'cleanup':
        deleted = backup.cleanup_old_backups(keep_count=args.keep)
        print(f"✅ {deleted}件の古いバックアップを削除しました")


if __name__ == '__main__':
    main()






















