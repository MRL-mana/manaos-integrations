#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS既存サービスとの統合テスト
"""

import json
import sys
from pathlib import Path

from step_deep_research.orchestrator import StepDeepResearchOrchestrator
from unified_logging import get_service_logger
logger = get_service_logger("integration-test")


def test_manaos_integration():
    """ManaOS統合テスト"""
    print("=" * 60)
    print("ManaOS統合テスト")
    print("=" * 60)
    
    # 設定読み込み
    config_path = Path("step_deep_research_config.json")
    if not config_path.exists():
        print(f"❌ 設定ファイルが見つかりません: {config_path}")
        return False
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # オーケストレーター初期化
    try:
        orchestrator = StepDeepResearchOrchestrator(config)
        print("✅ オーケストレーター初期化成功")
    except Exception as e:
        print(f"❌ オーケストレーター初期化失敗: {e}")
        return False
    
    # Trinity統合テスト
    print("\n[1] Trinity統合テスト")
    try:
        trinity = orchestrator.trinity
        
        # 各エージェントのルーティング確認
        from step_deep_research.trinity_integration import TrinityAgent
        assert trinity.get_agent_for_planning() == TrinityAgent.REMI
        assert trinity.get_agent_for_search() == TrinityAgent.LUNA
        assert trinity.get_agent_for_reading() == TrinityAgent.LUNA
        assert trinity.get_agent_for_verification() == TrinityAgent.MINA
        assert trinity.get_agent_for_writing() == TrinityAgent.REMI
        assert trinity.get_agent_for_critique() == TrinityAgent.MINA
        
        print("  ✅ Trinity統合正常")
    except Exception as e:
        print(f"  ❌ Trinity統合エラー: {e}")
        return False
    
    # 逆算データ生成器テスト
    print("\n[2] 逆算データ生成器テスト")
    try:
        reverse_generator = orchestrator.reverse_generator
        assert reverse_generator.learning_data_path.exists()
        print("  ✅ 逆算データ生成器正常")
    except Exception as e:
        print(f"  ❌ 逆算データ生成器エラー: {e}")
        return False
    
    # ManaOS既存モジュール統合テスト
    print("\n[3] ManaOS既存モジュール統合テスト")
    try:
        # manaos_logger
        from manaos_logger import get_logger
        test_logger = get_logger("test")
        test_logger.info("Test log message")
        print("  ✅ manaos_logger統合正常")
        
        # manaos_error_handler
        from manaos_error_handler import ManaOSErrorHandler
        test_handler = ManaOSErrorHandler("test")
        print("  ✅ manaos_error_handler統合正常")
        
    except Exception as e:
        print(f"  ❌ ManaOSモジュール統合エラー: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ すべての統合テストが成功しました！")
    print("=" * 60)
    
    return True


def main():
    """メイン関数"""
    success = test_manaos_integration()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

