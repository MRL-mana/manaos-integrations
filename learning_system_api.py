#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
learning_system_api.py  -  Learning System API ルートラッパー（Docker用）

docker-compose が `python -m learning_system_api` で起動するための
エントリポイント。実体は scripts/misc/learning_system_api.py にある。
"""
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
MISC = os.path.join(ROOT, "scripts", "misc")
for p in (ROOT, MISC):
    if p not in sys.path:
        sys.path.insert(0, p)

# scripts/misc/learning_system_api.py を実行
from scripts.misc.learning_system_api import app  # noqa: E402

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5126))
    app.run(host="0.0.0.0", port=port,
            debug=os.getenv("DEBUG", "false").lower() == "true")
