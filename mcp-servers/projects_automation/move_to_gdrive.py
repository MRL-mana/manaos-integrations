#!/usr/bin/env python3
"""
Trinity Multi-Agent System - Google Drive Migration Tool
大きなファイル/ディレクトリをGoogle Driveに移動
削除せずに移動するから安全！
"""

import subprocess
import shutil
from pathlib import Path
from datetime import datetime

class GDriveMigrator:
    def __init__(self):
        self.root_dir = Path("/root")
        self.gdrive_dir = Path("/root/Google Drive")
        self.log_file = self.root_dir / "gdrive_migration.log"
        self.total_moved = 0
        
        # Google Driveのアーカイブディレクトリ
        self.archive_base = self.gdrive_dir / "ManaOS_Archive" / datetime.now().strftime("%Y%m%d")
        
    def log(self, message):
        """ログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")
    
    def check_gdrive(self):
        """Google Drive確認"""
        self.log("🔍 Checking Google Drive...")
        
        if not self.gdrive_dir.exists():
            self.log("❌ Google Drive not found at /root/Google Drive")
            return False
        
        self.log(f"✅ Google Drive found: {self.gdrive_dir}")
        return True
    
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
    
    def move_to_gdrive(self, source_path, category, create_symlink=False):
        """
        ファイル/ディレクトリをGoogle Driveに移動
        
        Args:
            source_path: 移動元パス
            category: カテゴリ（backups、logs、projects等）
            create_symlink: シンボリックリンク作成するか
        """
        source = Path(source_path)
        
        if not source.exists():
            self.log(f"⚠️  Skip: {source.name} (does not exist)")
            return False
        
        # サイズ確認
        if source.is_dir():
            size_mb = self.get_dir_size(source)
        else:
            size_mb = source.stat().st_size / (1024**2)
        
        self.log(f"📦 Moving: {source.name} ({size_mb:.1f} MB)")
        
        # 移動先ディレクトリ作成
        target_category = self.archive_base / category
        target_category.mkdir(parents=True, exist_ok=True)
        
        target = target_category / source.name
        
        try:
            # 移動
            self.log(f"  → Moving to {target}...")
            shutil.move(str(source), str(target))
            
            # シンボリックリンク作成
            if create_symlink:
                self.log("  → Creating symlink...")
                source.symlink_to(target)
                self.log(f"  ✅ Symlink created: {source} -> {target}")
            
            self.log("✅ Moved successfully")
            self.total_moved += size_mb
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to move {source.name}: {e}")
            return False
    
    def move_priority_items(self):
        """優先度の高いアイテムを移動"""
        self.log("\n🎯 Moving priority items to Google Drive...")
        self.log("=" * 60)
        
        # 移動対象リスト（カテゴリ、パス、シンボリックリンク要否）
        items = [
            # バックアップ（シンボリック不要）
            ("backups", "backups", False),
            ("backups", "backups_automated", False),
            ("backups", "backups_ultimate", False),
            ("backups", "mana_backups", False),
            ("backups", "smart_backups", False),
            
            # ログアーカイブ（シンボリック不要）
            ("logs", "logs_archive", False),
            ("logs", "logs_archive_20251007", False),
            
            # 大規模プロジェクト（シンボリック必要）
            ("projects", "localGPT", True),
            ("projects", "open-webui", True),
            ("projects", "chatbot-ui", True),
            ("projects", "noVNC", True),
            ("projects", "MCP-Demo-Project", True),
            
            # 画像（シンボリック不要）
            ("media", "ai_image_gallery", False),
            ("media", "generated_images", False),
            ("media", "mana_generated_images", False),
            ("media", "downloaded_images", False),
            
            # アーカイブ（シンボリック不要）
            ("archives", "archive", False),
            ("archives", "old_docs_archive", False),
            ("archives", "manaos_integration_backup", False),
            
            # テストファイル（シンボリック不要）
            ("tests", "batch_processing_tests", False),
            ("tests", "mock_google_drive_tests", False),
            ("tests", "table_recognition_tests", False),
            
            # サンプル（シンボリック不要）
            ("samples", "sample-projects", False),
            
            # 古いワークスペース（シンボリック不要）
            ("old_workspace", "organized", False),
            ("old_workspace", "organized_files", False),
            ("old_workspace", "organized_workspace", False),
            ("old_workspace", "workspace_organized", False),
        ]
        
        successful = 0
        failed = 0
        
        for category, path_name, symlink in items:
            full_path = self.root_dir / path_name
            if self.move_to_gdrive(full_path, category, symlink):
                successful += 1
            else:
                failed += 1
        
        self.log(f"\n📊 Results: {successful} successful, {failed} failed")
        self.log(f"💾 Total moved: {self.total_moved:.1f} MB ({self.total_moved / 1024:.2f} GB)")
    
    def check_disk_usage(self):
        """ディスク使用率確認"""
        self.log("\n💾 Disk Usage:")
        
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.strip().split("\n"):
            self.log(f"  {line}")
    
    def run(self):
        """メイン処理"""
        self.log("🎭 Trinity Google Drive Migration")
        self.log("=" * 60)
        self.log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Google Drive確認
        if not self.check_gdrive():
            self.log("\n❌ Google Drive not available. Aborting.")
            return 1
        
        # 開始前のディスク使用率
        self.log("\n📊 BEFORE Migration:")
        self.check_disk_usage()
        
        # 移動実行
        self.move_priority_items()
        
        # 完了後のディスク使用率
        self.log("\n📊 AFTER Migration:")
        self.check_disk_usage()
        
        # サマリー
        self.log("\n" + "=" * 60)
        self.log("🎉 Migration Complete!")
        self.log(f"💾 Total moved to Google Drive: {self.total_moved:.1f} MB ({self.total_moved / 1024:.2f} GB)")
        self.log(f"📂 Archive location: {self.archive_base}")
        self.log(f"📝 Log file: {self.log_file}")
        self.log("=" * 60)
        
        return 0

def main():
    """メイン処理"""
    print("🎭 Trinity Google Drive Migration Tool")
    print("=" * 60)
    print("⚠️  This will move large files/directories to Google Drive:")
    print("  - Backups")
    print("  - Old logs")
    print("  - Large projects (with symlinks)")
    print("  - Generated images")
    print("  - Archives and test files")
    print()
    print("💡 Files will be moved (not deleted), so you can restore them anytime.")
    print()
    print("Press Ctrl+C to cancel, or press Enter to start...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return 1
    
    migrator = GDriveMigrator()
    
    try:
        return migrator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())




