#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manaosctl — ManaOS オペレーション CLI
======================================
配置先: tools/manaosctl.py

使い方:
  python tools/manaosctl.py status              # 全サービスのステータス表示
  python tools/manaosctl.py status --tier 0     # Tier0 のみ
  python tools/manaosctl.py status --json       # JSON 出力

  python tools/manaosctl.py up                  # auto_restart=true の全サービス起動
  python tools/manaosctl.py up --tier 1         # Tier1 のみ起動
  python tools/manaosctl.py up trinity          # 特定サービス起動
  python tools/manaosctl.py up --force          # auto_restart=false でも起動

  python tools/manaosctl.py restart trinity     # 特定サービス再起動
  python tools/manaosctl.py restart --tier 1    # Tier1 全再起動

  python tools/manaosctl.py heal                # DOWNサービスを自動復旧 (Tier0+1)
  python tools/manaosctl.py heal --force        # 全 Tier 強制復旧
  python tools/manaosctl.py heal --dry-run      # ドライラン

  python tools/manaosctl.py report              # blast_radius + heal 履歴サマリー
  python tools/manaosctl.py report --json       # JSON 出力
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    sys.exit(2)

# events.py を tools/ から import
sys.path.insert(0, str(Path(__file__).parent))
try:
    from events import emit as _emit, read_events, EVENT_LOG, EVENT_COLORS
except ImportError:
    def _emit(*a, **kw): pass
    def read_events(n=50): return []
    EVENT_LOG = None
    EVENT_COLORS = {}

# ── パス ─────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).parent.parent
LEDGER_PATH = REPO_ROOT / "config" / "services_ledger.yaml"
TOOLS_DIR   = REPO_ROOT / "tools"
LOG_DIR     = REPO_ROOT / "logs"
HEAL_LOG    = LOG_DIR / "heal.log"
PYTHON_EXE  = sys.executable

# ── カラー ────────────────────────────────────────────────────────────────────
RESET  = "\x1b[0m"
RED    = "\x1b[31m"
YELLOW = "\x1b[33m"
GREEN  = "\x1b[32m"
CYAN   = "\x1b[36m"
BOLD   = "\x1b[1m"
DIM    = "\x1b[2m"
MAGENTA = "\x1b[35m"

def c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


# ── Ledger ロード ─────────────────────────────────────────────────────────────
def load_ledger(path: Path = LEDGER_PATH) -> Dict[str, Any]:
    if not path.exists():
        print(f"[ERROR] services_ledger.yaml not found: {path}", file=sys.stderr)
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    services: Dict[str, Any] = {}
    for group in ("core", "optional"):
        for name, cfg in (raw.get(group) or {}).items():
            if isinstance(cfg, dict):
                cfg["name"] = name
                cfg["group"] = group
                services[name] = cfg
    return services


# ── ヘルスチェック ────────────────────────────────────────────────────────────
def is_alive(svc: Dict[str, Any], timeout: float = 2.0) -> bool:
    health_url = svc.get("health_url")
    port = svc.get("port")
    if health_url:
        try:
            with urllib.request.urlopen(health_url, timeout=timeout) as r:
                return r.status < 500
        except Exception:
            pass
    if port:
        try:
            with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
                return True
        except Exception:
            pass
    return False


# ── サービス起動 ──────────────────────────────────────────────────────────────
def start_one(svc: Dict[str, Any], dry_run: bool = False, wait: bool = True) -> bool:
    name = svc["name"]
    start_cmd = svc.get("start_cmd")
    if not start_cmd:
        print(c(f"  [SKIP] {name} — start_cmd 未定義", DIM))
        return False

    cmd = f'"{PYTHON_EXE}" {start_cmd[7:]}' if start_cmd.startswith("python ") else start_cmd

    if dry_run:
        print(c(f"  [DRY] {name} — {cmd}", CYAN))
        return True

    print(c(f"  → {name} 起動中...", CYAN), end=" ", flush=True)
    _emit("heal_trigger", service=name, detail=str(start_cmd), source="manaosctl")
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(cmd, cwd=str(REPO_ROOT), shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(c(f"ERROR ({e})", RED))
        return False

    if not wait:
        print(c("launched", GREEN))
        return True

    # ヘルスチェック待機（最大10秒）
    for _ in range(10):
        time.sleep(1)
        if is_alive(svc, timeout=1.5):
            print(c("OK", GREEN))
            _emit("service_up", service=name, detail="started by manaosctl", source="manaosctl")
            return True
    print(c("TIMEOUT", YELLOW))
    _emit("service_down", service=name, detail="startup timeout", source="manaosctl")
    return False


# ── stop ─────────────────────────────────────────────────────────────────────
def stop_one(svc: Dict[str, Any], dry_run: bool = False) -> bool:
    """ポートで Python プロセスを特定して SIGTERM。"""
    name = svc["name"]
    port = svc.get("port")
    if not port:
        print(c(f"  [SKIP] {name} — port 未定義", DIM))
        return False
    if dry_run:
        print(c(f"  [DRY] {name} — would kill process on port {port}", CYAN))
        return True

    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        pids = set()
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
        if not pids:
            print(c(f"  [SKIP] {name} — プロセス見当たらず (既に停止?)", DIM))
            return True
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True)
        print(c(f"  [STOPPED] {name} (PID: {pids})", GREEN))
        _emit("shutdown", service=name, detail=f"stopped pid={pids}", source="manaosctl")
        return True
    except Exception as e:
        print(c(f"  [ERROR] {name} — {e}", RED))
        return False


# ── topo sort ────────────────────────────────────────────────────────────────
def topo_sort(targets: List[str], services: Dict[str, Any]) -> List[str]:
    ordered: List[str] = []
    visited: set = set()
    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        for dep in (services.get(name, {}).get("depends_on") or []):
            if dep in targets:
                visit(dep)
        ordered.append(name)
    for n in targets:
        visit(n)
    return ordered


# ─────────────────────────────────────────────────────────────────────────────
# サブコマンド実装
# ─────────────────────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> int:
    """全サービスのステータスを表形式で表示。"""
    services = load_ledger()
    tiers = set(args.tiers) if getattr(args, "tiers", None) else None

    rows = []
    for name, svc in sorted(services.items(), key=lambda x: (x[1].get("tier", 9), x[0])):
        tier = svc.get("tier", 2)
        if tiers and tier not in tiers:
            continue
        if not svc.get("enabled", False):
            status = "DISABLED"
            color = DIM
        else:
            alive = is_alive(svc)
            status = "UP" if alive else "DOWN"
            color = GREEN if alive else RED
        rows.append({
            "service": name,
            "tier": tier,
            "port": svc.get("port", "-"),
            "status": status,
            "auto_restart": svc.get("auto_restart", False),
            "cost_risk": svc.get("cost_risk", "-"),
        })

    if getattr(args, "json", False):
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print(c(f"\n{'Service':<22} {'Tier':>4} {'Port':>6} {'Status':<10} {'AutoHeal':<10} CostRisk", BOLD))
    print("─" * 68)
    for r in rows:
        st_color = GREEN if r["status"] == "UP" else (RED if r["status"] == "DOWN" else DIM)
        ah = c("✓", GREEN) if r["auto_restart"] else c("✗", DIM)
        cr = c(str(r["cost_risk"]), YELLOW if r["cost_risk"] == "med" else (RED if r["cost_risk"] == "high" else RESET))
        print(f"{r['service']:<22} {r['tier']:>4} {str(r['port']):>6} {c(r['status'], st_color):<19} {ah:<12} {cr}")
    print()
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    """指定サービス / Tier を起動。"""
    services = load_ledger()
    all_tier  = getattr(args, "all", False)
    tiers = set(args.tiers) if getattr(args, "tiers", None) else ({0, 1, 2} if all_tier else {0, 1})
    force = getattr(args, "force", False) or all_tier  # --all は全サービス強制起動
    dry   = getattr(args, "dry_run", False)
    target_names: List[str] = getattr(args, "target", []) or []

    if target_names:
        targets = [n for n in target_names if n in services]
        unknown = [n for n in target_names if n not in services]
        if unknown:
            print(c(f"[WARN] 不明なサービス: {unknown}", YELLOW))
    else:
        targets = [
            name for name, svc in services.items()
            if svc.get("tier", 2) in tiers
            and svc.get("enabled", False)
            and (svc.get("auto_restart", False) or force)
        ]

    print(c(f"\n[UP] 対象: {targets}", BOLD))
    ordered = topo_sort(targets, services)
    failed = []
    for name in ordered:
        if is_alive(services[name]):
            print(c(f"  [SKIP] {name} — 既に起動中", DIM))
            continue
        ok = start_one(services[name], dry_run=dry)
        if not ok:
            failed.append(name)

    print(c(f"\n完了: failed={failed}", RED if failed else GREEN))
    return 1 if failed else 0


def cmd_restart(args: argparse.Namespace) -> int:
    """指定サービスを停止 → 起動。"""
    services = load_ledger()
    tiers = set(args.tiers) if getattr(args, "tiers", None) else None
    dry   = getattr(args, "dry_run", False)
    target_names: List[str] = getattr(args, "target", []) or []

    if target_names:
        targets = [n for n in target_names if n in services]
    elif tiers:
        targets = [name for name, svc in services.items()
                   if svc.get("tier", 2) in tiers and svc.get("enabled", False)]
    else:
        print("[ERROR] --tier または サービス名 を指定してください", file=sys.stderr)
        return 2

    print(c(f"\n[RESTART] 対象: {targets}", BOLD))
    for name in targets:
        print(c(f"\n  {name}", BOLD))
        stop_one(services[name], dry_run=dry)
        time.sleep(1.5)
        start_one(services[name], dry_run=dry)
    return 0


def cmd_heal(args: argparse.Namespace) -> int:
    """heal.py に委譲。"""
    heal_script = TOOLS_DIR / "heal.py"
    cmd = [PYTHON_EXE, str(heal_script)]
    if getattr(args, "dry_run", False):
        cmd.append("--dry-run")
    if getattr(args, "force", False):
        cmd.append("--force")
    if getattr(args, "json", False):
        cmd.append("--json")
    if getattr(args, "tiers", None):
        for t in args.tiers:
            cmd += ["--tier", str(t)]
    if getattr(args, "service", None):
        for s in args.service:
            cmd += ["--service", s]

    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return result.returncode


def cmd_report(args: argparse.Namespace) -> int:
    """blast_radius + heal ログの要約。"""
    services = load_ledger()

    # 現在のステータス
    up, down, disabled = [], [], []
    for name, svc in services.items():
        if not svc.get("enabled", False):
            disabled.append(name)
        elif is_alive(svc):
            up.append(name)
        else:
            down.append(name)

    # heal ログ最新20行
    heal_entries: List[str] = []
    if HEAL_LOG.exists():
        lines = HEAL_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        heal_entries = lines[-20:]

    report = {
        "generated_at": datetime.datetime.now().isoformat(),
        "summary": {
            "up": sorted(up),
            "down": sorted(down),
            "disabled": sorted(disabled),
            "total_up": len(up),
            "total_down": len(down),
        },
        "heal_log_tail": heal_entries,
    }

    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(c(f"\n=== ManaOS Report ({report['generated_at']}) ===", BOLD + CYAN))
    print(c(f"  UP:       {len(up):>3}  {sorted(up)}", GREEN))
    print(c(f"  DOWN:     {len(down):>3}  {sorted(down)}", RED if down else DIM))
    print(c(f"  DISABLED: {len(disabled):>3}", DIM))

    if heal_entries:
        print(c("\n--- 最新ヘルスログ (heal.log 末尾) ---", DIM))
        for line in heal_entries:
            print(c(f"  {line}", DIM))
    print()
    return 1 if down else 0


def cmd_cost(args: argparse.Namespace) -> int:
    """cost_risk=high/med のサービスを一覧表示。"""
    services = load_ledger()

    rows = []
    for name, svc in sorted(services.items(), key=lambda x: (x[1].get("tier", 9), x[0])):
        risk = svc.get("cost_risk", "low")
        if not svc.get("enabled", False):
            continue
        alive = is_alive(svc)
        rows.append({
            "service": name,
            "tier": svc.get("tier", 2),
            "port": svc.get("port", "-"),
            "cost_risk": risk,
            "status": "UP" if alive else "DOWN",
        })

    high = [r for r in rows if r["cost_risk"] == "high"]
    med  = [r for r in rows if r["cost_risk"] == "med"]

    if getattr(args, "json", False):
        print(json.dumps({"high": high, "med": med}, ensure_ascii=False, indent=2))
        return 0

    print(c(f"\n=== ManaOS Cost Monitor ===", BOLD))

    if high:
        print(c("\n  [HIGH COST] 重量/課金リスクあり", RED + BOLD))
        print(c(f"  {'Service':<22} {'Tier':>4} {'Port':>6} Status", BOLD))
        print("  " + "─" * 46)
        for r in high:
            st = c(r["status"], GREEN if r["status"] == "UP" else RED)
            print(f"  {r['service']:<22} {r['tier']:>4} {str(r['port']):>6} {st}")
    else:
        print(c("  [HIGH COST] なし", DIM))

    if med:
        print(c("\n  [MED COST] 中程度リスク", YELLOW + BOLD))
        print(c(f"  {'Service':<22} {'Tier':>4} {'Port':>6} Status", BOLD))
        print("  " + "─" * 46)
        for r in med:
            st = c(r["status"], GREEN if r["status"] == "UP" else RED)
            print(f"  {r['service']:<22} {r['tier']:>4} {str(r['port']):>6} {st}")
    else:
        print(c("  [MED COST] なし", DIM))

    running_high = [r for r in high if r["status"] == "UP"]
    if running_high:
        names = [r["service"] for r in running_high]
        print(c(f"\n  ⚠  HIGH COST 稼働中: {names}", RED))
        print(c("     不要なら manaosctl restart <name> で停止を検討してください", DIM))
    print()
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """サービス状態ダッシュボード（Tier × UP/DOWN/DISABLED の全体像）。"""
    import shutil
    services = load_ledger()
    width = min(shutil.get_terminal_size((100, 24)).columns, 120)

    # ステータス収集
    rows = []
    for name, svc in sorted(services.items(), key=lambda x: (x[1].get("tier", 9), x[0])):
        tier = svc.get("tier", 2)
        if not svc.get("enabled", False):
            status, st_color = "DISABLED", DIM
        else:
            alive = is_alive(svc)
            status, st_color = ("UP", GREEN) if alive else ("DOWN", RED)
        rows.append({
            "name": name,
            "tier": tier,
            "port": svc.get("port", "-"),
            "status": status,
            "color": st_color,
            "auto_restart": svc.get("auto_restart", False),
            "cost_risk": svc.get("cost_risk", "low"),
        })

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    up_count       = sum(1 for r in rows if r["status"] == "UP")
    down_count     = sum(1 for r in rows if r["status"] == "DOWN")
    disabled_count = sum(1 for r in rows if r["status"] == "DISABLED")
    high_running   = [r["name"] for r in rows if r["cost_risk"] == "high" and r["status"] == "UP"]

    bar = "═" * width
    print(c(bar, BOLD))
    title = f"  ManaOS Dashboard  {now}  |  UP:{up_count}  DOWN:{down_count}  DISABLED:{disabled_count}"
    print(c(title, BOLD + CYAN))
    print(c(bar, BOLD))

    cur_tier = -1
    for r in rows:
        if r["tier"] != cur_tier:
            cur_tier = r["tier"]
            label = {0: "Tier 0 — Core", 1: "Tier 1 — Main", 2: "Tier 2 — Optional"}.get(cur_tier, f"Tier {cur_tier}")
            print(c(f"\n  ▶ {label}", BOLD))
            print(c(f"  {'Service':<24} {'Port':>6}  {'Status':<10} {'AutoHeal':<9} CostRisk", DIM))
            print(c(f"  {'─'*24} {'─'*6}  {'─'*10} {'─'*9} {'─'*8}", DIM))
        ah  = c("✓ heal", GREEN) if r["auto_restart"] else c("✗", DIM)
        cr  = c(r["cost_risk"], YELLOW if r["cost_risk"] == "med" else (RED if r["cost_risk"] == "high" else DIM))
        st  = c(f"{r['status']:<10}", r["color"])
        print(f"  {r['name']:<24} {str(r['port']):>6}  {st} {ah:<16} {cr}")

    print(c(f"\n{bar}", BOLD))
    if high_running:
        print(c(f"  ⚠  HIGH COST 稼働中: {high_running}", RED))
    if down_count:
        down_names = [r["name"] for r in rows if r["status"] == "DOWN"]
        print(c(f"  ✗  DOWN サービス: {down_names}  → manaosctl heal で復旧", RED))
    if not down_count and not high_running:
        print(c("  ✓  全サービス正常", GREEN))
    print(c(bar, BOLD))
    print()
    return 1 if down_count else 0

def cmd_events(args: argparse.Namespace) -> int:
    """イベント履歴を時系列表示。"""
    n    = getattr(args, "n", 50)
    filt = getattr(args, "filter", None)
    events = read_events(n=max(n * 3, 200))  # 多めに読んでフィルタ後に残す

    if filt:
        events = [e for e in events if filt in e.get("event", "") or filt in e.get("service", "")]
    events = events[-n:]

    if getattr(args, "json", False):
        print(json.dumps(events, ensure_ascii=False, indent=2))
        return 0

    if not events:
        print(c("  (イベントなし — logs/events.jsonl がまだ空です)", DIM))
        return 0

    # 表示
    EVLEN = 16
    print(c(f"\n{'Time':<20} {'Event':<{EVLEN}} {'Service':<24} Detail", BOLD))
    print("─" * 90)
    for e in events:
        t    = e.get("time", "")[:19]
        ev   = e.get("event", "")[:EVLEN]
        svc  = e.get("service", "")[:24]
        det  = e.get("detail", "")[:50]
        col  = EVENT_COLORS.get(e.get("event", ""), "")
        print(f"{c(t, DIM)} {c(ev, col):<{EVLEN+10}} {svc:<24} {c(det, DIM)}")
    print()
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """直近イベントを llm_routing (port 5111) に投げて分析。"""
    import urllib.request

    n   = getattr(args, "n", 30)
    url = getattr(args, "url", "http://127.0.0.1:5111/api/llm/route")

    events = read_events(n=n)
    if not events:
        print(c("  (イベントなし — 先にサービスを起動してください)", DIM))
        return 0

    events_text = json.dumps(events, ensure_ascii=False, indent=2)
    prompt = (
        f"以下は ManaOS の直近 {len(events)} 件のイベントログです。\n"
        f"分析して「はっきり分かる日本語」で答えてください。\n"
        f"1. 異常パターン（頂点5件）\n"
        f"2. 問題の原因推定\n"
        f"3. 推奨アクション\n"
        f"\nEvents:\n{events_text}"
    )

    print(c(f"\n[ManaOS Event Analysis (n={len(events)})]", BOLD + CYAN))
    print(c(f"  LLM エンドポイント: {url}", DIM))
    print()

    payload = json.dumps({"prompt": prompt, "model": "auto"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            model     = result.get("model", "?")
            resp_text = result.get("response", "(レスポンスなし)")
            print(c(f"[使用モデル: {model}]", DIM))
            print()
            print(resp_text)
            print()
        _emit("analyze", detail=f"n={len(events)} model={result.get('model','?')}", source="manaosctl")
    except Exception as e:
        print(c(f"  [ERROR] LLM接続失敗: {e}", RED))
        print(c("  ヒント: llm_routing が起動しているか確認してください", DIM))
        return 1
    return 0
# ── エントリポイント ──────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manaosctl",
        description="ManaOS operations CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = sub.add_parser("status", help="サービス状態一覧")
    p_status.add_argument("--tier", type=int, action="append", dest="tiers")
    p_status.add_argument("--json", action="store_true")

    # up
    p_up = sub.add_parser("up", help="サービス起動")
    p_up.add_argument("target", nargs="*", help="サービス名（省略時は tier 対象）")
    p_up.add_argument("--tier", type=int, action="append", dest="tiers")
    p_up.add_argument("--all", action="store_true", help="Tier2 含む全サービス起動")
    p_up.add_argument("--force", action="store_true", help="auto_restart=false でも起動")
    p_up.add_argument("--dry-run", action="store_true")

    # restart
    p_restart = sub.add_parser("restart", help="サービス再起動")
    p_restart.add_argument("target", nargs="*")
    p_restart.add_argument("--tier", type=int, action="append", dest="tiers")
    p_restart.add_argument("--dry-run", action="store_true")

    # heal
    p_heal = sub.add_parser("heal", help="DOWN サービスを自動復旧")
    p_heal.add_argument("--tier",    type=int, action="append", dest="tiers")
    p_heal.add_argument("--service", type=str, action="append")
    p_heal.add_argument("--force",   action="store_true")
    p_heal.add_argument("--dry-run", action="store_true")
    p_heal.add_argument("--json",    action="store_true")

    # report
    p_report = sub.add_parser("report", help="状態レポート")
    p_report.add_argument("--json", action="store_true")

    # cost
    p_cost = sub.add_parser("cost", help="高コストサービス一覧 (cost_risk=high/med)")
    p_cost.add_argument("--json", action="store_true")

    # dashboard
    sub.add_parser("dashboard", help="全サービスダッシュボード表示")

    # events
    p_events = sub.add_parser("events", help="イベント履歴表示")
    p_events.add_argument("-n", type=int, default=30, help="表示件数 (デフォルト: 30)")
    p_events.add_argument("--filter", type=str, help="イベント名またはサービス名で絞り込む")
    p_events.add_argument("--json", action="store_true")

    # analyze
    p_analyze = sub.add_parser("analyze", help="イベントを LLM に詳細分析させる")
    p_analyze.add_argument("-n",    type=int, default=30, help="分析する直近件数 (デフォルト: 30)")
    p_analyze.add_argument("--url", type=str, default="http://127.0.0.1:5111/api/llm/route",
                           help="LLM ルーティング URL")
    p_analyze.add_argument("--json", action="store_true")

    args = parser.parse_args()

    dispatch = {
        "status":    cmd_status,
        "up":        cmd_up,
        "restart":   cmd_restart,
        "heal":      cmd_heal,
        "report":    cmd_report,
        "cost":      cmd_cost,
        "dashboard": cmd_dashboard,
        "events":    cmd_events,
        "analyze":   cmd_analyze,
    }
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
