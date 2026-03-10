"""
Fast-ish duplicate scanner for large AI/model files on Windows.

- Focuses on large files (default >= 200MB) to keep runtime reasonable.
- Looks at common model extensions plus Ollama blobs (extensionless large files under .ollama/models/blobs).
- Produces a human-readable report and a JSON file under ./artifacts.

No files are deleted by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DEFAULT_ROOTS = [
    r"C:\Users\mana4\.ollama\models",
    r"C:\Users\mana4\.lmstudio\models",
    r"D:\AI_Storage\Models",
    r"D:\huggingface_cache",
    r"D:\manaos_integrations",
]

# Large-file extensions worth deduping first
MODEL_EXTS = {
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".bin",
    ".gguf",
    ".onnx",
    ".tar",
    ".zip",
    ".7z",
}

# Some video outputs can be huge too
VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov"}


@dataclass(frozen=True)
class FileRec:
    path: str
    size: int


def _is_ollama_blob(path: str) -> bool:
    p = path.lower()
    # NOTE: keep trailing backslash to avoid partial matches
    return "\\.ollama\\models\\blobs\\" in p


def _should_include(path: str, size: int, min_size: int, include_videos: bool) -> bool:
    if size < min_size:
        return False
    ext = Path(path).suffix.lower()
    if ext in MODEL_EXTS:
        return True
    if include_videos and ext in VIDEO_EXTS:
        return True
    # Ollama stores big model blobs without extensions under blobs/
    if ext == "" and _is_ollama_blob(path):
        return True
    return False


def iter_files(root: str) -> Iterable[FileRec]:
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            st = e.stat(follow_symlinks=False)
                            yield FileRec(path=e.path, size=st.st_size)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, OSError):
            continue


def sha256_quick(path: str, size: int, head_bytes: int = 1024 * 1024) -> str | None:
    """
    Quick content signature:
    - sha256(head + tail + size)
    Good for filtering candidates before full hashing.
    """
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            head = f.read(head_bytes)
            if size > head_bytes:
                try:
                    f.seek(max(0, size - head_bytes))
                except OSError:
                    # Some filesystems might not like huge seeks; fallback to full read.
                    f.seek(0)
                tail = f.read(head_bytes)
            else:
                tail = b""
        h.update(size.to_bytes(8, "little", signed=False))
        h.update(head)
        h.update(tail)
        return h.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def sha256_full(path: str, chunk: int = 8 * 1024 * 1024) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                b = f.read(chunk)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def fmt_gb(n: int) -> str:
    return f"{n / (1024**3):.2f} GB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS, help="Root directories to scan")
    parser.add_argument("--min-mb", type=int, default=200, help="Minimum file size in MB (default 200)")
    parser.add_argument("--include-videos", action="store_true", help="Also include large video files")
    parser.add_argument("--max-files", type=int, default=0, help="Stop after N files (0 = no limit)")
    args = parser.parse_args()

    # Avoid Windows console cp932 crashes when paths contain non-ASCII.
    # We only need a stable run; the JSON report is the source of truth.
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")  # type: ignore[attr-defined]
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")  # type: ignore[attr-defined]
    except Exception:
        pass

    min_size = args.min_mb * 1024 * 1024
    roots = [r for r in args.roots if Path(r).exists()]

    print("=== Duplicate Scan (Large AI files) ===")
    print(f"min_size: {args.min_mb} MB")
    print(f"include_videos: {bool(args.include_videos)}")
    print(f"roots: {len(roots)}")
    for r in roots:
        print(f"  - {r}")
    print()

    # Phase 1: collect candidates and group by size
    by_size: Dict[int, List[str]] = {}
    scanned = 0
    included = 0
    t0 = time.time()

    for root in roots:
        for rec in iter_files(root):
            scanned += 1
            if args.max_files and scanned >= args.max_files:
                break
            if not _should_include(rec.path, rec.size, min_size, args.include_videos):
                continue
            included += 1
            by_size.setdefault(rec.size, []).append(rec.path)
        if args.max_files and scanned >= args.max_files:
            break

    size_groups = {s: ps for s, ps in by_size.items() if len(ps) > 1}
    print(f"scanned_entries: {scanned}")
    print(f"included_files: {included}")
    print(f"size_groups(>1): {len(size_groups)}")
    print(f"elapsed_phase1: {time.time() - t0:.1f}s")
    print()

    if not size_groups:
        print("No duplicate candidates (by size) for the selected targets.")
        return 0

    # Phase 2: quick hash per size-group
    quick_map: Dict[str, List[Tuple[str, int]]] = {}
    t1 = time.time()
    for size, paths in size_groups.items():
        for p in paths:
            q = sha256_quick(p, size=size)
            if not q:
                continue
            quick_map.setdefault(q, []).append((p, size))

    quick_groups = {q: lst for q, lst in quick_map.items() if len(lst) > 1}
    print(f"quick_groups(>1): {len(quick_groups)}")
    print(f"elapsed_phase2: {time.time() - t1:.1f}s")
    print()

    if not quick_groups:
        print("No duplicates after quick signature check.")
        return 0

    # Phase 3: full hash verification
    full_map: Dict[str, List[Tuple[str, int]]] = {}
    t2 = time.time()
    total_q = len(quick_groups)
    for idx, (_, lst) in enumerate(quick_groups.items(), 1):
        # same quick signature, same size likely; verify fully
        # Print progress so long runs don't look stuck.
        try:
            sz = lst[0][1] if lst else 0
            print(f"verifying {idx}/{total_q} candidates={len(lst)} size~{fmt_gb(sz)}")
        except Exception:
            print(f"verifying {idx}/{total_q} candidates={len(lst)}")

        for p, size in lst:
            h = sha256_full(p)
            if not h:
                continue
            full_map.setdefault(h, []).append((p, size))

    dup_groups = {h: lst for h, lst in full_map.items() if len(lst) > 1}
    elapsed3 = time.time() - t2

    # Summarize reclaimable bytes = (n-1)*size per group
    reclaimable = 0
    total_dupe_files = 0
    groups_out: List[dict] = []
    for h, lst in sorted(dup_groups.items(), key=lambda kv: (len(kv[1]), kv[1][0][1]), reverse=True):
        size = lst[0][1]
        n = len(lst)
        reclaimable += (n - 1) * size
        total_dupe_files += (n - 1)
        groups_out.append(
            {
                "sha256": h,
                "size_bytes": size,
                "count": n,
                "paths": [p for p, _ in lst],
            }
        )

    print("=== VERIFIED DUPLICATES (sha256) ===")
    print(f"groups: {len(dup_groups)}")
    print(f"duplicate_files(deletable): {total_dupe_files}")
    print(f"reclaimable: {fmt_gb(reclaimable)}")
    print(f"elapsed_phase3: {elapsed3:.1f}s")
    print()

    # Print top 10 groups
    for i, g in enumerate(groups_out[:10], 1):
        print(f"{i}. size={fmt_gb(g['size_bytes'])} count={g['count']} sha256={g['sha256'][:16]}...")
        print(f"   KEEP: {g['paths'][0]}")
        for p in g["paths"][1:]:
            print(f"   DUPE: {p}")
        print()

    # Write JSON report
    artifacts = Path(__file__).resolve().parent / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    out_path = artifacts / f"duplicate_report_large_ai_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(
        json.dumps(
            {
                "min_mb": args.min_mb,
                "include_videos": bool(args.include_videos),
                "roots": roots,
                "verified_groups": groups_out,
                "reclaimable_bytes": reclaimable,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"report_json: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
