#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 API Health Check
各APIの /health または主要エンドポイントを監視し、失敗時はログに記録
Webhook（Slack等）が設定されていれば失敗時に通知
"""

import json
import os
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen

from system3_http_retry import http_get_json_retry

try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

_DEFAULT_INTEGRATIONS = str(Path(__file__).resolve().parent)
INTEGRATIONS_DIR = Path(os.getenv("MANAOS_INTEGRATIONS_DIR", _DEFAULT_INTEGRATIONS))
LOG_DIR = INTEGRATIONS_DIR / "logs"
LOG_FILE = LOG_DIR / "system3_health_check.log"
STATE_FILE = LOG_DIR / "system3_health_check_state.json"
CONSECUTIVE_FAIL_THRESHOLD = int(
    os.getenv("SYSTEM3_ALERT_CONSECUTIVE_THRESHOLD", "2")
)  # この回数連続失敗したら通知（ノイズ削減）

SERVICES = [
    ("Intrinsic Score API", "http://127.0.0.1:5130/api/score"),
    ("Todo Queue API", "http://127.0.0.1:5134/api/metrics"),
    ("Learning System API", "http://127.0.0.1:5126/health"),
    ("RAG Memory API", "http://127.0.0.1:5103/health"),
]


def _load_state() -> dict:
    """連続失敗カウントを読み込み"""
    if not STATE_FILE.exists():
        return {"consecutive_fail_count": 0, "last_fails": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"consecutive_fail_count": 0, "last_fails": []}


def _save_state(consecutive_fail_count: int, last_fails: list) -> None:
    """状態を保存"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        STATE_FILE.write_text(
            json.dumps(
                {"consecutive_fail_count": consecutive_fail_count, "last_fails": last_fails},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def _send_alert(fails: list, consecutive_count: int = 1) -> None:
    """
    SYSTEM3_ALERT_WEBHOOK_URL / PHASE2_ALERT_WEBHOOK_URL / SLACK_WEBHOOK_URL が
    設定されていれば POST する。連続失敗が THRESHOLD 以上の場合のみ通知。
    """
    webhook_url = (
        os.getenv("SYSTEM3_ALERT_WEBHOOK_URL")
        or os.getenv("PHASE2_ALERT_WEBHOOK_URL")
        or os.getenv("SLACK_WEBHOOK_URL")
    )
    if not webhook_url or not webhook_url.strip():
        return
    if consecutive_count < CONSECUTIVE_FAIL_THRESHOLD:
        return
    try:
        msg = f"[System 3 Health Check] FAILED ({consecutive_count}回連続): {', '.join(fails[:5])}"
        body = json.dumps({"text": msg}).encode("utf-8")
        req = Request(
            webhook_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10) as _:
            pass
    except Exception:
        pass


def run_health_check() -> dict:
    """各サービスをチェックし、結果を返す"""
    results = {}
    for name, url in SERVICES:
        r = http_get_json_retry(url, timeout=3, retries=2, base_delay=0.5)
        results[name] = "ok" if r else "fail"
    return results


def log_results(results: dict) -> None:
    """結果をログファイルに追記"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fails = [n for n, s in results.items() if s == "fail"]
    line = f"{now} | " + " | ".join(f"{n}:{s}" for n, s in results.items())
    if fails:
        line += f" | FAILED: {', '.join(fails)}"
    line += "\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def main() -> dict:
    results = run_health_check()
    log_results(results)

    fails = [n for n, s in results.items() if s == "fail"]
    state = _load_state()

    if fails:
        count = state.get("consecutive_fail_count", 0) + 1
        _save_state(count, fails)
        logger.warning("System3 ヘルスチェック失敗 (%d回連続): %s", count, ", ".join(fails))
        if count >= CONSECUTIVE_FAIL_THRESHOLD:
            _send_alert(fails, count)
    else:
        _save_state(0, [])
        logger.info("System3 ヘルスチェック: 全サービス正常")

    return results


if __name__ == "__main__":
    r = main()
    fails = [n for n, s in r.items() if s == "fail"]
    if fails:
        print(f"FAILED: {', '.join(fails)}")
    else:
        print("OK")
