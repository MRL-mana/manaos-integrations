"""
ManaOS統合MCPサーバー
エントリーポイント
"""

import asyncio
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from manaos_unified_mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())











