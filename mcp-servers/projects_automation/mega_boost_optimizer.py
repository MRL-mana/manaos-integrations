#!/usr/bin/env python3
"""
🚀 ManaOS Mega Boost Optimizer
並列実行でシステム全体を一気に最適化
"""

import os
import sqlite3
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

class MegaBoostOptimizer:
    def __init__(self):
        self.results = {
            'databases': {'optimized': 0, 'errors': [], 'space_saved': 0},
            'logs': {'archived': 0, 'errors': [], 'space_saved': 0},
            'duplicates': {'removed': 0, 'errors': []},
            'services': {'cleaned': 0, 'errors': []}
        }
        self.root_path = Path('/root')
        
    def optimize_database(self, db_path):
        """データベースを最適化"""
        try:
            original_size = os.path.getsize(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute('VACUUM')
            conn.execute('ANALYZE')
            conn.close()
            new_size = os.path.getsize(db_path)
            saved = original_size - new_size
            return {'success': True, 'path': str(db_path), 'saved': saved}
        except Exception as e:
            return {'success': False, 'path': str(db_path), 'error': str(e)}
    
    def find_and_optimize_databases(self):
        """全DBを検索して最適化"""
        print("🔍 データベースを検索中...")
        
        # Google Driveアーカイブ内の重複を除外
        exclude_patterns = [
            'Google Drive/Database_Archive',
            'snap/firefox',
            'localGPT'
        ]
        
        db_files = []
        for db_file in self.root_path.rglob('*.db'):
            if any(pattern in str(db_file) for pattern in exclude_patterns):
                continue
            if db_file.stat().st_size > 1024:  # 1KB以上のみ
                db_files.append(db_file)
        
        print(f"📊 {len(db_files)}個のDBを最適化中...")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.optimize_database, db): db for db in db_files}
            
            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    self.results['databases']['optimized'] += 1
                    self.results['databases']['space_saved'] += result['saved']
                    print(f"  ✅ {Path(result['path']).name} - {result['saved']/1024:.1f}KB節約")
                else:
                    self.results['databases']['errors'].append(result)
                    print(f"  ⚠️  {Path(result['path']).name} - {result['error']}")
    
    def archive_old_logs(self):
        """古いログをアーカイブ"""
        print("\n📦 ログをアーカイブ中...")
        
        log_dir = self.root_path / 'logs'
        if not log_dir.exists():
            return
        
        archive_name = f"logs_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        archive_path = self.root_path / 'backups_ultimate' / archive_name
        archive_path.parent.mkdir(exist_ok=True)
        
        try:
            # 7日以上前のログのみアーカイブ
            cmd = f"find {log_dir} -type f -mtime +7 -name '*.log' | tar -czf {archive_path} -T - 2>/dev/null"
            subprocess.run(cmd, shell=True, check=False)
            
            if archive_path.exists():
                archive_size = os.path.getsize(archive_path)
                self.results['logs']['archived'] = 1
                self.results['logs']['space_saved'] = archive_size
                
                # アーカイブ後に古いログを削除
                subprocess.run(f"find {log_dir} -type f -mtime +7 -name '*.log' -delete", 
                             shell=True, check=False)
                
                print(f"  ✅ アーカイブ作成: {archive_size/1024/1024:.1f}MB")
            
        except Exception as e:
            self.results['logs']['errors'].append(str(e))
            print(f"  ⚠️  {e}")
    
    def remove_duplicate_archives(self):
        """重複アーカイブディレクトリを削除"""
        print("\n🗑️  重複アーカイブを削除中...")
        
        # Google Drive内の入れ子になったアーカイブを削除
        archive_pattern = self.root_path / 'Google Drive' / 'Database_Archive_*'
        
        try:
            nested_archives = list(self.root_path.glob('Google Drive/Database_Archive_*/Google Drive/Database_Archive_*'))
            
            for nested in nested_archives:
                if nested.is_dir():
                    shutil.rmtree(nested, ignore_errors=True)
                    self.results['duplicates']['removed'] += 1
                    print(f"  ✅ 削除: {nested.name}")
                    
        except Exception as e:
            self.results['duplicates']['errors'].append(str(e))
            print(f"  ⚠️  {e}")
    
    def clean_empty_databases(self):
        """空のDBファイルを削除"""
        print("\n🧹 空のDBファイルを削除中...")
        
        empty_count = 0
        for db_file in self.root_path.rglob('*.db'):
            if db_file.stat().st_size < 1024:  # 1KB未満
                try:
                    db_file.unlink()
                    empty_count += 1
                except sqlite3.Error:
                    pass
        
        if empty_count > 0:
            print(f"  ✅ {empty_count}個の空DBを削除")
            self.results['services']['cleaned'] = empty_count
    
    def generate_report(self):
        """最終レポート生成"""
        print("\n" + "="*60)
        print("🎉 MEGA BOOST MODE 完了レポート")
        print("="*60)
        
        print("\n📊 データベース最適化:")
        print(f"   ✅ 最適化: {self.results['databases']['optimized']}個")
        print(f"   💾 節約容量: {self.results['databases']['space_saved']/1024/1024:.2f}MB")
        
        print("\n📦 ログアーカイブ:")
        print(f"   ✅ アーカイブ: {self.results['logs']['archived']}個")
        print(f"   💾 圧縮容量: {self.results['logs']['space_saved']/1024/1024:.2f}MB")
        
        print("\n🗑️  重複削除:")
        print(f"   ✅ 削除: {self.results['duplicates']['removed']}個")
        
        print("\n🧹 クリーンアップ:")
        print(f"   ✅ 空DB削除: {self.results['services']['cleaned']}個")
        
        total_saved = (self.results['databases']['space_saved'] + 
                       self.results['logs']['space_saved']) / 1024 / 1024
        
        print(f"\n💰 総節約容量: {total_saved:.2f}MB")
        print("="*60)
        
        # JSON形式で保存
        report_path = self.root_path / f"mega_boost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 詳細レポート: {report_path}")
        
        return self.results

def main():
    print("🚀 ManaOS MEGA BOOST MODE 起動！\n")
    
    optimizer = MegaBoostOptimizer()
    
    # 並列実行
    with ThreadPoolExecutor(max_workers=3) as executor:
        db_future = executor.submit(optimizer.find_and_optimize_databases)
        log_future = executor.submit(optimizer.archive_old_logs)
        dup_future = executor.submit(optimizer.remove_duplicate_archives)
        
        # 全タスク完了を待つ
        db_future.result()
        log_future.result()
        dup_future.result()
    
    # 追加クリーンアップ
    optimizer.clean_empty_databases()
    
    # 最終レポート
    optimizer.generate_report()
    
    print("\n✨ MEGA BOOST MODE 完了！\n")

if __name__ == '__main__':
    main()

