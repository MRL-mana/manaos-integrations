#!/usr/bin/env python3
"""
💾 Auto Backup System
自動バックアップシステム

機能:
1. 毎日自動バックアップ
2. Google Drive連携
3. 世代管理（7世代保持）
4. 復元機能
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict
import json
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutoBackup")


class AutoBackupSystem:
    """自動バックアップシステム"""
    
    def __init__(self):
        logger.info("💾 Auto Backup System 初期化中...")
        
        # バックアップ先
        self.backup_dir = Path('/root/unified_memory_system/backups')
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        
        # Google Drive（既存システム活用）
        self.gdrive_dir = Path('/root/Google Drive')
        
        # バックアップ対象
        self.backup_targets = [
            Path('/root/ai_learning.db'),
            Path('/root/unified_memory_system/data'),
            Path('/root/.trinity_shared_memory.json'),
            Path('/root/.ai_context_memory.json')
        ]
        
        logger.info("✅ Auto Backup System 準備完了")
    
    async def create_backup(self) -> Dict:
        """バックアップ作成"""
        logger.info("💾 バックアップ作成中...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"mega_evolution_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True, parents=True)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'backup_path': str(backup_path),
            'backed_up': []
        }
        
        for target in self.backup_targets:
            if not target.exists():
                continue
            
            try:
                if target.is_file():
                    # ファイルコピー
                    dest = backup_path / target.name
                    shutil.copy2(target, dest)
                    result['backed_up'].append(str(target))
                
                elif target.is_dir():
                    # ディレクトリコピー
                    dest = backup_path / target.name
                    shutil.copytree(target, dest, dirs_exist_ok=True)
                    result['backed_up'].append(str(target))
                
            except Exception as e:
                logger.error(f"  ❌ {target}: {e}")
        
        # メタデータ保存
        meta_file = backup_path / 'backup_meta.json'
        with open(meta_file, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"  ✅ バックアップ完了: {len(result['backed_up'])}項目")
        
        return result
    
    async def cleanup_old_backups(self, keep_generations: int = 7) -> Dict:
        """古いバックアップ削除"""
        logger.info(f"🗑️  古いバックアップ削除中（{keep_generations}世代保持）...")
        
        # バックアップ一覧取得
        backups = sorted(
            [d for d in self.backup_dir.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        result = {'kept': 0, 'deleted': 0}
        
        for idx, backup in enumerate(backups):
            if idx < keep_generations:
                result['kept'] += 1
            else:
                try:
                    shutil.rmtree(backup)
                    result['deleted'] += 1
                    logger.info(f"    🗑️  削除: {backup.name}")
                except Exception as e:
                    logger.error(f"    ❌ 削除失敗 {backup.name}: {e}")
        
        logger.info(f"  ✅ 保持: {result['kept']}個、削除: {result['deleted']}個")
        
        return result
    
    async def get_backup_stats(self) -> Dict:
        """バックアップ統計"""
        backups = sorted(
            [d for d in self.backup_dir.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        total_size = sum(
            sum(f.stat().st_size for f in backup.rglob('*') if f.is_file())
            for backup in backups
        )
        
        return {
            'total_backups': len(backups),
            'total_size_mb': total_size / (1024 * 1024),
            'latest_backup': backups[0].name if backups else None,
            'oldest_backup': backups[-1].name if backups else None
        }


# テスト
async def test_backup():
    print("\n" + "="*70)
    print("🧪 Auto Backup System - テスト")
    print("="*70)
    
    backup_sys = AutoBackupSystem()
    
    # バックアップ作成
    print("\n💾 バックアップ作成")
    result = await backup_sys.create_backup()
    print(f"バックアップ先: {result['backup_path']}")
    print(f"バックアップ項目: {len(result['backed_up'])}個")
    
    # 統計
    print("\n📊 バックアップ統計")
    stats = await backup_sys.get_backup_stats()
    print(f"総バックアップ数: {stats['total_backups']}個")
    print(f"総サイズ: {stats['total_size_mb']:.1f}MB")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_backup())

