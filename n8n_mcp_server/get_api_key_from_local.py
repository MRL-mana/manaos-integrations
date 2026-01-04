"""
ローカルのn8nからAPIキーを取得するスクリプト
（n8nのWeb UIから手動で取得する必要があります）
"""
import webbrowser
import os

N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5679")

print("=" * 60)
print("n8n APIキー取得ガイド")
print("=" * 60)
print()
print("ローカルのn8nからAPIキーを取得してください")
print()
print("手順:")
print("1. ブラウザでn8nを開きます...")
print()

# ブラウザでn8nを開く
settings_url = f"{N8N_BASE_URL}/settings/api"
print(f"URL: {settings_url}")
webbrowser.open(settings_url)

print()
print("2. 以下の手順でAPIキーを作成してください:")
print("   - 右上のユーザーアイコンをクリック")
print("   - Settings を選択")
print("   - 左メニューから API を選択")
print("   - Create API Key をクリック")
print("   - APIキー名を入力（例: MCP Server）")
print("   - Create をクリック")
print("   - 生成されたAPIキーをコピー")
print()
print("3. コピーしたAPIキーを入力してください:")
print()

api_key = input("APIキー: ").strip()

if not api_key:
    print("[NG] APIキーが入力されていません")
    exit(1)

print()
print("=" * 60)
print("APIキーを設定中...")
print("=" * 60)
print()

# MCP設定ファイルを更新
mcp_config_path = os.path.expanduser("~/.cursor/mcp.json")

if not os.path.exists(mcp_config_path):
    print(f"[NG] MCP設定ファイルが見つかりません: {mcp_config_path}")
    exit(1)

import json

with open(mcp_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# n8n MCPサーバーの設定を更新
if "mcpServers" in config and "n8n" in config["mcpServers"]:
    if "env" not in config["mcpServers"]["n8n"]:
        config["mcpServers"]["n8n"]["env"] = {}
    
    config["mcpServers"]["n8n"]["env"]["N8N_API_KEY"] = api_key
    config["mcpServers"]["n8n"]["env"]["N8N_BASE_URL"] = N8N_BASE_URL
    
    # JSONに変換して保存
    with open(mcp_config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("[OK] MCP設定ファイルを更新しました")
    print(f"   ファイル: {mcp_config_path}")
    print()
    print("=" * 60)
    print("次のステップ")
    print("=" * 60)
    print("1. Cursorを再起動してください（MCP設定を反映するため）")
    print("2. または、環境変数に設定:")
    print(f'   $env:N8N_API_KEY = "{api_key}"')
    print()
    print("3. ワークフローの状態を確認:")
    print("   python n8n_mcp_server/check_workflow_status.py 2ViGYzDtLBF6H4zn")
    print()
else:
    print("[NG] n8n MCPサーバーの設定が見つかりません")
    print("先に add_to_cursor_mcp.ps1 を実行してください")
    exit(1)











