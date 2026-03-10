#!/usr/bin/env python3
"""
Trinity Multi-Agent System - Dual Storage Cleanup
メインストレージ（/root）と追加ストレージ（/mnt/storage500）を徹底クリーンアップ
"""

import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

class DualStorageCleanup:
    def __init__(self):
        self.root_dir = Path("/root")
        self.storage500 = Path("/mnt/storage500")
        self.log_file = self.root_dir / "dual_cleanup_log.txt"
        self.total_freed = 0
        
    def log(self, message):
        """ログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")
    
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
    
    def check_disk_usage(self):
        """ディスク使用率確認"""
        self.log("\n💾 Disk Usage:")
        
        for mount in ["/", "/mnt/storage500"]:
            try:
                stat = os.statvfs(mount)  # type: ignore[attr-defined]
                total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
                used_gb = ((stat.f_blocks - stat.f_bavail) * stat.f_frsize) / (1024**3)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                usage_pct = (used_gb / total_gb) * 100
                
                self.log(f"  {mount}: {used_gb:.1f}GB / {total_gb:.1f}GB ({usage_pct:.1f}% used, {free_gb:.1f}GB free)")
            except Exception:
                self.log(f"  {mount}: Not available")
    
    def delete_directory(self, dir_path, reason):
        """ディレクトリを削除"""
        if not dir_path.exists():
            self.log(f"⚠️  Skip: {dir_path.name} (does not exist)")
            return 0
        
        size_mb = self.get_dir_size(dir_path)
        self.log(f"🗑️  Deleting: {dir_path.name} ({size_mb} MB) - {reason}")
        
        try:
            shutil.rmtree(dir_path)
            self.log("  ✅ Deleted successfully")
            return size_mb
        except Exception as e:
            self.log(f"  ❌ Failed: {e}")
            return 0
    
    def cleanup_var_log(self):
        """"/var/log をクリーンアップ（953MB）"""
        self.log("\n🧹 Phase 1: Cleaning /var/log...")
        self.log("=" * 60)
        
        freed = 0
        
        # 古いログファイルを削除
        patterns = ["*.log.*", "*.gz", "*.1", "*.2", "*.3", "*.old"]
        
        for pattern in patterns:
            try:
                result = subprocess.run(
                    ["find", "/var/log", "-name", pattern, "-type", "f"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    files = result.stdout.strip().split("\n")
                    for file_path in files:
                        try:
                            size = os.path.getsize(file_path)
                            os.remove(file_path)
                            freed += size / (1024**2)
                        except IOError:
                            pass
            except IOError:
                pass
        
        # journalctl クリーンアップ
        try:
            subprocess.run(
                ["journalctl", "--vacuum-time=3d"],
                capture_output=True,
                timeout=60
            )
        except subprocess.SubprocessError:
            pass
        
        self.log(f"✅ /var/log cleaned: {freed:.1f} MB freed")
        self.total_freed += freed
        return freed
    
    def cleanup_root_large_dirs(self):
        """メインストレージの大きなディレクトリを削除"""
        self.log("\n🧹 Phase 2: Cleaning /root large directories...")
        self.log("=" * 60)
        
        # 削除対象リスト（確実に不要なもの）
        delete_list = [
            ("localGPT", "Large RAG project - not in active use"),
            ("open-webui", "UI project - not in active use"),
            ("chatbot-ui", "UI project - not in active use"),
            ("noVNC", "VNC client - not in active use"),
            ("logs_archive", "Old log archive"),
            ("logs_archive_20251007", "Old log archive"),
            ("backups", "Empty backup directory"),
            ("backups_automated", "Old backups"),
            ("backups_ultimate", "Old backups"),
            ("mana_backups", "Old backups"),
            ("ai_image_gallery", "Old generated images"),
            ("generated_images", "Old generated images"),
            ("mana_generated_images", "Old generated images"),
            ("downloaded_images", "Old downloaded images"),
            ("archive", "General archive"),
            ("old_docs_archive", "Old documentation"),
            ("organized_files", "Old organized files"),
            ("organized_workspace", "Old workspace"),
            ("batch_processing_tests", "Old test files"),
            ("mock_google_drive_tests", "Old test files"),
            ("sample-projects", "Sample projects"),
            ("MCP-Demo-Project", "Demo project"),
        ]
        
        freed = 0
        for dir_name, reason in delete_list:
            dir_path = self.root_dir / dir_name
            freed += self.delete_directory(dir_path, reason)
        
        self.log(f"✅ /root large dirs cleaned: {freed} MB freed")
        self.total_freed += freed
        return freed
    
    def cleanup_storage500(self):
        """追加ストレージをクリーンアップ"""
        self.log("\n🧹 Phase 3: Cleaning /mnt/storage500...")
        self.log("=" * 60)
        
        if not self.storage500.exists():
            self.log("⚠️  /mnt/storage500 does not exist, skipping")
            return 0
        
        freed = 0
        
        # 削除対象（古いバックアップなど）
        delete_list = [
            ("backups", "Old backups"),
            ("logs", "Old logs"),
            ("archive", "Old archive"),
            ("temp", "Temporary files"),
            ("old", "Old files"),
        ]
        
        for dir_name, reason in delete_list:
            dir_path = self.storage500 / dir_name
            freed += self.delete_directory(dir_path, reason)
        
        self.log(f"✅ /mnt/storage500 cleaned: {freed} MB freed")
        self.total_freed += freed
        return freed
    
    def cleanup_docker(self):
        """Dockerをクリーンアップ"""
        self.log("\n🧹 Phase 4: Cleaning Docker...")
        self.log("=" * 60)
        
        commands = [
            (["docker", "system", "prune", "-af", "--volumes"], "Docker system prune"),
            (["docker", "builder", "prune", "-af"], "Docker builder prune"),
        ]
        
        freed = 0
        for cmd, desc in commands:
            try:
                self.log(f"  Running: {desc}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if "Total reclaimed space" in result.stdout:
                    self.log(f"  ✅ {result.stdout.split('Total reclaimed space:')[1].strip()}")
            except Exception as e:
                self.log(f"  ⚠️  {desc} skipped: {e}")
        
        return freed
    
    def cleanup_root_files(self):
        """ルートディレクトリの不要ファイルを削除"""
        self.log("\n🧹 Phase 5: Cleaning /root files...")
        self.log("=" * 60)
        
        # 削除対象ファイルパターン
        patterns = [
            "*.pyc",
            "*.pyo",
            "__pycache__",
            ".cache",
            "*.tmp",
            "*.temp",
            ".npm",
            ".cargo",
        ]
        
        freed = 0
        for pattern in patterns:
            try:
                if pattern == "__pycache__":
                    # __pycache__ディレクトリを削除
                    for pycache in self.root_dir.rglob("__pycache__"):
                        size = self.get_dir_size(pycache)
                        try:
                            shutil.rmtree(pycache)
                            freed += size
                        except Exception:
                            pass
                else:
                    # ファイルを削除
                    for file_path in self.root_dir.glob(pattern):
                        if file_path.is_file():
                            try:
                                size = file_path.stat().st_size / (1024**2)
                                file_path.unlink()
                                freed += size
                            except IOError:
                                pass
                        elif file_path.is_dir():
                            size = self.get_dir_size(file_path)
                            try:
                                shutil.rmtree(file_path)
                                freed += size
                            except IOError:
                                pass
            except IOError:
                pass
        
        self.log(f"✅ Root files cleaned: {freed:.1f} MB freed")
        self.total_freed += freed
        return freed
    
    def run(self):
        """全クリーンアップを実行"""
        self.log("🎭 Trinity Dual Storage Cleanup")
        self.log("=" * 60)
        self.log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 開始前のディスク使用率
        self.log("\n📊 BEFORE Cleanup:")
        self.check_disk_usage()
        
        # 各フェーズ実行
        self.cleanup_var_log()
        self.cleanup_root_large_dirs()
        self.cleanup_storage500()
        self.cleanup_docker()
        self.cleanup_root_files()
        
        # 完了後のディスク使用率
        self.log("\n📊 AFTER Cleanup:")
        self.check_disk_usage()
        
        # サマリー
        self.log("\n" + "=" * 60)
        self.log("🎉 Cleanup Complete!")
        self.log(f"💾 Total space freed: {self.total_freed:.1f} MB ({self.total_freed / 1024:.2f} GB)")
        self.log(f"📝 Log file: {self.log_file}")
        self.log("=" * 60)

def main():
    """メイン処理"""
    print("🎭 Trinity Dual Storage Cleanup Tool")
    print("=" * 60)
    print("⚠️  This will delete:")
    print("  - Old logs (/var/log)")
    print("  - Large unused projects (localGPT, open-webui, etc.)")
    print("  - Old backups and archives")
    print("  - Docker unused data")
    print("  - Cache files")
    print()
    print("⚠️  Requires sudo privileges")
    print()
    print("Press Ctrl+C to cancel, or press Enter to start...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return 1
    
    cleaner = DualStorageCleanup()
    
    try:
        cleaner.run()
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())



