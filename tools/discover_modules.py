#!/usr/bin/env python3
"""
ManaOS mcp-servers 動的モジュール発見ツール
================================================
Usage:
    python tools/discover_modules.py              # 全モジュール一覧
    python tools/discover_modules.py --json       # JSON形式
    python tools/discover_modules.py --catalog    # CATALOG.md 再生成
    python tools/discover_modules.py --check      # 構文エラーチェック
    python tools/discover_modules.py --stats      # 統計情報

2026-03-04 自動生成
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

MCP_SERVERS_DIR = Path(__file__).parent.parent / "mcp-servers"
SERVICES_LEDGER = Path(__file__).parent.parent / "config" / "services_ledger.yaml"


@dataclass
class ModuleInfo:
    folder: str
    main_file: str
    file_count: int
    total_size_kb: float
    flask_routes: list[str]
    has_flask: bool
    has_fastapi: bool
    has_uvicorn: bool
    docstring: str
    syntax_ok: bool
    syntax_error: Optional[str]


def _extract_docstring(path: Path) -> str:
    """ファイルの先頭 docstring または # コメントを返す"""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:20]
        # """...""" docstring
        for i, line in enumerate(lines):
            if '"""' in line or "'''" in line:
                return line.strip().strip('"""').strip("'''").strip() or ""
        # # コメント
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and len(stripped) > 5:
                return stripped.lstrip("# ").strip()
    except Exception:
        pass
    return ""


def _check_syntax(path: Path) -> tuple[bool, Optional[str]]:
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def _find_flask_routes(path: Path) -> list[str]:
    routes = []
    try:
        for m in re.finditer(r'@\w+\.route\(["\']([^"\']+)["\']', path.read_text(encoding="utf-8", errors="ignore")):
            routes.append(m.group(1))
    except Exception:
        pass
    return routes


def scan_module(folder: Path) -> ModuleInfo:
    py_files = sorted(folder.glob("*.py"))
    if not py_files:
        return ModuleInfo(
            folder=folder.name, main_file="", file_count=0,
            total_size_kb=0.0, flask_routes=[], has_flask=False,
            has_fastapi=False, has_uvicorn=False, docstring="",
            syntax_ok=True, syntax_error=None,
        )

    # メインファイル = 最大サイズ
    main = max(py_files, key=lambda f: f.stat().st_size)
    total_kb = sum(f.stat().st_size for f in py_files) / 1024
    content = main.read_text(encoding="utf-8", errors="ignore")

    routes = _find_flask_routes(main)
    has_flask = "from flask" in content or "import flask" in content or "Flask(__name__)" in content
    has_fastapi = "from fastapi" in content or "FastAPI()" in content
    has_uvicorn = "uvicorn" in content
    docstring = _extract_docstring(main)
    syntax_ok, syntax_error = _check_syntax(main)

    return ModuleInfo(
        folder=folder.name,
        main_file=main.name,
        file_count=len(py_files),
        total_size_kb=round(total_kb, 1),
        flask_routes=routes[:10],  # 最大10件
        has_flask=has_flask,
        has_fastapi=has_fastapi,
        has_uvicorn=has_uvicorn,
        docstring=docstring[:120],
        syntax_ok=syntax_ok,
        syntax_error=syntax_error,
    )


def scan_all() -> list[ModuleInfo]:
    if not MCP_SERVERS_DIR.exists():
        print(f"ERROR: {MCP_SERVERS_DIR} が見つかりません", file=sys.stderr)
        sys.exit(1)
    modules = []
    for d in sorted(MCP_SERVERS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            modules.append(scan_module(d))
    return modules


def print_table(modules: list[ModuleInfo]) -> None:
    print(f"{'フォルダ':<36} {'メインファイル':<45} {'ファイル数':>6} {'KB':>7} {'routes':>6} {'框架':>8}")
    print("-" * 116)
    for m in modules:
        fw = ("Flask" if m.has_flask else "") + ("FastAPI" if m.has_fastapi else "")
        syntax_flag = "❌" if not m.syntax_ok else ""
        print(
            f"{(m.folder + ' ' + syntax_flag):<36} {m.main_file:<45} {m.file_count:>6} "
            f"{m.total_size_kb:>7.1f} {len(m.flask_routes):>6} {fw:>8}"
        )
    print()
    total_files = sum(m.file_count for m in modules)
    total_kb = sum(m.total_size_kb for m in modules)
    errors = [m for m in modules if not m.syntax_ok]
    print(f"総計: {len(modules)} モジュール / {total_files} ファイル / {total_kb:.0f} KB")
    if errors:
        print(f"\n❌ 構文エラー ({len(errors)}件):")
        for m in errors:
            print(f"  {m.folder}/{m.main_file}: {m.syntax_error}")


def print_stats(modules: list[ModuleInfo]) -> None:
    total_files = sum(m.file_count for m in modules)
    total_kb = sum(m.total_size_kb for m in modules)
    flask_count = sum(1 for m in modules if m.has_flask)
    fastapi_count = sum(1 for m in modules if m.has_fastapi)
    route_total = sum(len(m.flask_routes) for m in modules)
    syntax_errors = [m for m in modules if not m.syntax_ok]

    print("=== ManaOS mcp-servers 統計 ===")
    print(f"モジュール数  : {len(modules)}")
    print(f"総ファイル数  : {total_files}")
    print(f"総サイズ      : {total_kb:.0f} KB ({total_kb/1024:.1f} MB)")
    print(f"Flask モジュール : {flask_count}")
    print(f"FastAPI モジュール: {fastapi_count}")
    print(f"Flask routes 合計: {route_total}")
    print(f"構文エラー    : {len(syntax_errors)}")
    print()
    print("Top 10 ファイル数:")
    for m in sorted(modules, key=lambda x: x.file_count, reverse=True)[:10]:
        print(f"  {m.folder:<36} {m.file_count} py")
    print()
    print("Top 10 サイズ (KB):")
    for m in sorted(modules, key=lambda x: x.total_size_kb, reverse=True)[:10]:
        print(f"  {m.folder:<36} {m.total_size_kb:.1f} KB")


def generate_catalog(modules: list[ModuleInfo]) -> str:
    lines = [
        "# ManaOS mcp-servers 完全カタログ\n",
        f"**自動生成**: {__import__('datetime').date.today()}  ",
        f"**総ファイル数**: {sum(m.file_count for m in modules):,}  ",
        f"**モジュール数**: {len(modules)}  ",
        "",
        "| フォルダ | メインファイル | ファイル数 | KB | routes | 概要 |",
        "|---|---|---|---|---|---|",
    ]
    for m in modules:
        ok = "" if m.syntax_ok else " ❌"
        lines.append(
            f"| `{m.folder}`{ok} | `{m.main_file}` | {m.file_count} | {m.total_size_kb:.0f} "
            f"| {len(m.flask_routes)} | {m.docstring[:60]} |"
        )
    lines.append("")
    lines.append(f"*更新: `python tools/discover_modules.py --catalog > mcp-servers/CATALOG.md`*")
    return "\n".join(lines)


def check_syntax(modules: list[ModuleInfo]) -> int:
    errors = [m for m in modules if not m.syntax_ok]
    if not errors:
        print("✅ 全モジュール 構文エラーなし")
        return 0
    print(f"❌ {len(errors)} 件の構文エラー:")
    for m in errors:
        print(f"  {m.folder}/{m.main_file}: {m.syntax_error}")
    return 1


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="ManaOS mcp-servers モジュール発見ツール")
    parser.add_argument("--json", action="store_true", help="JSON 形式で出力")
    parser.add_argument("--catalog", action="store_true", help="CATALOG.md 形式で出力")
    parser.add_argument("--check", action="store_true", help="構文エラーチェックのみ")
    parser.add_argument("--stats", action="store_true", help="統計情報を表示")
    parser.add_argument("--update-catalog", action="store_true",
                        help=f"mcp-servers/CATALOG.md を直接更新")
    args = parser.parse_args()

    modules = scan_all()

    if args.json:
        print(json.dumps([asdict(m) for m in modules], ensure_ascii=False, indent=2))
    elif args.catalog:
        print(generate_catalog(modules))
    elif args.check:
        sys.exit(check_syntax(modules))
    elif args.stats:
        print_stats(modules)
    elif args.update_catalog:
        catalog_path = MCP_SERVERS_DIR / "CATALOG.md"
        catalog_path.write_text(generate_catalog(modules), encoding="utf-8")
        print(f"✅ {catalog_path} を更新しました ({len(modules)} モジュール)")
    else:
        print_table(modules)
        print()
        print("オプション: --json / --catalog / --check / --stats / --update-catalog")


if __name__ == "__main__":
    main()
