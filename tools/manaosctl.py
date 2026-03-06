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
  python tools/manaosctl.py watch --log logs/watch.log  # ローリングログ追記

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
from collections import deque
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
# 通知ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def send_notify(title: str, message: str, priority: str = "default") -> str:
    """Slack → ntfy.sh 自動フォールバック通知。
    戻り値: 'slack' | 'ntfy' | 'failed'
    """
    import json as _json

    # ── Slack 試行 ───────────────────────────────────────────────────────────
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("SLACK_WEBHOOK_URL="):
                    webhook_url = line.split("=", 1)[1].strip()
                    break

    if webhook_url:
        try:
            body = _json.dumps({"text": f"*[{title}]* {message}"}).encode("utf-8")
            req = urllib.request.Request(
                webhook_url, data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status < 300:
                    return "slack"
        except Exception:
            pass  # ntfy へフォールバック

    # ── ntfy.sh フォールバック ────────────────────────────────────────────────
    topic = os.environ.get("NTFY_TOPIC", "manaos-default")
    url   = f"https://ntfy.sh/{topic}"
    try:
        body_bytes = message.encode("utf-8")
        # ntfy の Title ヘッダーは ASCII のみ受け付ける
        ascii_title = title.encode("ascii", errors="replace").decode("ascii")
        req = urllib.request.Request(
            url, data=body_bytes,
            headers={
                "Title":        ascii_title,
                "Priority":     priority,
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status < 300:
                return "ntfy"
    except Exception:
        pass

    return "failed"


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
    n         = getattr(args, "n", 50)
    filt      = getattr(args, "filter", None)
    since_min = getattr(args, "since", None)
    events    = read_events(n=max(n * 3, 200))  # 多めに読んでフィルタ後に残す

    if filt:
        events = [e for e in events if filt in e.get("event", "") or filt in e.get("service", "")]
    if since_min is not None:
        cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=since_min)).isoformat()[:19]
        events = [e for e in events if e.get("time", "")[:19] >= cutoff]
    events = events[-n:]

    if getattr(args, "json", False):
        print(json.dumps(events, ensure_ascii=False, indent=2))
        return 0

    if not events:
        print(c("  (イベントなし — logs/events.jsonl がまだ空です)", DIM))
        return 0

    hparts = [f"{len(events)}件"]
    if filt:      hparts.append(f"filter={filt}")
    if since_min: hparts.append(f"since={since_min}m")
    print(c(f"\n[Events  {'  '.join(hparts)}]", BOLD + CYAN))

    # 表示
    EVLEN = 16
    print(c(f"{'Time':<20} {'Event':<{EVLEN}} {'Service':<24} Detail", BOLD))
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
    use_notify   = getattr(args, "notify", False)
    log_path_str = getattr(args, "log", None)
    log_file     = open(log_path_str, "a", encoding="utf-8") if log_path_str else None

    def _log(line: str) -> None:
        """コンソールとオプションのログファイルに同時出力。"""
        print(line)
        if log_file:
            import re as _re
            log_file.write(_re.sub(r"\x1b\[[0-9;]*m", "", line) + "\n")
            log_file.flush()

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
            up_cnt   = sum(1 for s in cur_status.values() if s == "UP")
            down_cnt = sum(1 for s in cur_status.values() if s == "DOWN")
            changes: List[str] = []
            for name, st in cur_status.items():
                prev = prev_status.get(name)
                if prev and prev != st:
                    col = GREEN if st == "UP" else (RED if st == "DOWN" else DIM)
                    changes.append(c(f"{name}: {prev} → {st}", col))
                    _emit(f"service_{st.lower()}", service=name,
                          detail=f"watch detected: {prev}→{st}",
                          source="manaosctl-watch")

            up_str   = c(f"UP:{up_cnt}", GREEN)
            down_str = c(f"DOWN:{down_cnt}", RED if down_cnt else DIM)
            _log(c(f"\n[{now}]", DIM) + f"  {up_str}  {down_str}")

            if changes:
                _log(c("  ⚠ 変化検出!", YELLOW))
                for ch in changes:
                    _log(f"    {ch}")
                newly_down = [n for n, s in cur_status.items()
                              if s == "DOWN" and prev_status.get(n) in ("UP", None)]
                if use_policy:
                    if newly_down:
                        _log(c(f"  → policy --check 自動実行 (新規DOWN: {newly_down})", MAGENTA))
                        subprocess.run(
                            [PYTHON_EXE, __file__, "policy", "--check"],
                            cwd=str(REPO_ROOT),
                        )
                if use_notify and newly_down:
                    names_str = ", ".join(newly_down)
                    result = send_notify(
                        title="ManaOS DOWN Alert",
                        message=f"DOWN detected: {names_str} ({now})",
                        priority="high",
                    )
                    _log(c(f"  → ntfy 通知送信: {result} ({names_str})", MAGENTA))
            else:
                _log(c("  変化なし", DIM))

            if down_cnt:
                down_names = [n for n, s in cur_status.items() if s == "DOWN"]
                _log(c(f"  DOWN: {down_names}", RED))

            prev_status = cur_status

            if once:
                break
            time.sleep(interval)

    except KeyboardInterrupt:
        _log(c("\n\n  Watch 停止。", DIM))
    finally:
        if log_file:
            log_file.close()

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


# ── GTD ───────────────────────────────────────────────────────────────────────
def cmd_gtd(args: argparse.Namespace) -> int:
    """GTD 操作: morning / capture / inbox / status"""
    import re as _re

    subcmd = getattr(args, "subcmd", None) or "status"

    GTD_ROOT  = REPO_ROOT / "gtd"
    GTD_INBOX = GTD_ROOT / "inbox"
    GTD_NA    = GTD_ROOT / "next-actions" / "items"
    GTD_LOGS  = GTD_ROOT / "daily-logs"

    def _inbox_count() -> int:
        return len([f for f in GTD_INBOX.glob("*.md") if f.name.upper() != "README.MD"])

    def _na_count() -> int:
        return len([f for f in GTD_NA.glob("*.md") if f.name.upper() != "README.MD"])

    if subcmd == "morning":
        today   = datetime.datetime.now().strftime("%Y-%m-%d")
        log     = GTD_LOGS / f"{today}.md"
        inbox_n = _inbox_count()
        na_items = sorted([f for f in GTD_NA.glob("*.md") if f.name.upper() != "README.MD"])
        na_lines = "\n".join(f"  - {f.stem}" for f in na_items) or "  （Next Actions なし）"

        if not log.exists():
            GTD_LOGS.mkdir(parents=True, exist_ok=True)
            log.write_text(
                f"# {today} 日次ログ\n\n"
                f"## 今日の3大優先事項\n1. \n2. \n3. \n\n"
                f"## 今日のNext Actions候補\n{na_lines}\n\n"
                f"## Inbox状況\n  件数: {inbox_n} 件\n\n"
                f"## 完了タスク\n- \n\n"
                f"## 気づき・メモ\n- \n\n"
                f"## 明日への申し送り\n- \n",
                encoding="utf-8",
            )
            print(c(f"✅ 日次ログ作成: {log}", GREEN))
        else:
            print(c(f"  📄 今日のログ: {log}", DIM))

        print()
        print(log.read_text(encoding="utf-8"))
        print(c(f"  📥 Inbox: {inbox_n} 件  |  ✅ Next Actions: {_na_count()} 件", CYAN))
        return 0

    elif subcmd == "capture":
        text_parts = getattr(args, "text", []) or []
        text = " ".join(text_parts).strip()
        if not text:
            print(c("[ERROR] テキストを指定してください: manaosctl gtd capture <text>", RED), file=sys.stderr)
            return 1
        context_tag = getattr(args, "context", None) or ""
        due_date    = getattr(args, "due",     None) or ""
        now  = datetime.datetime.now()
        slug = _re.sub(r"[^\w\s]", "", text)[:25].strip().replace(" ", "_")
        fname = f"{now.strftime('%Y%m%d_%H%M')}_CLI_{slug}.md"
        GTD_INBOX.mkdir(parents=True, exist_ok=True)
        path  = GTD_INBOX / fname
        meta_lines = [
            f"- キャプチャ日時: {now.strftime('%Y-%m-%d %H:%M')}",
            f"- ソース: manaosctl",
        ]
        if context_tag:
            meta_lines.append(f"- context: {context_tag}")
        if due_date:
            meta_lines.append(f"- due: {due_date}")
        path.write_text(
            f"# {text}\n\n" + "\n".join(meta_lines) + f"\n\n## 内容\n{text}\n",
            encoding="utf-8",
        )
        count = _inbox_count()
        extras = ""
        if context_tag: extras += f"  [{context_tag}]"
        if due_date:    extras += f"  due:{due_date}"
        print(c(f"✅ Inbox 保存: {fname}{extras}  (残 {count} 件)", GREEN))
        return 0

    elif subcmd == "inbox":
        items = sorted(
            [f for f in GTD_INBOX.glob("*.md") if f.name.upper() != "README.MD"],
            reverse=True,
        )
        use_json = getattr(args, "json", False)
        if use_json:
            print(json.dumps([f.stem for f in items], ensure_ascii=False, indent=2))
            return 0
        print()
        print(c(f"  [GTD Inbox  {len(items)} 件]", BOLD + CYAN))
        print(c("  " + "─" * 50, DIM))
        for i, f in enumerate(items[:30]):
            print(f"    [{i+1}] {f.stem}")
        if len(items) > 30:
            print(c(f"    ... 他 {len(items) - 30} 件", DIM))
        print()
        return 0

    elif subcmd == "next":
        items = sorted(
            [f for f in GTD_NA.glob("*.md") if f.name.upper() != "README.MD"]
        )
        projects_dir = GTD_ROOT / "projects" / "items"
        proj_items: list[Path] = []
        if projects_dir.exists():
            proj_items = sorted([f for f in projects_dir.rglob("*.md") if f.name.upper() != "README.MD"])
        use_json = getattr(args, "json", False)

        # 各 Next Action ファイルから context / due を抽出
        def _parse_na(f: Path) -> dict:
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                txt = ""
            ctx  = ""
            due  = ""
            for line in txt.splitlines():
                if line.startswith("- context:"):
                    ctx = line.split(":", 1)[1].strip()
                elif line.startswith("- due:"):
                    due = line.split(":", 1)[1].strip()
            return {"name": f.stem, "context": ctx, "due": due}

        na_data = [_parse_na(f) for f in items]
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # フィルター
        filter_ctx   = getattr(args, "filter",    None)
        only_today   = getattr(args, "due_today", False)
        only_overdue = getattr(args, "overdue",   False)
        if filter_ctx:
            fk = filter_ctx.lstrip("@").lower()
            na_data = [nd for nd in na_data if fk in nd["context"].lstrip("@").lower()]
        if only_today:
            na_data = [nd for nd in na_data if nd["due"] == today_str]
        if only_overdue:
            na_data = [nd for nd in na_data if nd["due"] and nd["due"] < today_str]

        if use_json:
            print(json.dumps({
                "next_actions": na_data,
                "projects":     [str(f.relative_to(REPO_ROOT)) for f in proj_items],
            }, ensure_ascii=False, indent=2))
            return 0
        print()
        print(c(f"  [Next Actions  {len(na_data)} 件{' (filtered)' if filter_ctx or only_today or only_overdue else ''}]", BOLD + GREEN))
        print(c("  " + "─" * 50, DIM))
        if na_data:
            for nd in na_data:
                line = f"    ✅ {nd['name']}"
                extras = []
                if nd["context"]:
                    extras.append(c(nd["context"], CYAN))
                if nd["due"]:
                    overdue = nd["due"] < today_str
                    due_str = c(f"due:{nd['due']}", RED if overdue else YELLOW)
                    if overdue:
                        due_str += c(" [期限超過]", RED + BOLD)
                    extras.append(due_str)
                if extras:
                    line += "  " + "  ".join(extras)
                print(line)
        else:
            print(c("    （なし）", DIM))
        if proj_items:
            print()
            print(c(f"  [Projects  {len(proj_items)} ファイル]", BOLD + YELLOW))
            print(c("  " + "─" * 50, DIM))
            for f in proj_items:
                print(f"    📁 {f.relative_to(GTD_ROOT / 'projects')}")
        print()
        return 0

    elif subcmd == "process":
        # Inbox の各アイテムを next-actions / projects / someday / waiting / done に振り分ける
        import shutil as _shutil
        DEST_MAP = {
            "n": GTD_NA,
            "next": GTD_NA,
            "p": GTD_ROOT / "projects" / "items",
            "project": GTD_ROOT / "projects" / "items",
            "s": GTD_ROOT / "someday",
            "someday": GTD_ROOT / "someday",
            "w": GTD_ROOT / "waiting",
            "waiting": GTD_ROOT / "waiting",
            "d": GTD_ROOT / "archive" / "done",
            "done": GTD_ROOT / "archive" / "done",
            "x": None,  # skip / delete
        }
        LABEL_MAP = {
            "n": c("Next Actions", GREEN),
            "p": c("Projects",    YELLOW),
            "s": c("Someday",     DIM),
            "w": c("Waiting",     CYAN),
            "d": c("Done/Archive", MAGENTA),
            "x": c("Skip",        DIM),
        }
        target_arg = getattr(args, "target", None)
        dest_flag  = getattr(args, "to",     None)

        items = sorted(
            [f for f in GTD_INBOX.glob("*.md") if f.name.upper() != "README.MD"]
        )
        if not items:
            print(c("  Inbox は空です。", DIM))
            return 0

        # --target + --to でバッチ移動
        if target_arg and dest_flag:
            dest_key = dest_flag.lower()
            if dest_key not in DEST_MAP:
                print(c(f"[ERROR] --to に指定できる値: next / projects / someday / waiting / done", RED), file=sys.stderr)
                return 1
            matched = [f for f in items if target_arg.lower() in f.stem.lower()]
            if not matched:
                print(c(f"  '{target_arg}' に一致する Inbox アイテムが見つかりません", YELLOW))
                return 1
            for f in matched:
                dest_dir = DEST_MAP.get(dest_key.rstrip("s"), DEST_MAP.get(dest_key))
                dest_dir.mkdir(parents=True, exist_ok=True)
                _shutil.move(str(f), str(dest_dir / f.name))
                print(c(f"  ✅ {f.name}  →  {dest_dir.name}/", GREEN))
            print(c(f"  {len(matched)} 件処理完了", CYAN))
            return 0

        # インタラクティブモード
        print()
        print(c(f"  [GTD Process  Inbox {len(items)} 件]", BOLD + CYAN))
        print(c("  n=Next  p=Project  s=Someday  w=Waiting  d=Done  x=Skip  q=終了", DIM))
        print(c("  " + "─" * 60, DIM))
        moved = 0
        for f in items:
            print(f"\n  📥 {c(f.stem, BOLD)}")
            # ファイルの1行目（タイトル）を表示
            try:
                first_line = f.read_text(encoding="utf-8", errors="replace").splitlines()[0].lstrip("# ").strip()
                if first_line != f.stem:
                    print(c(f"     {first_line}", DIM))
            except Exception:
                pass
            choice = input("  → ").strip().lower()
            if choice == "q":
                print(c("  中断しました", DIM))
                break
            if choice == "x" or not choice:
                print(c("   Skip", DIM))
                continue
            dest_key = {"next": "n", "project": "p", "projects": "p",
                        "someday": "s", "waiting": "w", "done": "d"}.get(choice, choice)
            short = dest_key.rstrip("s")
            dest_dir = DEST_MAP.get(short) or DEST_MAP.get(dest_key)
            if dest_dir is None:
                print(c("   不明な選択、スキップ", YELLOW))
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            _shutil.move(str(f), str(dest_dir / f.name))
            moved += 1
            label = LABEL_MAP.get(short, dest_key)
            print(c(f"   → {label} に移動", GREEN))
        print()
        print(c(f"  {moved} 件処理  |  残 Inbox: {_inbox_count()} 件", CYAN))
        return 0

    elif subcmd == "weekly":
        # 週次レビュー: 先週のログ + 今週の傾向 + Inbox状況
        today   = datetime.datetime.now()
        use_json = getattr(args, "json", False)
        logs    = sorted([f for f in GTD_LOGS.glob("[0-9][0-9][0-9][0-9]-*.md")], reverse=True)
        week_logs = [f for f in logs if f.name >= (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")]
        inbox_n = _inbox_count()
        na_n    = _na_count()
        # Inbox件数推移（直近7日分のログからInbox件数を読む）
        trend   = []
        for wl in reversed(week_logs):
            try:
                txt = wl.read_text(encoding="utf-8", errors="replace")
                for line in txt.splitlines():
                    if "件数:" in line and "件" in line:
                        import re as _re2
                        m = _re2.search(r"(\d+)\s*件", line)
                        if m:
                            trend.append({"date": wl.stem, "inbox": int(m.group(1))})
                        break
            except Exception:
                pass
        if use_json:
            print(json.dumps({
                "week_logs":      [f.stem for f in week_logs],
                "inbox_now":      inbox_n,
                "next_actions":   na_n,
                "inbox_trend":    trend,
            }, ensure_ascii=False, indent=2))
            return 0
        print()
        print(c(f"  [GTD Weekly Review  {today.strftime('%Y-%m-%d')}]", BOLD + CYAN))
        print(c("  " + "─" * 60, DIM))
        print(f"  📄 先週のログ: {len(week_logs)} 日分  （{', '.join(f.stem for f in week_logs[:5])} ...）")
        print(f"  📥 現在のInbox: {inbox_n} 件")
        print(f"  ✅ Next Actions: {na_n} 件")
        if trend:
            print()
            print(c("  Inbox 推移 (直近ログより)", DIM))
            for t in trend:
                bar = "█" * min(t["inbox"], 20)
                print(f"    {t['date']}  {bar}  {t['inbox']}件")
        print()
        print(c("  ヒント: manaosctl gtd process  → Inbox を振り分けて Next Actions を作る", DIM))
        return 0

    elif subcmd == "do":
        # 「今これをやる」宣言: Next Actions から選択→ログ記録→通知→タイマー
        na_items  = sorted(
            [f for f in GTD_NA.glob("*.md") if f.name.upper() != "README.MD"]
        )
        task_name = getattr(args, "name",  None)
        task_idx  = getattr(args, "index", None)
        timer_min = getattr(args, "timer", 0)

        # ── タスク選択 ────────────────────────────────────────────────────────
        if task_name is None and task_idx is None:
            if not na_items:
                print(c("  Next Actions にアイテムがありません。", DIM))
                print(c("  先に: manaosctl gtd process  (Inbox から振り分け)", DIM))
                return 0
            print()
            print(c("  [Next Actions  \u4eca\u4f55\u3092\u3084\u308b\uff1f]", BOLD + GREEN))
            print(c("  " + "\u2500" * 45, DIM))
            for i, f in enumerate(na_items, 1):
                nd = {"name": f.stem}
                print(f"    [{i}] {nd['name']}")
            print()
            try:
                ans = input("  \u756a\u53f7\u3092\u5165\u529b (0=\u30ad\u30e3\u30f3\u30bb\u30eb): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if ans == "0" or ans == "":
                return 0
            try:
                idx = int(ans) - 1
                task_name = na_items[idx].stem
            except (ValueError, IndexError):
                print(c(f"  [ERROR] \u7121\u52b9\u306a\u756a\u53f7: {ans}", RED))
                return 1
        elif task_idx is not None:
            idx = task_idx - 1
            if idx < 0 or idx >= len(na_items):
                print(c(f"  [ERROR] \u30a4\u30f3\u30c7\u30c3\u30af\u30b9 {task_idx} \u306f\u7bc4\u56f2\u5916\uff081\uff5e{len(na_items)}\uff09", RED))
                return 1
            task_name = na_items[idx].stem
        # --name で直接指定の場合はそのまま

        # ── 日次ログに記録 ────────────────────────────────────────────────────
        now_dt  = datetime.datetime.now()
        now_str = now_dt.strftime("%H:%M")
        today   = now_dt.strftime("%Y-%m-%d")
        log_file_path = GTD_LOGS / f"{today}.md"
        if log_file_path.exists():
            txt = log_file_path.read_text(encoding="utf-8")
            if "\n## \u4f5c\u696d\u30ed\u30b0\n" not in txt:
                txt = txt.rstrip("\n") + "\n\n## \u4f5c\u696d\u30ed\u30b0\n"
            txt += f"- {now_str} \u25b6\ufe0f \u4f5c\u696d\u958b\u59cb: {task_name}\n"
            log_file_path.write_text(txt, encoding="utf-8")
            print(c(f"  \ud83d\udcc4 \u65e5\u6b21\u30ed\u30b0\u306b\u8a18\u9332: {log_file_path.name}", DIM))

        # ── 通知 ──────────────────────────────────────────────────────────────
        notify_result = send_notify(
            title="GTD: \u4f5c\u696d\u958b\u59cb",
            message=f"\u25b6\ufe0f {task_name}",
            priority="default",
        )
        print()
        print(c(f"  \u25b6\ufe0f \u4f5c\u696d\u958b\u59cb: {task_name}", BOLD + GREEN))
        print(c(f"  {now_str} \uff5e  (\u901a\u77e5: {notify_result})", DIM))

        # ── タイマー登録 (Windows タスクスケジューラ) ─────────────────────────
        if timer_min > 0:
            import platform as _platform
            if _platform.system() == "Windows":
                try:
                    notify_dt   = now_dt + datetime.timedelta(minutes=timer_min)
                    task_tname  = f"GTD_DO_{now_dt.strftime('%Y%m%d%H%M%S')}"
                    notify_time = notify_dt.strftime("%H:%M")
                    py_exe  = sys.executable
                    ctl_py  = str(Path(__file__).resolve())
                    cmd_str = (
                        f'"{py_exe}" "{ctl_py}" notify '
                        f'--title "GTD\u78ba\u8a8d" '
                        f'--message "{timer_min}\u5206\u7d4c\u904e\u3002{task_name} \u306e\u9032\u6357\u306f\uff1f"'
                    )
                    res = subprocess.run(
                        [
                            "schtasks", "/create",
                            "/tn",  task_tname,
                            "/tr",  cmd_str,
                            "/sc",  "ONCE",
                            "/st",  notify_time,
                            "/f",
                        ],
                        capture_output=True, text=True,
                    )
                    if res.returncode == 0:
                        print(c(f"  \u23f1 {timer_min}\u5206\u5f8c\u30bf\u30a4\u30de\u30fc\u8a2d\u5b9a: {notify_time}", CYAN))
                    else:
                        print(c(f"  [WARN] \u30bf\u30a4\u30de\u30fc\u767b\u9332\u5931\u6557: {res.stderr.strip()}", YELLOW))
                except Exception as _e:
                    print(c(f"  [WARN] \u30bf\u30a4\u30de\u30fc\u4f8b\u5916: {_e}", YELLOW))
            else:
                print(c(f"  [INFO] \u30bf\u30a4\u30de\u30fc\u767b\u9332\u306fWindows\u306e\u307f\u5bfe\u5fdc", DIM))
        print()
        return 0

    elif subcmd == "done":
        # 「完了！」宣言: Next Action をアーカイブに移動 + 日次ログ記録 + 通知
        import shutil as _shutil2
        na_items = sorted(
            [f for f in GTD_NA.glob("*.md") if f.name.upper() != "README.MD"]
        )
        task_name = getattr(args, "name",  None)
        task_idx  = getattr(args, "index", None)

        # ── タスク選択 ────────────────────────────────────────────────────────
        if task_name is None and task_idx is None:
            if not na_items:
                print(c("  Next Actions にアイテムがありません。", DIM))
                return 0
            print()
            print(c("  [Next Actions  \u5b8c\u4e86\u3057\u305f\u30bf\u30b9\u30af\u306f\uff1f]", BOLD + GREEN))
            print(c("  " + "\u2500" * 45, DIM))
            for i, f in enumerate(na_items, 1):
                print(f"    [{i}] {f.stem}")
            print()
            try:
                ans = input("  \u756a\u53f7\u3092\u5165\u529b (0=\u30ad\u30e3\u30f3\u30bb\u30eb): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if ans == "0" or ans == "":
                return 0
            try:
                idx = int(ans) - 1
                src_file = na_items[idx]
            except (ValueError, IndexError):
                print(c(f"  [ERROR] \u7121\u52b9\u306a\u756a\u53f7: {ans}", RED))
                return 1
        elif task_idx is not None:
            idx = task_idx - 1
            if idx < 0 or idx >= len(na_items):
                print(c(f"  [ERROR] \u30a4\u30f3\u30c7\u30c3\u30af\u30b9 {task_idx} \u306f\u7bc4\u56f2\u5916\uff081\uff5e{len(na_items)}\uff09", RED))
                return 1
            src_file = na_items[idx]
        else:
            # --name: 部分一致で検索
            matched = [f for f in na_items if task_name.lower() in f.stem.lower()]
            if not matched:
                print(c(f"  [ERROR] \"{task_name}\" に一致する Next Action が見つかりません", RED))
                return 1
            src_file = matched[0]

        task_name = src_file.stem

        # ── アーカイブに移動 ──────────────────────────────────────────────────
        done_dir = GTD_ROOT / "archive" / "done"
        done_dir.mkdir(parents=True, exist_ok=True)
        now_dt  = datetime.datetime.now()
        today   = now_dt.strftime("%Y-%m-%d")
        now_str = now_dt.strftime("%H:%M")
        # 同名ファイルが既にある場合はタイムスタンプ付きで保存
        dst_name = f"{today}_{task_name}.md"
        dst_file = done_dir / dst_name
        if dst_file.exists():
            dst_file = done_dir / f"{today}_{now_dt.strftime('%H%M%S')}_{task_name}.md"
        _shutil2.move(str(src_file), str(dst_file))
        print(c(f"  \ud83d\udcc1 \u30a2\u30fc\u30ab\u30a4\u30d6\u306b\u79fb\u52d5: {dst_file.relative_to(GTD_ROOT)}", DIM))

        # ── 日次ログに記録 ────────────────────────────────────────────────────
        log_file_path = GTD_LOGS / f"{today}.md"
        if log_file_path.exists():
            txt = log_file_path.read_text(encoding="utf-8")
            if "\n## \u4f5c\u696d\u30ed\u30b0\n" not in txt:
                txt = txt.rstrip("\n") + "\n\n## \u4f5c\u696d\u30ed\u30b0\n"
            txt += f"- {now_str} \u2705 \u5b8c\u4e86: {task_name}\n"
            log_file_path.write_text(txt, encoding="utf-8")
            print(c(f"  \ud83d\udcc4 \u65e5\u6b21\u30ed\u30b0\u306b\u8a18\u9332: {log_file_path.name}", DIM))

        # ── 通知 ──────────────────────────────────────────────────────────────
        remaining = len([f for f in GTD_NA.glob("*.md") if f.name.upper() != "README.MD"])
        notify_result = send_notify(
            title="GTD: \u5b8c\u4e86\uff01",
            message=f"\u2705 {task_name}  (\u6b8b\u308a {remaining} \u4ef6)",
            priority="default",
        )
        print()
        print(c(f"  \u2705 \u5b8c\u4e86\uff01: {task_name}", BOLD + GREEN))
        print(c(f"  {now_str}  \u6b8b\u308a {remaining} \u4ef6  (\u901a\u77e5: {notify_result})", DIM))
        print()
        return 0

    elif subcmd == "commit":
        # GTD 変更を git にコミット（オプションで push も実行）
        do_push = getattr(args, "push", False)
        today   = datetime.datetime.now().strftime("%Y-%m-%d")
        res_add = subprocess.run(
            ["git", "add", "gtd/"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if res_add.returncode != 0:
            print(c(f"  [ERROR] git add: {res_add.stderr.strip()}", RED))
            return 1
        commit_msg = f"gtd(auto): {today} daily log + GTD update"
        res_commit = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if res_commit.returncode != 0:
            combined = res_commit.stdout + res_commit.stderr
            _no_change = ("nothing to commit", "Changes not staged", "no changes added")
            if any(x in combined for x in _no_change):
                print(c("  変更なし（コミット不要）", DIM))
                return 0
            print(c(f"  [ERROR] git commit: {res_commit.stderr.strip()}", RED))
            return 1
        print(c(f"  ✅ コミット: {commit_msg}", GREEN))
        if do_push:
            res_push = subprocess.run(
                ["git", "push", "origin", "master"],
                capture_output=True, text=True, cwd=str(REPO_ROOT)
            )
            if res_push.returncode == 0:
                print(c("  ✅ Push 完了", GREEN))
            else:
                print(c(f"  [ERROR] push: {res_push.stderr.strip()}", RED))
                return 1
        return 0

    else:  # status
        today     = datetime.datetime.now().strftime("%Y-%m-%d")
        inbox_n   = _inbox_count()
        na_n      = _na_count()
        log_exists = (GTD_LOGS / f"{today}.md").exists()
        use_json  = getattr(args, "json", False)
        if use_json:
            print(json.dumps({
                "date":            today,
                "inbox_count":     inbox_n,
                "next_actions":    na_n,
                "daily_log_today": log_exists,
            }, ensure_ascii=False, indent=2))
            return 0
        print()
        print(c(f"  [GTD Status  {today}]", BOLD + CYAN))
        print(c("  " + "─" * 40, DIM))
        print(f"  📥 Inbox:          {inbox_n} 件")
        print(f"  ✅ Next Actions:   {na_n} 件")
        print(f"  📄 今日の日次ログ: {'✓ あり' if log_exists else '✗ なし (manaosctl gtd morning で作成)'}")
        print()
        return 0


# ---------------------------------------------------------------------------
# Service → Log file mapping
# ---------------------------------------------------------------------------
_SERVICE_LOG_MAP: dict = {
    "ollama":              None,
    "llm_routing":         "logs/llm-router-enhanced.log",
    "memory":              "logs/memory_unified.log",
    "unified_api":         "logs/unified.log",
    "shell_ui":            "logs/unified.log",
    "autonomy":            "logs/autonomy_system.log",
    "secretary":           "logs/secretary-system.log",
    "learning":            "logs/learning_system.log",
    "personality":         "logs/personality_system.log",
    "intent_router":       "logs/intent_router.log",
    "task_queue":          "logs/task-queue-system.log",
    "trinity":             "logs/trinity_err.log",
    "pixel7_bridge":       "logs/pixel7_bridge_err.log",
    "slack_integration":   "logs/slack-integration.log",
    "gallery":             "logs/gallery_api.log",
    "step_deep_research":  None,
    "autostart":           "logs/autostart.log",
    "comfyui":             None,
    "video_pipeline":      None,
    "windows_automation":  None,
    "pico_hid":            None,
    "voicevox":            None,
    "n8n":                 None,
}


def _tail_file(path: Path, n: int) -> list:
    """ファイル末尾 n 行を返す。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return list(deque(f, maxlen=n))
    except Exception:
        return []


def cmd_logs(args: argparse.Namespace) -> int:
    """サービスのログファイル末尾 N 行を表示する。"""
    service = args.service
    n       = getattr(args, "n", 30)
    repo    = REPO_ROOT

    if service == "list":
        print(c("\n  サービス ログファイル一覧", BOLD + CYAN))
        for svc, log in sorted(_SERVICE_LOG_MAP.items()):
            mark = c("✓", GREEN) if log else c("—", DIM)
            desc = log if log else c("(ログファイル未設定)", DIM)
            print(f"    {mark}  {svc:<22} {desc}")
        print()
        return 0

    if service not in _SERVICE_LOG_MAP:
        print(c(f"\n  ⚠  サービス '{service}' はマップ未登録です。", YELLOW))
        print(c(f"     登録済みサービス: {', '.join(sorted(_SERVICE_LOG_MAP.keys()))}", DIM))
        print(c( "     'list' を指定すると一覧を表示します。", DIM))
        return 1

    log_rel = _SERVICE_LOG_MAP[service]
    if not log_rel:
        print(c(f"\n  —  {service}: ログファイル未設定（外部プロセスまたは未対応サービス）\n", DIM))
        return 0

    log_path = repo / log_rel
    if not log_path.exists():
        print(c(f"\n  ⚠  ログファイルが見つかりません: {log_path}\n", YELLOW))
        return 1

    total = sum(1 for _ in open(log_path, encoding="utf-8", errors="replace"))
    lines = _tail_file(log_path, n)
    print(c(f"\n  {service} ログ  (末尾 {len(lines)} 行 / 全 {total} 行)", BOLD + CYAN))
    print(c(f"  {log_path}", DIM))
    print(c("  " + "─" * 70, DIM))
    for line in lines:
        line = line.rstrip("\n")
        up = line.upper()
        if any(k in up for k in ("ERROR", "CRITICAL", "EXCEPTION", "TRACEBACK")):
            print(c(f"  {line}", RED))
        elif any(k in up for k in ("WARNING", "WARN")):
            print(c(f"  {line}", YELLOW))
        else:
            print(f"  {line}")
    print(c("  " + "─" * 70, DIM))
    print()
    return 0


def cmd_notify(args: argparse.Namespace) -> int:
    """Slack → ntfy.sh 自動フォールバック通知を送信する。"""
    title   = getattr(args, "title",    "ManaOS Notify")
    prio    = getattr(args, "priority", "default")
    message = " ".join(args.message) if isinstance(args.message, list) else args.message

    print(c(f"\n  ManaOS Notify  [{title}]", BOLD + CYAN))
    print(c(f"  {message}", DIM))
    result = send_notify(title=title, message=message, priority=prio)
    col = GREEN if result in ("slack", "ntfy") else RED
    print(c(f"\n  送信結果: {result}", col))
    return 0 if result != "failed" else 1


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
    p_events.add_argument("--since", type=int, default=None, help="最近N分以内のイベントのみ表示")
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
    p_watch.add_argument("--log",    type=str, default=None,
                         help="ANSI除去したログを追記するファイルパス")
    p_watch.add_argument("--notify", action="store_true",
                         help="サービスDOWN検出時に ntfy/Slack 通知を自動送信")

    # logs
    p_logs = sub.add_parser("logs", help="サービスのログ末尾 N 行を表示 (service=list で一覧)")
    p_logs.add_argument("service", help="サービス名 (例: llm_routing) または 'list'")
    p_logs.add_argument("-n", type=int, default=30, help="表示行数 (デフォルト: 30)")

    # notify
    p_notify = sub.add_parser("notify", help="ntfy.sh / Slack に通知を送信する")
    p_notify.add_argument("message", nargs="+", help="送信するメッセージ")
    p_notify.add_argument("--title",    type=str, default="ManaOS Notify", help="通知タイトル")
    p_notify.add_argument("--priority", type=str, default="default",
                          choices=["min", "low", "default", "high", "urgent"],
                          help="ntfy 優先度 (default: default)")

    # gtd
    p_gtd = sub.add_parser("gtd", help="GTD 操作 (morning / capture / inbox / next / process / weekly / status)")
    p_gtd_sub = p_gtd.add_subparsers(dest="subcmd")
    p_gtd_sub.add_parser("morning", help="今日の日次ログを表示（なければ作成）")
    p_gtd_capture = p_gtd_sub.add_parser("capture", help="Inbox にテキストを保存")
    p_gtd_capture.add_argument("text", nargs="+", help="保存するテキスト")
    p_gtd_capture.add_argument("--context", type=str, default=None, help="コンテキストタグ (e.g. @pc @phone @outside)")
    p_gtd_capture.add_argument("--due",     type=str, default=None, help="期限日 YYYY-MM-DD")
    p_gtd_inbox = p_gtd_sub.add_parser("inbox", help="Inbox 一覧表示")
    p_gtd_inbox.add_argument("--json", action="store_true")
    p_gtd_next = p_gtd_sub.add_parser("next", help="Next Actions 一覧表示")
    p_gtd_next.add_argument("--json",      action="store_true")
    p_gtd_next.add_argument("--filter",    type=str,  default=None, help="@context でフィルタ  例: --filter @pc")
    p_gtd_next.add_argument("--due-today", action="store_true", help="今日期限のアイテムのみ")
    p_gtd_next.add_argument("--overdue",   action="store_true", help="期限超過のみ")
    p_gtd_process = p_gtd_sub.add_parser("process", help="Inbox アイテムを振り分ける（インタラクティブ or バッチ）")
    p_gtd_process.add_argument("--target", type=str, default=None, help="対象ファイル名の一部文字列")
    p_gtd_process.add_argument("--to",     type=str, default=None, help="移動先: next/projects/someday/waiting/done")
    p_gtd_weekly = p_gtd_sub.add_parser("weekly", help="週次レビュー（先週ログ + Inbox推移）")
    p_gtd_weekly.add_argument("--json", action="store_true")
    p_gtd_do = p_gtd_sub.add_parser("do", help="\u300c\u4eca\u3053\u308c\u3092\u3084\u308b\u300d\u5ba3\u8a00: Next Action \u64cd\u4f5c\u958b\u59cb + \u30ed\u30b0\u8a18\u9332 + \u901a\u77e5")
    p_gtd_do.add_argument("--index", type=int,  default=None, help="Next Action \u306e\u756a\u53f7 (1-based)")
    p_gtd_do.add_argument("--name",  type=str,  default=None, help="\u30bf\u30b9\u30af\u540d\u3092\u76f4\u63a5\u6307\u5b9a")
    p_gtd_do.add_argument("--timer", type=int,  default=0,    help="N\u5206\u5f8c\u306b\u78ba\u8a8d\u901a\u77e5 (Windows\u30bf\u30b9\u30af\u30b9\u30b1\u30b8\u30e5\u30fc\u30e9\u30fc\u767b\u9332)")
    p_gtd_done = p_gtd_sub.add_parser("done", help="\u300c\u5b8c\u4e86\uff01\u300d\u5ba3\u8a00: Next Action \u3092\u30a2\u30fc\u30ab\u30a4\u30d6\u306b\u79fb\u52d5 + \u30ed\u30b0\u8a18\u9332 + \u901a\u77e5")
    p_gtd_done.add_argument("--index", type=int,  default=None, help="Next Action \u306e\u756a\u53f7 (1-based)")
    p_gtd_done.add_argument("--name",  type=str,  default=None, help="\u30bf\u30b9\u30af\u540d\u3092\u76f4\u63a5\u6307\u5b9a")
    p_gtd_commit = p_gtd_sub.add_parser("commit", help="GTD 変更を git にコミット")
    p_gtd_commit.add_argument("--push", action="store_true", help="コミット後に git push origin master も実行")
    p_gtd_status = p_gtd_sub.add_parser("status", help="GTD ステータス概要")
    p_gtd_status.add_argument("--json", action="store_true")

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
        "gtd":       cmd_gtd,
        "notify":    cmd_notify,
        "logs":      cmd_logs,
    }
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
