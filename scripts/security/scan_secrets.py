#!/usr/bin/env python3
"""
Lightweight secret scanner (no external deps).

- Scans **tracked files** (git ls-files) in the current working tree (HEAD).
- Looks for common token / key patterns and private key headers.

Usage:
  python scripts/security/scan_secrets.py
  python scripts/security/scan_secrets.py --show-all
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("slack_bot_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{30,}")),
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("google_api_key", re.compile(r"AIzaSy[A-Za-z0-9_-]{30,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    (
        "private_key_header",
        re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----"),
    ),
    # Common "KEY=..." style (catch accidental hardcoding)
    (
        "env_like_api_key",
        re.compile(
            r"(?i)\b(?P<key>SLACK_BOT_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|CIVITAI_API_KEY|N8N_API_KEY)\s*=\s*['\"](?P<val>[^'\"]+)['\"]"
        ),
    ),
]


def _run_git_ls_files(repo_root: Path) -> list[Path]:
    p = subprocess.run(
        ["git", "ls-files"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "git ls-files failed")
    files: list[Path] = []
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        files.append(repo_root / line)
    return files


def _looks_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    # crude heuristic: lots of non-text bytes
    sample = data[:4096]
    if not sample:
        return False
    nontext = sum(1 for b in sample if b < 9 or (13 < b < 32) or b == 127)
    return (nontext / len(sample)) > 0.3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo-root",
        default=".",
        help="Repo root (default: current directory).",
    )
    ap.add_argument(
        "--show-all",
        action="store_true",
        help="Show every match (otherwise, show up to 5 per file).",
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    try:
        files = _run_git_ls_files(repo_root)
    except Exception as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 2

    findings: list[str] = []

    for fp in files:
        try:
            data = fp.read_bytes()
        except OSError:
            continue

        if _looks_binary(data):
            continue

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            # Common on Windows Japanese environments
            text = data.decode("cp932", errors="ignore")
        if not text:
            continue

        per_file_hits = 0
        for name, rx in PATTERNS:
            for m in rx.finditer(text):
                if name == "env_like_api_key":
                    key = (m.groupdict().get("key") or "").strip()
                    val = (m.groupdict().get("val") or "").strip()
                    val_l = val.lower()
                    # Skip obvious placeholders / docs examples
                    if (
                        len(val) < 20
                        or "<" in val
                        or "..." in val
                        or "your_" in val_l
                        or "your-" in val_l
                        or "your " in val_l
                        or "replace" in val_l
                        or "changeme" in val_l
                        or "example" in val_l
                        or "dummy" in val_l
                        or "here" in val_l
                    ):
                        continue

                    snippet = f"{key}={val}"
                else:
                    snippet = m.group(0)

                # line number best-effort
                line_no = text.count("\n", 0, m.start()) + 1
                # redact long secrets in output
                if len(snippet) > 12 and name not in ("private_key_header", "aws_access_key_id"):
                    snippet = snippet[:6] + "…" + snippet[-4:]
                findings.append(f"{fp.relative_to(repo_root)}:{line_no}: {name}: {snippet}")
                per_file_hits += 1
                if (not args.show_all) and per_file_hits >= 5:
                    findings.append(f"{fp.relative_to(repo_root)}:…: (more matches omitted)")
                    break
            if (not args.show_all) and per_file_hits >= 5:
                break

    if not findings:
        print("[OK] No obvious secrets found in tracked files.")
        return 0

    print("[NG] Potential secrets found:")
    for line in findings:
        print(f"- {line}")
    print("\nIf these are real secrets, rotate them and remove from git history.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

