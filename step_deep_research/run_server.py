#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
step_deep_research/run_server.py  -  環境設定済み起動ラッパー

直接実行: py.exe -3.10 step_deep_research/run_server.py
"""
import sys
import os
import runpy

# リポジトリルートを sys.path に追加（unified_logging などを解決）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in [_ROOT, os.path.join(_ROOT, "scripts", "misc"), os.path.join(_ROOT, "unified_api")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ポート設定: STEP_DEEP_RESEARCH_PORT > 5120（汎用PORTを上書きして競合を防ぐ）
os.environ['PORT'] = str(int(os.environ.get('STEP_DEEP_RESEARCH_PORT', 5120)))

# api_server.py を __main__ として実行（app.run() を起動）
_server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_server.py")
runpy.run_path(_server_path, run_name="__main__")

