#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Blast Radius Checker
============================
配置先: tools/check_blast_radius.py

使い方:
  python check_blast_radius.py                         # 全サービスのサマリー
  python check_blast_radius.py --service unified_api   # unified_api が落ちた時の影響範囲
  python check_blast_radius.py --service memory        # memory が落ちた時
  python check_blast_radius.py --recovery-order        # Tier 順の復旧手順書を出力
  python check_blast_radius.py --live                  # 実サービスを HTTP プローブして DOWN のブラスト半径を表示
  python check_blast_radius.py --ledger path/to/services_ledger.yaml

終了コード:
  0 = OK
  1 = エラー (ファイルなし / YAML 不正)
"""

from __future__ import annotations

import argparse
import http.client
import sys
import urllib.error
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Windows での文字エンコーディング設定
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

try:
    import yaml
except ImportError:
    print("pyyaml が必要です: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ── カラー出力 ────────────────────────────────────────────────────────────────
RESET  = "\x1b[0m"
RED    = "\x1b[31m"
YELLOW = "\x1b[33m"
GREEN  = "\x1b[32m"
CYAN   = "\x1b[36m"
BOLD   = "\x1b[1m"
DIM    = "\x1b[2m"

LIVE_TIMEOUT = 2.0

def c(text: str, color: str, use_color: bool = True) -> str:
    return f"{color}{text}{RESET}" if use_color else text


# ── データモデル ──────────────────────────────────────────────────────────────
@dataclass
class Service:
    name: str
    group: str          # "core" or "optional"
    port: Optional[int]
    url: Optional[str]
    enabled: bool
    tier: int           # 0 / 1 / 2
    depends_on: List[str] = field(default_factory=list)
    description: str = ""
    blast_note: str = ""


# ── YAML ロード ──────────────────────────────────────────────────────────────
def load_ledger(path: str) -> Dict[str, Service]:
    """ledger を読んで {service_name: Service} を返す"""
    p = Path(path)
    if not p.exists():
        print(f"[ERROR] ファイルが見つかりません: {path}", file=sys.stderr)
        sys.exit(1)

    with open(p, "r", encoding="utf-8") as f:
        raw: Dict[str, Any] = yaml.safe_load(f) or {}

    services: Dict[str, Service] = {}
    for group in ("core", "optional"):
        section = raw.get(group, {}) or {}
        for name, cfg in section.items():
            if not isinstance(cfg, dict):
                continue
            services[name] = Service(
                name=name,
                group=group,
                port=cfg.get("port"),
                url=cfg.get("url"),
                enabled=bool(cfg.get("enabled", False)),
                tier=int(cfg.get("tier", 2)),
                depends_on=[str(d) for d in (cfg.get("depends_on") or [])],
                description=cfg.get("description", ""),
                blast_note=cfg.get("blast_note", ""),
            )

    return services


# ── 逆依存グラフ構築 ──────────────────────────────────────────────────────────
def build_reverse_deps(services: Dict[str, Service]) -> Dict[str, Set[str]]:
    """
    reverse_deps[X] = {A, B, ...}
    → X が落ちたとき A と B も影響を受ける (A/B は X に依存している)
    """
    rev: Dict[str, Set[str]] = {name: set() for name in services}
    for svc in services.values():
        for dep in svc.depends_on:
            if dep in rev:
                rev[dep].add(svc.name)
    return rev


# ── blast radius 計算 ────────────────────────────────────────────────────────
def compute_blast_radius(
    target: str,
    services: Dict[str, Service],
    reverse_deps: Dict[str, Set[str]],
) -> List[str]:
    """
    target が落ちたとき、連鎖的に停止するサービス一覧を BFS で返す。
    target 自身は含まない。
    """
    affected: Set[str] = set()
    queue: deque[str] = deque([target])
    while queue:
        current = queue.popleft()
        for child in reverse_deps.get(current, set()):
            if child not in affected:
                affected.add(child)
                queue.append(child)
    return sorted(affected, key=lambda n: services[n].tier if n in services else 9)


# ── トポロジカルソート (復旧順序) ────────────────────────────────────────────
def recovery_order(services: Dict[str, Service]) -> List[Service]:
    """
    Kahn's algorithm。tier が同じ場合は depends_on が少ない方を先に。
    復旧時の起動順序として使う。
    """
    in_degree: Dict[str, int] = {n: 0 for n in services}
    graph: Dict[str, Set[str]] = {n: set() for n in services}

    for svc in services.values():
        for dep in svc.depends_on:
            if dep in services:
                graph[dep].add(svc.name)
                in_degree[svc.name] += 1

    # tier 0 → 1 → 2 の順で処理するため優先度付きキューを使う
    ready: List[str] = sorted(
        [n for n, d in in_degree.items() if d == 0],
        key=lambda n: (services[n].tier, n),
    )

    order: List[Service] = []
    while ready:
        current = ready.pop(0)
        order.append(services[current])
        for child in sorted(graph[current], key=lambda n: (services[n].tier, n)):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                ready.append(child)
                ready.sort(key=lambda n: (services[n].tier, n))

    return order


# ── ライブヘルスチェック ──────────────────────────────────────────────────────
def probe_live(svc: Service) -> tuple:
    """サービスの /health を HTTP プローブして (name, status) を返す。
    status: 'OK' | 'DOWN' | 'NO_URL' | 'SKIP'  -- urllib のみ使用 (追加依存なし)。"""
    if not svc.enabled:
        return svc.name, "SKIP"
    base = svc.url or (f"http://127.0.0.1:{svc.port}" if svc.port else None)
    if not base:
        return svc.name, "NO_URL"
    target = base.rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(target, timeout=LIVE_TIMEOUT) as resp:
            return svc.name, "OK" if resp.status < 400 else f"HTTP_{resp.status}"
    except urllib.error.HTTPError as exc:
        return svc.name, "OK" if exc.code < 500 else f"HTTP_{exc.code}"
    except (
        http.client.RemoteDisconnected,
        ConnectionResetError,
        ConnectionRefusedError,
    ):
        return svc.name, "DOWN"
    except OSError:
        return svc.name, "DOWN"
    except Exception:
        return svc.name, "DOWN"


def cmd_live(
    services: Dict[str, Service],
    reverse_deps: Dict[str, Set[str]],
    use_color: bool,
) -> None:
    """全サービスを並列 HTTP プローブし、DOWN サービスのブラスト半径を表示する。"""
    sep = "=" * 70
    print(c("\n  " + sep, BOLD, use_color))
    print(c("  ManaOS Live Health + Blast Risk", BOLD, use_color))
    print(c("  " + sep, BOLD, use_color))
    print(c(f"  probing {len(services)} services (timeout: {LIVE_TIMEOUT}s) ...\n", DIM, use_color))

    # ── 並列プローブ ──
    results: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(probe_live, svc): svc for svc in services.values()}
        for fut in as_completed(futs):
            name, status = fut.result()
            results[name] = status

    # ── tier 別テーブル表示 ──
    down_enabled: List[str] = []
    for tier in (0, 1, 2):
        tier_svcs = sorted(
            [s for s in services.values() if s.tier == tier],
            key=lambda s: s.name,
        )
        if not tier_svcs:
            continue
        print(f"  {tier_badge(tier, use_color)}")
        print("  " + "-" * 66)
        for svc in tier_svcs:
            st = results.get(svc.name, "SKIP")
            if st == "OK":
                st_str = c("  OK  ", GREEN, use_color)
            elif st in ("SKIP", "NO_URL"):
                st_str = c(f" {st:<5}", DIM, use_color)
            else:
                st_str = c(f" {st:<5}", RED, use_color)
                if svc.enabled:
                    down_enabled.append(svc.name)
            en_str = c("ON ", GREEN, use_color) if svc.enabled else c("off", DIM, use_color)
            port_s = f":{svc.port}" if svc.port else "      "
            print(f"    [{st_str}] {en_str}  {tier_badge(svc.tier, use_color)}  {svc.name:25s}  {port_s}")
        print()

    ok_n   = sum(1 for v in results.values() if v == "OK")
    skip_n = sum(1 for v in results.values() if v in ("SKIP", "NO_URL"))
    down_n = len(down_enabled)

    summary_col = GREEN if down_n == 0 else (RED if down_n >= 3 else YELLOW)
    print(c(f"  Health: OK={ok_n}  DOWN={down_n}  SKIP={skip_n}", summary_col, use_color))

    if not down_enabled:
        print(c("  All enabled services are UP. No cascade risk.", GREEN, use_color))
        print()
        return

    # ── DOWN サービスのブラスト半径分析 ──
    print(c("\n  " + "=" * 68, BOLD, use_color))
    print(c("  Cascade Risk Analysis (DOWN services)", BOLD, use_color))
    print(c("  " + "=" * 68, BOLD, use_color))

    total_at_risk: Set[str] = set()
    for svc_name in down_enabled:
        affected = compute_blast_radius(svc_name, services, reverse_deps)
        total_at_risk.update(affected)
        svc = services[svc_name]
        risk_label = (
            c(f"{len(affected)} services at risk!", RED, use_color)
            if affected
            else c("isolated (no cascade)", GREEN, use_color)
        )
        print(f"\n  {tier_badge(svc.tier, use_color)}  {c(svc_name, RED, use_color)} DOWN  ->  {risk_label}")
        if svc.blast_note:
            print(f"    note: {c(svc.blast_note, YELLOW, use_color)}")
        if affected:
            for aff_name in affected[:10]:
                aff   = services.get(aff_name)
                badge = tier_badge(aff.tier, use_color) if aff else "[?]"
                print(f"    -> {badge}  {aff_name}")
            if len(affected) > 10:
                print(c(f"    ... and {len(affected) - 10} more", DIM, use_color))

    if total_at_risk:
        risk_col = RED if len(total_at_risk) > 5 else YELLOW
        print(c(f"\n  Total unique at-risk services: {len(total_at_risk)}", risk_col, use_color))
    print(c("  Tip: --service <name> for full recovery steps", DIM, use_color))
    print()


# ── 表示ヘルパー ──────────────────────────────────────────────────────────────
TIER_LABEL = {0: "[TIER-0:CRIT]", 1: "[TIER-1:MAJOR]", 2: "[TIER-2:OPT ]"}
TIER_COLOR = {0: RED, 1: YELLOW, 2: GREEN}

def tier_badge(tier: int, use_color: bool) -> str:
    label = TIER_LABEL.get(tier, f"TIER-{tier}")
    return c(label, TIER_COLOR.get(tier, ""), use_color)


def print_service_row(svc: Service, use_color: bool, prefix: str = "  ") -> None:
    badge = tier_badge(svc.tier, use_color)
    port_str = f":{svc.port}" if svc.port else "     "
    enabled = c("ON ", GREEN, use_color) if svc.enabled else c("off", DIM, use_color)
    group = c(f"[{svc.group}]", CYAN, use_color)
    print(f"{prefix}{badge}  {enabled}  {group:20s}  {svc.name:25s}  {port_str}   {svc.description}")


# --- Command: summary --------------------------------------------------
def cmd_summary(services: Dict[str, Service], use_color: bool) -> None:
    sep = "=" * 70
    print(c("\n  " + sep, BOLD, use_color))
    print(c("  ManaOS Services Summary", BOLD, use_color))
    print(c("  " + sep, BOLD, use_color))

    for tier in (0, 1, 2):
        tier_svc = [s for s in services.values() if s.tier == tier]
        if not tier_svc:
            continue
        print(f"\n  {tier_badge(tier, use_color)}  ({len(tier_svc)} services)")
        print("  " + "-" * 66)
        for svc in sorted(tier_svc, key=lambda s: s.name):
            print_service_row(svc, use_color)

    total   = len(services)
    enabled = sum(1 for s in services.values() if s.enabled)
    print(f"\n  total: {total} services / enabled: {enabled}")


# --- Command: blast radius --------------------------------------------
def cmd_blast_radius(
    target: str,
    services: Dict[str, Service],
    reverse_deps: Dict[str, Set[str]],
    use_color: bool,
) -> None:
    if target not in services:
        known = ", ".join(sorted(services.keys()))
        print(f"[ERROR] Service '{target}' not found.\nKnown: {known}", file=sys.stderr)
        sys.exit(1)

    svc      = services[target]
    affected = compute_blast_radius(target, services, reverse_deps)
    sep      = "=" * 70

    print(c("\n  " + sep, BOLD, use_color))
    print(c(f"  Blast Radius: '{target}' が落ちたとき", BOLD, use_color))
    print(c("  " + sep, BOLD, use_color))
    print(f"\n  対象: {tier_badge(svc.tier, use_color)}  {svc.name}")
    print(f"  説明: {svc.description}")
    if svc.blast_note:
        print(f"  影響メモ: {c(svc.blast_note, YELLOW, use_color)}")

    print(f"\n  直接依存 (this depends on):")
    if svc.depends_on:
        for dep in svc.depends_on:
            dep_svc = services.get(dep)
            badge   = tier_badge(dep_svc.tier, use_color) if dep_svc else "[---]"
            print(f"    {badge}  {dep}")
    else:
        print("    (none - root service)")

    print(f"\n  爆風範囲 - 連鎖停止するサービス ({len(affected)} 件):")
    if affected:
        for aff_name in affected:
            aff   = services.get(aff_name)
            badge = tier_badge(aff.tier, use_color) if aff else "[?]"
            note  = f"  <- {aff.blast_note}" if (aff and aff.blast_note) else ""
            col   = RED if (aff and aff.tier == 0) else YELLOW if (aff and aff.tier == 1) else ""
            print(c(f"    {badge}  {aff_name:25s}{note}", col, use_color))
    else:
        print(f"    {c('(none - no cascading impact)', GREEN, use_color)}")

    surviving = sorted(
        [n for n, s in services.items() if n != target and n not in affected],
        key=lambda n: services[n].tier,
    )
    print(f"\n  無傷で動き続けるサービス ({len(surviving)} 件):")
    for sv_name in surviving:
        sv = services[sv_name]
        print(f"    {tier_badge(sv.tier, use_color)}  {sv_name}")

    print(f"\n  復旧手順:")
    for dep in sorted(svc.depends_on, key=lambda d: services[d].tier if d in services else 9):
        print(f"    [0] {dep} が起動済みか確認")
    print(f"    [1] {target} を再起動")
    for aff_name in affected:
        aff   = services.get(aff_name)
        step  = "[2]" if (aff and aff.tier <= 1) else "[3]"
        badge = tier_badge(aff.tier, use_color) if aff else "[?]"
        print(f"    {step} {aff_name} を再起動  {badge}")


# --- Command: recovery order runbook ---------------------------------
def cmd_recovery_order(services: Dict[str, Service], use_color: bool) -> None:
    order   = recovery_order(services)
    all_rev = build_reverse_deps(services)
    sep     = "=" * 70

    print(c("\n  " + sep, BOLD, use_color))
    print(c("  ManaOS Recovery Runbook (復旧手順書)", BOLD, use_color))
    print(c("  " + sep + "\n", BOLD, use_color))
    print("  起動順序 (Tier 0 -> 1 -> 2, 依存関係を解決済み):\n")

    current_tier = -1
    for i, svc in enumerate(order, 1):
        if svc.tier != current_tier:
            current_tier = svc.tier
            tier_label   = {
                0: "Tier 0 -- 根幹 (最優先)",
                1: "Tier 1 -- 主要機能",
                2: "Tier 2 -- 便利機能",
            }.get(svc.tier, f"Tier {svc.tier}")
            print(f"\n  {tier_badge(svc.tier, use_color)}  {tier_label}")
            print("  " + "-" * 60)

        enabled_str = c("ON ", GREEN, use_color) if svc.enabled else c("off", DIM, use_color)
        port_str    = f":{svc.port}" if svc.port else "      "
        deps_str    = f"<- {', '.join(svc.depends_on)}" if svc.depends_on else "(no deps)"
        print(f"    {i:2d}. {enabled_str}  {svc.name:25s}  {port_str}   {c(deps_str, DIM, use_color)}")

    print(f"\n  total: {len(order)} services\n")

    # ---- Quick quiz (3 questions) ----
    print(c("  " + "-" * 68, BOLD, use_color))
    print(c("  Quick Quiz (即答チェック)", BOLD, use_color))
    print(c("  " + "-" * 68, BOLD, use_color))

    questions = [
        ("unified_api",   "Q1: unified_api が落ちたとき死ぬ UI / タスクは?"),
        ("memory",        "Q2: memory が落ちたとき動き続ける機能は? (劣化運転可能)"),
        ("pixel7_bridge", "Q3: Pixel7 系が落ちた時、ManaOS core は無傷?"),
    ]
    for svc_name, question in questions:
        print(f"\n  {question}")
        if svc_name not in services:
            print(f"    (service '{svc_name}' is not defined in ledger)")
            continue
        affected  = compute_blast_radius(svc_name, services, all_rev)
        surviving = [n for n in services if n != svc_name and n not in affected]
        if affected:
            labels = ", ".join(f"{n}(T{services[n].tier})" for n in affected[:8])
            if len(affected) > 8:
                labels += f" ...+{len(affected)-8} more"
            print(f"    A: {c('IMPACT ->', RED, use_color)} {labels}")
        else:
            print(f"    A: {c('NO IMPACT (isolated service)', GREEN, use_color)}")
        core_survivors = [
            n for n in surviving
            if services[n].group == "core" and services[n].tier <= 1
        ]
        if core_survivors:
            print(f"    Degraded-run core: {c(', '.join(core_survivors[:6]), GREEN, use_color)}")
    print()


# --- main -----------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="ManaOS Blast Radius Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python check_blast_radius.py\n"
            "  python check_blast_radius.py --service unified_api\n"
            "  python check_blast_radius.py --service memory\n"
            "  python check_blast_radius.py --recovery-order\n"
        ),
    )
    parser.add_argument("--ledger", "-l", default="services_ledger.yaml",
                        help="services_ledger.yaml のパス")
    parser.add_argument("--service", "-s", default=None,
                        help="blast radius を表示するサービス名")
    parser.add_argument("--recovery-order", "-r", action="store_true",
                        help="復旧手順書を出力")
    parser.add_argument("--live", "-L", action="store_true",
                        help="実サービスに HTTP プローブして DOWN のブラスト半径を表示")
    parser.add_argument("--no-color", action="store_true",
                        help="カラー出力を無効化")
    args = parser.parse_args()
    use_color = not args.no_color and sys.stdout.isatty()

    # Ledger ファイル検索
    ledger_path = args.ledger
    if not Path(ledger_path).exists():
        candidates = [
            Path(__file__).parent.parent / "config" / "services_ledger.yaml",
            Path(__file__).parent / "services_ledger.yaml",
            Path("config") / "services_ledger.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                ledger_path = str(candidate)
                break

    services     = load_ledger(ledger_path)
    reverse_deps = build_reverse_deps(services)

    if args.live:
        cmd_live(services, reverse_deps, use_color)
    elif args.service:
        cmd_blast_radius(args.service, services, reverse_deps, use_color)
    elif args.recovery_order:
        cmd_recovery_order(services, use_color)
    else:
        cmd_summary(services, use_color)
        print(c("  Hint: --service <name> | --recovery-order | --live", DIM, use_color))
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
