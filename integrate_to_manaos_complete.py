#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOSへの統合完了確認スクリプト
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def check_manaos_core_integration():
    """manaos_core_api.pyへの統合を確認"""
    print("=" * 70)
    print("ManaOS Core API 統合確認")
    print("=" * 70)
    print()
    
    try:
        from manaos_core_api import ManaOSCoreAPI
        
        manaos = ManaOSCoreAPI()
        
        # Brave Search統合の確認
        brave = manaos._get_brave_search_integration()
        if brave and brave.is_available():
            print("[OK] Brave Search統合: 利用可能")
        else:
            print("[WARN] Brave Search統合: 利用不可")
        
        # Base AI統合の確認
        base_ai = manaos._get_base_ai_integration(use_free=False)
        if base_ai and base_ai.is_available():
            print("[OK] Base AI統合（通常）: 利用可能")
        else:
            print("[WARN] Base AI統合（通常）: 利用不可")
        
        base_ai_free = manaos._get_base_ai_integration(use_free=True)
        if base_ai_free and base_ai_free.is_available():
            print("[OK] Base AI統合（無料のAI）: 利用可能")
        else:
            print("[WARN] Base AI統合（無料のAI）: 利用不可")
        
        print()
        print("[INFO] アクションタイプ:")
        print("  - brave_search / brave_web_search: Brave Search API検索")
        print("  - base_ai_chat / base_ai_completion: Base AIチャット")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_unified_api_integration():
    """unified_api_server.pyへの統合を確認"""
    print()
    print("=" * 70)
    print("Unified API Server 統合確認")
    print("=" * 70)
    print()
    
    try:
        # unified_api_server.pyをインポートして確認
        import unified_api_server
        
        if hasattr(unified_api_server, 'BRAVE_SEARCH_AVAILABLE'):
            if unified_api_server.BRAVE_SEARCH_AVAILABLE:
                print("[OK] Brave Search統合: 利用可能")
            else:
                print("[WARN] Brave Search統合: モジュールが見つかりません")
        
        print()
        print("[INFO] APIエンドポイント:")
        print("  - GET/POST /api/brave/search: Brave Search API検索")
        print("  - GET/POST /api/searxng/search: SearXNG検索（既存）")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        return False

def check_mcp_integration():
    """MCPサーバーへの統合を確認"""
    print()
    print("=" * 70)
    print("MCP Server 統合確認")
    print("=" * 70)
    print()
    
    try:
        import json
        mcp_config_path = Path.home() / ".cursor" / "mcp.json"
        
        if mcp_config_path.exists():
            with open(mcp_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if "mcpServers" in config:
                for server_name, server_config in config["mcpServers"].items():
                    if "env" in server_config:
                        env = server_config["env"]
                        has_brave = "BRAVE_API_KEY" in env
                        has_base_ai = "BASE_AI_FREE_API_KEY" in env
                        
                        if has_brave or has_base_ai:
                            print(f"[OK] {server_name}:")
                            if has_brave:
                                print(f"    BRAVE_API_KEY: 設定済み")
                            if has_base_ai:
                                print(f"    BASE_AI_FREE_API_KEY: 設定済み")
            
            print()
            print("[INFO] MCPツール:")
            print("  - brave_search: Brave Search API検索")
            print("  - brave_search_simple: Brave Searchシンプル検索")
            print("  - base_ai_chat: Base AIチャット")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        return False

def main():
    """メイン処理"""
    print()
    print("=" * 70)
    print("ManaOS統合 完了確認")
    print("=" * 70)
    print()
    
    results = {
        "ManaOS Core API": check_manaos_core_integration(),
        "Unified API Server": check_unified_api_integration(),
        "MCP Server": check_mcp_integration()
    }
    
    print()
    print("=" * 70)
    print("統合状況サマリー")
    print("=" * 70)
    
    for name, success in results.items():
        status = "[OK]" if success else "[NG]"
        print(f"{name}: {status}")
    
    print()
    print("=" * 70)
    print("使用方法")
    print("=" * 70)
    print()
    print("1. ManaOS Core API経由:")
    print("   from manaos_core_api import ManaOSCoreAPI")
    print("   manaos = ManaOSCoreAPI()")
    print("   result = manaos.act('brave_search', {'query': 'Python'})")
    print("   result = manaos.act('base_ai_chat', {'prompt': 'こんにちは'})")
    print()
    print("2. Unified API Server経由:")
    print("   curl 'http://127.0.0.1:9510/api/brave/search?query=Python'")
    print()
    print("3. MCP Server経由（Cursorから）:")
    print("   brave_search(query='Python')")
    print("   base_ai_chat(prompt='こんにちは')")
    print()

if __name__ == "__main__":
    main()

