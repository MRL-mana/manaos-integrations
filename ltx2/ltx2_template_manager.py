#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LTX-2 テンプレート管理

統合テスト要件:
- list_templates() が動作すること

実運用:
- ltx2_templates 配下のJSONを列挙・保存
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


def _default_templates_dir() -> Path:
    raw = (os.getenv("MANAOS_LTX2_TEMPLATES_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path(__file__).resolve().parent / "ltx2_templates").resolve()


@dataclass
class LTX2TemplateManager:
    templates_dir: Path | None = None

    def __post_init__(self) -> None:
        self.templates_dir = (self.templates_dir or _default_templates_dir()).resolve()
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Seed: 既存の参考テンプレートがある場合はコピー（無ければ何もしない）
        seed = Path(__file__).resolve().parent / "ltx2_workflow_template.json"
        dest = self.templates_dir / "ltx2_workflow_template.json"
        if seed.exists() and not dest.exists():
            try:
                dest.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass

    def list_templates(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for p in sorted(self.templates_dir.glob("*.json")):  # type: ignore[union-attr]
            out.append({"name": p.stem, "path": str(p)})
        return out

    def load_template(self, name: str) -> Dict[str, Any]:
        path = self.templates_dir / f"{name}.json"  # type: ignore[operator]
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_template(self, name: str, data: Dict[str, Any]) -> str:
        path = self.templates_dir / f"{name}.json"  # type: ignore[operator]
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(path)
