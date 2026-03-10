#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LTX-2 ワークフロー生成/ロード

実運用では ComfyUI の Export(API) JSON をベースにするのが確実。
ここでは Infinity 統合が参照できる共通ユーティリティとして提供。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class LTX2WorkflowGenerator:
    workflows_dir: Path | None = None

    def __post_init__(self) -> None:
        self.workflows_dir = (self.workflows_dir or (Path(__file__).resolve().parent / "ltx2_workflows")).resolve()
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

    def load(self, path: str | Path) -> Dict[str, Any]:
        p = Path(path)
        if not p.is_absolute():
            p = (self.workflows_dir / p).resolve()  # type: ignore[operator]
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, name: str, workflow: Dict[str, Any]) -> str:
        out_path = (self.workflows_dir / name).with_suffix(".json")  # type: ignore[operator]
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(workflow, f, ensure_ascii=False)
        return str(out_path)
