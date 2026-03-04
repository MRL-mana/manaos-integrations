#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📖 inject_lessons_to_claude_md.py
===================================
CLAUDE.md の自動注入セクションを最新の教訓で更新するスクリプト。

使い方:
    python scripts/misc/inject_lessons_to_claude_md.py

動作:
  1. lessons_recorder から最新の教訓を取得（get_context_text）
  2. CLAUDE.md 内の <!-- LESSONS_AUTO_START --> ～ <!-- LESSONS_AUTO_END --> を更新
  3. マーカーがなければ末尾に追加

スケジューリング例:
    # Windowsタスクスケジューラ or git hook (pre-commit) に登録
    python %REPO_ROOT%\\scripts\\misc\\inject_lessons_to_claude_md.py
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

# ── パス設定 ──────────────────────────────────────────────────────────────
_THIS = Path(__file__).resolve()
_MISC_DIR = _THIS.parent           # scripts/misc/
_REPO_ROOT = _MISC_DIR.parent.parent  # manaos_integrations/

if str(_MISC_DIR) not in sys.path:
    sys.path.insert(0, str(_MISC_DIR))

# ── デフォルトパス ────────────────────────────────────────────────────────
DEFAULT_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"

# ── マーカー ──────────────────────────────────────────────────────────────
MARKER_START = "<!-- LESSONS_AUTO_START -->"
MARKER_END   = "<!-- LESSONS_AUTO_END -->"

# ── 取得件数上限 ──────────────────────────────────────────────────────────
LESSONS_LIMIT = 20


def build_lessons_section(lessons_text: str, total: int, by_category: dict) -> str:
    """マーカー間に挿入するMarkdown文字列を組み立てる"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    cat_summary = "  ".join(f"{k}: {v}件" for k, v in by_category.items()) if by_category else "なし"
    lines = [
        MARKER_START,
        "",
        "## 📖 最新教訓ログ（自動注入）",
        "",
        f"> 自動更新: {now}  |  合計 **{total}** 件  |  {cat_summary}",
        "> このセクションは `inject_lessons_to_claude_md.py` が自動更新します。手動編集不可。",
        "",
    ]
    if lessons_text.strip():
        lines.append(lessons_text.rstrip())
    else:
        lines.append("*教訓はまだ記録されていません。*")
    lines += ["", MARKER_END]
    return "\n".join(lines)


def inject(claude_md_path: Path = DEFAULT_CLAUDE_MD, limit: int = LESSONS_LIMIT, dry_run: bool = False) -> str:
    """CLAUDE.md を更新して変更内容を返す"""
    # ── 教訓取得 ──
    from lessons_recorder import get_lessons_recorder
    recorder = get_lessons_recorder()
    lessons_text = recorder.get_context_text(limit=limit)
    stats = recorder.stats()
    total = stats.get("total", 0)
    by_category = stats.get("by_category", {})

    section = build_lessons_section(lessons_text, total, by_category)

    # ── CLAUDE.md 読み込み ──
    if not claude_md_path.exists():
        raise FileNotFoundError(f"CLAUDE.md が見つかりません: {claude_md_path}")
    content = claude_md_path.read_text(encoding="utf-8")

    # ── マーカー間を置換 ──
    if MARKER_START in content and MARKER_END in content:
        start_idx = content.index(MARKER_START)
        end_idx   = content.index(MARKER_END) + len(MARKER_END)
        new_content = content[:start_idx] + section + content[end_idx:]
    else:
        # マーカーがなければ末尾に追加（1行空けて）
        new_content = content.rstrip() + "\n\n" + section + "\n"

    if dry_run:
        print("[dry-run] 変更プレビュー:")
        print(section)
        return section

    claude_md_path.write_text(new_content, encoding="utf-8")
    return section


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="CLAUDE.md に最新の教訓を自動注入")
    parser.add_argument("--claude-md", type=Path, default=DEFAULT_CLAUDE_MD, help="CLAUDE.md のパス")
    parser.add_argument("--limit", type=int, default=LESSONS_LIMIT, help=f"教訓取得件数 (デフォルト: {LESSONS_LIMIT})")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずプレビューのみ")
    args = parser.parse_args()

    try:
        section = inject(args.claude_md, limit=args.limit, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"✅ CLAUDE.md を更新しました: {args.claude_md}")
            print(f"   教訓セクション: {section.count(chr(10))} 行")
    except ImportError as e:
        print(f"❌ lessons_recorder が見つかりません: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
