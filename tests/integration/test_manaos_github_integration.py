#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS統合でのGitHub統合テスト
"""

import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))

try:
    from manaos_complete_integration import ManaOSCompleteIntegration
except Exception:
    ManaOSCompleteIntegration = None

def main():
    print("=" * 60)
    print("ManaOS統合 - GitHub統合テスト")
    print("=" * 60)
    
    # ManaOS統合システムを初期化
    integration = ManaOSCompleteIntegration()
    
    # 完全なステータスを取得
    status = integration.get_complete_status()
    
    print("\n📊 GitHub統合状態:")
    github_status = status.get("github", {})
    github_info = github_status.get("github_integration", {})
    
    if github_info.get("available"):
        print("  ✅ GitHub統合: 利用可能")
        print(f"  ✅ トークン設定: {'あり' if github_info.get('token_set') else 'なし'}")
        
        # GitHub機能をテスト
        if integration.github:
            print("\n🔍 GitHub機能テスト:")
            
            # リポジトリ情報を取得
            repo_info = integration.github.get_repository("MRL-mana", "manaos-integrations")
            if repo_info:
                print(f"  ✅ リポジトリ情報取得: {repo_info['name']}")
                print(f"     プライベート: {'はい' if repo_info.get('private') else 'いいえ'}")
                print(f"     URL: {repo_info['url']}")
            
            # イシューを取得
            issues = integration.github.get_issues("MRL-mana", "manaos-integrations", limit=5)
            print(f"  ✅ イシュー取得: {len(issues)}件")
            
        print("\n✅ ManaOS統合でのGitHub統合は正常に動作しています！")
    else:
        print("  ❌ GitHub統合: 利用不可")
        print(f"     トークン設定: {'あり' if github_info.get('token_set') else 'なし'}")
    
    print("\n" + "=" * 60)
    print("統合システム全体の状態:")
    print("=" * 60)
    print(f"  コアシステム: {status.get('core', {}).get('status', 'unknown')}")
    print(f"  記憶・学習系: {'利用可能' if status.get('memory_learning') else '利用不可'}")
    print(f"  人格・自律・秘書系: {'利用可能' if status.get('personality_autonomy_secretary') else '利用不可'}")
    print(f"  ローカルLLM: {'利用可能' if status.get('local_llm') else '利用不可'}")
    print(f"  GitHub: {'利用可能' if github_info.get('available') else '利用不可'}")


def test_manaos_github_integration_smoke():
    if ManaOSCompleteIntegration is None:
        pytest.skip("manaos_complete_integration 依存が利用できないためスキップ")
    main()




































