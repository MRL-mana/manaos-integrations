#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このはサーバー側のBrave Search APIキーをローカルのMCP設定に追加するスクリプト
"""

import subprocess
import json
import os
from pathlib import Path

def get_brave_api_key_from_konoha():
    """このはサーバー側からBrave Search APIキーを取得"""
    print("[1] このはサーバー側からBrave Search APIキーを取得中...")
    print("-" * 70)
    
    try:
        # SSH経由で環境変数を取得
        result = subprocess.run(
            ["ssh", "konoha", "env | grep BRAVE_API_KEY"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if 'BRAVE_API_KEY=' in line:
                    api_key = line.split('=', 1)[1]
                    print(f"  [OK] Brave Search APIキーを取得しました")
                    print(f"  APIキー: {api_key[:10]}...")
                    return api_key
    except subprocess.TimeoutExpired:
        print("  [WARN] SSH接続がタイムアウトしました")
    except FileNotFoundError:
        print("  [WARN] SSHコマンドが見つかりません")
    except Exception as e:
        print(f"  [WARN] SSH接続に失敗しました: {e}")
    
    print("  手動でAPIキーを入力してください")
    api_key = input("Brave Search APIキーを入力してください: ").strip()
    return api_key

def update_mcp_config(api_key: str):
    """MCP設定ファイルを更新"""
    print()
    print("[2] MCP設定ファイルを読み込み中...")
    print("-" * 70)
    
    mcp_config_path = Path.home() / ".cursor" / "mcp.json"
    mcp_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 既存の設定を読み込む
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print("  [OK] 既存の設定ファイルを読み込みました")
        except Exception as e:
            print(f"  [WARN] 設定ファイルの読み込みに失敗しました。新規作成します。: {e}")
            config = {"mcpServers": {}}
    else:
        print("  [INFO] 設定ファイルが存在しません。新規作成します。")
        config = {"mcpServers": {}}
    
    # mcpServersプロパティが存在しない場合は作成
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    print()
    print("[3] Brave Search APIキーをMCP設定に追加中...")
    print("-" * 70)
    
    updated = False
    
    # 各MCPサーバーに環境変数を追加
    for server_name, server_config in config["mcpServers"].items():
        # envプロパティが存在しない場合は作成
        if "env" not in server_config:
            server_config["env"] = {}
        
        # BRAVE_API_KEYを追加または更新
        if "BRAVE_API_KEY" not in server_config["env"] or server_config["env"]["BRAVE_API_KEY"] != api_key:
            server_config["env"]["BRAVE_API_KEY"] = api_key
            print(f"  [OK] {server_name} にBRAVE_API_KEYを追加しました")
            updated = True
        else:
            print(f"  [INFO] {server_name} には既にBRAVE_API_KEYが設定されています")
    
    # JSONに変換して保存
    if updated:
        print()
        print("[4] MCP設定ファイルを保存中...")
        print("-" * 70)
        with open(mcp_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"  [OK] MCP設定ファイルを保存しました: {mcp_config_path}")
    
    return updated

def update_env_files(api_key: str):
    """.envファイルを更新"""
    print()
    print("[5] .envファイルにも追加中...")
    print("-" * 70)
    
    script_dir = Path(__file__).parent
    env_path = script_dir / ".env"
    env_path_konoha = script_dir / "konoha_mcp_servers" / ".env"
    
    # メインの.envファイル
    if env_path.exists():
        env_content = env_path.read_text(encoding='utf-8')
        if "BRAVE_API_KEY=" not in env_content:
            env_content += f"\nBRAVE_API_KEY={api_key}\n"
            env_path.write_text(env_content, encoding='utf-8')
            print(f"  [OK] .envファイルに追加しました: {env_path}")
        else:
            # 既存の値を更新
            lines = env_content.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith("BRAVE_API_KEY="):
                    new_lines.append(f"BRAVE_API_KEY={api_key}")
                else:
                    new_lines.append(line)
            env_path.write_text('\n'.join(new_lines), encoding='utf-8')
            print(f"  [OK] .envファイルを更新しました: {env_path}")
    else:
        env_path.write_text(f"BRAVE_API_KEY={api_key}\n", encoding='utf-8')
        print(f"  [OK] .envファイルを作成しました: {env_path}")
    
    # konoha_mcp_servers/.envファイル
    env_path_konoha.parent.mkdir(parents=True, exist_ok=True)
    if env_path_konoha.exists():
        env_content_konoha = env_path_konoha.read_text(encoding='utf-8')
        if "BRAVE_API_KEY=" not in env_content_konoha:
            env_content_konoha += f"\nBRAVE_API_KEY={api_key}\n"
            env_path_konoha.write_text(env_content_konoha, encoding='utf-8')
            print(f"  [OK] konoha_mcp_servers/.envファイルに追加しました")
        else:
            lines = env_content_konoha.split('\n')
            new_lines = []
            for line in lines:
                if line.startswith("BRAVE_API_KEY="):
                    new_lines.append(f"BRAVE_API_KEY={api_key}")
                else:
                    new_lines.append(line)
            env_path_konoha.write_text('\n'.join(new_lines), encoding='utf-8')
            print(f"  [OK] konoha_mcp_servers/.envファイルを更新しました")
    else:
        env_path_konoha.write_text(f"BRAVE_API_KEY={api_key}\n", encoding='utf-8')
        print(f"  [OK] konoha_mcp_servers/.envファイルを作成しました")

def main():
    """メイン処理"""
    print("=" * 70)
    print("Brave Search APIキーをMCP設定に追加")
    print("=" * 70)
    print()
    
    # APIキーを取得
    api_key = get_brave_api_key_from_konoha()
    
    if not api_key:
        print("[ERROR] APIキーが入力されていません")
        return
    
    # MCP設定を更新
    updated = update_mcp_config(api_key)
    
    # .envファイルを更新
    update_env_files(api_key)
    
    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)
    print()
    print("[次のステップ]")
    print("1. Cursorを再起動してMCP設定を反映してください")
    print("2. Brave Search APIを使用するMCPサーバーが動作することを確認してください")
    print()
    print("設定ファイルの場所:")
    print(f"  MCP設定: {Path.home() / '.cursor' / 'mcp.json'}")
    print(f"  .env: {Path(__file__).parent / '.env'}")
    print(f"  konoha_mcp_servers/.env: {Path(__file__).parent / 'konoha_mcp_servers' / '.env'}")
    print()

if __name__ == "__main__":
    main()



