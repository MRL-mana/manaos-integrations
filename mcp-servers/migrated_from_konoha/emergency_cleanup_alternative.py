#!/usr/bin/env python3
"""
緊急ディスククリーンアップ - 代替手段
シェルが壊れている状況での緊急対応
"""

import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta

def emergency_cleanup():
    """緊急クリーンアップ実行"""
    print("🚨 緊急ディスククリーンアップ開始")
    print("=" * 50)
    
    # 1. trinity_workspace内の大きなファイルを圧縮
    print("📦 trinity_workspace内の大きなファイルを圧縮...")
    compressed_count = 0
    
    for file_path in Path("/root/trinity_workspace").rglob("*"):
        if file_path.is_file():
            try:
                file_size = file_path.stat().st_size
                # 1MB以上のファイルを圧縮
                if file_size > 1024 * 1024 and not str(file_path).endswith('.gz'):
                    compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
                    
                    with open(file_path, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # 元ファイルを削除
                    file_path.unlink()
                    compressed_count += 1
                    print(f"  ✅ 圧縮: {file_path.name} ({file_size:,} bytes)")
                    
            except Exception as e:
                print(f"  ❌ 圧縮失敗: {file_path.name} - {e}")
    
    print(f"📦 圧縮完了: {compressed_count}個のファイル")
    
    # 2. 古いファイルを削除
    print("\n🗑️ 古いファイルを削除...")
    deleted_count = 0
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for file_path in Path("/root/trinity_workspace").rglob("*"):
        if file_path.is_file():
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # 7日以上古い一時ファイルを削除
                if (file_mtime < cutoff_date and 
                    any(keyword in str(file_path).lower() for keyword in ['temp', 'tmp', 'cache', 'backup'])):
                    
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    print(f"  🗑️ 削除: {file_path.name} ({file_size:,} bytes)")
                    
            except Exception as e:
                print(f"  ❌ 削除失敗: {file_path.name} - {e}")
    
    print(f"🗑️ 削除完了: {deleted_count}個のファイル")
    
    # 3. ディレクトリサイズを確認
    print("\n📊 trinity_workspace内のディレクトリサイズ:")
    total_size = 0
    
    for item in Path("/root/trinity_workspace").iterdir():
        if item.is_dir():
            dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            total_size += dir_size
            size_mb = dir_size / (1024 * 1024)
            print(f"  📁 {item.name}: {size_mb:.2f} MB")
    
    print(f"\n📊 総サイズ: {total_size / (1024 * 1024):.2f} MB")
    
    # 4. 緊急メッセージファイルを作成
    emergency_msg = f"""
🚨 緊急ディスククリーンアップ完了
実行日時: {datetime.now().isoformat()}
圧縮ファイル数: {compressed_count}
削除ファイル数: {deleted_count}
総サイズ: {total_size / (1024 * 1024):.2f} MB

⚠️ システム再起動を推奨します
"""
    
    with open("/root/trinity_workspace/EMERGENCY_CLEANUP_COMPLETE.txt", "w") as f:
        f.write(emergency_msg)
    
    print("\n✅ 緊急クリーンアップ完了!")
    print("📄 詳細レポート: EMERGENCY_CLEANUP_COMPLETE.txt")
    print("⚠️ システム再起動を推奨します")

if __name__ == "__main__":
    emergency_cleanup()

