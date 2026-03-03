#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dialog_style_presets.yaml のプリセットを persona_config.yaml に適用する。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml. Install with: pip install pyyaml")
    raise SystemExit(1)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="seiso_gal_feminine")
    parser.add_argument("--presets", default="config/dialog_style_presets.yaml")
    parser.add_argument("--persona", default="persona_config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    presets_path = repo_root / args.presets
    persona_path = repo_root / args.persona

    if not presets_path.exists():
        print(f"presets not found: {presets_path}")
        return 1
    if not persona_path.exists():
        print(f"persona config not found: {persona_path}")
        return 1

    presets_data = load_yaml(presets_path)
    presets = presets_data.get("presets") or {}
    preset = presets.get(args.preset)
    if not isinstance(preset, dict):
        print(f"preset not found: {args.preset}")
        return 1

    persona_data = load_yaml(persona_path)
    persona = persona_data.setdefault("persona", {})

    persona["active_style_preset"] = args.preset
    persona["style_preset_meta"] = {
        "name": preset.get("name"),
        "description": preset.get("description"),
    }

    style = preset.get("style") or {}
    conversation_style = persona.setdefault("conversation_style", {})
    conversation_style["tone"] = style.get("tone", conversation_style.get("tone", ""))
    conversation_style["formality"] = "カジュアルだが丁寧"
    conversation_style["language"] = "日本語"

    system_prompt = persona.get("system_prompt", "")
    preset_note = (
        "\n\n[口調プリセット]\n"
        f"- active_style_preset: {args.preset}\n"
        f"- call_user: {style.get('call_user', 'マナ')}\n"
        f"- pronoun: {style.get('pronoun', 'わたし')}\n"
        "- 報告時は事実優先、誇張しない\n"
        "- 安全原則（fail-closed/最小権限/可観測性）を絶対に崩さない\n"
    )

    base_prompt = system_prompt.split("\n\n[口調プリセット]")[0].rstrip()
    persona["system_prompt"] = base_prompt + preset_note

    if args.dry_run:
        print(json.dumps({"preset": args.preset, "persona_preview": persona}, ensure_ascii=False, indent=2))
        return 0

    persona_path.write_text(yaml.safe_dump(persona_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(json.dumps({"ok": True, "preset": args.preset, "persona": str(persona_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
