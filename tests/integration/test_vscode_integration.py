#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS VSCode/Cursor統合テスト
各サービスの接続状態を確認
"""

import sys
import json
import subprocess
from pathlib import Path
import time

def check_mcp_config():
    """MCP設定ファイルを確認"""
    print("\n📋 MCP設定確認:")
    print("=" * 60)
    
    cursor_mcp = Path.home() / ".cursor" / "mcp.json"
    vscode_settings = Path.home() / ".vscode" / "settings.json"
    
    # Cursor設定
    if cursor_mcp.exists():
        with open(cursor_mcp, 'r', encoding='utf-8') as f:
            cursor_config = json.load(f)
        servers = cursor_config.get('mcpServers', {})
        print(f"✅ Cursor MCP設定: {len(servers)} サーバー登録済み")
        print(f"   サーバー一覧: {', '.join(list(servers.keys())[:5])}...")
    else:
        print(f"❌ Cursor MCP設定が見つかりません")
    
    # VSCode設定
    if vscode_settings.exists():
        with open(vscode_settings, 'r', encoding='utf-8') as f:
            vscode_config = json.load(f)
        manaos = vscode_config.get('manaos', {})
        if manaos:
            print(f"✅ VSCode ManaOS設定: 有効")
            print(f"   - メモリ: {manaos.get('memory', {}).get('enabled', False)}")
            print(f"   - 学習: {manaos.get('learning', {}).get('enabled', False)}")
            print(f"   - LLMルーティング: {manaos.get('llmRouting', {}).get('enabled', False)}")
        else:
            print(f"⚠️  VSCode ManaOS設定: 見つかりません")
    else:
        print(f"❌ VSCode設定が見つかりません")

def check_modules():
    """利用可能なモジュールを確認"""
    print("\n📦 ManaOSモジュール確認:")
    print("=" * 60)
    
    manaos_path = Path("c:\\Users\\mana4\\Desktop\\manaos_integrations")
    
    modules = [
        "mrl_memory_system.py",
        "learning_system_api.py",
        "learning_system.py",
        "manaos_unified_client.py",
        "maneaos_logger.py"
    ]
    
    for module in modules:
        path = manaos_path / module
        if path.exists():
            print(f"✅ {module}")
        else:
            print(f"❌ {module} - 見つかりません")

def check_port_availability():
    """ポートの利用可能状況を確認"""
    print("\n🔌 ポート利用状況:")
    print("=" * 60)
    
    ports = {
        5103: "MRL Memory",
        5104: "Learning System",
        5117: "LLM Routing",
        9502: "Unified API"
    }
    
    import socket
    
    for port, name in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            print(f"✅ ポート {port} ({name}): 接続可能 - サービス起動中？")
        else:
            print(f"⭕ ポート {port} ({name}): 未使用")
        sock.close()

def check_python_env():
    """Python環境を確認"""
    print("\n🐍 Python環境:")
    print("=" * 60)
    
    print(f"Python: {sys.version}")
    print(f"実行ファイル: {sys.executable}")
    
    # 主要モジュールの確認
    try:
        import importlib.metadata
        flask_version = importlib.metadata.version("flask")
        print(f"✅ Flask: {flask_version}")
    except Exception:
        print(f"❌ Flask: インストール済みではありません")
    
    try:
        import requests
        print(f"✅ Requests: インストール済み")
    except ImportError:
        print(f"❌ Requests: インストール済みではありません")

def main():
    """メイン処理"""
    print("\n" + "=" * 60)
    print("🔍 ManaOS VSCode/Cursor統合テスト")
    print("=" * 60)
    
    check_python_env()
    check_mcp_config()
    check_modules()
    check_port_availability()
    
    print("\n" + "=" * 60)
    print("✅ 統合テスト完了")
    print("=" * 60)
    
    print("\n📝 次のステップ:")
    print("  1. 各モジュールが揃っているか確認")
    print("  2. 必要なポートが空いているか確認")
    print("  3. 以下コマンドでサービスを個別に起動:")
    print("")
    print("  cd c:\\Users\\mana4\\Desktop\\manaos_integrations")
    print("  python mrl_memory_system.py")
    print("  python learning_system_api.py")
    print("")


