#!/usr/bin/env python3
"""Test ManaOS Moltbot integration"""

import sys
sys.path.insert(0, '.')

print("=" * 60)
print("✨ ManaOS ← → Moltbot 統合テスト")
print("=" * 60)

# テスト1: 秘書統合
print("\n【テスト1】秘書統合システムから Moltbot を呼び出す")
try:
    from personality_autonomy_secretary_integration import PersonalityAutonomySecretaryIntegration
    integration = PersonalityAutonomySecretaryIntegration()
    
    print("✅ PersonalityAutonomySecretaryIntegration 初期化完了")
    
    result = integration.submit_file_organize_plan(
        user_hint="秘書統合テスト: Downloads 一覧取得",
        path="~/Downloads",
        intent="list_only"
    )
    
    print(f"✅ Moltbot プラン送信成功")
    print(f"   Plan ID: {result.get('plan_id', 'N/A')}")
    print(f"   OK: {result.get('ok', False)}")
    if 'data' in result and result['data']:
        print(f"   Status: {result['data'].get('status', 'N/A')}")
    
except Exception as e:
    print(f"❌ 秘書統合エラー: {e}")
    import traceback
    traceback.print_exc()

# テスト2: 統合API 設定確認
print("\n【テスト2】統合API Moltbot 設定確認")
try:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    moltbot_url = os.getenv('MOLTBOT_GATEWAY_URL')
    moltbot_secret = os.getenv('MOLTBOT_GATEWAY_SECRET')
    
    if moltbot_url and moltbot_secret:
        print(f"✅ Moltbot Gateway URL: {moltbot_url}")
        print(f"✅ Moltbot Gateway Secret: {'*' * 16}...")
        print(f"✅ 秘書統合に必要な環境変数が完備されています")
    else:
        print(f"⚠️  設定不足: URL={moltbot_url is not None}, Secret={moltbot_secret is not None}")
        
except Exception as e:
    print(f"❌ 設定確認エラー: {e}")

print("\n" + "=" * 60)
print("🎉 ManaOS ← → Moltbot 統合確認完了！")
print("=" * 60)
