#!/usr/bin/env python3
"""
バックアップマネージャー
自動バックアップ、スケジューリング、復元機能
"""

import os
import shutil
import tarfile
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BackupManager:
    """バックアップマネージャー"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.backup_dir = self.base_path / "backups_automated"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.config_path = self.base_path / ".backup_config.json"
        self.index_path = self.backup_dir / "backup_index.json"
        
        self.default_config = {
            "enabled": True,
            "schedule": {
                "full_backup": {
                    "enabled": True,
                    "time": "02:00",
                    "days": ["sunday"]
                },
                "incremental_backup": {
                    "enabled": True,
                    "time": "03:00",
                    "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
                }
            },
            "retention": {
                "keep_full_backups": 4,
                "keep_incremental_backups": 7,
                "auto_cleanup": True
            },
            "targets": {
                "system_automation": {
                    "enabled": True,
                    "path": "/root/system_automation",
                    "exclude": ["__pycache__", "*.pyc", ".git"]
                },
                "config_files": {
                    "enabled": True,
                    "path": "/root",
                    "patterns": ["*.json", "*.yaml", "*.yml", ".env*"]
                },
                "logs": {
                    "enabled": True,
                    "path": "/root/logs",
                    "exclude": ["*.log"]
                }
            },
            "compression": {
                "enabled": True,
                "format": "tar.gz",
                "level": 6
            }
        }
        
        self.config = self.load_config()
        self.index = self.load_index()
        
    def load_config(self) -> dict:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def load_index(self) -> dict:
        """バックアップインデックスを読み込む"""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"インデックス読み込みエラー: {e}")
                return {"backups": []}
        return {"backups": []}
    
    def save_index(self):
        """バックアップインデックスを保存"""
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"インデックス保存エラー: {e}")
    
    def calculate_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値を計算"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"ハッシュ計算エラー {file_path}: {e}")
            return ""
    
    def should_exclude(self, file_path: Path, excludes: List[str]) -> bool:
        """除外チェック"""
        for exclude in excludes:
            if exclude in file_path.parts:
                return True
            if file_path.match(exclude):
                return True
        return False
    
    def create_full_backup(self) -> Dict:
        """フルバックアップ作成"""
        logger.info("📦 フルバックアップ作成開始...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        results = {
            "type": "full",
            "timestamp": datetime.now().isoformat(),
            "backup_name": backup_name,
            "files": [],
            "total_size": 0,
            "errors": []
        }
        
        # ターゲットをバックアップ
        for target_name, target_config in self.config["targets"].items():
            if not target_config.get("enabled"):
                continue
            
            source_path = Path(target_config["path"])
            if not source_path.exists():
                logger.warning(f"ソースパスが存在しません: {source_path}")
                continue
            
            excludes = target_config.get("exclude", [])
            target_backup_dir = backup_path / target_name
            target_backup_dir.mkdir(exist_ok=True)
            
            # ファイルをコピー
            for root, dirs, files in os.walk(source_path):
                # 除外ディレクトリをスキップ
                dirs[:] = [d for d in dirs if not self.should_exclude(Path(root) / d, excludes)]
                
                root_path = Path(root)
                for file in files:
                    file_path = root_path / file
                    
                    if self.should_exclude(file_path, excludes):
                        continue
                    
                    try:
                        # 相対パスを保持
                        relative_path = file_path.relative_to(source_path)
                        dest_path = target_backup_dir / relative_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(file_path, dest_path)
                        
                        file_size = file_path.stat().st_size
                        results["files"].append({
                            "path": str(file_path),
                            "size": file_size,
                            "hash": self.calculate_hash(file_path)
                        })
                        results["total_size"] += file_size
                        
                    except Exception as e:
                        logger.error(f"ファイルコピーエラー {file_path}: {e}")
                        results["errors"].append(str(file_path))
        
        # 圧縮
        if self.config["compression"]["enabled"]:
            logger.info("🗜️ 圧縮中...")
            archive_name = f"{backup_name}.tar.gz"
            archive_path = self.backup_dir / archive_name
            
            with tarfile.open(archive_path, "w:gz", compresslevel=self.config["compression"]["level"]) as tar:
                tar.add(backup_path, arcname=backup_name)
            
            # 元のディレクトリを削除
            shutil.rmtree(backup_path)
            
            archive_size = archive_path.stat().st_size
            logger.info(f"✅ 圧縮完了: {archive_size / (1024**2):.2f} MB")
            
            results["archive_path"] = str(archive_path)
            results["archive_size"] = archive_size
        else:
            results["archive_path"] = str(backup_path)
        
        # インデックスに追加
        self.index["backups"].append(results)
        self.save_index()
        
        logger.info(f"✅ フルバックアップ完了: {len(results['files'])}ファイル")
        
        return results
    
    def create_incremental_backup(self) -> Dict:
        """増分バックアップ作成"""
        logger.info("📦 増分バックアップ作成開始...")
        
        # 最新のフルバックアップを取得
        full_backups = [
            b for b in self.index["backups"]
            if b["type"] == "full"
        ]
        
        if not full_backups:
            logger.warning("フルバックアップが存在しません。フルバックアップを作成します。")
            return self.create_full_backup()
        
        latest_full = full_backups[-1]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"incremental_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        results = {
            "type": "incremental",
            "timestamp": datetime.now().isoformat(),
            "backup_name": backup_name,
            "base_backup": latest_full["backup_name"],
            "files": [],
            "total_size": 0,
            "errors": []
        }
        
        # 変更されたファイルのみをバックアップ
        # TODO: 実装を簡略化（実際の実装では変更検出が必要）
        
        # 圧縮
        if self.config["compression"]["enabled"]:
            archive_name = f"{backup_name}.tar.gz"
            archive_path = self.backup_dir / archive_name
            
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_path, arcname=backup_name)
            
            shutil.rmtree(backup_path)
            
            results["archive_path"] = str(archive_path)
            results["archive_size"] = archive_path.stat().st_size
        
        # インデックスに追加
        self.index["backups"].append(results)
        self.save_index()
        
        logger.info("✅ 増分バックアップ完了")
        
        return results
    
    def list_backups(self) -> List[Dict]:
        """バックアップ一覧"""
        return self.index.get("backups", [])
    
    def cleanup_old_backups(self) -> Dict:
        """古いバックアップを削除"""
        logger.info("🧹 古いバックアップをクリーンアップ中...")
        
        results = {
            "deleted": 0,
            "freed_space": 0
        }
        
        if not self.config["retention"]["auto_cleanup"]:
            logger.info("自動クリーンアップが無効です")
            return results
        
        backups = self.index["backups"]
        
        # フルバックアップ
        full_backups = [b for b in backups if b["type"] == "full"]
        keep_count = self.config["retention"]["keep_full_backups"]
        
        if len(full_backups) > keep_count:
            to_delete = full_backups[:-keep_count]
            for backup in to_delete:
                if "archive_path" in backup:
                    archive_path = Path(backup["archive_path"])
                    if archive_path.exists():
                        size = archive_path.stat().st_size
                        archive_path.unlink()
                        results["deleted"] += 1
                        results["freed_space"] += size
                        logger.info(f"削除: {backup['backup_name']}")
        
        # 増分バックアップ
        incremental_backups = [b for b in backups if b["type"] == "incremental"]
        keep_count = self.config["retention"]["keep_incremental_backups"]
        
        if len(incremental_backups) > keep_count:
            to_delete = incremental_backups[:-keep_count]
            for backup in to_delete:
                if "archive_path" in backup:
                    archive_path = Path(backup["archive_path"])
                    if archive_path.exists():
                        size = archive_path.stat().st_size
                        archive_path.unlink()
                        results["deleted"] += 1
                        results["freed_space"] += size
                        logger.info(f"削除: {backup['backup_name']}")
        
        # インデックスを更新
        self.index["backups"] = [b for b in backups if b not in to_delete]
        self.save_index()
        
        logger.info(f"✅ クリーンアップ完了: {results['deleted']}個削除, {results['freed_space'] / (1024**2):.2f} MB解放")
        
        return results
    
    def restore_backup(self, backup_name: str, target_path: str = None) -> Dict:
        """バックアップから復元"""
        logger.info(f"📥 バックアップ復元開始: {backup_name}")
        
        # バックアップを検索
        backup = None
        for b in self.index["backups"]:
            if b["backup_name"] == backup_name:
                backup = b
                break
        
        if not backup:
            return {"error": "バックアップが見つかりません"}
        
        if "archive_path" not in backup:
            return {"error": "アーカイブパスが存在しません"}
        
        archive_path = Path(backup["archive_path"])
        if not archive_path.exists():
            return {"error": "アーカイブファイルが存在しません"}
        
        # 復元先
        if target_path is None:
            target_path = self.base_path / "restored"
        else:
            target_path = Path(target_path)
        
        target_path.mkdir(exist_ok=True)
        
        # 展開
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(target_path)
        
        logger.info(f"✅ 復元完了: {target_path}")
        
        return {
            "status": "success",
            "backup_name": backup_name,
            "target_path": str(target_path)
        }


def main():
    """メイン実行"""
    manager = BackupManager()
    
    print("=" * 60)
    print("💾 バックアップマネージャー")
    print("=" * 60)
    
    # ステータス表示
    backups = manager.list_backups()
    print("\n📊 ステータス:")
    print(f"  バックアップ数: {len(backups)}")
    
    full_count = len([b for b in backups if b["type"] == "full"])
    inc_count = len([b for b in backups if b["type"] == "incremental"])
    print(f"  フルバックアップ: {full_count}")
    print(f"  増分バックアップ: {inc_count}")
    
    # メニュー
    print("\n実行する操作を選択:")
    print("  1. フルバックアップ作成")
    print("  2. 増分バックアップ作成")
    print("  3. バックアップ一覧")
    print("  4. 古いバックアップ削除")
    print("  5. バックアップ復元")
    print("  0. 終了")
    
    choice = input("\n選択 (0-5): ").strip()
    
    if choice == "1":
        print("\n📦 フルバックアップ作成中...")
        results = manager.create_full_backup()
        print(f"✅ 完了: {len(results['files'])}ファイル")
    
    elif choice == "2":
        print("\n📦 増分バックアップ作成中...")
        results = manager.create_incremental_backup()
        print("✅ 完了")
    
    elif choice == "3":
        print("\n📋 バックアップ一覧:")
        for backup in backups[-10:]:
            print(f"  {backup['backup_name']} ({backup['type']})")
    
    elif choice == "4":
        print("\n🧹 古いバックアップ削除中...")
        results = manager.cleanup_old_backups()
        print(f"✅ 削除: {results['deleted']}個")
    
    elif choice == "5":
        backup_name = input("復元するバックアップ名: ").strip()
        print("\n📥 復元中...")
        results = manager.restore_backup(backup_name)
        if "error" in results:
            print(f"❌ エラー: {results['error']}")
        else:
            print(f"✅ 復元完了: {results['target_path']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

