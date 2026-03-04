from __future__ import annotations

import mimetypes
import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ItemRoot:
    id: str
    label: str
    path: Path
    max_files: int


IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}

SIDECAR_SUFFIXES = (
    ".png.json",
    ".jpg.json",
    ".jpeg.json",
    ".webp.json",
    ".gif.json",
    ".mp4.json",
    ".webm.json",
    ".mov.json",
    ".mkv.json",
)


def scan_items(roots: list[ItemRoot], max_depth: int = 6) -> list[dict]:
    items: list[dict] = []
    now = int(time.time())

    for root in roots:
        base = root.path
        if not base.exists() or not base.is_dir():
            continue

        limit = max(1, int(root.max_files))
        # 早期終了バッファ: max_files の 4 倍まで溜まったら打ち切ってからソート
        # これにより 8000+ ファイルのディレクトリでも O(max_files) 相当で終わる
        early_stop = limit * 4
        collected: list[dict] = []

        walk_done = False
        for dirpath, dirnames, filenames in os.walk(base):
            if walk_done:
                break
            rel_dir = Path(dirpath).relative_to(base)
            depth = len(rel_dir.parts)
            if depth >= max_depth:
                dirnames[:] = []
                continue

            for fn in filenames:
                p = Path(dirpath) / fn
                low = p.name.lower()
                # ComfyUI等の sidecar metadata は「見れる」目的では邪魔なので除外
                if low.endswith(SIDECAR_SUFFIXES):
                    continue
                try:
                    st = p.stat()
                except Exception:
                    continue

                rel = p.relative_to(base).as_posix()
                ext = p.suffix.lower()
                if ext in IMAGE_EXT:
                    kind = "image"
                elif ext in VIDEO_EXT:
                    kind = "video"
                else:
                    continue

                mime, _ = mimetypes.guess_type(str(p))
                collected.append(
                    {
                        "root_id": root.id,
                        "root_label": root.label,
                        "rel_path": rel,
                        "name": p.name,
                        "ext": ext,
                        "kind": kind,
                        "mime": mime or ("application/octet-stream"),
                        "size_bytes": int(st.st_size),
                        "mtime": int(st.st_mtime),
                        "age_sec": max(0, now - int(st.st_mtime)),
                    }
                )

                # 早期終了: バッファが一杯になったらここでソート→切り捨て
                if len(collected) >= early_stop:
                    collected.sort(key=lambda x: int(x.get("mtime") or 0), reverse=True)
                    collected = collected[:limit]
                    walk_done = True
                    break

        collected.sort(key=lambda x: int(x.get("mtime") or 0), reverse=True)
        items.extend(collected[:limit])

    items.sort(key=lambda x: int(x.get("mtime") or 0), reverse=True)
    return items


def resolve_item_roots(repo_root: Path, items_yaml: dict) -> list[ItemRoot]:
    raw = items_yaml.get("items") or []
    roots: list[ItemRoot] = []
    if not isinstance(raw, list):
        return []
    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "").strip()
        if not rid:
            continue
        label = str(r.get("label") or rid)
        raw_path = str(r.get("path") or "").strip()
        rel = os.path.expandvars(os.path.expanduser(raw_path))
        if not rel:
            continue
        max_files = int(r.get("max_files") or 80)

        candidate = Path(rel)
        if candidate.is_absolute():
            p = candidate.resolve()
        else:
            p = (repo_root / rel).resolve()
        roots.append(ItemRoot(id=rid, label=label, path=p, max_files=max_files))
    return roots


def safe_resolve_under_root(root: Path, rel_path: str) -> Path | None:
    try:
        rel = rel_path.replace("\\", "/")
        candidate = (root / rel).resolve()
        root_resolved = root.resolve()
        if root_resolved == candidate or root_resolved in candidate.parents:
            return candidate
        return None
    except Exception:
        return None
