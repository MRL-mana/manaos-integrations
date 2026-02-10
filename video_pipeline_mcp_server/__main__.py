import asyncio
import sys
from pathlib import Path

# 親ディレクトリを追加（manaos_integrations直下のモジュール参照用）
sys.path.insert(0, str(Path(__file__).parent.parent))

from .server import main

if __name__ == "__main__":
    asyncio.run(main())
