#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCPサーバー設定検証スクリプト
環境変数の設定状況を確認します
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

# 必要な環境変数の定義
REQUIRED_ENV_VARS = {
    "manaos_unified_mcp_server": [
        # 必須ではないが推奨
        ("COMFYUI_URL", False, "http://localhost:8188"),
        ("MANAOS_INTEGRATION_API_URL", False, "http://localhost:9500"),
        ("OBSIDIAN_VAULT_PATH", False, "/app/obsidian_vault"),
    ],
    "n8n_mcp_server": [
        ("N8N_BASE_URL", False, "http://localhost:5678"),
        ("N8N_API_KEY", True, None),  # APIキーは必須
    ],
    "svi_mcp_server": [
        ("COMFYUI_URL", False, "http://localhost:8188"),
    ],
}

OPTIONAL_ENV_VARS = [
    "SEARXNG_BASE_URL",
    "OPENWEBUI_URL",
    "OPENWEBUI_API_KEY",
    "BASE_AI_USE_FREE",
    "SLACK_BOT_TOKEN",
    "SLACK_WEBHOOK_URL",
    "BRAVE_API_KEY",
    "ROWS_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
]


def check_env_var(name: str, required: bool, default: str = None) -> Tuple[bool, str, str]:
    """
    環境変数をチェック
    
    Returns:
        (is_set, value, message)
    """
    value = os.getenv(name)
    
    if value:
        return (True, value, f"✅ {name}: 設定済み")
    elif default:
        return (False, default, f"⚠️  {name}: 未設定（デフォルト値: {default} を使用）")
    elif required:
        return (False, None, f"❌ {name}: 未設定（必須）")
    else:
        return (False, None, f"⚠️  {name}: 未設定（オプション）")


def validate_mcp_server_config(server_name: str) -> Tuple[bool, List[str]]:
    """
    MCPサーバーの設定を検証
    
    Returns:
        (is_valid, messages)
    """
    messages = []
    is_valid = True
    
    if server_name not in REQUIRED_ENV_VARS:
        messages.append(f"⚠️  サーバー '{server_name}' の定義が見つかりません")
        return (False, messages)
    
    messages.append(f"\n📋 {server_name} の設定確認:")
    messages.append("=" * 60)
    
    for env_var, required, default in REQUIRED_ENV_VARS[server_name]:
        is_set, value, message = check_env_var(env_var, required, default)
        messages.append(message)
        if required and not is_set:
            is_valid = False
    
    return (is_valid, messages)


def validate_all_optional() -> List[str]:
    """オプション環境変数をチェック"""
    messages = []
    messages.append("\n📋 オプション設定:")
    messages.append("=" * 60)
    
    for env_var in OPTIONAL_ENV_VARS:
        is_set, value, message = check_env_var(env_var, False)
        messages.append(message)
    
    return messages


def main():
    """メイン関数"""
    print("🔍 MCPサーバー設定検証")
    print("=" * 60)
    
    all_valid = True
    all_messages = []
    
    # 各MCPサーバーの設定を確認
    for server_name in REQUIRED_ENV_VARS.keys():
        is_valid, messages = validate_mcp_server_config(server_name)
        all_messages.extend(messages)
        if not is_valid:
            all_valid = False
    
    # オプション設定を確認
    all_messages.extend(validate_all_optional())
    
    # 結果を表示
    for message in all_messages:
        print(message)
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ すべての必須設定が正しく設定されています")
        return 0
    else:
        print("❌ 一部の必須設定が不足しています")
        print("\n💡 対処法:")
        print("1. .env.example をコピーして .env ファイルを作成")
        print("2. .env ファイルに必要な環境変数を設定")
        print("3. 環境変数を読み込む（python-dotenvを使用するか、システム環境変数に設定）")
        return 1


if __name__ == "__main__":
    sys.exit(main())
