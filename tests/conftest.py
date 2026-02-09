#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS テスト共通設定
"""
import sys
import io
from pathlib import Path

# リポジトリルートを sys.path に追加
REPO_ROOT = str(Path(__file__).resolve().parents[1])
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# manaos_logger がモジュールレベルで sys.stdout/stderr を TextIOWrapper に
# 差し替えるが、pytest の capture 機構と衝突する。
# テスト実行時は差し替えを無効化する。
_original_stdout = sys.stdout
_original_stderr = sys.stderr


def pytest_configure(config):
    """pytest 起動時に manaos_logger をインポートしてから stdout/stderr を復元"""
    # manaos_logger のインポート自体で sys.stdout/stderr が書き換わるので、
    # ここで先にインポートして即座に戻す。
    try:
        import manaos_logger  # noqa: F401
    except Exception:
        pass
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
