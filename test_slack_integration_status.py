#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack Integration状態確認
"""

import sys
import os
import httpx
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_slack_integration_process():
    """Slack Integrationプロセス確認"""
    print("=== Slack Integrationプロセス確認 ===")
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*Python*' } | Select-Object Id, ProcessName"],
            capture_output=True,
            text=True
        )
        if "slack_integration" in result.stdout.lower():
            print("✅ Slack Integrationプロセス実行中")
            print(result.stdout)
            return True
        else:
            print("⚠️ Slack Integrationプロセスが見つかりません")
            return False
    except:
        print("⚠️ プロセス確認失敗")
        return False

def check_slack_api():
    """Slack Integration API確認"""
    print("\n=== Slack Integration API確認 ===")
    port = os.getenv("PORT", "5114")
    api_url = f"http://localhost:{port}"
    
    try:
        response = httpx.get(f"{api_url}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Slack Integration API: 正常応答")
            print(f"   ポート: {port}")
            print(f"   ステータス: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"⚠️ Slack Integration API: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"❌ Slack Integration API: 接続不可（起動していない可能性）")
        print(f"   ポート: {port}")
        return False
    except Exception as e:
        print(f"❌ Slack Integration API: エラー - {e}")
        return False

def check_file_secretary_integration():
    """File Secretary統合確認"""
    print("\n=== File Secretary統合確認 ===")
    try:
        from slack_integration import execute_command
        
        # File Secretaryコマンドをテスト
        result = execute_command(
            text="Inboxどう？",
            user="test_user",
            channel="test_channel"
        )
        
        if result.get("status") == "success":
            service = result.get("service", "unknown")
            if service == "file_secretary":
                print("✅ File Secretary統合: 正常")
                return True
            else:
                print(f"⚠️ File Secretary統合: {service}（expected: file_secretary）")
                return False
        else:
            print(f"⚠️ File Secretary統合: {result.get('status')}")
            return False
    except Exception as e:
        print(f"⚠️ File Secretary統合確認エラー: {e}")
        return False

def check_environment_variables():
    """環境変数確認"""
    print("\n=== 環境変数確認 ===")
    port = os.getenv("PORT", "未設定（デフォルト: 5114）")
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "未設定")
    file_secretary_url = os.getenv("FILE_SECRETARY_URL", "未設定（デフォルト: http://localhost:5120）")
    
    print(f"PORT: {port}")
    print(f"SLACK_WEBHOOK_URL: {'設定済み' if webhook_url != '未設定' else '未設定'}")
    print(f"FILE_SECRETARY_URL: {file_secretary_url}")
    
    return webhook_url != "未設定"

def main():
    """メイン処理"""
    print("=" * 60)
    print("Slack Integration状態確認")
    print("=" * 60)
    
    results = {}
    results['process'] = check_slack_integration_process()
    results['api'] = check_slack_api()
    results['file_secretary'] = check_file_secretary_integration()
    results['env'] = check_environment_variables()
    
    print("\n" + "=" * 60)
    print("状態サマリ")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ OK" if result else "⚠️ NG"
        print(f"{name:20s}: {status}")
    
    print(f"\n合計: {passed}/{total} 項目が確認されました")
    
    if results['api']:
        print("\n🎉 Slack Integration APIは動作しています！")
        if results['file_secretary']:
            print("   ✅ File Secretary統合も正常です")
    else:
        print("\n⚠️ Slack Integrationが起動していません")
        print("   起動方法:")
        print("   python slack_integration.py")
        print("   または")
        print("   $env:PORT='5114'")
        print("   python slack_integration.py")

if __name__ == '__main__':
    main()

