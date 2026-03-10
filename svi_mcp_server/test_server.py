"""
SVI MCPサーバーのテストスクリプト
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from svi_mcp_server.server import server, get_svi_integration

async def test_tools():
    """ツールのテスト"""
    print("=" * 60)
    print("SVI MCPサーバー テスト")
    print("=" * 60)
    print()
    
    # ツール一覧の取得
    print("[1] ツール一覧の取得...")
    tools = await server.list_tools()  # type: ignore[misc]
    print(f"   [OK] {len(tools)}個のツールが見つかりました")
    for tool in tools:
        print(f"      - {tool.name}: {tool.description[:50]}...")
    print()
    
    # 接続確認ツールのテスト
    print("[2] 接続確認ツールのテスト...")
    result = await server.call_tool("svi_check_connection", {})  # type: ignore[call-arg]
    print(f"   結果: {result[0].text[:100]}...")
    print()
    
    print("[OK] テスト完了")

if __name__ == "__main__":
    asyncio.run(test_tools())











