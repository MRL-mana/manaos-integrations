"""
Unified API Server MCPサーバーのエントリーポイント
"""

from unified_api_mcp_server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
