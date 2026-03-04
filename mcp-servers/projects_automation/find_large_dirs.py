#!/usr/bin/env python3
"""
Trinity Multi-Agent System - Large Directory Finder
特に大きなディレクトリを特定して削除候補を提案
"""

import subprocess
from pathlib import Path

def find_large_directories():
    """100MB以上のディレクトリを特定"""
    print("🔍 Finding directories over 100MB...")
    print("=" * 70)
    
    root_dir = Path("/root")
    large_dirs = []
    
    # トップレベルディレクトリをチェック
    for item in root_dir.iterdir():
        if item.is_dir():
            try:
                result = subprocess.run(
                    ["du", "-sm", str(item)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    size_mb = int(result.stdout.split()[0])
                    if size_mb >= 100:
                        large_dirs.append((item.name, size_mb))
            except subprocess.SubprocessError:
                pass
    
    # サイズでソート
    large_dirs.sort(key=lambda x: x[1], reverse=True)
    
    print(f"{'Directory':<50} {'Size (MB)':>10}")
    print("-" * 70)
    
    for name, size in large_dirs:
        print(f"{name:<50} {size:>10}")
    
    print("=" * 70)
    print(f"Total: {len(large_dirs)} directories over 100MB")
    print(f"Combined size: {sum(s for _, s in large_dirs):.1f} MB")
    
    return large_dirs

def analyze_deletable():
    """削除可能なディレクトリを提案"""
    print("\n\n💡 Deletion candidates:")
    print("=" * 70)
    
    candidates = [
        ("localGPT", "Large RAG project - safe to delete if not in use"),
        ("open-webui", "UI project - safe to delete if not in use"),
        ("chatbot-ui", "UI project - safe to delete if not in use"),
        ("noVNC", "VNC client - safe to delete if not in use"),
        ("google-cloud-sdk", "Google Cloud tools - reinstallable"),
        ("obsidian_vault", "Can be backed up to Google Drive first"),
        ("manaos_v3", "Can be archived if stable"),
        ("trinity_automation/archive", "Old archived files"),
        ("logs_archive", "Old logs - safe to delete"),
        ("logs_archive_20251007", "Old logs - safe to delete"),
    ]
    
    for dir_name, description in candidates:
        dir_path = Path("/root") / dir_name
        if dir_path.exists():
            try:
                result = subprocess.run(
                    ["du", "-sm", str(dir_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    size_mb = int(result.stdout.split()[0])
                    print(f"📁 {dir_name} ({size_mb} MB)")
                    print(f"   {description}")
                    print()
            except Exception:
                pass

if __name__ == "__main__":
    print("🎭 Trinity Large Directory Finder")
    print("=" * 70)
    
    large_dirs = find_large_directories()
    analyze_deletable()
    
    print("\n💾 Current disk usage:")
    subprocess.run(["df", "-h", "/"])




