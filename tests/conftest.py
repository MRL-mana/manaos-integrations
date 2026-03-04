#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS テスト共通設定

manaos_logger がモジュールレベルで sys.stdout/stderr を reconfigure するため、
pytest の TerminalWriter が参照するファイルハンドルが閉じられてしまう問題を防止。
各フェーズ (configure / sessionfinish / unconfigure) で復元を行う。
"""
import os
import sys
import io
from pathlib import Path

# リポジトリルートおよびサブモジュールを sys.path に追加
_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = str(_ROOT)

_EXTRA_ROOTS = [
    _ROOT,
    _ROOT / "unified_api",     # unified_logging 等
    _ROOT / "scripts" / "misc",
    _ROOT / "scripts" / "cursor",
    _ROOT / "scripts" / "gpu",
    _ROOT / "scripts" / "github",
    _ROOT / "llm",
    _ROOT / "file_secretary",
    _ROOT / "mrl_memory",
    _ROOT / "step_deep_research",
]
for _p in _EXTRA_ROOTS:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# ── 安全な stdout/stderr の保存 ──────────────────────────────
# os.dup で FD を複製し、独立した TextIOWrapper を作る。
# これにより manaos_logger が元の FD を閉じても影響を受けない。
try:
    _safe_stdout = io.TextIOWrapper(
        io.BufferedWriter(io.FileIO(os.dup(sys.stdout.fileno()), closefd=True)),
        encoding="utf-8",
        errors="replace",
        line_buffering=True,
    )
except (AttributeError, io.UnsupportedOperation, OSError):
    _safe_stdout = sys.stdout

try:
    _safe_stderr = io.TextIOWrapper(
        io.BufferedWriter(io.FileIO(os.dup(sys.stderr.fileno()), closefd=True)),
        encoding="utf-8",
        errors="replace",
        line_buffering=True,
    )
except (AttributeError, io.UnsupportedOperation, OSError):
    _safe_stderr = sys.stderr


def _restore_stdio():
    """sys.stdout/stderr が閉じていたら安全なコピーに差し替える"""
    try:
        if sys.stdout is None or sys.stdout.closed:
            sys.stdout = _safe_stdout
    except (AttributeError, ValueError):
        sys.stdout = _safe_stdout

    try:
        if sys.stderr is None or sys.stderr.closed:
            sys.stderr = _safe_stderr
    except (AttributeError, ValueError):
        sys.stderr = _safe_stderr


def _patch_terminal_writer(config):
    """pytest の TerminalWriter._file が閉じていたら安全なものに差し替える"""
    try:
        tw = config._tw  # type: ignore[attr-defined]
        if tw._file is None or tw._file.closed:
            tw._file = _safe_stdout
    except (AttributeError, ValueError):
        pass


def pytest_configure(config):
    """pytest 起動時に manaos_logger をインポートしてから stdout/stderr を復元"""
    try:
        import manaos_logger  # noqa: F401
    except Exception:
        pass
    _restore_stdio()


def pytest_sessionfinish(session, exitstatus):
    """セッション終了時にターミナルライターを修復"""
    _restore_stdio()
    _patch_terminal_writer(session.config)


def pytest_unconfigure(config):
    """pytest 終了時の最終復元"""
    _restore_stdio()
    _patch_terminal_writer(config)
