#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このはサーバーのバックアップ済み・母艦移行済みファイルを安全に削除するスクリプト
"""

import subprocess
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class KonohaBackupCleaner:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.ssh_host = "konoha"
        self.deleted_items = []
        self.failed_items = []
        self.total_freed = 0
        
    def run_ssh_command(self, command: str, timeout: int = 30) -> Optional[str]:
        """SSH経由でコマンドを実行"""
        try:
            result = subprocess.run(
                ["ssh", self.ssh_host, command],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"[WARN] コマンド実行エラー: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            print(f"[WARN] コマンドがタイムアウトしました: {command}")
            return None
        except Exception as e:
            print(f"[WARN] コマンド実行エラー: {e}")
            return None
    
    def get_directory_size(self, path: str) -> int:
        """ディレクトリのサイズを取得（バイト）"""
        result = self.run_ssh_command(f"du -sb {path} 2>/dev/null | cut -f1")
        if result:
            try:
                return int(result)
            except ValueError:
                return 0
        return 0
    
    def find_backup_items(self) -> List[Dict[str, any]]:
        """バックアップ済み・移行済みのアイテムを検索"""
        print("[検索] バックアップ済み・移行済みアイテムを検索中...")
        print("-" * 70)
        
        items = []
        
        # 検索パターン
        search_patterns = [
            # ディレクトリ
            ("find /root -maxdepth 2 -type d -name '*backup*'", "backup"),
            ("find /root -maxdepth 2 -type d -name '*バックアップ*'", "backup"),
            ("find /root -maxdepth 2 -type d -name '*migrated*'", "migrated"),
            ("find /root -maxdepth 2 -type d -name '*移行*'", "migrated"),
            ("find /root -maxdepth 2 -type d -name '*母艦*'", "migrated"),
            ("find /mnt/storage500 -maxdepth 2 -type d -name '*backup*'", "backup"),
            ("find /mnt/storage500 -maxdepth 2 -type d -name '*archived*'", "archived"),
            ("find /mnt/storage500 -maxdepth 2 -type d -name '*移行*'", "migrated"),
            ("find /mnt/storage500 -maxdepth 2 -type d -name '*母艦*'", "migrated"),
        ]
        
        for pattern, category in search_patterns:
            result = self.run_ssh_command(pattern)
            if result:
                for line in result.split('\n'):
                    if line.strip():
                        items.append({
                            'path': line.strip(),
                            'category': category,
                            'type': 'directory'
                        })
        
        # 既知のバックアップディレクトリ
        known_backups = [
            "/root/backup",
            "/root/manaos-backup",
            "/root/.mana_memory_backups",
            "/root/old_configs_backup",
            "/mnt/storage500/backups",
            "/mnt/storage500/root_backups",
            "/mnt/storage500/archived_data",
        ]
        
        for path in known_backups:
            # 存在確認
            result = self.run_ssh_command(f"test -e {path} && echo 'exists' || echo 'not_found'")
            if result == "exists":
                items.append({
                    'path': path,
                    'category': 'backup',
                    'type': 'directory'
                })
        
        # 重複を除去
        seen = set()
        unique_items = []
        for item in items:
            if item['path'] not in seen:
                seen.add(item['path'])
                unique_items.append(item)
        
        return unique_items
    
    def check_if_safe_to_delete(self, path: str) -> bool:
        """削除しても安全かチェック"""
        # 絶対に削除してはいけないパス
        absolutely_protected = [
            '/',
            '/etc',
            '/var',
            '/usr',
            '/bin',
            '/sbin',
            '/opt',
            '/sys',
            '/proc',
            '/dev',
        ]
        
        for protected in absolutely_protected:
            if path == protected or (path.startswith(protected + '/') and protected != '/'):
                return False
        
        # /root や /mnt/storage500 配下のバックアップは削除可能
        # ただし、ルートディレクトリ自体は削除しない
        if path in ['/root', '/mnt/storage500']:
            return False
        
        # シンボリックリンクは削除可能
        result = self.run_ssh_command(f"test -L {path} && echo 'link' || echo 'not_link'")
        if result == "link":
            return True
        
        # バックアップ関連の名前が含まれているか確認
        backup_keywords = ['backup', 'バックアップ', 'migrated', '移行', '母艦', 'archived']
        path_lower = path.lower()
        if any(keyword in path_lower for keyword in backup_keywords):
            return True
        
        # /root や /mnt/storage500 配下で、バックアップ関連の名前が含まれている場合は削除可能
        if path.startswith('/root/') or path.startswith('/mnt/storage500/'):
            return True
        
        return False
    
    def delete_item(self, item: Dict[str, any], retry_count: int = 3) -> bool:
        """アイテムを削除（リトライ機能付き）"""
        path = item['path']
        
        if not self.check_if_safe_to_delete(path):
            print(f"  [SKIP] スキップ（保護されたパス）: {path}")
            return False
        
        # サイズを取得
        size = self.get_directory_size(path) if item['type'] == 'directory' else 0
        
        if self.dry_run:
            size_mb = size / (1024 * 1024)
            print(f"  [DRY RUN] 削除予定: {path} ({size_mb:.2f} MB)")
            self.deleted_items.append({
                'path': path,
                'size': size,
                'category': item['category']
            })
            self.total_freed += size
            return True
        else:
            # 実際に削除（リトライ）
            for attempt in range(retry_count):
                if item['type'] == 'directory':
                    command = f"rm -rf {path}"
                else:
                    command = f"rm -f {path}"
                
                result = self.run_ssh_command(command, timeout=120)
                if result is not None:
                    size_mb = size / (1024 * 1024)
                    print(f"  [OK] 削除完了: {path} ({size_mb:.2f} MB)")
                    self.deleted_items.append({
                        'path': path,
                        'size': size,
                        'category': item['category']
                    })
                    self.total_freed += size
                    return True
                else:
                    if attempt < retry_count - 1:
                        print(f"  [RETRY] リトライ中 ({attempt + 1}/{retry_count}): {path}")
                        import time
                        time.sleep(2)  # 2秒待機
                    else:
                        print(f"  [ERROR] 削除失敗: {path}")
                        self.failed_items.append(path)
                        return False
            return False
    
    def show_summary(self):
        """削除結果のサマリーを表示"""
        print("\n" + "=" * 70)
        print("[サマリー] 削除結果サマリー")
        print("=" * 70)
        
        total_mb = self.total_freed / (1024 * 1024)
        total_gb = total_mb / 1024
        
        print(f"削除アイテム数: {len(self.deleted_items)}")
        print(f"解放容量: {total_mb:.2f} MB ({total_gb:.2f} GB)")
        print(f"失敗アイテム数: {len(self.failed_items)}")
        
        if self.deleted_items:
            print("\n削除されたアイテム:")
            for item in self.deleted_items:
                size_mb = item['size'] / (1024 * 1024)
                print(f"  - {item['path']} ({size_mb:.2f} MB) [{item['category']}]")
        
        if self.failed_items:
            print("\n削除失敗したアイテム:")
            for path in self.failed_items:
                print(f"  - {path}")
    
    def run_cleanup(self):
        """クリーンアップを実行"""
        print("=" * 70)
        if self.dry_run:
            print("[クリーンアップ] このはサーバーのバックアップクリーンアップ（DRY RUN）")
        else:
            print("[クリーンアップ] このはサーバーのバックアップクリーンアップ（実際に削除）")
        print("=" * 70)
        print()
        
        # 接続確認
        print("[1] このはサーバーへの接続確認...")
        test_result = self.run_ssh_command("echo 'connected'")
        if test_result != "connected":
            print("[ERROR] このはサーバーに接続できませんでした")
            return False
        print("[OK] 接続成功")
        print()
        
        # バックアップアイテムを検索
        items = self.find_backup_items()
        print(f"[OK] {len(items)}件のバックアップアイテムを発見")
        print()
        
        if not items:
            print("削除対象のアイテムが見つかりませんでした")
            return True
        
        # 各アイテムの情報を表示
        print("[2] 削除対象アイテムの確認...")
        print("-" * 70)
        for item in items:
            size = self.get_directory_size(item['path']) if item['type'] == 'directory' else 0
            size_mb = size / (1024 * 1024)
            print(f"  [DIR] {item['path']} ({size_mb:.2f} MB) [{item['category']}]")
        print()
        
        # 削除実行
        print("[3] 削除実行...")
        print("-" * 70)
        for item in items:
            self.delete_item(item)
        print()
        
        # サマリー表示
        self.show_summary()
        
        return True

def main():
    """メイン処理"""
    import sys
    
    # 引数確認
    dry_run = True
    auto_yes = False
    
    if len(sys.argv) > 1:
        if "--execute" in sys.argv:
            dry_run = False
        if "--yes" in sys.argv or "-y" in sys.argv:
            auto_yes = True
    
    if not dry_run:
        print("[警告] 実際にファイルを削除します！")
        if not auto_yes:
            try:
                response = input("続行しますか？ (yes/no): ")
                if response.lower() != "yes":
                    print("キャンセルしました")
                    return
            except EOFError:
                print("[ERROR] 対話入力ができません。--yes フラグを使用してください")
                return
        else:
            print("[INFO] --yes フラグが指定されました。自動的に続行します")
    else:
        print("[INFO] DRY RUNモード: 実際には削除しません")
        print("   実際に削除する場合は: python cleanup_konoha_backups.py --execute --yes")
        print()
    
    cleaner = KonohaBackupCleaner(dry_run=dry_run)
    cleaner.run_cleanup()

if __name__ == "__main__":
    main()
