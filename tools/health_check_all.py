#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/health_check_all.py  - ManaOS 全サービスヘルスチェッカー

使い方:
    python tools/health_check_all.py              # テーブル表示
    python tools/health_check_all.py --json       # JSON 出力
    python tools/health_check_all.py --watch 10   # 10秒ごとに繰り返し

"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any
import urllib.request
import urllib.error

# ── サービス定義 ──────────────────────────────────────────────
SERVICES = [
    # name                   url                                     tags
    ("unified-api",         "http://127.0.0.1:9502/health",        ["core","docker"]),
    ("mrl-memory",          "http://127.0.0.1:9507/health",        ["core","docker"]),
    ("learning-system",     "http://127.0.0.1:9508/health",        ["core","docker"]),
    ("tool-server",         "http://127.0.0.1:9503/health",        ["docker"]),
    ("prometheus",          "http://127.0.0.1:9090/-/healthy",     ["monitoring","docker"]),
    ("cadvisor",            "http://127.0.0.1:8080/healthz",       ["monitoring","docker"]),
    ("grafana",             "http://127.0.0.1:3000/api/health",    ["monitoring","docker"]),
    ("open-webui",          "http://127.0.0.1:3001/health",        ["docker"]),
    ("secretary-api",       "http://127.0.0.1:5003/health",        ["docker"]),
    ("monitoring-dash",     "http://127.0.0.1:5005/health",        ["docker"]),
    ("n8n",                 "http://127.0.0.1:5678/healthz",       ["docker"]),
    ("gallery-api",         "http://127.0.0.1:5559/health",        ["optional","docker"]),
    ("moltbot-gateway",     "http://127.0.0.1:8088/health",        ["optional"]),
    # Windows 直接起動サービス
    ("step-deep-research",  "http://127.0.0.1:5120/health",        ["optional","windows"]),
    ("file-secretary",      "http://127.0.0.1:8089/health",        ["optional","windows"]),
    ("ops-dashboard",       "http://127.0.0.1:9640/health",        ["optional","windows"]),
    ("perf-monitor",        "http://127.0.0.1:9425/health",        ["docker"]),
    ("slack-bot",           "http://127.0.0.1:5300/health",        ["docker"]),
    ("voicevox",            "http://127.0.0.1:50021/version",      ["docker"]),
    ("command-hub",         "http://127.0.0.1:5004/health",        ["docker"]),
    ("task-executor",       "http://127.0.0.1:5176/health",        ["docker"]),
    ("enhanced-api",        "http://127.0.0.1:5008/health",        ["docker"]),
    ("enhanced-integ",      "http://127.0.0.1:5007/health",        ["docker"]),
    ("unified-ui",          "http://127.0.0.1:5009/health",        ["docker"]),
]

TIMEOUT = 4  # seconds


def check_one(name: str, url: str, tags: list) -> Dict[str, Any]:
    """1サービスのヘルスチェック"""
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            latency_ms = int((time.monotonic() - start) * 1000)
            body = resp.read(512).decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
                status = data.get("status", "ok") if isinstance(data, dict) else "ok"
            except Exception:
                status = "ok"
            return {
                "name": name, "url": url, "tags": tags,
                "healthy": True, "status": status,
                "latency_ms": latency_ms, "error": None,
            }
    except urllib.error.HTTPError as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        if e.code < 500:  # 4xx は稼働中とみなしてOK
            return {"name": name, "url": url, "tags": tags,
                    "healthy": True, "status": f"http_{e.code}",
                    "latency_ms": latency_ms, "error": None}
        return {"name": name, "url": url, "tags": tags,
                "healthy": False, "status": "error",
                "latency_ms": latency_ms, "error": f"HTTP {e.code}"}
    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {"name": name, "url": url, "tags": tags,
                "healthy": False, "status": "offline",
                "latency_ms": latency_ms, "error": str(e)[:80]}


def run_checks(filter_tag: str = None) -> list:
    targets = [(n, u, t) for n, u, t in SERVICES if not filter_tag or filter_tag in t]
    results = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        future_map = {ex.submit(check_one, n, u, t): (n, u, t) for n, u, t in targets}
        for fut in as_completed(future_map):
            results.append(fut.result())
    return sorted(results, key=lambda r: r["name"])


def print_table(results: list, ts: str):
    ok = sum(1 for r in results if r["healthy"])
    total = len(results)
    print(f"\n  ManaOS ヘルスチェック  {ts}  [{ok}/{total} healthy]\n")
    print(f"  {'SERVICE':<22} {'STATUS':<10} {'LATENCY':>8}  URL")
    print(f"  {'─'*22} {'─'*10} {'─'*8}  {'─'*35}")
    for r in results:
        mark = "✓" if r["healthy"] else "✗"
        color_on  = "\033[32m" if r["healthy"] else "\033[31m"
        color_off = "\033[0m"
        lat = f"{r['latency_ms']}ms" if r["latency_ms"] < 9999 else "timeout"
        port = r["url"].split(":")[2].split("/")[0]
        print(f"  {color_on}{mark} {r['name']:<21}{color_off} {r['status']:<10} {lat:>8}  :{port}")
    print()


def main():
    ap = argparse.ArgumentParser(description="ManaOS 全サービスヘルスチェッカー")
    ap.add_argument("--json", action="store_true", help="JSON 出力")
    ap.add_argument("--watch", type=int, metavar="SEC", help="繰り返し間隔(秒)")
    ap.add_argument("--tag", default=None, help="フィルタ: core / docker / optional / windows")
    ap.add_argument("--fail-only", action="store_true", help="unhealthy のみ表示")
    args = ap.parse_args()

    def once():
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results = run_checks(args.tag)
        if args.fail_only:
            results = [r for r in results if not r["healthy"]]
        if args.json:
            print(json.dumps({"timestamp": ts, "results": results}, ensure_ascii=False, indent=2))
        else:
            print_table(results, ts)
        return results

    if args.watch:
        try:
            while True:
                once()
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n停止しました。")
    else:
        results = once()
        healthy = sum(1 for r in results if r["healthy"])
        sys.exit(0 if healthy > 0 else 1)


if __name__ == "__main__":
    main()
