#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack接続テスト
SlackからFile Secretaryが使えるか確認
"""

import sys
import os
import httpx
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_slack_integration_api():
    """Slack Integration API確認"""
    print("=== Slack Integration API確認 ===")
    try:
        response = httpx.get("http://localhost:5114/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Slack Integration API: 正常応答")
            print(f"   ステータス: {data.get('status')}")
            return True
        else:
            print(f"⚠️ Slack Integration API: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print("❌ Slack Integration API: 接続不可（起動していない可能性）")
        return False
    except Exception as e:
        print(f"❌ Slack Integration API: エラー - {e}")
        return False

def check_slack_config():
    """Slack設定確認"""
    print("\n=== Slack設定確認 ===")
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    verification_token = os.getenv("SLACK_VERIFICATION_TOKEN", "")
    
    webhook_ok = bool(webhook_url)
    token_ok = bool(verification_token)
    
    print(f"SLACK_WEBHOOK_URL: {'✅ 設定済み' if webhook_ok else '⚠️ 未設定'}")
    print(f"SLACK_VERIFICATION_TOKEN: {'✅ 設定済み' if token_ok else '⚠️ 未設定'}")
    
    return webhook_ok or token_ok

def check_file_secretary_api():
    """File Secretary API確認"""
    print("\n=== File Secretary API確認 ===")
    try:
        response = httpx.get("http://localhost:5120/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ File Secretary API: 正常応答")
            print(f"   ステータス: {data.get('status')}")
            return True
        else:
            print(f"⚠️ File Secretary API: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print("❌ File Secretary API: 接続不可")
        return False
    except Exception as e:
        print(f"❌ File Secretary API: エラー - {e}")
        return False

def test_file_secretary_command():
    """File Secretaryコマンドテスト"""
    print("\n=== File Secretaryコマンドテスト ===")
    try:
        from slack_integration import execute_command
        
        result = execute_command(
            text="Inboxどう？",
            user="test_user",
            channel="test_channel"
        )
        
        if result.get("status") == "success":
            service = result.get("service", "unknown")
            if service == "file_secretary":
                print("✅ File Secretaryコマンド: 正常動作")
                response_text = result.get("response_text", "")
                if response_text:
                    print(f"   レスポンス: {response_text[:100]}...")
                return True
            else:
                print(f"⚠️ File Secretaryコマンド: {service}（expected: file_secretary）")
                return False
        else:
            print(f"⚠️ File Secretaryコマンド: {result.get('status')}")
            print(f"   エラー: {result.get('error', 'unknown')}")
            return False
    except Exception as e:
        print(f"❌ File Secretaryコマンドテストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_slack_endpoints():
    """Slackエンドポイント確認"""
    print("\n=== Slackエンドポイント確認 ===")
    endpoints = [
        ("/health", "GET"),
        ("/api/slack/events", "POST"),
        ("/api/slack/command", "POST"),
        ("/api/slack/webhook", "POST")
    ]
    
    all_ok = True
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = httpx.get(f"http://localhost:5114{endpoint}", timeout=2.0)
            else:
                response = httpx.post(f"http://localhost:5114{endpoint}", json={}, timeout=2.0)
            
            if response.status_code in [200, 400, 401]:  # 400/401は設定の問題、エンドポイントは存在
                print(f"✅ {method} {endpoint}: 利用可能")
            else:
                print(f"⚠️ {method} {endpoint}: HTTP {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"⚠️ {method} {endpoint}: エラー - {e}")
            all_ok = False
    
    return all_ok

def main():
    """メイン処理"""
    print("=" * 60)
    print("Slack接続テスト")
    print("=" * 60)
    
    results = {}
    results['slack_api'] = check_slack_integration_api()
    results['file_secretary_api'] = check_file_secretary_api()
    results['slack_config'] = check_slack_config()
    results['file_secretary_command'] = test_file_secretary_command()
    results['slack_endpoints'] = check_slack_endpoints()
    
    print("\n" + "=" * 60)
    print("テスト結果")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ OK" if result else "⚠️ NG"
        print(f"{name:25s}: {status}")
    
    print(f"\n合計: {passed}/{total} テスト通過")
    
    if all([results['slack_api'], results['file_secretary_api'], results['file_secretary_command']]):
        print("\n🎉 SlackからFile Secretaryが使えます！")
        if results['slack_config']:
            print("   ✅ Slack設定も完了しています")
        else:
            print("   ⚠️ Slack設定が必要です（Webhook URLまたはVerification Token）")
            print("   - 設定方法: SLACK_PUBLIC_SETUP_COMPLETE.md を参照")
    else:
        print("\n⚠️ SlackからFile Secretaryが使えない可能性があります")
        if not results['slack_api']:
            print("   - Slack Integrationを起動してください")
        if not results['file_secretary_api']:
            print("   - File Secretary APIを起動してください")

if __name__ == '__main__':
    main()






















