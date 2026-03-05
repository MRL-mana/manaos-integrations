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

  python tools/manaosctl.py deps                    # 全サービス依存一覧
  python tools/manaosctl.py deps llm_routing        # 特定サービスの依存詳細
  python tools/manaosctl.py deps --order            # 起動順序表示
  python tools/manaosctl.py deps --tree             # ASCII blast-radius ツリー
  python tools/manaosctl.py deps --json             # JSON出力

  python tools/manaosctl.py watch                   # 定期監視ループ（60秒間隔）
  python tools/manaosctl.py watch --interval 30     # 30秒間隔
  python tools/manaosctl.py watch --once            # 1回だけ実行して終了
  python tools/manaosctl.py watch --policy          # DOWN検出時に policy --check を自動実行

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
LEDGER_PATH   = REPO_ROOT / "config" / "services_ledger.yaml"
POLICY_PATH   = REPO_ROOT / "config" / "policies.yaml"
SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"
TOOLS_DIR     = REPO_ROOT / "tools"
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
def load_settings() -> Dict[str, Any]:
    """config/settings.yaml を読み込む（なければ空dict）。"""
    if not SETTINGS_PATH.exists():
        return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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
DEP_WAIT_TIMEOUT = 30   # 依存サービスのヘルスチェック待機上限（秒）


def wait_for_deps(svc: Dict[str, Any], services: Dict[str, Any]) -> bool:
    """depends_on に列挙されたサービスが全部 UP になるまで最大 DEP_WAIT_TIMEOUT 秒待つ。"""
    deps = [d for d in (svc.get("depends_on") or []) if d in services]
    if not deps:
        return True
    deadline = time.time() + DEP_WAIT_TIMEOUT
    pending = list(deps)
    print(c(f"  ⏳ deps 待機: {pending}", DIM), end="", flush=True)
    while pending and time.time() < deadline:
        time.sleep(1)
        print(".", end="", flush=True)
        pending = [d for d in pending if not is_alive(services[d], timeout=1.5)]
    print()
    if pending:
        print(c(f"  [WARN] deps タイムアウト: {pending} — 起動を続行", YELLOW))
        return False
    return True


def start_one(svc: Dict[str, Any], dry_run: bool = False, wait: bool = True,
              services: Dict[str, Any] | None = None) -> bool:
    name = svc["name"]
    start_cmd = svc.get("start_cmd")
    if not start_cmd:
        print(c(f"  [SKIP] {name} — start_cmd 未定義", DIM))
        return False

    cmd = f'"{PYTHON_EXE}" {start_cmd[7:]}' if start_cmd.startswith("python ") else start_cmd

    if dry_run:
        deps = svc.get("depends_on") or []
        hint = svc.get("recovery_hint", "")
        print(c(f"  [DRY] {name} — {cmd}", CYAN))
        if deps:
            print(c(f"        deps: {deps}", DIM))
        if hint:
            print(c(f"        💡 {hint}", DIM))
        return True

    # 依存サービスが UP するまで待機
    if services:
        wait_for_deps(svc, services)

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
            "hint": svc.get("recovery_hint", ""),
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
        if r["status"] == "DOWN" and r["hint"]:
            print(c(f"  {'':22}  💡 {r['hint']}", DIM))
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
        ok = start_one(services[name], dry_run=dry, services=services)
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
    if down:
        print(c(f"  DOWN:     {len(down):>3}", RED))
        for name in sorted(down):
            svc = services[name]
            print(c(f"    ✗ {name}  (Tier{svc.get('tier','-')})", RED))
            blast = svc.get("blast_note", "")
            if blast:
                print(c(f"      ⚡ 影響: {blast}", YELLOW))
            hint = svc.get("recovery_hint", "")
            if hint:
                print(c(f"      💡 復旧ヒント: {hint}", DIM))
    else:
        print(c(f"  DOWN:       0  []", DIM))
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

    # ── Policy パネル ────────────────────────────────────────────────────────
    try:
        import yaml as _yaml
        with open(POLICY_PATH, encoding="utf-8") as _f:
            _pol_data = _yaml.safe_load(_f)
        _policies = [p for p in (_pol_data.get("policies") or []) if p.get("enabled", True)]

        AUTOLABEL = {"read_only": ("read_only", DIM), "suggest": ("suggest ", YELLOW), "execute": ("execute ", GREEN)}
        print(c(f"\n  ▶ Policy ({len(_policies)} enabled)", BOLD))
        print(c(f"  {'Name':<32} {'Trigger':<22} {'Action':<10} {'Autonomy':<10} tier≥N", DIM))
        print(c(f"  {'─'*32} {'─'*22} {'─'*10} {'─'*10} {'─'*5}", DIM))
        for _p in _policies:
            _lbl, _col = AUTOLABEL.get(_p.get("autonomy_level", ""), (_p.get("autonomy_level", "?"), DIM))
            _tr = str(_p.get("tier_restriction", 0))
            print(f"  {_p['name']:<32} {_p.get('trigger',''):<22} {_p.get('action',''):<10} {c(_lbl, _col):<19} {_tr}")

        # 直近 policy 発火イベントを最大5件表示
        _pol_events = [e for e in read_events(n=200)
                       if e.get("event", "").startswith("policy_")][-5:]
        if _pol_events:
            print(c(f"\n  直近 Policy 発火:", DIM))
            for _e in _pol_events:
                _t = _e.get("time", "")[:19]
                _ev = _e.get("event", "")
                _det = _e.get("detail", "")[:60]
                print(c(f"    {_t}  {_ev:<24} {_det}", DIM))
    except Exception:
        pass

    print(c(bar, BOLD))
    print()
    return 1 if down_count else 0


def cmd_shell(args: argparse.Namespace) -> int:
    """ManaOS Shell ブラウザ UI を開く。unified_api が UP していることを確認してから起動。"""
    import webbrowser as _wb
    port = int(os.environ.get("UNIFIED_API_PORT", "9502"))
    url  = f"http://127.0.0.1:{port}/shell"

    # unified_api の生存確認
    services = load_ledger()
    ua = services.get("unified_api", {})
    alive = is_alive(ua) if ua else False

    if not alive:
        print(c("✗ unified_api が DOWN しています。先に起動してください:", RED))
        print(c("    manaosctl up --tier 0", DIM))
        return 1

    print(c(f"✓ unified_api UP   →   {url}", GREEN))
    _wb.open(url)
    return 0


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


def cmd_deps(args: argparse.Namespace) -> int:
    """サービスの依存ツリーの可視化。起動順序、上流/下流の影響表示。"""
    services = load_ledger()
    target_name: Optional[str] = getattr(args, "service", None)
    show_order  = getattr(args, "order", False)
    as_json     = getattr(args, "json", False)

    def get_upstream(name: str) -> List[str]:
        return [d for d in (services.get(name, {}).get("depends_on") or []) if d in services]

    def get_downstream(name: str) -> List[str]:
        return [n for n, svc in services.items() if name in (svc.get("depends_on") or [])]

    def all_upstream(name: str, visited: Optional[set] = None) -> List[str]:
        if visited is None:
            visited = set()
        for dep in get_upstream(name):
            if dep not in visited:
                visited.add(dep)
                all_upstream(dep, visited)
        return sorted(visited)

    def all_downstream(name: str, visited: Optional[set] = None) -> List[str]:
        if visited is None:
            visited = set()
        for ds in get_downstream(name):
            if ds not in visited:
                visited.add(ds)
                all_downstream(ds, visited)
        return sorted(visited)

    if as_json:
        if target_name and target_name in services:
            result: Dict[str, Any] = {
                "service":     target_name,
                "upstream":    all_upstream(target_name),
                "downstream":  all_downstream(target_name),
                "start_order": topo_sort(list(services.keys()), services),
            }
        else:
            result = {
                name: {
                    "depends_on":  get_upstream(name),
                    "depended_by": get_downstream(name),
                }
                for name in sorted(services)
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # ─── 起動順序表示 ──────────────────────────────────────────────────
    if show_order:
        enabled = [n for n, s in services.items() if s.get("enabled", False)]
        ordered = topo_sort(enabled, services)
        print(c(f"\n{'#':>3}  {'Service':<24} {'Tier':>4}  depends_on", BOLD))
        print("─" * 70)
        for i, name in enumerate(ordered, 1):
            svc  = services[name]
            deps = ", ".join(get_upstream(name)) or c("─", DIM)
            alive = is_alive(svc)
            st = c("●", GREEN if alive else (DIM if not svc.get("enabled") else RED))
            print(f"{i:>3}  {st} {name:<23} {str(svc.get('tier','?')):>4}  {c(deps, DIM)}")
        print()
        return 0

    # ─── ASCII blast-radius ツリー ─────────────────────────────────────
    if getattr(args, "tree", False):
        if target_name:
            if target_name not in services:
                print(c(f"[ERROR] サービス '{target_name}' が見つかりません", RED))
                return 1
            roots = [target_name]
            dn_count = len(all_downstream(target_name))
            print(c(f"\n  ▶ {target_name} 依存ツリー  (blast-radius: 下流への影響)", BOLD))
            print(c(f"  このサービスが落ちると下流 {dn_count} サービスが連鎖影響を受ける", DIM))
        else:
            roots = sorted(
                [n for n, s in services.items()
                 if s.get("enabled", False)
                 and not [d for d in (s.get("depends_on") or []) if d in services]],
                key=lambda n: (services[n].get("tier", 9), n)
            )
            print(c(f"\n  ▶ 依存ツリー  (blast-radius: 根→葉の方向)", BOLD))
            print(c("  根サービスが落ちると下流の葉サービスが連鎖影響を受ける", DIM))
        print()

        visited: set = set()

        def _st(name: str) -> str:
            svc = services.get(name, {})
            if not svc.get("enabled", True):
                return c("○", DIM)
            return c("●", GREEN) if is_alive(svc, timeout=0.5) else c("●", RED)

        def render_tree(name: str, prefix: str, is_last: bool) -> None:
            conn = "└─→ " if is_last else "├─→ "
            svc  = services.get(name, {})
            tier = c(f"Tier{svc.get('tier','?')}", DIM)
            loop = c(" (↩ 既出)", DIM) if name in visited else ""
            print(f"  {prefix}{c(conn, DIM)}{_st(name)} {name}  {tier}{loop}")
            if name in visited:
                return
            visited.add(name)
            ds_list = sorted(get_downstream(name))
            for i, ds in enumerate(ds_list):
                ext = "    " if is_last else "│   "
                render_tree(ds, prefix + ext, i == len(ds_list) - 1)

        for root in roots:
            svc  = services[root]
            tier = c(f"Tier{svc.get('tier','?')}", DIM)
            print(f"  {_st(root)} {c(root, BOLD)}  {tier}")
            ds_list = sorted(get_downstream(root))
            for i, ds in enumerate(ds_list):
                render_tree(ds, "  ", i == len(ds_list) - 1)
            print()

        print(c("  ヒント: manaosctl deps <name> で特定サービスの up/down stream 詳細", DIM))
        print()
        return 0

    # ─── 特定サービスの詳細 ────────────────────────────────────────────
    if target_name:
        if target_name not in services:
            print(c(f"[ERROR] 不明なサービス: {target_name}", RED), file=sys.stderr)
            return 2
        svc         = services[target_name]
        alive       = is_alive(svc)
        st          = c("UP", GREEN) if alive else c("DOWN", RED)
        up_direct   = get_upstream(target_name)
        up_all      = all_upstream(target_name)
        down_direct = get_downstream(target_name)
        down_all    = all_downstream(target_name)
        dead_deps   = [d for d in up_all if not is_alive(services[d], timeout=1.5)]

        print(c(f"\n▶ {target_name}  [", BOLD) + st + c(f"]  Tier {svc.get('tier','?')}", BOLD))
        print(c(f"  {svc.get('description','')}", DIM))
        if dead_deps:
            print(c(f"  ⚠  上流 DOWN: {dead_deps}  ← そのサービスを先に復旧すること", RED))
        print()
        print(c("  ↑ requires  (direct): ", DIM) + (c(", ".join(up_direct), CYAN)   if up_direct   else c("─", DIM)))
        print(c("  ↑ requires  (all)   : ", DIM) + (c(", ".join(up_all), CYAN)      if up_all      else c("─", DIM)))
        print(c("  ↓ needed by (direct): ", DIM) + (c(", ".join(down_direct), YELLOW) if down_direct else c("─", DIM)))
        print(c("  ↓ needed by (all)   : ", DIM) + (c(", ".join(down_all), YELLOW)  if down_all    else c("─", DIM)))
        print()
        if down_all:
            print(c(f"  ⚠  このサービスが落ちると {len(down_all)} サービスが影響を受ける: {down_all}", MAGENTA))
        return 0

    # ─── 全サービスの依存一覧 ──────────────────────────────────────────
    print(c(f"\n{'Service':<24} {'Tier':>4}  {'depends_on':<38} needed_by", BOLD))
    print("─" * 94)
    for name in sorted(services, key=lambda n: (services[n].get("tier", 9), n)):
        svc   = services[name]
        alive = is_alive(svc) if svc.get("enabled") else None
        if alive is True:
            st = c("●", GREEN)
        elif alive is False:
            st = c("●", RED)
        else:
            st = c("○", DIM)
        tier    = str(svc.get("tier", "?"))
        deps    = ", ".join(get_upstream(name))   or "─"
        rev_dep = ", ".join(get_downstream(name)) or "─"
        print(f"{st} {name:<23} {tier:>4}  {c(deps[:38], DIM):<44} {c(rev_dep[:30], DIM)}")
    print(c("\n  ヒント: manaosctl deps <name> で個別詳細 / --order で起動順表示", DIM))
    print()
    return 0


def cmd_policy(args: argparse.Namespace) -> int:
    """config/policies.yaml のポリシーを評価・表示する。"""
    if not POLICY_PATH.exists():
        print(c(f"[ERROR] policies.yaml が見つかりません: {POLICY_PATH}", RED))
        return 2

    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        raw_policies = yaml.safe_load(f) or {}
    policies = raw_policies.get("policies", [])

    # --list モード
    if getattr(args, "list", False):
        _AL_COLOR = {"execute": GREEN, "suggest": YELLOW, "read_only": DIM}
        print(c(f"\n  {'Name':<34} {'Trigger':<20} {'Action':<10} {'Autonomy':<12} En", BOLD))
        print("  " + "─" * 84)
        for p in policies:
            en     = c("✓", GREEN) if p.get("enabled") else c("✗", DIM)
            al     = p.get("autonomy_level", "—")
            al_fmt = c(f"{al:<12}", _AL_COLOR.get(al, RESET))
            tr     = f"tier≥{p['tier_restriction']}" if "tier_restriction" in p else "—"
            print(
                f"  {p['name']:<34} {p.get('trigger',''):<20} {p.get('action',''):<10}"
                f" {al_fmt} {en}  [{tr}]"
            )
            print(f"    {c(p.get('description',''), DIM)}")
        print()
        return 0

    # --check モード（デフォルト）: ポリシーを評価してアクションを実行
    services   = load_ledger()
    settings   = load_settings()
    events_log = read_events(n=500)
    now_ts     = datetime.datetime.now()
    fired:   list[str] = []
    blocked: list[str] = []
    pending: list[str] = []

    # ── ヘルパー ──────────────────────────────────────────────────────────
    def _parse_ts(t_str: str) -> datetime.datetime:
        try:
            return datetime.datetime.fromisoformat(t_str)
        except (ValueError, TypeError):
            return datetime.datetime(2000, 1, 1)

    def _in_cooldown(p_name: str, cooldown_minutes: int) -> bool:
        if cooldown_minutes <= 0:
            return False
        cutoff = now_ts - datetime.timedelta(minutes=cooldown_minutes)
        return any(
            e.get("event") == "policy"
            and f"policy:{p_name}" in e.get("detail", "")
            and _parse_ts(e.get("time", "")) >= cutoff
            for e in events_log
        )

    def _get_tier(svc_name: str) -> int:
        return services.get(svc_name, {}).get("tier", 99)

    def _do_notify(p_name: str, trigger: str, target: str, ev: dict) -> None:
        msg = f"[Policy: {p_name}] {trigger} 検出: {target} — {ev.get('detail', '')}"
        print(c(f"\n[POLICY] {p_name} → NOTIFY: {msg}", MAGENTA))
        _emit("policy", service=target,
              detail=f"notify by policy:{p_name}", source="manaosctl")
        notified = False
        # 1st: slack_integration サービス経由
        try:
            payload = json.dumps({"text": msg}, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:5590/notify", data=payload,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=3):
                pass
            notified = True
        except Exception:
            pass
        # 2nd: MANAOS_SLACK_WEBHOOK 環境変数 or settings.yaml から直接 POST（フォールバック）
        if not notified:
            webhook_url = (os.environ.get("MANAOS_SLACK_WEBHOOK")
                           or settings.get("notifications", {}).get("slack_webhook_url", ""))
            if webhook_url:
                try:
                    payload = json.dumps({"text": msg}, ensure_ascii=False).encode("utf-8")
                    req = urllib.request.Request(
                        webhook_url, data=payload,
                        headers={"Content-Type": "application/json"}, method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=5):
                        pass
                    notified = True
                    print(c("  → Slack webhook (直接) 送信完了", DIM))
                except Exception as e:
                    print(c(f"  → Slack webhook 失敗: {e}", DIM))
        if not notified:
            print(c("  → 通知先なし (slack_integration DOWN / MANAOS_SLACK_WEBHOOK 未設定)", DIM))
        fired.append(f"{p_name}→notify:{target}")

    # ── ポリシーループ ────────────────────────────────────────────────────
    for p in policies:
        if not p.get("enabled", True):
            continue

        p_name    = p["name"]
        trigger   = p.get("trigger", "")
        cond      = p.get("condition", {})
        action    = p.get("action", "")
        al        = p.get("autonomy_level", "execute")   # フィールドなし→execute
        t_restr   = p.get("tier_restriction", 0)         # フィールドなし→全Tier許可
        within    = cond.get("within_minutes", 60)
        cooldown  = p.get("cooldown_minutes", 0)
        threshold = cond.get("count_threshold", 1)
        cutoff    = now_ts - datetime.timedelta(minutes=within)

        # クールダウン中はスキップ
        if _in_cooldown(p_name, cooldown):
            continue

        # trigger にマッチするイベントを within_minutes 以内で取得
        matched = [
            e for e in events_log
            if e.get("event") == trigger
            and _parse_ts(e.get("time", "")) >= cutoff
        ]
        if not matched:
            continue

        # ── 追加フィルタ ─────────────────────────────────────────────────
        if "cost_risk" in cond:
            r = cond["cost_risk"]
            matched = [e for e in matched
                       if services.get(e.get("service", ""), {}).get("cost_risk") == r]
        if "tier" in cond:
            req_t = int(cond["tier"])
            matched = [e for e in matched if _get_tier(e.get("service", "")) == req_t]
        if not matched:
            continue

        # count_threshold チェック
        if len(matched) < threshold:
            continue

        # ── アクション（autonomy_level ガード付き）────────────────────────
        # block: autonomy_level に関わらず常に記録
        if action == "block":
            ev     = matched[0]
            target = ev.get("service", "") or p.get("target", "")
            print(c(f"\n[POLICY] {p_name} → BLOCKED: {target} ({trigger})", RED))
            _emit("policy", service=target,
                  detail=f"blocked by policy:{p_name}", source="manaosctl")
            blocked.append(f"{p_name}→block:{target}")
            continue

        # notify: read_only でも実行（情報通知は常に許可）
        if action == "notify":
            ev     = matched[0]
            target = ev.get("service", "") or p.get("target", "")
            _do_notify(p_name, trigger, target, ev)
            continue

        # stop / heal / analyze: autonomy_level でガード
        if al == "read_only":
            print(c(f"\n[POLICY] {p_name} → SKIP (read_only): {action} は手動実行のみ", DIM))
            blocked.append(f"{p_name}→skip(read_only):{action}")
            continue

        if al == "suggest":
            ev     = matched[0]
            target = ev.get("service", "") or p.get("target", "")
            print(c(f"\n[POLICY] {p_name} → SUGGEST (未実行・要承認): {action} {target}", YELLOW))
            print(c(f"  実行するには: manaosctl {action} {target}", DIM))
            _emit("policy", service=target,
                  detail=f"suggest by policy:{p_name}", source="manaosctl")
            pending.append(f"{p_name}→suggest:{action}:{target}")
            continue

        # al == "execute" ── 自動実行 ─────────────────────────────────────
        ev       = matched[0]
        target   = ev.get("service", "") or p.get("target", "")
        svc_tier = _get_tier(target)

        # tier_restriction: svc_tier < t_restr の場合は自動実行しない
        if svc_tier < t_restr:
            print(c(f"\n[POLICY] {p_name} → SKIP (tier_restriction={t_restr}): "
                    f"{target}(tier={svc_tier}) — 手動確認が必要", YELLOW))
            pending.append(f"{p_name}→skip(tier<{t_restr}):{target}")
            continue

        if action == "stop" and target and target in services:
            if is_alive(services[target]):
                print(c(f"\n[POLICY] {p_name} → STOP {target}", MAGENTA))
                stop_one(services[target])
                _emit("policy", service=target,
                      detail=f"auto-stop by policy:{p_name}", source="manaosctl")
                fired.append(f"{p_name}→stop:{target}")

        elif action == "heal" and target:
            print(c(f"\n[POLICY] {p_name} → HEAL {target}", MAGENTA))
            heal_script = TOOLS_DIR / "heal.py"
            subprocess.Popen(
                [PYTHON_EXE, str(heal_script), "--service", target],
                cwd=str(REPO_ROOT),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            _emit("policy", service=target,
                  detail=f"auto-heal by policy:{p_name}", source="manaosctl")
            fired.append(f"{p_name}→heal:{target}")

        elif action == "analyze":
            print(c(f"\n[POLICY] {p_name} → ANALYZE (LLM自動分析)", MAGENTA))
            subprocess.Popen(
                [PYTHON_EXE, __file__, "analyze"],
                cwd=str(REPO_ROOT),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            _emit("policy", detail=f"auto-analyze by policy:{p_name}", source="manaosctl")
            fired.append(f"{p_name}→analyze")

    # ── サマリー ──────────────────────────────────────────────────────────
    print()
    if fired:
        print(c(f"[POLICY] 実行済み:   {fired}", GREEN))
    if pending:
        print(c(f"[POLICY] 承認待ち:   {pending}", YELLOW))
    if blocked:
        print(c(f"[POLICY] スキップ:   {blocked}", DIM))
    if not fired and not pending and not blocked:
        print(c("[POLICY] 発火条件に該当するポリシーはなし", DIM))

    if getattr(args, "json", False):
        print(json.dumps(
            {"fired": fired, "pending": pending, "blocked": blocked},
            ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """定期的に status + policy チェックを繰り返す監視ループ。"""
    settings     = load_settings()
    watch_cfg    = settings.get("watch", {})
    _raw_interval = getattr(args, "interval", None)
    interval     = (_raw_interval if _raw_interval is not None
                    else watch_cfg.get("default_interval", 60))
    once         = getattr(args, "once", False)
    use_policy   = getattr(args, "policy", False) or watch_cfg.get("policy_on_down", False)

    print(c(f"\n  ManaOS Watch  (interval={interval}s, Ctrl+C で停止)", BOLD + CYAN))
    print(c("  " + "─" * 50, DIM))

    prev_status: Dict[str, str] = {}

    try:
        while True:
            now      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            services = load_ledger()

            # ── ステータス収集 ──────────────────────────────────────────
            cur_status: Dict[str, str] = {}
            for name, svc in services.items():
                if not svc.get("enabled", False):
                    cur_status[name] = "DISABLED"
                else:
                    cur_status[name] = "UP" if is_alive(svc) else "DOWN"

            # ── 変化検出 ────────────────────────────────────────────────
            changes: List[str] = []
            for name, st in cur_status.items():
                prev = prev_status.get(name)
                if prev and prev != st:
                    col = GREEN if st == "UP" else (RED if st == "DOWN" else DIM)
                    changes.append(c(f"{name}: {prev} → {st}", col))
                    _emit(f"service_{st.lower()}", service=name,
                          detail=f"watch detected: {prev}→{st}",
                          source="manaosctl-watch")

            up_cnt   = sum(1 for s in cur_status.values() if s == "UP")
            down_cnt = sum(1 for s in cur_status.values() if s == "DOWN")

            up_str   = c(f"UP:{up_cnt}", GREEN)
            down_str = c(f"DOWN:{down_cnt}", RED if down_cnt else DIM)
            print(c(f"\n[{now}]", DIM) + f"  {up_str}  {down_str}", end="")

            if changes:
                print(c("  ⚠ 変化検出!", YELLOW))
                for ch in changes:
                    print(f"    {ch}")
                if use_policy:
                    newly_down = [n for n, s in cur_status.items()
                                  if s == "DOWN" and prev_status.get(n) in ("UP", None)]
                    if newly_down:
                        print(c(f"  → policy --check 自動実行 (新規DOWN: {newly_down})", MAGENTA))
                        subprocess.run(
                            [PYTHON_EXE, __file__, "policy", "--check"],
                            cwd=str(REPO_ROOT),
                        )
            else:
                print(c("  変化なし", DIM))

            if down_cnt:
                down_names = [n for n, s in cur_status.items() if s == "DOWN"]
                print(c(f"  DOWN: {down_names}", RED))

            prev_status = cur_status

            if once:
                break
            time.sleep(interval)

    except KeyboardInterrupt:
        print(c("\n\n  Watch 停止。", DIM))

    return 0


def cmd_tier(args: argparse.Namespace) -> int:
    """Tier 別サービス一覧を表示する（OS 層マップ）。"""
    services = load_ledger()
    tier_map: dict[int, list[str]] = {}
    for name, svc in services.items():
        t = svc.get("tier", 99)
        tier_map.setdefault(t, []).append(name)

    tier_labels = {
        0: ("Tier 0  — コアインフラ（落ちたら全滅）", RED),
        1: ("Tier 1  — 主要機能（なるべく常時 UP）", YELLOW),
        2: ("Tier 2  — オプション（必要な時だけ）", DIM),
    }

    if getattr(args, "json", False):
        out: dict[str, list[dict]] = {}
        for tier_num in sorted(tier_map):
            out[str(tier_num)] = [
                {
                    "name": n,
                    "port": services[n].get("port"),
                    "enabled": services[n].get("enabled", True),
                    "status": "UP" if is_alive(services[n], timeout=1.5) else "DOWN",
                }
                for n in sorted(tier_map[tier_num])
            ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print()
    for tier_num in sorted(tier_map):
        label, color = tier_labels.get(tier_num, (f"Tier {tier_num}", DIM))
        print(c(f"\n  {label}", color + BOLD if color != DIM else BOLD))
        print(c("  " + "─" * 60, DIM))
        for name in sorted(tier_map[tier_num]):
            svc = services[name]
            port = svc.get("port", "—")
            enabled = svc.get("enabled", True)
            if not enabled:
                status_str = c("DISABLED", DIM)
            elif is_alive(svc, timeout=1.5):
                status_str = c("UP", GREEN)
            else:
                status_str = c("DOWN", RED)
            deps = ", ".join(svc.get("depends_on") or []) or "─"
            print(f"    {status_str}  {name:<25} :{str(port):<7} deps: {c(deps, DIM)}")
    print()
    print(c("  ヒント: manaosctl status --json / manaosctl deps --order", DIM))
    print()
    return 0


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

    # shell
    sub.add_parser("shell", help="ManaOS Shell ブラウザ UI を開く (http://127.0.0.1:9502/shell)")

    # deps
    p_deps = sub.add_parser("deps", help="依存ツリー可視化・起動順序表示")
    p_deps.add_argument("service", nargs="?", help="詳細表示するサービス名")
    p_deps.add_argument("--order", action="store_true", help="起動順序リスト表示")
    p_deps.add_argument("--tree",  action="store_true", help="ASCII blast-radius ツリー表示")
    p_deps.add_argument("--json",  action="store_true")

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

    # policy
    p_policy = sub.add_parser("policy", help="ポリシーを評価・一覧表示")
    p_policy.add_argument("--list",  action="store_true", help="ポリシー一覧表示のみ")
    p_policy.add_argument("--check", action="store_true", help="ポリシーを評価してアクション実行（デフォルト）")
    p_policy.add_argument("--json",  action="store_true")

    # tier
    p_tier = sub.add_parser("tier", help="Tier 別サービス一覧（OS 層マップ）")
    p_tier.add_argument("--json", action="store_true")

    # watch
    p_watch = sub.add_parser("watch", help="定期監視ループ（status + policy）")
    p_watch.add_argument("--interval", type=int, default=None,
                         help="チェック間隔秒（省略時は settings.yaml の値または 60）")
    p_watch.add_argument("--once",   action="store_true", help="1回だけ実行して終了")
    p_watch.add_argument("--policy", action="store_true",
                         help="DOWN検出時に policy --check を自動実行")

    args = parser.parse_args()

    dispatch = {
        "status":    cmd_status,
        "up":        cmd_up,
        "restart":   cmd_restart,
        "heal":      cmd_heal,
        "report":    cmd_report,
        "cost":      cmd_cost,
        "dashboard": cmd_dashboard,
        "shell":     cmd_shell,
        "deps":      cmd_deps,
        "events":    cmd_events,
        "analyze":   cmd_analyze,
        "policy":    cmd_policy,
        "tier":      cmd_tier,
        "watch":     cmd_watch,
    }
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
