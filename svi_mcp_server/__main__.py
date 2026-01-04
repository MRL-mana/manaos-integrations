"""
SVI × Wan 2.2 動画生成 MCPサーバー
エントリーポイント
"""

import asyncio
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from svi_mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())

