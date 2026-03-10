#!/usr/bin/env python3
"""
Trinity Multi-Agent System - Storage Migration Tool
/root から /mnt/storage500 への安全な移行ツール
"""

import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

class StorageMigrator:
    def __init__(self):
        self.root_dir = Path("/root")
        self.storage_dir = Path("/mnt/storage500")
        self.log_file = self.root_dir / "migration_log.txt"
        
    def log(self, message):
        """ログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")
    
    def check_storage500(self):
        """追加ストレージの確認"""
        self.log("🔍 Checking /mnt/storage500...")
        
        if not self.storage_dir.exists():
            self.log("❌ /mnt/storage500 does not exist!")
            return False
        
        # 空き容量確認
        stat = os.statvfs(str(self.storage_dir))  # type: ignore[attr-defined]
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        self.log(f"✅ /mnt/storage500 available: {free_gb:.1f} GB free")
        return free_gb > 5  # 5GB以上の空きが必要
    
    def create_directories(self):
        """移行先ディレクトリ構造作成"""
        self.log("📁 Creating directory structure...")
        
        dirs = [
            "backups",
            "logs_archive",
            "projects",
            "generated_content",
            "databases_archive",
            "dev_tools",
            "docs_archive"
        ]
        
        for dir_name in dirs:
            target_dir = self.storage_dir / dir_name
            target_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"  ✓ Created: {target_dir}")
    
    def get_dir_size(self, path):
        """ディレクトリサイズ取得（MB）"""
        try:
            result = subprocess.run(
                ["du", "-sm", str(path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return int(result.stdout.split()[0])
            return 0
        except subprocess.SubprocessError:
            return 0
    
    def migrate_directory(self, source_name, target_category, create_symlink=True):
        """ディレクトリを安全に移行"""
        source = self.root_dir / source_name
        
        if not source.exists():
            self.log(f"⚠️  Skip: {source_name} (does not exist)")
            return False
        
        # サイズ確認
        size_mb = self.get_dir_size(source)
        self.log(f"📦 Migrating: {source_name} ({size_mb} MB)")
        
        target = self.storage_dir / target_category / source_name
        
        try:
            # rsyncで安全にコピー
            self.log(f"  → Copying to {target}...")
            result = subprocess.run(
                ["rsync", "-av", "--progress", str(source) + "/", str(target) + "/"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                self.log(f"  ❌ Copy failed: {result.stderr}")
                return False
            
            # コピー成功を確認
            target_size = self.get_dir_size(target)
            if abs(size_mb - target_size) > 1:  # 1MB以上の差があればエラー
                self.log(f"  ❌ Size mismatch: source={size_mb}MB, target={target_size}MB")
                return False
            
            self.log(f"  ✓ Copy verified ({target_size} MB)")
            
            # 元のディレクトリを削除
            self.log("  → Removing source...")
            shutil.rmtree(source)
            
            # シンボリックリンク作成
            if create_symlink:
                self.log("  → Creating symlink...")
                os.symlink(target, source)
                self.log(f"  ✓ Symlink created: {source} -> {target}")
            
            self.log(f"✅ Migration complete: {source_name}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error migrating {source_name}: {e}")
            return False
    
    def migrate_file(self, source_name, target_category):
        """ファイルを安全に移行"""
        source = self.root_dir / source_name
        
        if not source.exists():
            self.log(f"⚠️  Skip: {source_name} (does not exist)")
            return False
        
        size_mb = source.stat().st_size / (1024**2)
        self.log(f"📄 Migrating file: {source_name} ({size_mb:.1f} MB)")
        
        target = self.storage_dir / target_category / source_name
        
        try:
            shutil.copy2(source, target)
            self.log(f"  ✓ Copied to {target}")
            
            # 検証
            if source.stat().st_size == target.stat().st_size:
                source.unlink()
                self.log(f"✅ File migration complete: {source_name}")
                return True
            else:
                self.log(f"❌ Size mismatch for {source_name}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error migrating file {source_name}: {e}")
            return False
    
    def run_priority_a(self):
        """優先度A: すぐに移動すべきもの"""
        self.log("\n🎯 Priority A: Large directories")
        self.log("=" * 60)
        
        migrations = [
            # バックアップ
            ("backups", "backups", False),  # シンボリック不要
            ("backups_automated", "backups", False),
            ("backups_ultimate", "backups", False),
            ("mana_backups", "backups", False),
            ("smart_backups", "backups", False),
            
            # ログアーカイブ
            ("logs_archive", "logs_archive", False),
            ("logs_archive_20251007", "logs_archive", False),
            
            # プロジェクト
            ("localGPT", "projects", True),  # シンボリック必要
            ("open-webui", "projects", True),
            ("chatbot-ui", "projects", True),
            ("noVNC", "projects", True),
            
            # 画像
            ("generated_images", "generated_content", True),
            ("mana_generated_images", "generated_content", True),
            ("downloaded_images", "generated_content", True),
            ("ai_image_gallery", "generated_content", True),
        ]
        
        successful = 0
        failed = 0
        
        for source, category, symlink in migrations:
            if self.migrate_directory(source, category, symlink):
                successful += 1
            else:
                failed += 1
        
        self.log(f"\n📊 Priority A Results: {successful} successful, {failed} failed")
        return successful, failed
    
    def check_disk_usage(self):
        """ディスク使用率確認"""
        self.log("\n💾 Checking disk usage...")
        
        for mount in ["/", "/mnt/storage500"]:
            stat = os.statvfs(mount)  # type: ignore[attr-defined]
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            used_gb = ((stat.f_blocks - stat.f_bavail) * stat.f_frsize) / (1024**3)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            usage_pct = (used_gb / total_gb) * 100
            
            self.log(f"{mount}: {used_gb:.1f}GB / {total_gb:.1f}GB ({usage_pct:.1f}% used, {free_gb:.1f}GB free)")

def main():
    """メイン処理"""
    print("🎭 Trinity Storage Migration Tool")
    print("=" * 60)
    
    migrator = StorageMigrator()
    
    # ストレージ確認
    if not migrator.check_storage500():
        print("❌ Cannot proceed: /mnt/storage500 not available or insufficient space")
        return 1
    
    # 現在のディスク使用率
    migrator.check_disk_usage()
    
    # ディレクトリ構造作成
    migrator.create_directories()
    
    # 優先度Aの移行実行
    print("\n⚠️  Starting migration... This may take several minutes.")
    print("Press Ctrl+C to cancel.\n")
    
    try:
        successful, failed = migrator.run_priority_a()
        
        # 完了後のディスク使用率
        migrator.check_disk_usage()
        
        print("\n" + "=" * 60)
        print("🎉 Migration complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📝 Log: {migrator.log_file}")
        
        return 0 if failed == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())



