"""n8nワークフローを直接インポートするスクリプト"""
import os
import json
import requests
from pathlib import Path

# MCP設定ファイルを読み込む
mcp_path = Path(os.path.expanduser('~/.cursor/mcp.json'))
config = json.loads(mcp_path.read_text(encoding='utf-8'))
n8n_config = config.get('mcpServers', {}).get('n8n', {})
env = n8n_config.get('env', {})

base_url = env.get('N8N_BASE_URL', 'http://100.93.120.33:5678')
api_key = env.get('N8N_API_KEY', '')

# ワークフローファイルを読み込む（簡略版を優先）
simple_file = Path(__file__).parent.parent / 'n8n_workflow_template_simple.json'
workflow_file = Path(__file__).parent.parent / 'n8n_workflow_template.json'
if simple_file.exists():
    workflow_file = simple_file
if not workflow_file.exists():
    print(f"[NG] ワークフローファイルが見つかりません: {workflow_file}")
    exit(1)

with open(workflow_file, 'r', encoding='utf-8') as f:
    workflow_data = json.load(f)

# n8n APIが不要とするプロパティを削除
properties_to_remove = ['triggerCount', 'updatedAt', 'versionId', 'pinData', 'staticData', 'tags']
for prop in properties_to_remove:
    if prop in workflow_data:
        del workflow_data[prop]

# webhookIdも削除（n8nが自動生成する）
for node in workflow_data.get('nodes', []):
    if 'webhookId' in node:
        del node['webhookId']

print(f"ワークフロー名: {workflow_data.get('name', 'Unknown')}")
print(f"Base URL: {base_url}")
print()

# n8nにインポート
try:
    url = f"{base_url}/api/v1/workflows"
    headers = {
        'Content-Type': 'application/json',
        'X-N8N-API-KEY': api_key
    }
    
    response = requests.post(
        url,
        json=workflow_data,
        headers=headers,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        workflow_id = result.get('id')
        workflow_name = result.get('name')
        
        print(f"[OK] ワークフローをインポートしました")
        print(f"  ID: {workflow_id}")
        print(f"  名前: {workflow_name}")
        print()
        
        # 有効化
        if workflow_id:
            activate_url = f"{base_url}/api/v1/workflows/{workflow_id}/activate"
            activate_response = requests.post(
                activate_url,
                headers=headers,
                timeout=30
            )
            
            if activate_response.status_code == 200:
                print(f"[OK] ワークフローを有効化しました")
            else:
                print(f"[警告] 有効化に失敗: {activate_response.status_code} - {activate_response.text}")
        
        print()
        print(f"ワークフローURL: {base_url}/workflow/{workflow_id}")
    else:
        print(f"[NG] エラー: {response.status_code}")
        print(f"  {response.text}")
except Exception as e:
    print(f"[NG] エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
