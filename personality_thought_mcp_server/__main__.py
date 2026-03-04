"""personality_thought_mcp_server パッケージのエントリーポイント"""
from .server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
