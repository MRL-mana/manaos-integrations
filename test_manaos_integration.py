#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS統合テスト
File SecretaryがManaOSシステムと統合されているか確認
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_intent_router():
    """Intent Router統合テスト"""
    print("=== Intent Router統合テスト ===")
    try:
        from intent_router import IntentRouter, IntentType
        
        router = IntentRouter()
        
        test_cases = [
            ("Inboxどう？", IntentType.FILE_STATUS),
            ("終わった", IntentType.FILE_ORGANIZE),
            ("戻して", IntentType.FILE_RESTORE),
            ("探して：日報", IntentType.FILE_SEARCH),
        ]
        
        all_ok = True
        for text, expected in test_cases:
            result = router.classify(text)
            if result.intent_type == expected:
                print(f"✅ \"{text}\" -> {result.intent_type.value} (confidence: {result.confidence:.2f})")
            else:
                print(f"⚠️ \"{text}\" -> {result.intent_type.value} (expected: {expected.value})")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"❌ Intent Router統合エラー: {e}")
        return False

def test_slack_integration():
    """Slack Integration統合テスト"""
    print("\n=== Slack Integration統合テスト ===")
    try:
        from slack_integration import execute_command
        
        # File Secretaryコマンドをテスト
        test_cases = [
            "Inboxどう？",
            "終わった",
            "戻して",
        ]
        
        all_ok = True
        for text in test_cases:
            try:
                result = execute_command(
                    text=text,
                    user="test_user",
                    channel="test_channel"
                )
                
                if result.get("status") == "success":
                    service = result.get("service", "unknown")
                    if service == "file_secretary":
                        print(f"✅ \"{text}\" -> File Secretary API呼び出し成功")
                    else:
                        print(f"⚠️ \"{text}\" -> {service} (expected: file_secretary)")
                        all_ok = False
                else:
                    print(f"⚠️ \"{text}\" -> {result.get('status')}: {result.get('error', 'unknown')}")
                    all_ok = False
            except Exception as e:
                print(f"⚠️ \"{text}\" -> エラー: {e}")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"❌ Slack Integration統合エラー: {e}")
        return False

def test_api_connection():
    """API接続テスト"""
    print("\n=== File Secretary API接続テスト ===")
    try:
        import httpx
        
        api_url = os.getenv("FILE_SECRETARY_URL", "http://localhost:5120")
        
        # ヘルスチェック
        response = httpx.get(f"{api_url}/health", timeout=5.0)
        if response.status_code == 200:
            print(f"✅ API接続成功: {api_url}")
            return True
        else:
            print(f"⚠️ API接続失敗: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"❌ API接続不可: {api_url} (起動していない可能性)")
        return False
    except Exception as e:
        print(f"❌ API接続エラー: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("ManaOS統合テスト")
    print("=" * 60)
    
    results = {}
    results['intent_router'] = test_intent_router()
    results['api_connection'] = test_api_connection()
    results['slack_integration'] = test_slack_integration()
    
    print("\n" + "=" * 60)
    print("統合テスト結果")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ OK" if result else "❌ NG"
        print(f"{name:20s}: {status}")
    
    print(f"\n合計: {passed}/{total} 統合が確認されました")
    
    if all(results.values()):
        print("\n🎉 ManaOS統合は完全に動作しています！")
        print("\n利用可能な機能:")
        print("  ✅ Intent Router: File Secretaryコマンド認識")
        print("  ✅ Slack Integration: File Secretary API呼び出し")
        print("  ✅ API接続: File Secretary APIサーバー接続")
    else:
        print("\n⚠️ 一部の統合が動作していません")
        if not results['api_connection']:
            print("  - File Secretary APIサーバーを起動してください")
        if not results['intent_router']:
            print("  - Intent Routerの設定を確認してください")
        if not results['slack_integration']:
            print("  - Slack Integrationの設定を確認してください")

if __name__ == '__main__':
    main()






















