"""Web Voice Interface MCPサーバーのエントリーポイント"""
from web_voice_mcp_server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
