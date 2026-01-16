"""Portal Voice Integration MCPサーバーのエントリーポイント"""
from portal_voice_integration_mcp_server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
