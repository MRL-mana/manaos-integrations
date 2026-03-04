#!/usr/bin/env python3
"""
コマンド実行問題の診断と修正スクリプト
"""
import os
import sys
import subprocess
from pathlib import Path


def diagnose():
    """問題を診断"""
    print("🔍 コマンド実行問題の診断\n")

    issues = []

    # 1. Python環境確認
    print("1. Python環境:")
    print(f"   Version: {sys.version}")
    print(f"   Executable: {sys.executable}")
    print(f"   Path: {sys.path[:3]}")

    # 2. 環境変数確認
    print("\n2. 環境変数:")
    important_vars = ["PATH", "SHELL", "HOME", "USER"]
    for var in important_vars:
        value = os.getenv(var, "NOT SET")
        print(f"   {var}: {value}")
        if var == "PATH" and not value:
            issues.append("PATH環境変数が設定されていません")

    # 3. subprocessテスト
    print("\n3. subprocessテスト:")
    test_commands = [
        ("echo", ["echo", "test"]),
        ("pwd", ["pwd"]),
        ("python3", ["python3", "--version"]),
    ]

    for name, cmd in test_commands:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                env=os.environ.copy()
            )
            if result.returncode == 0:
                print(f"   ✅ {name}: OK")
                if result.stdout:
                    print(f"      Output: {result.stdout.strip()}")
            else:
                print(f"   ❌ {name}: Exit code {result.returncode}")
                if result.stderr:
                    print(f"      Error: {result.stderr.strip()}")
                issues.append(f"{name}コマンドが失敗しました")
        except FileNotFoundError:
            print(f"   ❌ {name}: コマンドが見つかりません")
            issues.append(f"{name}コマンドが見つかりません")
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            issues.append(f"{name}コマンドの実行エラー: {e}")

    # 4. ファイルアクセステスト
    print("\n4. ファイルアクセス:")
    test_files = [
        "/root/manaos_command_hub/main.py",
        "/bin/bash",
        "/usr/bin/python3",
    ]
    for file_path in test_files:
        path = Path(file_path)
        if path.exists():
            print(f"   ✅ {file_path}: 存在")
        else:
            print(f"   ❌ {file_path}: 存在しない")
            issues.append(f"{file_path}が見つかりません")

    # 5. 問題のまとめ
    print("\n" + "="*60)
    if issues:
        print("⚠️  発見された問題:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("✅ 問題は見つかりませんでした")
    print("="*60)

    return issues


def suggest_fixes(issues):
    """修正方法を提案"""
    if not issues:
        return

    print("\n💡 推奨される修正方法:\n")

    if any("PATH" in issue for issue in issues):
        print("1. PATH環境変数の設定:")
        print("   export PATH=/usr/bin:/bin:/usr/local/bin:$PATH")

    if any("コマンドが見つかりません" in issue for issue in issues):
        print("\n2. 必要なコマンドのインストール:")
        print("   sudo apt-get update")
        print("   sudo apt-get install -y python3 python3-pip")

    print("\n3. Pythonスクリプトを直接使用:")
    print("   cd /root/manaos_command_hub")
    print("   python3 start_server_direct.py")


def main():
    print("="*60)
    print("コマンド実行問題の診断と修正")
    print("="*60)
    print()

    issues = diagnose()
    suggest_fixes(issues)

    print("\n" + "="*60)
    print("診断完了")
    print("="*60)


if __name__ == "__main__":
    main()





