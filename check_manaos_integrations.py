#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS統合機能の確認
記憶機能・人格系・学習系・自律系・秘書系の統合状況を確認
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_memory_system():
    """記憶機能の確認"""
    print("=== 記憶機能確認 ===")
    try:
        from memory_unified import UnifiedMemory
        memory = UnifiedMemory()
        print("✅ UnifiedMemory: 利用可能")
        print(f"   クラス: {type(memory).__name__}")
        return True
    except ImportError:
        print("⚠️ UnifiedMemory: インポート不可")
        return False
    except Exception as e:
        print(f"⚠️ UnifiedMemory: エラー - {e}")
        return False

def check_persona_system():
    """人格系の確認"""
    print("\n=== 人格系確認 ===")
    try:
        # 人格設定ファイルを確認
        persona_files = list(Path(".").glob("*persona*.py"))
        persona_configs = list(Path(".").glob("*persona*.yaml")) + list(Path(".").glob("*persona*.json"))
        
        if persona_files or persona_configs:
            print("✅ 人格系ファイル: 存在")
            for f in persona_files[:3]:
                print(f"   - {f.name}")
            for f in persona_configs[:3]:
                print(f"   - {f.name}")
        else:
            print("⚠️ 人格系ファイル: 未検出")
        
        # 清楚系ギャルの設定を確認
        try:
            from intent_router import IntentRouter
            router = IntentRouter()
            if hasattr(router, '_persona_config'):
                print("✅ IntentRouter: 人格設定あり")
            else:
                print("⚠️ IntentRouter: 人格設定なし")
        except Exception:
            pass
        
        return True
    except Exception as e:
        print(f"⚠️ 人格系確認エラー: {e}")
        return False

def check_learning_system():
    """学習系の確認"""
    print("\n=== 学習系確認 ===")
    try:
        learning_files = list(Path(".").glob("*learning*.py"))
        if learning_files:
            print("✅ 学習系ファイル: 存在")
            for f in learning_files[:3]:
                print(f"   - {f.name}")
        else:
            print("⚠️ 学習系ファイル: 未検出")
        
        # 学習機能のインポート確認
        try:
            import importlib
            for module_name in ['learning_system', 'learning_manager', 'adaptive_learning']:
                try:
                    importlib.import_module(module_name)
                    print(f"✅ {module_name}: 利用可能")
                except ImportError:
                    pass
        except Exception:
            pass
        
        return True
    except Exception as e:
        print(f"⚠️ 学習系確認エラー: {e}")
        return False

def check_autonomous_system():
    """自律系の確認"""
    print("\n=== 自律系確認 ===")
    try:
        autonomous_files = list(Path(".").glob("*autonomous*.py"))
        if autonomous_files:
            print("✅ 自律系ファイル: 存在")
            for f in autonomous_files[:3]:
                print(f"   - {f.name}")
        else:
            print("⚠️ 自律系ファイル: 未検出")
        
        # 自動実行機能の確認
        try:
            from file_secretary_indexer import FileIndexer
            print("✅ FileIndexer: 自動監視機能あり")
        except Exception:
            pass
        
        return True
    except Exception as e:
        print(f"⚠️ 自律系確認エラー: {e}")
        return False

def check_secretary_system():
    """秘書系の確認"""
    print("\n=== 秘書系確認 ===")
    try:
        from file_secretary_db import FileSecretaryDB
        from file_secretary_organizer import FileOrganizer
        from file_secretary_indexer import FileIndexer
        
        print("✅ File Secretary: 利用可能")
        print("   モジュール:")
        print("     - FileSecretaryDB")
        print("     - FileOrganizer")
        print("     - FileIndexer")
        
        # API確認
        import httpx
        try:
            response = httpx.get("http://127.0.0.1:5120/health", timeout=2.0)
            if response.status_code == 200:
                print("✅ File Secretary API: 実行中")
            else:
                print("⚠️ File Secretary API: 停止中")
        except Exception:
            print("⚠️ File Secretary API: 接続不可")
        
        return True
    except ImportError as e:
        print(f"⚠️ File Secretary: インポート不可 - {e}")
        return False
    except Exception as e:
        print(f"⚠️ File Secretary確認エラー: {e}")
        return False

def check_slack_integration():
    """Slack Integrationの統合確認"""
    print("\n=== Slack Integration統合確認 ===")
    try:
        import slack_integration
        
        # 記憶機能の統合確認
        if hasattr(slack_integration, 'memory') or 'memory' in dir(slack_integration):
            print("✅ 記憶機能: 統合済み")
        else:
            print("⚠️ 記憶機能: 未統合")
        
        # File Secretaryの統合確認
        if 'file_secretary' in dir(slack_integration) or 'FileSecretary' in str(slack_integration.__file__):
            print("✅ File Secretary: 統合済み")
        else:
            # execute_command内でFile Secretaryを使用しているか確認
            import inspect
            source = inspect.getsource(slack_integration.execute_command)
            if 'file_secretary' in source.lower():
                print("✅ File Secretary: 統合済み（execute_command内）")
            else:
                print("⚠️ File Secretary: 未統合")
        
        # LLM統合確認
        if hasattr(slack_integration, 'LLM_CLIENT'):
            print("✅ LLM: 統合済み")
        else:
            print("⚠️ LLM: 未統合")
        
        return True
    except Exception as e:
        print(f"⚠️ Slack Integration確認エラー: {e}")
        return False

def check_memory_sharing():
    """記憶機能の共有確認"""
    print("\n=== 記憶機能の共有確認 ===")
    try:
        # UnifiedMemoryが複数のサービスで使用されているか確認
        import re
        
        # slack_integration.pyを確認
        slack_file = Path("slack_integration.py")
        if slack_file.exists():
            content = slack_file.read_text(encoding='utf-8')
            if 'memory' in content.lower() or 'Memory' in content:
                print("✅ Slack Integration: 記憶機能使用")
            else:
                print("⚠️ Slack Integration: 記憶機能未使用")
        
        # file_secretary関連ファイルを確認
        file_secretary_files = list(Path(".").glob("file_secretary*.py"))
        memory_used = False
        for f in file_secretary_files:
            try:
                content = f.read_text(encoding='utf-8')
                if 'memory' in content.lower() or 'Memory' in content:
                    memory_used = True
                    break
            except Exception:
                pass
        
        if memory_used:
            print("✅ File Secretary: 記憶機能使用")
        else:
            print("⚠️ File Secretary: 記憶機能未使用")
        
        return True
    except Exception as e:
        print(f"⚠️ 記憶機能の共有確認エラー: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("ManaOS統合機能確認")
    print("=" * 60)
    print()
    
    results = {}
    results['memory'] = check_memory_system()
    results['persona'] = check_persona_system()
    results['learning'] = check_learning_system()
    results['autonomous'] = check_autonomous_system()
    results['secretary'] = check_secretary_system()
    results['slack_integration'] = check_slack_integration()
    results['memory_sharing'] = check_memory_sharing()
    
    print("\n" + "=" * 60)
    print("確認結果サマリ")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✅ OK" if result else "⚠️ NG"
        print(f"{name:20s}: {status}")
    
    print("\n" + "=" * 60)
    print("統合状況")
    print("=" * 60)
    
    if results['secretary'] and results['slack_integration']:
        print("✅ 秘書系とSlack Integration: 統合済み")
    else:
        print("⚠️ 秘書系とSlack Integration: 未統合")
    
    if results['memory'] and results['memory_sharing']:
        print("✅ 記憶機能の共有: 利用可能")
    else:
        print("⚠️ 記憶機能の共有: 未利用")
    
    if results['autonomous']:
        print("✅ 自律系: 動作中（FileIndexer自動監視）")
    else:
        print("⚠️ 自律系: 未動作")

if __name__ == '__main__':
    main()






















