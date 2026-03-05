#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Self-Healing Engine
===========================
配置先: tools/heal.py

使い方:
  python tools/heal.py                        # auto_restart=true のDOWNサービスを自動復旧
  python tools/heal.py --dry-run              # 実際には起動せず、何が起動されるか確認
  python tools/heal.py --tier 0               # Tier0 のみ対象
  python tools/heal.py --tier 0 --tier 1      # Tier0+1 対象
  python tools/heal.py --service llm_routing  # 特定サービスを強制起動（auto_restart 無視）
  python tools/heal.py --force                # auto_restart=false でも全て起動
  python tools/heal.py --json                 # JSON 形式で結果出力

終了コード:
  0 = 全て OK (復旧不要 or 復旧成功)
  1 = 一部または全て復旧失敗
  2 = 設定エラー
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Windows 文字コード対策
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
    from events import emit as _emit_event
except ImportError:
    def _emit_event(*a, **kw): pass  # フォールバック: 無視

# ── 設定 ─────────────────────────────────────────────────────────────────────
REPO_ROOT    = Path(__file__).parent.parent
LEDGER_PATH  = REPO_ROOT / "config" / "services_ledger.yaml"
LOG_DIR      = REPO_ROOT / "logs"
HEAL_LOG     = LOG_DIR / "heal.log"
PYTHON_EXE   = sys.executable
HEAL_TIMEOUT     = 10.0  # ヘルスチェック待機 (秒)
RETRY_MAX        = 3     # 起動リトライ回数
RETRY_WAIT       = 3.0   # リトライ間隔 (秒)
DEP_WAIT_TIMEOUT = 30    # 依存サービス UP 待機上限 (秒)

# ── カラー ────────────────────────────────────────────────────────────────────
RESET  = "\x1b[0m"
RED    = "\x1b[31m"
YELLOW = "\x1b[33m"
GREEN  = "\x1b[32m"
CYAN   = "\x1b[36m"
BOLD   = "\x1b[1m"
DIM    = "\x1b[2m"


def c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


# ── ログ ──────────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(HEAL_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── Ledger ロード ─────────────────────────────────────────────────────────────
def load_ledger() -> Dict[str, Any]:
    if not LEDGER_PATH.exists():
        print(f"[ERROR] services_ledger.yaml not found: {LEDGER_PATH}", file=sys.stderr)
        sys.exit(2)
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
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
    """health_url が存在すれば HTTP プローブ。なければポートチェック。"""
    health_url = svc.get("health_url")
    port = svc.get("port")

    if health_url:
        try:
            with urllib.request.urlopen(health_url, timeout=timeout) as r:
                return r.status < 500
        except Exception:
            pass
        # health_url が失敗 → ポートフォールバック
    if port:
        import socket
        try:
            with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
                return True
        except Exception:
            pass
    return False


# ── 依存待機 ────────────────────────────────────────────────────────────────
def wait_for_deps(svc: Dict[str, Any], all_services: Dict[str, Any]) -> bool:
    """depends_on のサービスが全部 UP になるまで最大 DEP_WAIT_TIMEOUT 秒待つ。"""
    deps = [d for d in (svc.get("depends_on") or []) if d in all_services]
    if not deps:
        return True
    alive_deps = [d for d in deps if is_alive(all_services[d], timeout=1.5)]
    pending = [d for d in deps if d not in alive_deps]
    if not pending:
        return True
    log(f"  ⏳ {svc['name']} — deps待機: {pending}")
    deadline = time.time() + DEP_WAIT_TIMEOUT
    while pending and time.time() < deadline:
        time.sleep(1)
        pending = [d for d in pending if not is_alive(all_services[d], timeout=1.5)]
    if pending:
        log(f"  [WARN] {svc['name']} — deps タイムアウト: {pending} — 起動続行")
        return False
    log(f"  [DEPS OK] {svc['name']} — 全依存 UP")
    return True


# ── 起動 ─────────────────────────────────────────────────────────────────────
def start_service(svc: Dict[str, Any], dry_run: bool = False,
                  all_services: Dict[str, Any] | None = None) -> bool:
    """
    start_cmd を実行してバックグラウンド起動。
    HEAL_TIMEOUT 秒以内にヘルスチェック成功すれば True。
    """
    name = svc["name"]
    start_cmd = svc.get("start_cmd")
    if not start_cmd:
        log(f"  [SKIP] {name} — start_cmd が未定義")
        return False

    # コマンド組み立て: python → PYTHON_EXE に置換
    if start_cmd.startswith("python "):
        cmd = f'"{PYTHON_EXE}" {start_cmd[7:]}'
    else:
        cmd = start_cmd

    if dry_run:
        log(f"  [DRY-RUN] {name} — would run: {cmd}")
        return True

    # 依存サービスが UP するまで待機
    if all_services:
        wait_for_deps(svc, all_services)

    log(f"  [STARTING] {name} — {cmd}")
    _emit_event("heal_trigger", service=name, detail=cmd, source="heal.py")
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                cmd,
                cwd=str(REPO_ROOT),
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                cmd,
                cwd=str(REPO_ROOT),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception as e:
        log(f"  [ERROR] {name} 起動失敗: {e}")
        return False

    # ヘルスチェック待機
    deadline = time.time() + HEAL_TIMEOUT
    while time.time() < deadline:
        time.sleep(1.5)
        if is_alive(svc, timeout=2.0):
            log(f"  [OK] {name} — ヘルスチェック通過")
            _emit_event("heal_ok", service=name, detail="health check passed", source="heal.py")
            return True

    log(f"  [FAIL] {name} — {HEAL_TIMEOUT}秒以内にヘルスチェック未通過")
    _emit_event("heal_fail", service=name, detail=f"no response within {HEAL_TIMEOUT}s", source="heal.py")
    return False


# ── 依存関係を考慮した起動順序 ───────────────────────────────────────────────
def topo_sort(targets: List[str], services: Dict[str, Any]) -> List[str]:
    """targets の中で depends_on を考慮した起動順序を返す。"""
    ordered: List[str] = []
    visited = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        svc = services.get(name, {})
        for dep in (svc.get("depends_on") or []):
            if dep in targets:
                visit(dep)
        ordered.append(name)

    for n in targets:
        visit(n)
    return ordered


# ── メイン ────────────────────────────────────────────────────────────────────
def main() -> None:
    global LEDGER_PATH
    parser = argparse.ArgumentParser(description="ManaOS Self-Healing Engine")
    parser.add_argument("--dry-run",  action="store_true", help="実際には起動しない")
    parser.add_argument("--tier",     type=int, action="append", dest="tiers",
                        help="対象 Tier (複数指定可, デフォルト=0,1)")
    parser.add_argument("--service",  type=str, action="append", dest="services",
                        help="特定サービスを強制起動 (auto_restart 無視)")
    parser.add_argument("--force",    action="store_true", help="auto_restart=false でも全て起動")
    parser.add_argument("--json",     action="store_true", help="JSON 形式で出力")
    parser.add_argument("--ledger",   type=str, default=str(LEDGER_PATH))

    args = parser.parse_args()
    LEDGER_PATH = Path(args.ledger)

    all_services = load_ledger()
    target_tiers = set(args.tiers) if args.tiers else {0, 1}

    # 対象サービスを決定
    if args.services:
        # 明示的に指定されたサービスのみ（force 扱い）
        targets = [s for s in args.services if s in all_services]
        unknown = [s for s in args.services if s not in all_services]
        if unknown:
            print(f"[WARN] 不明なサービス: {unknown}", file=sys.stderr)
    else:
        targets = [
            name for name, svc in all_services.items()
            if svc.get("tier", 2) in target_tiers
            and svc.get("enabled", False)
            and (svc.get("auto_restart", False) or args.force)
        ]

    # 現在のステータス確認（DOWN のみ処理）
    log(f"=== ManaOS Heal ({datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}) ===")
    log(f"  対象: tiers={target_tiers}, services={targets}, dry_run={args.dry_run}")

    down_targets: List[str] = []
    already_up: List[str] = []
    for name in targets:
        svc = all_services[name]
        if is_alive(svc):
            already_up.append(name)
        else:
            down_targets.append(name)

    if not down_targets:
        log("  [ALL OK] DOWN サービスなし。復旧不要。")
        if args.json:
            print(json.dumps({"status": "ok", "healed": [], "failed": [], "already_up": already_up}))
        sys.exit(0)

    log(f"  DOWN 検知: {down_targets}")

    # ── 上流障害 vs 単独障害 の分類 ──────────────────────────────────────────
    # 依存先がひとつでも DOWN なら「上流障害 (upstream_dead)」
    # 依存先がすべて UP  なら「単独障害 (isolated_dead)」
    upstream_dead: List[str] = []   # 依存先が落ちているため巻き込まれた
    isolated_dead: List[str] = []   # 依存先は UP、自分だけクラッシュ
    for name in down_targets:
        deps = [d for d in (all_services.get(name, {}).get("depends_on") or [])
                if d in all_services]
        dead_deps = [d for d in deps if not is_alive(all_services[d], timeout=1.5)]
        if dead_deps:
            upstream_dead.append(name)
            log(f"  [UPSTREAM FAIL] {name} — 依存 DOWN: {dead_deps}")
        else:
            isolated_dead.append(name)
            log(f"  [ISOLATED FAIL] {name} — 依存は正常、単独クラッシュ")

    if upstream_dead:
        log(f"  ⚠  上流障害サービス (deps復旧後に自動リトライ): {upstream_dead}")
    if isolated_dead:
        log(f"  ✗  単独障害サービス (即時復旧対象): {isolated_dead}")

    log(f"  起動順序解決中...")
    ordered = topo_sort(down_targets, all_services)
    log(f"  起動順: {ordered}")

    results: Dict[str, str] = {}
    failed: List[str] = []
    healed: List[str] = []

    for name in ordered:
        svc = all_services[name]
        success = False
        for attempt in range(1, RETRY_MAX + 1):
            log(f"  [{attempt}/{RETRY_MAX}] {name} 起動試行...")
            ok = start_service(svc, dry_run=args.dry_run, all_services=all_services)
            if ok:
                success = True
                break
            if attempt < RETRY_MAX:
                log(f"  リトライ待機 {RETRY_WAIT}秒...")
                time.sleep(RETRY_WAIT)

        if success:
            healed.append(name)
            results[name] = "healed"
            log(f"  [RECOVERED] {name}")
        else:
            failed.append(name)
            results[name] = "failed"
            log(f"  [FAILED] {name} — 手動確認が必要")

    # サマリー
    log(f"=== Heal 完了: recovered={healed}, failed={failed} ===")

    if args.json:
        print(json.dumps({
            "status": "ok" if not failed else "partial" if healed else "failed",
            "healed": healed,
            "failed": failed,
            "already_up": already_up,
            "upstream_dead": upstream_dead,
            "isolated_dead": isolated_dead,
            "results": results,
        }, ensure_ascii=False, indent=2))

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
