"""Portal Integration API MCPサーバーのエントリーポイント"""
from portal_integration_mcp_server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
