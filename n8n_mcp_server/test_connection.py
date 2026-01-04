"""n8n API接続テスト"""
import os
import json
import requests
from pathlib import Path

# MCP設定ファイルを読み込む
mcp_path = Path(os.path.expanduser('~/.cursor/mcp.json'))
if not mcp_path.exists():
    print(f"[NG] MCP設定ファイルが見つかりません: {mcp_path}")
    exit(1)

config = json.loads(mcp_path.read_text(encoding='utf-8'))
n8n_config = config.get('mcpServers', {}).get('n8n', {})
env = n8n_config.get('env', {})

base_url = env.get('N8N_BASE_URL', 'http://100.93.120.33:5678')
api_key = env.get('N8N_API_KEY', '')

print(f"Base URL: {base_url}")
print(f"API Key: {api_key[:20]}..." if api_key else "API Key: Not set")
print()

# ワークフロー一覧を取得
try:
    response = requests.get(
        f'{base_url}/api/v1/workflows',
        headers={'X-N8N-API-KEY': api_key} if api_key else {},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        workflows = response.json()
        if isinstance(workflows, dict) and 'data' in workflows:
            workflows = workflows['data']
        print(f"Workflows: {len(workflows)}")
        print()
        print("[OK] n8n APIに接続できました")
    else:
        print(f"[NG] エラー: {response.text}")
except Exception as e:
    print(f"[NG] 接続エラー: {e}")















