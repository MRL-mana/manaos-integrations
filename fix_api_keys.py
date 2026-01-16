#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIキーを正しく設定し直すスクリプト
"""

import json
import os
from pathlib import Path

def update_env_file():
    """.envファイルを更新"""
    print("[1] .envファイルを更新中...")
    print("-" * 70)
    
    script_dir = Path(__file__).parent
    env_path = script_dir / ".env"
    
    # 正しいAPIキー
    brave_api_key = "BSAiH65IwkYNaDe2HWdgbkpKhqFIhBg"  # Brave Search APIキー（マナ2）
    base_ai_free_api_key = "BSAywv5GfARItfoSwOs362lvsqMkHHb"  # Base AI 無料のAI APIキー
    
    # 既存の内容を読み込む
    env_content = ""
    if env_path.exists():
        env_content = env_path.read_text(encoding='utf-8')
    
    # APIキーを更新
    lines = env_content.split('\n')
    new_lines = []
    updated_keys = {}
    
    for line in lines:
        if line.startswith("BRAVE_API_KEY="):
            new_lines.append(f"BRAVE_API_KEY={brave_api_key}")
            updated_keys["BRAVE_API_KEY"] = brave_api_key
        elif line.startswith("BASE_AI_FREE_API_KEY="):
            new_lines.append(f"BASE_AI_FREE_API_KEY={base_ai_free_api_key}")
            updated_keys["BASE_AI_FREE_API_KEY"] = base_ai_free_api_key
        elif line.startswith("BASE_AI_API_KEY="):
            # Base AI APIキーは削除（実際のキーがないため）
            # または、Base AIの無料キーを使う場合はそのまま
            if "BSAiH65IwkYNaDe2HWdgbkpKhqFIhBg" in line:
                # これはBrave Search APIキーなので削除
                continue
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # 新しいキーを追加（存在しない場合）
    if "BRAVE_API_KEY=" not in env_content:
        new_lines.append(f"BRAVE_API_KEY={brave_api_key}")
        updated_keys["BRAVE_API_KEY"] = brave_api_key
    
    if "BASE_AI_FREE_API_KEY=" not in env_content:
        new_lines.append(f"BASE_AI_FREE_API_KEY={base_ai_free_api_key}")
        updated_keys["BASE_AI_FREE_API_KEY"] = base_ai_free_api_key
    
    env_path.write_text('\n'.join(new_lines), encoding='utf-8')
    
    print("  [OK] .envファイルを更新しました")
    for key, value in updated_keys.items():
        print(f"    {key}: {value[:10]}...")
    
    return updated_keys

def update_mcp_config(api_keys: dict):
    """MCP設定ファイルを更新"""
    print()
    print("[2] MCP設定ファイルを更新中...")
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
        
        # 各MCPサーバーにAPIキーを更新
        for server_name, server_config in config["mcpServers"].items():
            if "env" not in server_config:
                server_config["env"] = {}
            
            # Brave Search APIキーを更新
            if "BRAVE_API_KEY" in api_keys:
                old_key = server_config["env"].get("BRAVE_API_KEY", "")
                if old_key != api_keys["BRAVE_API_KEY"]:
                    server_config["env"]["BRAVE_API_KEY"] = api_keys["BRAVE_API_KEY"]
                    print(f"  [OK] {server_name} のBRAVE_API_KEYを更新しました")
                    updated = True
            
            # Base AI APIキーを更新
            if "BASE_AI_FREE_API_KEY" in api_keys:
                old_key = server_config["env"].get("BASE_AI_FREE_API_KEY", "")
                if old_key != api_keys["BASE_AI_FREE_API_KEY"]:
                    server_config["env"]["BASE_AI_FREE_API_KEY"] = api_keys["BASE_AI_FREE_API_KEY"]
                    print(f"  [OK] {server_name} のBASE_AI_FREE_API_KEYを更新しました")
                    updated = True
            
            # Base AI APIキーがBrave Search APIキーと同じ場合は削除
            if "BASE_AI_API_KEY" in server_config["env"]:
                if server_config["env"]["BASE_AI_API_KEY"] == api_keys.get("BRAVE_API_KEY"):
                    del server_config["env"]["BASE_AI_API_KEY"]
                    print(f"  [OK] {server_name} の誤ったBASE_AI_API_KEYを削除しました")
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

def main():
    """メイン処理"""
    print("=" * 70)
    print("APIキーを正しく設定し直す")
    print("=" * 70)
    print()
    print("正しい設定:")
    print("  BRAVE_API_KEY: BSAiH65IwkYNaDe2HWdgbkpKhqFIhBg (Brave Search APIキー)")
    print("  BASE_AI_FREE_API_KEY: BSAywv5GfARItfoSwOs362lvsqMkHHb (Base AI 無料のAI)")
    print()
    
    # .envファイルを更新
    api_keys = update_env_file()
    
    # MCP設定を更新
    update_mcp_config(api_keys)
    
    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)
    print()
    print("[次のステップ]")
    print("1. Cursorを再起動してMCP設定を反映してください")
    print("2. Brave Search APIとBase AI APIをテストしてください")
    print()

if __name__ == "__main__":
    main()


