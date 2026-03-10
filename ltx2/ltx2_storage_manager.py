#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LTX-2 ストレージ管理（Infinity/テンプレート共通）

目的:
- 統合テストが期待する最小API（get_storage_stats）を提供
- 生成物/一時ファイル/テンプレート等の置き場を標準化
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


def _default_root() -> Path:
    return Path(os.getenv("MANAOS_LTX2_STORAGE", "")).expanduser().resolve() if os.getenv("MANAOS_LTX2_STORAGE") else (Path(__file__).resolve().parent / "ltx2_storage")


def _dir_size_bytes(root: Path) -> int:
    total = 0
    if not root.exists():
        return 0
    for p in root.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except Exception:
            continue
    return total


@dataclass
class LTX2StorageManager:
    root: Path | None = None

    def __post_init__(self) -> None:
        self.root = (self.root or _default_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"  # type: ignore[operator]

    @property
    def outputs_dir(self) -> Path:
        return self.root / "outputs"  # type: ignore[operator]

    @property
    def temp_dir(self) -> Path:
        return self.root / "temp"  # type: ignore[operator]

    def get_storage_stats(self) -> Dict[str, Any]:
        """統合テスト互換: total_size_gb を必ず含めて返す。"""
        total_bytes = _dir_size_bytes(self.root)  # type: ignore
        return {
            "root": str(self.root),
            "total_size_bytes": int(total_bytes),
            "total_size_gb": float(total_bytes) / (1024**3),
            "paths": {
                "cache": str(self.cache_dir),
                "outputs": str(self.outputs_dir),
                "temp": str(self.temp_dir),
            },
        }
