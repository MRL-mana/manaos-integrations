"""
CursorからMCPツールとして直接呼び出すためのヘルパー
実際にはCursorのMCP設定に追加する必要がありますが、
このスクリプトでMCPサーバーの機能を直接テストできます
"""
import os
import sys
import asyncio
import json
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from n8n_mcp_server.server import call_tool

async def import_workflow_via_mcp():
    """MCPツールとしてワークフローをインポート"""
    workflow_file = str(Path(__file__).parent.parent / "n8n_workflow_template.json")
    
    print("=" * 60)
    print("n8nワークフロー MCPツール経由インポート")
    print("=" * 60)
    
    # MCPツールを直接呼び出し
    result = await call_tool("n8n_import_workflow", {
        "workflow_file": workflow_file,
        "activate": True
    })
    
    # 結果を表示
    for content in result:
        print(content.text)  # type: ignore
        # JSONをパースして成功かどうかを判定
        try:
            data = json.loads(content.text)  # type: ignore
            if data.get("status") == "success":
                print("\n[OK] ワークフローをインポートしました！")
                return 0
        except Exception:
            pass
    
    return 1

if __name__ == "__main__":
    exit_code = asyncio.run(import_workflow_via_mcp())
    sys.exit(exit_code)


















