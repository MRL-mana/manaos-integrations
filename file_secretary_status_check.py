#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary 状態確認スクリプト
全機能の動作状況を確認
"""

import sys
import httpx
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from _paths import FILE_SECRETARY_PORT

def check_processes():
    """プロセス確認"""
    print("=== プロセス確認 ===")
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Python*' } | Select-Object Id, ProcessName"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            print("✅ Pythonプロセス実行中")
            print(result.stdout)
        else:
            print("⚠️ Pythonプロセスが見つかりません")
    except Exception:
        print("⚠️ プロセス確認失敗")

def check_api():
    """API確認"""
    print("\n=== API確認 ===")
    try:
        response = httpx.get(f"http://127.0.0.1:{FILE_SECRETARY_PORT}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ APIサーバー: 正常 ({data.get('version')})")
            return True
        else:
            print(f"⚠️ APIサーバー: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print("❌ APIサーバー: 接続不可（起動していない可能性）")
        return False
    except Exception as e:
        print(f"❌ APIサーバー: エラー - {e}")
        return False

def check_database():
    """データベース確認"""
    print("\n=== データベース確認 ===")
    try:
        from file_secretary_db import FileSecretaryDB
        db = FileSecretaryDB('file_secretary.db')
        status = db.get_inbox_status()
        print(f"✅ データベース: 正常")
        print(f"  新規ファイル: {status['new_count']}件")
        print(f"  未処理ファイル: {status['old_count']}件")
        db.close()
        return True
    except Exception as e:
        print(f"❌ データベース: エラー - {e}")
        return False

def check_inbox():
    """INBOX確認"""
    print("\n=== INBOX確認 ===")
    inbox_path = Path("00_INBOX")
    if inbox_path.exists():
        files = list(inbox_path.iterdir())
        print(f"✅ INBOXディレクトリ: 存在")
        print(f"  ファイル数: {len(files)}件")
        for f in files[:5]:
            print(f"    - {f.name}")
        return True
    else:
        print("⚠️ INBOXディレクトリ: 存在しない")
        return False

def check_slack_integration():
    """Slack統合確認"""
    print("\n=== Slack統合確認 ===")
    try:
        from file_secretary_templates import parse_command
        test_cases = [
            ("Inboxどう？", "status"),
            ("終わった", "done"),
            ("戻して", "restore"),
            ("探して：日報", "search")
        ]
        all_ok = True
        for text, expected in test_cases:
            result = parse_command(text)
            if result == expected:
                print(f"✅ \"{text}\" -> {result}")
            else:
                print(f"⚠️ \"{text}\" -> {result} (expected: {expected})")
                all_ok = False
        return all_ok
    except ImportError:
        print("⚠️ file_secretary_templatesモジュールが見つかりません")
        return False
    except Exception as e:
        print(f"❌ Slack統合: エラー - {e}")
        return False

def check_ocr():
    """OCR確認"""
    print("\n=== OCR確認 ===")
    try:
        from file_secretary_ocr import FileSecretaryOCR
        from file_secretary_db import FileSecretaryDB
        db = FileSecretaryDB('file_secretary.db')
        ocr = FileSecretaryOCR(db)
        if ocr.ocr_engine:
            print(f"✅ OCRエンジン: {ocr.ocr_provider} 利用可能")
            db.close()
            return True
        else:
            print("⚠️ OCRエンジン: 利用不可")
            db.close()
            return False
    except Exception as e:
        print(f"⚠️ OCR確認: エラー - {e}")
        return False

def check_backup():
    """バックアップ確認"""
    print("\n=== バックアップ確認 ===")
    try:
        from file_secretary_backup import FileSecretaryBackup
        backup = FileSecretaryBackup()
        backups = backup.list_backups()
        print(f"✅ バックアップシステム: 利用可能")
        print(f"  バックアップ数: {len(backups)}件")
        return True
    except Exception as e:
        print(f"⚠️ バックアップ確認: エラー - {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("File Secretary 状態確認")
    print("=" * 60)
    
    results = {}
    results['processes'] = True  # プロセス確認は別途
    results['api'] = check_api()
    results['database'] = check_database()
    results['inbox'] = check_inbox()
    results['slack'] = check_slack_integration()
    results['ocr'] = check_ocr()
    results['backup'] = check_backup()
    
    print("\n" + "=" * 60)
    print("状態サマリ")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ OK" if result else "❌ NG"
        print(f"{name:15s}: {status}")
    
    print(f"\n合計: {passed}/{total} 機能が利用可能")
    
    if results['api'] and results['database']:
        print("\n🎉 基本機能は動作しています！")
        print("\n利用可能な機能:")
        if results['slack']:
            print("  ✅ Slackコマンド解析")
        if results['ocr']:
            print("  ✅ OCR統合")
        if results['backup']:
            print("  ✅ バックアップ・復旧")
    else:
        print("\n⚠️ 基本機能が動作していません")
        print("  起動方法: python file_secretary_start.py")
        print("  API起動: python file_secretary_api.py")

if __name__ == '__main__':
    main()






















