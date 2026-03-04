#!/usr/bin/env python3
"""
ストレージ状況確認スクリプト
バックアップ暴走の影響をチェック
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

def get_disk_usage():
    """ディスク使用量を取得"""
    try:
        # dfコマンドの結果をパース
        result = os.popen('df -h').read()
        lines = result.strip().split('\n')
        
        disk_info = []
        for line in lines[1:]:  # ヘッダーをスキップ
            parts = line.split()
            if len(parts) >= 6:
                disk_info.append({
                    'filesystem': parts[0],
                    'size': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'use_percent': parts[4],
                    'mounted_on': parts[5]
                })
        
        return disk_info
    except Exception as e:
        print(f"ディスク情報取得エラー: {e}")
        return []

def get_directory_size(path):
    """ディレクトリのサイズを取得"""
    total_size = 0
    file_count = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                    file_count += 1
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, FileNotFoundError):
        pass
    
    return total_size, file_count

def format_size(size_bytes):
    """サイズを人間が読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def analyze_storage():
    """ストレージ分析"""
    print("📊 ストレージ状況分析")
    print("=" * 60)
    
    # ディスク使用量
    disk_info = get_disk_usage()
    print("\n💾 ディスク使用量:")
    for disk in disk_info:
        if disk['mounted_on'] == '/':
            print(f"  🖥️  ルートディスク: {disk['used']}/{disk['size']} ({disk['use_percent']})")
            print(f"     利用可能: {disk['available']}")
        elif disk['mounted_on'].startswith('/mnt'):
            print(f"  💿 マウントポイント {disk['mounted_on']}: {disk['used']}/{disk['size']} ({disk['use_percent']})")
    
    # 主要ディレクトリのサイズ
    print("\n📁 主要ディレクトリのサイズ:")
    
    directories_to_check = [
        '/root/logs',
        '/root/unified_backups', 
        '/root/backups',
        '/root/ai_learning_backups',
        '/root/memory_backups',
        '/root/trinity_workspace',
        '/root/Google Drive'
    ]
    
    total_size = 0
    directory_info = {}
    
    for dir_path in directories_to_check:
        if os.path.exists(dir_path):
            size, file_count = get_directory_size(dir_path)
            directory_info[dir_path] = {
                'size_bytes': size,
                'size_formatted': format_size(size),
                'file_count': file_count
            }
            total_size += size
            
            # 使用率の計算
            usage_indicator = "🟢" if size < 1024**3 else "🟡" if size < 5*1024**3 else "🔴"
            print(f"  {usage_indicator} {dir_path}: {format_size(size)} ({file_count:,}ファイル)")
        else:
            print(f"  ⚪ {dir_path}: 存在しません")
    
    # ヘルスレポートファイルの確認
    print("\n🏥 ヘルスレポートファイル:")
    health_reports_dir = '/root/logs'
    if os.path.exists(health_reports_dir):
        health_files = list(Path(health_reports_dir).glob('health_report_*.json'))
        health_size = sum(f.stat().st_size for f in health_files if f.exists())
        
        print(f"  📄 ファイル数: {len(health_files)}個")
        print(f"  💾 総サイズ: {format_size(health_size)}")
        
        if len(health_files) > 100:
            print(f"  ⚠️  警告: ヘルスレポートファイルが多すぎます！")
        elif len(health_files) > 50:
            print(f"  ⚠️  注意: ヘルスレポートファイルが多いです")
        else:
            print(f"  ✅ 正常: ヘルスレポートファイル数は適切です")
    
    # サマリー
    print(f"\n📊 総合サマリー:")
    print(f"  💾 総ディレクトリサイズ: {format_size(total_size)}")
    
    # 警告チェック
    warnings = []
    if total_size > 10 * 1024**3:  # 10GB以上
        warnings.append("ディスク使用量が多すぎます")
    
    for dir_path, info in directory_info.items():
        if info['size_bytes'] > 5 * 1024**3:  # 5GB以上
            warnings.append(f"{dir_path}が大きすぎます ({info['size_formatted']})")
    
    if warnings:
        print(f"\n⚠️  警告:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print(f"  ✅ ストレージ使用量は正常です")
    
    # レポート保存
    report = {
        'timestamp': datetime.now().isoformat(),
        'disk_info': disk_info,
        'directory_info': directory_info,
        'total_size_bytes': total_size,
        'total_size_formatted': format_size(total_size),
        'warnings': warnings
    }
    
    report_file = f"/root/trinity_workspace/storage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 詳細レポート: {report_file}")
    print("=" * 60)

if __name__ == "__main__":
    analyze_storage()
