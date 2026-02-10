"""Phase1 MCP サーバー エントリーポイント"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
