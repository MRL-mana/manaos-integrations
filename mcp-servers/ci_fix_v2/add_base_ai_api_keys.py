#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base AI APIキーを設定に追加するスクリプト
"""

import json
import os
from pathlib import Path

def update_mcp_config(api_keys: dict):
    """MCP設定ファイルを更新"""
    print("[1] MCP設定ファイルを更新中...")
    print("-" * 70)
    
    mcp_config_path = Path.home() / ".cursor" / "mcp.json"
    
    if not mcp_config_path.exists():
        print(f"  [WARN] MCP設定ファイルが見つかりません: {mcp_config_path}")
        return False
    
    try:
        with open(mcp_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        updated = False
        
        # 各MCPサーバーにBase AI APIキーを追加
        for server_name, server_config in config["mcpServers"].items():
            if "env" not in server_config:
                server_config["env"] = {}
            
            # Base AI APIキーを追加
            for key_name, api_key in api_keys.items():
                if key_name not in server_config["env"] or server_config["env"][key_name] != api_key:
                    server_config["env"][key_name] = api_key
                    print(f"  [OK] {server_name} に{key_name}を追加しました")
                    updated = True
        
        if updated:
            with open(mcp_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"  [OK] MCP設定ファイルを保存しました: {mcp_config_path}")
            return True
        else:
            print("  [INFO] 更新する項目がありませんでした")
            return False
            
    except Exception as e:
        print(f"  [ERROR] MCP設定ファイルの更新に失敗しました: {e}")
        return False

def update_env_files(api_keys: dict):
    """.envファイルを更新"""
    print()
    print("[2] .envファイルを更新中...")
    print("-" * 70)
    
    script_dir = Path(__file__).parent
    env_paths = [
        script_dir / ".env",
        script_dir / "konoha_mcp_servers" / ".env"
    ]
    
    for env_path in env_paths:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 既存の内容を読み込む
        env_content = ""
        if env_path.exists():
            env_content = env_path.read_text(encoding='utf-8')
        
        updated = False
        
        # 各APIキーを追加または更新
        for key_name, api_key in api_keys.items():
            if f"{key_name}=" not in env_content:
                if env_content and not env_content.endswith('\n'):
                    env_content += '\n'
                env_content += f"{key_name}={api_key}\n"
                updated = True
                print(f"  [OK] {env_path.name} に{key_name}を追加しました")
            else:
                # 既存の値を更新
                lines = env_content.split('\n')
                new_lines = []
                found = False
                for line in lines:
                    if line.startswith(f"{key_name}="):
                        new_lines.append(f"{key_name}={api_key}")
                        found = True
                        updated = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"{key_name}={api_key}")
                    updated = True
                env_content = '\n'.join(new_lines)
                if updated:
                    print(f"  [OK] {env_path.name} の{key_name}を更新しました")
        
        if updated:
            env_path.write_text(env_content, encoding='utf-8')

def main():
    """メイン処理"""
    print("=" * 70)
    print("Base AI APIキーを設定に追加")
    print("=" * 70)
    print()
    
    # Base AI APIキー
    api_keys = {
        "BASE_AI_API_KEY": "BSAiH65IwkYNaDe2HWdgbkpKhqFIhBg",  # 無料
        "BASE_AI_FREE_API_KEY": "BSAywv5GfARItfoSwOs362lvsqMkHHb"  # 無料のAI
    }
    
    print("設定するAPIキー:")
    for key_name, api_key in api_keys.items():
        masked_key = api_key[:8] + "*" * (len(api_key) - 16) + api_key[-8:]
        print(f"  {key_name}: {masked_key}")
    print()
    
    # MCP設定を更新
    update_mcp_config(api_keys)
    
    # .envファイルを更新
    update_env_files(api_keys)
    
    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)
    print()
    print("[次のステップ]")
    print("1. Cursorを再起動してMCP設定を反映してください")
    print("2. Base AI APIを使用する機能が動作することを確認してください")
    print()
    print("設定されたAPIキー:")
    print(f"  BASE_AI_API_KEY: {api_keys['BASE_AI_API_KEY'][:8]}...")
    print(f"  BASE_AI_FREE_API_KEY: {api_keys['BASE_AI_FREE_API_KEY'][:8]}...")
    print()

if __name__ == "__main__":
    main()



