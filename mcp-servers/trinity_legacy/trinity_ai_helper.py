#!/usr/bin/env python3
"""
Trinity Multi-Agent System - AI Helper Functions
AI（私）が簡単にコマンド実行できるヘルパー関数
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

# シンプルなラッパー関数群

def cmd(command, timeout=60):
    """
    コマンドを実行して結果を返す（最もシンプル）
    
    使用例:
        result = cmd("df -h /")
        print(result['stdout'])
    """
    try:
        result = subprocess.run(
            ["/bin/bash", "-c", command],
            cwd="/root",
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'exit_code': -1
        }

def disk_usage():
    """ディスク使用率を取得"""
    result = cmd("df -h / | tail -1")
    return result['stdout'].strip()

def list_large_files(min_size_mb=100):
    """大きなファイルをリスト"""
    result = cmd(f"find /root -type f -size +{min_size_mb}M -exec du -h {{}} + 2>/dev/null | sort -hr | head -20")
    return result['stdout']

def list_large_dirs():
    """大きなディレクトリをリスト"""
    result = cmd("du -sh /root/*/ 2>/dev/null | sort -hr | head -20")
    return result['stdout']

def cleanup_logs():
    """古いログファイルを削除"""
    commands = [
        "find /var/log -name '*.log.*' -type f -delete",
        "find /var/log -name '*.gz' -type f -delete",
        "journalctl --vacuum-time=3d"
    ]
    
    results = []
    for cmd_str in commands:
        results.append(cmd(cmd_str))
    
    return results

def get_system_info():
    """システム情報を取得"""
    info = {}
    
    # ディスク使用率
    info['disk'] = disk_usage()
    
    # メモリ
    mem = cmd("free -h | grep Mem")
    info['memory'] = mem['stdout'].strip()
    
    # CPU
    cpu = cmd("top -bn1 | grep 'Cpu(s)' | head -1")
    info['cpu'] = cpu['stdout'].strip()
    
    # プロセス数
    proc = cmd("ps aux | wc -l")
    info['processes'] = proc['stdout'].strip()
    
    return info

def trinity_status():
    """Trinity全体のステータス"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'system': get_system_info(),
        'trinity_files': {}
    }
    
    # Trinity関連ファイルの存在確認
    trinity_files = [
        '/root/trinity_hybrid_shell.py',
        '/root/trinity_ai_helper.py',
        '/root/ai_shell_wrapper.py',
        '/root/trinity_cmd.py'
    ]
    
    for file_path in trinity_files:
        status['trinity_files'][file_path] = Path(file_path).exists()
    
    return status

# クイックコマンド集

def quick_cleanup():
    """クイッククリーンアップ"""
    print("🧹 Quick Cleanup Starting...")
    
    # ログクリーンアップ
    print("  1. Cleaning logs...")
    cleanup_logs()
    
    # キャッシュクリーンアップ
    print("  2. Cleaning cache...")
    cmd("find /root -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null")
    cmd("find /root -name '*.pyc' -delete 2>/dev/null")
    
    # 一時ファイル
    print("  3. Cleaning temp files...")
    cmd("rm -rf /tmp/* 2>/dev/null")
    cmd("rm -rf /var/tmp/* 2>/dev/null")
    
    print("✅ Quick Cleanup Complete!")
    print(f"Current disk usage: {disk_usage()}")

def trinity_demo():
    """Trinity Hybrid Shell デモ"""
    print("🎭 Trinity Hybrid Shell Demo")
    print("=" * 60)
    
    print("\n📊 System Info:")
    info = get_system_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n📁 Large Directories:")
    print(list_large_dirs())
    
    print("\n🎯 Trinity Status:")
    status = trinity_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Trinity AI Helper - Quick Commands:")
        print()
        print("  python3 trinity_ai_helper.py demo        - Run demo")
        print("  python3 trinity_ai_helper.py cleanup     - Quick cleanup")
        print("  python3 trinity_ai_helper.py disk        - Show disk usage")
        print("  python3 trinity_ai_helper.py large-dirs  - Show large directories")
        print("  python3 trinity_ai_helper.py status      - Trinity status")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == 'demo':
        trinity_demo()
    elif action == 'cleanup':
        quick_cleanup()
    elif action == 'disk':
        print(disk_usage())
    elif action == 'large-dirs':
        print(list_large_dirs())
    elif action == 'status':
        status = trinity_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)




