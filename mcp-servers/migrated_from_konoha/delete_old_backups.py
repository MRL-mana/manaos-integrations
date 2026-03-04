#!/usr/bin/env python3
"""
古いバックアップファイル削除スクリプト
ディスク容量確保のための安全な削除
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta

def safe_delete_old_backups():
    """古いバックアップファイルを安全に削除"""
    print("🗑️ 古いバックアップファイルの安全な削除開始")
    print("=" * 60)
    
    # 削除対象のディレクトリとパターン
    backup_locations = [
        {
            'path': '/root/unified_backups',
            'pattern': '*',
            'days_old': 7,  # 7日以上古いもの
            'description': '統一バックアップ'
        },
        {
            'path': '/root/ai_learning_backups', 
            'pattern': '*',
            'days_old': 7,
            'description': 'AI学習バックアップ'
        },
        {
            'path': '/root/memory_backups',
            'pattern': '*',
            'days_old': 7,
            'description': 'メモリバックアップ'
        },
        {
            'path': '/root/logs',
            'pattern': 'health_report_*.json',
            'days_old': 1,  # 1日以上古いヘルスレポート
            'description': 'ヘルスレポート'
        },
        {
            'path': '/root/logs',
            'pattern': '*.log.*',  # ローテートされたログファイル
            'days_old': 3,
            'description': 'ローテートログ'
        }
    ]
    
    total_deleted = 0
    total_size_freed = 0
    deletion_log = []
    
    cutoff_date = datetime.now() - timedelta(days=1)  # デフォルト1日前
    
    for location in backup_locations:
        backup_path = Path(location['path'])
        if not backup_path.exists():
            print(f"⚠️  {location['description']}: パスが存在しません - {backup_path}")
            continue
            
        print(f"\n📁 {location['description']} ({backup_path}):")
        
        # カスタム日数設定
        custom_cutoff = datetime.now() - timedelta(days=location['days_old'])
        
        deleted_count = 0
        freed_size = 0
        
        try:
            # パターンマッチングでファイル検索
            if '*' in location['pattern']:
                files_to_check = list(backup_path.rglob('*'))
            else:
                files_to_check = list(backup_path.rglob(location['pattern']))
            
            for file_path in files_to_check:
                if file_path.is_file():
                    try:
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        # 日数チェック
                        if file_mtime < custom_cutoff:
                            file_size = file_path.stat().st_size
                            
                            # 安全チェック: 重要なファイルは除外
                            if is_safe_to_delete(file_path):
                                # Google Driveに移動（重要ファイルの場合）
                                if is_important_file(file_path):
                                    move_to_gdrive(file_path)
                                
                                # ファイル削除
                                file_path.unlink()
                                
                                deleted_count += 1
                                freed_size += file_size
                                
                                deletion_log.append({
                                    'file': str(file_path),
                                    'size': file_size,
                                    'deleted_at': datetime.now().isoformat()
                                })
                                
                                print(f"  🗑️  削除: {file_path.name} ({format_size(file_size)})")
                            else:
                                print(f"  ⚠️  スキップ: {file_path.name} (重要ファイル)")
                                
                    except Exception as e:
                        print(f"  ❌ エラー: {file_path.name} - {e}")
            
            print(f"  ✅ {location['description']}: {deleted_count}個削除, {format_size(freed_size)}解放")
            
        except Exception as e:
            print(f"  ❌ {location['description']}処理エラー: {e}")
        
        total_deleted += deleted_count
        total_size_freed += freed_size
    
    # サマリー
    print(f"\n📊 削除サマリー:")
    print(f"  🗑️  削除ファイル数: {total_deleted}個")
    print(f"  💾 解放容量: {format_size(total_size_freed)}")
    
    # 削除ログを保存
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'total_deleted': total_deleted,
        'total_size_freed': total_size_freed,
        'deletions': deletion_log
    }
    
    try:
        with open('/root/trinity_workspace/backup_deletion_log.json', 'w') as f:
            json.dump(log_data, f, indent=2)
        print(f"  📄 削除ログ: backup_deletion_log.json")
    except Exception as e:
        print(f"  ❌ ログ保存失敗: {e}")
    
    return total_deleted, total_size_freed

def is_safe_to_delete(file_path):
    """ファイルが安全に削除できるかチェック"""
    file_str = str(file_path).lower()
    
    # 危険なファイルパターンを除外
    dangerous_patterns = [
        'system', 'config', 'database', 'db', 'sqlite',
        'env', 'secret', 'key', 'password', 'credential',
        'docker-compose', 'dockerfile', 'requirements'
    ]
    
    for pattern in dangerous_patterns:
        if pattern in file_str:
            return False
    
    return True

def is_important_file(file_path):
    """重要なファイルかどうかチェック"""
    file_str = str(file_path).lower()
    
    important_patterns = [
        'backup_info.json', 'config.json', 'settings.json',
        'database', 'db', 'sqlite'
    ]
    
    for pattern in important_patterns:
        if pattern in file_str:
            return True
    
    return False

def move_to_gdrive(file_path):
    """重要なファイルをGoogle Driveに移動"""
    try:
        gdrive_path = Path('/root/Google Drive/backups/important_files')
        gdrive_path.mkdir(parents=True, exist_ok=True)
        
        dest_path = gdrive_path / file_path.name
        shutil.move(str(file_path), str(dest_path))
        print(f"    📁 Google Driveに移動: {file_path.name}")
    except Exception as e:
        print(f"    ❌ Google Drive移動失敗: {e}")

def format_size(size_bytes):
    """サイズを人間が読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def main():
    """メイン実行"""
    print("🚨 古いバックアップファイル削除開始")
    print("⚠️  ディスク容量不足の緊急対応")
    print("=" * 60)
    
    try:
        deleted_count, freed_size = safe_delete_old_backups()
        
        print(f"\n✅ バックアップファイル削除完了!")
        print(f"📊 結果: {deleted_count}個のファイル削除, {format_size(freed_size)}解放")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 削除処理エラー: {e}")
        print("⚠️  手動でのファイル削除を検討してください")

if __name__ == "__main__":
    main()

