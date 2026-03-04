#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git pre-commit hook — 教訓を CLAUDE.md に自動注入

.git/hooks/pre-commit から呼び出される。
コミット前に inject_lessons_to_claude_md.py を実行し、
CLAUDE.md が更新されたら git add する。
"""
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent  # .git/hooks/ → repo root
_INJECT = _REPO / "scripts" / "misc" / "inject_lessons_to_claude_md.py"
_CLAUDE_MD = _REPO / "CLAUDE.md"


def main() -> int:
    if not _INJECT.exists():
        print(f"[hook] inject script not found: {_INJECT}", file=sys.stderr)
        return 0  # スクリプトがなくてもコミットは通す

    # inject 実行
    result = subprocess.run(
        [sys.executable, str(_INJECT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"[hook] inject_lessons failed (non-fatal): {result.stderr.strip()}", file=sys.stderr)
        return 0  # 失敗してもブロックしない

    # CLAUDE.md が変更されていれば git add
    diff = subprocess.run(
        ["git", "diff", "--name-only", str(_CLAUDE_MD)],
        capture_output=True,
        text=True,
        cwd=str(_REPO),
    )
    if _CLAUDE_MD.name in diff.stdout:
        subprocess.run(["git", "add", str(_CLAUDE_MD)], cwd=str(_REPO))
        print("[hook] CLAUDE.md を更新してステージングしました")

    return 0


if __name__ == "__main__":
    sys.exit(main())
