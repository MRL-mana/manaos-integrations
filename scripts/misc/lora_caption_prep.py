#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LoRA 学習用: 画像→キャプション(.txt) 自動生成ツール

やること（最小）:
- 指定フォルダ内の画像を列挙
- 画像と同名の .txt が無ければ作成（Ollama Vision でタグ生成）
- オプションで画像/テキストを連番リネーム（ミスを減らす）

注意:
- 生成品質は Vision モデルとプロンプトに依存
- 既存の .txt は上書きしない（--overwrite で上書き可）
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import requests


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _ollama_url() -> str:
    return (os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def _list_vision_models(base_url: str) -> List[str]:
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=5)
        r.raise_for_status()
        data = r.json() or {}
        models = data.get("models") or []
        out = []
        for m in models:
            name = (m.get("name") or "").strip()
            if name:
                out.append(name)
        return out
    except Exception:
        return []


def _pick_default_vision_model(models: List[str]) -> Optional[str]:
    if not models:
        return None
    preferred = ["qwen", "vl", "llava", "vision"]
    for key in preferred:
        for m in models:
            if key in m.lower():
                return m
    return models[0]


def _read_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _clean_caption(text: str) -> str:
    t = (text or "").strip()
    # よくある囲い/コードブロックを除去
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    t = re.sub(r"```$", "", t)
    # 改行→カンマ
    t = re.sub(r"\s*\n\s*", ", ", t)
    # 連続カンマを潰す
    t = re.sub(r",\s*,+", ", ", t)
    # 末尾カンマ除去
    t = t.strip(" ,")
    return t


@dataclass
class CaptionOptions:
    trigger: str = ""
    ignore: List[str] = None  # type: ignore[assignment]
    max_tags: int = 25

    def __post_init__(self) -> None:
        if self.ignore is None:
            self.ignore = []


def build_caption_prompt(opts: CaptionOptions) -> str:
    ignore = ", ".join([x for x in opts.ignore if x])
    return (
        "You are creating captions for training a LoRA. "
        "Return ONLY a comma-separated list of short English tags (no sentences). "
        f"Keep it under {opts.max_tags} tags. "
        "Focus on stable identity features (face, hair style, accessories) and pose. "
        "Do NOT include camera/quality/watermark/UI. "
        + (f"Ignore these variable attributes if present: {ignore}. " if ignore else "")
    )


def generate_caption_ollama(
    base_url: str,
    model: str,
    image_path: Path,
    opts: CaptionOptions,
    timeout: float = 120.0,
) -> str:
    prompt = build_caption_prompt(opts)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "images": [_read_b64(image_path)],
    }
    r = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json() or {}
    resp = data.get("response") or ""
    caption = _clean_caption(str(resp))
    if opts.trigger:
        caption = f"{opts.trigger}, {caption}".strip(" ,") if caption else opts.trigger
    return caption


def iter_images(input_dir: Path) -> List[Path]:
    files = []
    for p in input_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            files.append(p)
    return sorted(files)


def sequential_name(index: int, width: int = 6) -> str:
    return f"{index:0{width}d}"


def rename_pair(image_path: Path, new_stem: str, overwrite: bool = False) -> Tuple[Path, Path]:
    new_image = image_path.with_name(new_stem + image_path.suffix.lower())
    txt_path = image_path.with_suffix(".txt")
    new_txt = new_image.with_suffix(".txt")

    if new_image.exists() and not overwrite:
        raise FileExistsError(f"이미지 rename collision: {new_image}")
    if new_txt.exists() and not overwrite:
        raise FileExistsError(f"txt rename collision: {new_txt}")

    image_path.replace(new_image)
    if txt_path.exists():
        txt_path.replace(new_txt)
    return new_image, new_txt


def main() -> int:
    ap = argparse.ArgumentParser(description="LoRA用: 画像→キャプション(.txt) 自動生成")
    ap.add_argument("input_dir", help="画像フォルダ")
    ap.add_argument("--model", default=os.getenv("MANAOS_VISION_MODEL", "").strip() or None)
    ap.add_argument("--ollama-url", default=_ollama_url())
    ap.add_argument("--trigger", default="", help="先頭に必ず付けるトリガーワード")
    ap.add_argument(
        "--ignore",
        default="",
        help="キャプションから除外したい可変要素（カンマ区切り、例: red shirt, blue background）",
    )
    ap.add_argument("--max-tags", type=int, default=25)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--overwrite", action="store_true", help="既存.txtを上書き")
    ap.add_argument(
        "--rename",
        choices=["none", "sequential"],
        default="none",
        help="画像とtxtを連番リネームするか（デフォルト: none）",
    )
    ap.add_argument("--rename-width", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.is_dir():
        print(f"[ERROR] not a directory: {input_dir}")
        return 2

    ollama = str(args.ollama_url).rstrip("/")
    models = _list_vision_models(ollama)
    model = args.model or _pick_default_vision_model(models)
    if not model:
        print("[ERROR] Ollama vision model not found. Set --model or MANAOS_VISION_MODEL.")
        if models:
            print("[INFO] available models:")
            for m in models:
                print(f"  - {m}")
        return 3

    ignore_list = [x.strip() for x in str(args.ignore).split(",") if x.strip()]
    opts = CaptionOptions(trigger=str(args.trigger).strip(), ignore=ignore_list, max_tags=int(args.max_tags))

    images = iter_images(input_dir)
    if not images:
        print("[INFO] no images found")
        return 0

    # optional rename first (so captions match final names)
    if args.rename == "sequential":
        renamed = []
        for i, img in enumerate(images, start=1):
            new_stem = sequential_name(i, width=int(args.rename_width))
            if args.dry_run:
                renamed.append(img)
                continue
            new_img, _new_txt = rename_pair(img, new_stem, overwrite=False)
            renamed.append(new_img)
        images = renamed

    made = 0
    skipped = 0
    for img in images:
        txt = img.with_suffix(".txt")
        if txt.exists() and not args.overwrite:
            skipped += 1
            continue

        if args.dry_run:
            made += 1
            continue

        try:
            cap = generate_caption_ollama(
                base_url=ollama,
                model=model,
                image_path=img,
                opts=opts,
                timeout=float(args.timeout),
            )
            txt.write_text(cap + "\n", encoding="utf-8")
            made += 1
            print(f"[OK] {img.name} -> {txt.name}")
        except Exception as e:
            print(f"[ERROR] caption failed: {img.name}: {e}")
            return 1

    print(f"[DONE] model={model} captions_created={made} skipped={skipped} dir={input_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
