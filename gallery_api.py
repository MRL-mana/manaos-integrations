#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gallery_api.py - Gallery API エントリポイント（Docker/直接起動用ラッパー）

gallery_api_server.py を scripts/misc/ から正しい sys.path で実行するためのラッパー。
"""

import sys
import os

# プロジェクトルート（/app）を sys.path の先頭に確保
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 実体の gallery_api_server を実行
from scripts.misc.gallery_api_server import app, GALLERY_PORT  # noqa: E402

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=GALLERY_PORT, debug=False)
