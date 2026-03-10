#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 状態監視スクリプト
起動状態・キュー滞留を監視し、異常時は Slack に通知（オプション）
"""

import os
import sys
import time
import json
import argparse

from _paths import COMFYUI_PORT

# Windows で UTF-8 出力
if sys.platform == "win32":
    try:
        import io

        if hasattr(sys.stdout, "buffer"):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    except Exception:
        pass

DEFAULT_COMFYUI_URL = f"http://127.0.0.1:{COMFYUI_PORT}"
COMFYUI_URL = os.getenv("COMFYUI_URL", DEFAULT_COMFYUI_URL)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
CHECK_INTERVAL = int(os.getenv("COMFYUI_MONITOR_INTERVAL", "60"))
QUEUE_WARN_THRESHOLD = int(os.getenv("COMFYUI_QUEUE_WARN", "5"))


def check_comfyui_status():
    """ComfyUI の /system_stats または /queue を確認。戻り: (ok, message, queue_len)"""
    try:
        import urllib.request

        req = urllib.request.Request(
            f"{COMFYUI_URL}/system_stats",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            json.loads(r.read().decode("utf-8", errors="replace"))
        # queue 長を取得（API によってキーが異なる場合あり）
        queue_len = 0
        try:
            qreq = urllib.request.Request(
                f"{COMFYUI_URL}/queue",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(qreq, timeout=3) as qr:
                qdata = json.loads(qr.read().decode("utf-8", errors="replace"))
            queue_running = qdata.get("queue_running") or []
            queue_pending = qdata.get("queue_pending") or []
            queue_len = len(queue_running) + len(queue_pending)
        except Exception:
            pass
        return True, "ComfyUI 応答正常", queue_len
    except Exception as e:
        return False, str(e), 0


def send_slack(message: str, webhook_url: str = None):  # type: ignore
    """Slack Incoming Webhook にメッセージ送信"""
    url = webhook_url or SLACK_WEBHOOK_URL
    if not url:
        return False
    try:
        import urllib.request

        payload = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="ComfyUI 状態監視（オプション: Slack 通知）")
    parser.add_argument("--once", action="store_true", help="1回だけチェックして終了")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="チェック間隔（秒）")
    parser.add_argument(
        "--slack",
        type=str,
        default="",
        help="Slack Webhook URL（未指定時は環境変数 SLACK_WEBHOOK_URL）",
    )
    parser.add_argument(
        "--queue-warn",
        type=int,
        default=QUEUE_WARN_THRESHOLD,
        help="キュー数がこの値を超えたら警告",
    )
    args = parser.parse_args()

    webhook = args.slack or SLACK_WEBHOOK_URL
    last_fail_time = None
    last_notify_time = None

    while True:
        ok, msg, queue_len = check_comfyui_status()
        if ok:
            if last_fail_time and webhook:
                # 復旧通知（1回だけ）
                if last_notify_time is None or (time.time() - last_notify_time) > 300:
                    send_slack("[ComfyUI] 復旧しました。%s" % COMFYUI_URL, webhook)
                    last_notify_time = time.time()
            last_fail_time = None
            if queue_len >= args.queue_warn and webhook:
                if last_notify_time is None or (time.time() - last_notify_time) > 600:
                    send_slack(
                        "[ComfyUI] キュー滞留: %d 件（閾値 %d）" % (queue_len, args.queue_warn),
                        webhook,
                    )
                    last_notify_time = time.time()
            print(f"[OK] {msg}" + (f" queue={queue_len}" if queue_len else ""), flush=True)
        else:
            print(f"[NG] ComfyUI 応答なし: {msg}", flush=True)
            if webhook:
                if last_fail_time is None:
                    last_fail_time = time.time()
                    send_slack(f"[ComfyUI] 応答なし: {COMFYUI_URL} - {msg}", webhook)
                elif time.time() - last_fail_time > 300:
                    send_slack("[ComfyUI] 依然として応答なし: %s" % COMFYUI_URL, webhook)
                    last_fail_time = time.time()

        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
