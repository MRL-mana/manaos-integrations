#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Daily Report
===================
配置先: scripts/misc/manaos_daily_report.py

直近イベント + サービス状態を LLM に投げて日報を生成し
logs/analysis/YYYYMMDD_HHMM.txt に保存する。

TaskScheduler から 1時間ごとに呼び出す:
  python scripts/misc/manaos_daily_report.py

オプション:
  -n N      分析イベント件数 (デフォルト: 50)
  --stdout  ファイルに保存せず標準出力のみ
  --slack   Slack 通知も送る（webhook_url が設定済みの場合）
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT   = Path(__file__).parent.parent.parent
TOOLS_DIR   = REPO_ROOT / "tools"
ANALYSIS_DIR = REPO_ROOT / "logs" / "analysis"
LLM_URL     = "http://127.0.0.1:5111/api/llm/route"

sys.path.insert(0, str(TOOLS_DIR))
try:
    from events import read_events, emit
except ImportError:
    def read_events(n=50): return []
    def emit(*a, **kw): pass


def get_service_status() -> list[dict]:
    """manaosctl status --json を subprocess で呼び出してサービス一覧を取得。"""
    import subprocess
    python = str(Path(sys.executable))
    manaosctl = str(TOOLS_DIR / "manaosctl.py")
    try:
        r = subprocess.run(
            [python, manaosctl, "status", "--json"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT),
        )
        return json.loads(r.stdout).get("services", [])
    except Exception:
        return []


def build_prompt(events: list[dict], services: list[dict], n_events: int) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    up   = sum(1 for s in services if s.get("alive"))
    down = sum(1 for s in services if not s.get("alive"))

    svc_summary = f"サービス合計 {len(services)} 件: UP={up} / DOWN={down}"
    down_names  = [s["name"] for s in services if not s.get("alive")]
    if down_names:
        svc_summary += f"\nDOWN中: {down_names}"

    events_text = json.dumps(events, ensure_ascii=False, indent=2) if events else "（イベントなし）"

    return (
        f"ManaOS 定期レポート ({now})\n\n"
        f"## サービス状態\n{svc_summary}\n\n"
        f"## 直近 {n_events} 件のイベント\n{events_text}\n\n"
        f"以上のデータを分析して、以下の形式で日本語レポートを作成してください:\n\n"
        f"### 1. 総合評価（1行）\n"
        f"### 2. 異常・懸念事項（箇条書き、最大5件）\n"
        f"### 3. 推奨アクション（優先度順、最大3件）\n"
        f"### 4. 今後の予測（1〜2文）\n"
    )


def call_llm(prompt: str, timeout: int = 90) -> tuple[str, str]:
    """LLM routing API を呼び出す。(response_text, model_name) を返す。"""
    payload = json.dumps({"prompt": prompt, "model": "auto"}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        LLM_URL, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("response", ""), result.get("model", "?")


def save_report(report: str, model: str) -> Path:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    path = ANALYSIS_DIR / f"{ts}.txt"
    header = (
        f"# ManaOS Daily Report\n"
        f"# Generated : {datetime.datetime.now().isoformat()}\n"
        f"# Model     : {model}\n"
        f"{'='*60}\n\n"
    )
    path.write_text(header + report, encoding="utf-8")
    return path


def notify_slack(text: str) -> None:
    """slack_integration サービスが動いていれば Slack 通知。"""
    try:
        import urllib.parse
        payload = json.dumps({"text": f"[ManaOS Daily Report]\n{text[:500]}"}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:5590/notify",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass  # Slack 通知失敗は無視


def main() -> None:
    parser = argparse.ArgumentParser(description="ManaOS 定期分析レポート")
    parser.add_argument("-n", type=int, default=50, help="分析するイベント件数")
    parser.add_argument("--stdout", action="store_true", help="標準出力のみ（ファイル未保存）")
    parser.add_argument("--slack",  action="store_true", help="Slack にも通知")
    args = parser.parse_args()

    events   = read_events(n=args.n)
    services = get_service_status()
    prompt   = build_prompt(events, services, args.n)

    print(f"[ManaOS Daily Report] イベント={len(events)}件, サービス={len(services)}件 → LLM送信中...", flush=True)

    try:
        report, model = call_llm(prompt)
    except Exception as e:
        print(f"[ERROR] LLM接続失敗: {e}", file=sys.stderr)
        print("ヒント: llm_routing が起動しているか確認してください", file=sys.stderr)
        sys.exit(1)

    if args.stdout:
        print(f"\n[モデル: {model}]\n")
        print(report)
    else:
        path = save_report(report, model)
        print(f"[OK] 保存先: {path}")
        print(f"[モデル: {model}]")
        print()
        print(report)

    emit("analyze", detail=f"daily_report n={len(events)} model={model}", source="daily_report")

    if args.slack:
        notify_slack(report)


if __name__ == "__main__":
    main()
