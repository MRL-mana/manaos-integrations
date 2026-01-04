"""
MCPサーバーの機能を直接呼び出してワークフローをインポート
"""
import os
import sys
import asyncio
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from n8n_mcp_server.server import import_workflow

async def main():
    """メイン関数"""
    workflow_file = str(Path(__file__).parent.parent / "n8n_workflow_template.json")
    
    print("=" * 60)
    print("n8nワークフロー MCP経由インポート")
    print("=" * 60)
    
    # MCPサーバーのimport_workflow関数を直接呼び出し
    result = await import_workflow({
        "workflow_file": workflow_file,
        "activate": True
    })
    
    # 結果を表示
    for content in result:
        print(content.text)
    
    # 成功かどうかを判定
    success = any("success" in content.text.lower() for content in result)
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


















