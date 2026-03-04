#!/usr/bin/env python3
"""
Trinity Multi-Agent System - Disk Space Analyzer
大きなファイルとディレクトリを特定するツール
"""

import os
import subprocess
from pathlib import Path

def get_dir_size(path):
    """ディレクトリのサイズを取得（MB）"""
    try:
        result = subprocess.run(
            ["du", "-sm", path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            size_mb = int(result.stdout.split()[0])
            return size_mb
        return 0
    except subprocess.SubprocessError:
        return 0

def analyze_root_directories():
    """ルートディレクトリ直下を分析"""
    print("🔍 Analyzing /root directories...")
    print("=" * 70)
    
    root_dir = Path("/root")
    sizes = []
    
    for item in root_dir.iterdir():
        if item.is_dir():
            size_mb = get_dir_size(str(item))
            if size_mb > 0:
                sizes.append((item.name, size_mb, "DIR"))
        elif item.is_file():
            size_mb = item.stat().st_size / (1024 * 1024)
            if size_mb > 10:  # 10MB以上のファイルのみ
                sizes.append((item.name, size_mb, "FILE"))
    
    # サイズでソート
    sizes.sort(key=lambda x: x[1], reverse=True)
    
    # トップ30を表示
    print(f"{'Name':<50} {'Size (MB)':>10} {'Type':>6}")
    print("-" * 70)
    
    total_size = 0
    for name, size, ftype in sizes[:30]:
        print(f"{name:<50} {size:>10.1f} {ftype:>6}")
        total_size += size
    
    print("=" * 70)
    print(f"Top 30 Total: {total_size:.1f} MB")
    
    # サマリー
    print("\n📊 Summary:")
    print(f"Total directories/files analyzed: {len(sizes)}")
    print(f"Directories over 100MB: {len([s for s in sizes if s[1] > 100 and s[2] == 'DIR'])}")
    print(f"Directories over 1GB: {len([s for s in sizes if s[1] > 1024 and s[2] == 'DIR'])}")
    
    return sizes

def check_system_directories():
    """システムディレクトリを確認"""
    print("\n\n🔍 Checking system directories...")
    print("=" * 70)
    
    system_dirs = [
        "/var/log",
        "/var/lib/docker",
        "/tmp",
        "/var/tmp",
        "/var/cache"
    ]
    
    for dir_path in system_dirs:
        if os.path.exists(dir_path):
            size_mb = get_dir_size(dir_path)
            print(f"{dir_path:<30} {size_mb:>10.1f} MB")

if __name__ == "__main__":
    print("🎭 Trinity Disk Space Analyzer")
    print("=" * 70)
    
    sizes = analyze_root_directories()
    check_system_directories()
    
    print("\n✅ Analysis complete!")




