#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LTX-2 NSFW 設定

注意: ここでは「NSFWを生成する」機能は提供しません。
目的は、ワークフローに渡す設定の“読み込み・適用”の共通口を持つことです。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


def _default_config_path() -> Path:
    raw = (os.getenv("MANAOS_LTX2_NSFW_CONFIG") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path(__file__).resolve().parent / "ltx2_nsfw_config.json").resolve()


DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "mode": "safe",
    "notes": "This config only controls workflow parameters. It does not bypass any policy.",
    "workflow": {
        "negative_prompt_append": "",
        "positive_prompt_append": "",
    },
}


@dataclass
class LTX2NSFWConfig:
    path: Path | None = None

    def __post_init__(self) -> None:
        self.path = (self.path or _default_config_path()).resolve()
        if not self.path.exists():
            try:
                self.path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

    def get_workflow_config(self) -> Dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as f:  # type: ignore[union-attr]
                data = json.load(f)
        except Exception:
            data = DEFAULT_CONFIG
        wf = data.get("workflow") if isinstance(data, dict) else None
        return wf if isinstance(wf, dict) else dict(DEFAULT_CONFIG["workflow"])


class LTX2NSFWWorkflowBuilder:
    """ワークフローdictへ NSFW設定を“付け足す”ヘルパ。

    どのノード/入力キーに反映するかは、環境のワークフローに依存するため、
    ここでは最小限の“文字列結合”ユーティリティのみ提供します。
    """

    @staticmethod
    def apply_prompt_suffix(prompt: str, suffix: str) -> str:
        p = (prompt or "").strip()
        s = (suffix or "").strip()
        if not s:
            return p
        if not p:
            return s
        return f"{p}, {s}"
