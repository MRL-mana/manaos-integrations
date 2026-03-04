"""
tests/performance/conftest.py
performance テストの sys.path 設定

llm/ やその他のモジュールを sys.path に追加する。
sys.exit(1) を含む古いスクリプト型テストへの対応も含む。
"""

import sys
import pytest
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_EXTRA_PATHS = [
    _PROJECT_ROOT,
    _PROJECT_ROOT / "llm",
    _PROJECT_ROOT / "scripts" / "misc",
]

for _p in _EXTRA_PATHS:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
