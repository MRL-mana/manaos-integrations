"""
Step Deep Research Service MCPサーバーのエントリーポイント
"""

from step_deep_research_mcp_server.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
