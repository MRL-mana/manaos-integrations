#!/usr/bin/env python3
"""ManaOS 外部Watchdog（Raspberry Pi想定）

MVP目的（D優先）:
  - ping OK なのに /ready が 200 でない状態が一定時間続いたら「OSフリーズ疑い」とみなす
  - 復旧アクション（電断→復帰）を“必ず実行”し、結果を Slack に“必ず返す”

設計:
  - /ready は L1（listenできていれば200）前提
  - 電断は n8n Webhook 経由（Tapoクラウド連携をn8n側に寄せる）
  - Slack通知は watchdog から直接 Webhook を叩く（n8n障害に巻き込まれない）

環境変数:
  - MANAOS_HOST: 監視対象ホスト/IP（例: 192.168.1.10）
  - MANAOS_PORT: 監視対象ポート（例: 9502）
  - READY_PATH: 既定 /ready
  - CHECK_INTERVAL_SEC: 既定 10
  - SUSPECT_WINDOW_SEC: 既定 60
  - COOLDOWN_SEC: 既定 180
  - BOOT_WAIT_MAX_SEC: 既定 300
  - MAX_HARD_RETRIES: 既定 2
  - POWER_CYCLE_WEBHOOK_URL: n8n側の復旧Webhook（必須）
  - SLACK_WEBHOOK_URL: Slack Incoming Webhook（任意だが推奨）

n8n Webhook（期待I/F）:
  - POST JSON: {"action":"power_cycle","off_seconds":15,"reason":"...","incident_id":"..."}
  - 成功時: 2xx を返す（bodyは任意）
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class Config:
    host: str
    port: int
    ready_path: str
    check_interval_sec: int
    suspect_window_sec: int
    cooldown_sec: int
    boot_wait_max_sec: int
    max_hard_retries: int
    power_cycle_webhook_url: str
    slack_webhook_url: Optional[str]


@dataclass
class State:
    status: str  # HEALTHY | SUSPECT | RECOVERING | DEGRADED
    suspect_since: Optional[float]
    cooldown_until: Optional[float]
    consecutive_hard_failures: int
    last_incident_id: Optional[str]


STATE_PATH = Path(__file__).with_name("watchdog_state.json")


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def load_config() -> Config:
    host = os.getenv("MANAOS_HOST", "127.0.0.1")
    port = _env_int("MANAOS_PORT", 9502)
    ready_path = os.getenv("READY_PATH", "/ready")

    check_interval_sec = _env_int("CHECK_INTERVAL_SEC", 10)
    suspect_window_sec = _env_int("SUSPECT_WINDOW_SEC", 60)
    cooldown_sec = _env_int("COOLDOWN_SEC", 180)
    boot_wait_max_sec = _env_int("BOOT_WAIT_MAX_SEC", 300)
    max_hard_retries = _env_int("MAX_HARD_RETRIES", 2)

    power_cycle_webhook_url = os.getenv("POWER_CYCLE_WEBHOOK_URL", "").strip()
    if not power_cycle_webhook_url:
        raise SystemExit("POWER_CYCLE_WEBHOOK_URL が未設定です（n8nの復旧Webhook URLを入れてください）")

    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    return Config(
        host=host,
        port=port,
        ready_path=ready_path,
        check_interval_sec=check_interval_sec,
        suspect_window_sec=suspect_window_sec,
        cooldown_sec=cooldown_sec,
        boot_wait_max_sec=boot_wait_max_sec,
        max_hard_retries=max_hard_retries,
        power_cycle_webhook_url=power_cycle_webhook_url,
        slack_webhook_url=slack_webhook_url,
    )


def load_state() -> State:
    if not STATE_PATH.exists():
        return State(
            status="HEALTHY",
            suspect_since=None,
            cooldown_until=None,
            consecutive_hard_failures=0,
            last_incident_id=None,
        )

    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return State(
            status=str(payload.get("status", "HEALTHY")),
            suspect_since=payload.get("suspect_since"),
            cooldown_until=payload.get("cooldown_until"),
            consecutive_hard_failures=int(payload.get("consecutive_hard_failures", 0)),
            last_incident_id=payload.get("last_incident_id"),
        )
    except Exception:
        return State(
            status="HEALTHY",
            suspect_since=None,
            cooldown_until=None,
            consecutive_hard_failures=0,
            last_incident_id=None,
        )


def save_state(state: State) -> None:
    STATE_PATH.write_text(
        json.dumps(
            {
                "status": state.status,
                "suspect_since": state.suspect_since,
                "cooldown_until": state.cooldown_until,
                "consecutive_hard_failures": state.consecutive_hard_failures,
                "last_incident_id": state.last_incident_id,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def http_get_status(url: str, timeout_sec: int = 3) -> Tuple[Optional[int], Optional[str]]:
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout_sec) as resp:
            return int(resp.status), None
    except HTTPError as e:
        return int(e.code), f"HTTPError {e.code}"
    except URLError as e:
        return None, f"URLError {getattr(e, 'reason', e)}"
    except Exception as e:
        return None, f"Error {e}"


def http_post_json(url: str, data: Dict[str, Any], timeout_sec: int = 10) -> Tuple[bool, str]:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            code = int(resp.status)
            ok = 200 <= code < 300
            return ok, f"HTTP {code}"
    except HTTPError as e:
        return False, f"HTTPError {e.code}"
    except URLError as e:
        return False, f"URLError {getattr(e, 'reason', e)}"
    except Exception as e:
        return False, f"Error {e}"


def ping_ok(host: str) -> bool:
    """Linux想定（Raspberry Pi）。Windowsでも動くように最低限吸収。"""
    if os.name == "nt":
        cmd = ["ping", "-n", "1", "-w", "1000", host]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", host]

    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return res.returncode == 0
    except Exception:
        return False


def slack_notify(slack_webhook_url: Optional[str], text: str) -> None:
    if not slack_webhook_url:
        print(f"[slack:skip] {text}")
        return

    ok, detail = http_post_json(slack_webhook_url, {"text": text}, timeout_sec=10)
    if not ok:
        print(f"[slack:fail] {detail} | {text}")


def now_ts() -> float:
    return time.time()


def main() -> None:
    cfg = load_config()
    state = load_state()

    ready_url = f"http://{cfg.host}:{cfg.port}{cfg.ready_path}"

    print("=" * 70)
    print("ManaOS Watchdog (MVP) start")
    print(f"target: {cfg.host}:{cfg.port}{cfg.ready_path}")
    print(f"interval={cfg.check_interval_sec}s suspect_window={cfg.suspect_window_sec}s cooldown={cfg.cooldown_sec}s")
    print("=" * 70)

    while True:
        t = now_ts()

        if state.cooldown_until and t < state.cooldown_until:
            remain = int(state.cooldown_until - t)
            if remain % 30 == 0:
                slack_notify(cfg.slack_webhook_url, f"【監視抑止】cooldown中のため復旧スキップ | remain={remain}s")
            time.sleep(cfg.check_interval_sec)
            continue

        is_ping_ok = ping_ok(cfg.host)
        ready_code, ready_err = http_get_status(ready_url, timeout_sec=3)
        is_ready_ok = ready_code == 200

        if is_ready_ok:
            if state.status != "HEALTHY":
                state.status = "HEALTHY"
                state.suspect_since = None
                save_state(state)
            time.sleep(cfg.check_interval_sec)
            continue

        # /ready が落ちている
        if not is_ping_ok:
            # OSフリーズ扱いにしない（回線/電源系）: 今回のMVPスコープ外
            if state.status != "DEGRADED":
                state.status = "DEGRADED"
                state.suspect_since = None
                save_state(state)
            time.sleep(cfg.check_interval_sec)
            continue

        # ping OK で /ready NG → SUSPECT
        if not state.suspect_since:
            state.suspect_since = t
            state.status = "SUSPECT"
            save_state(state)

        elapsed = int(t - (state.suspect_since or t))
        if elapsed < cfg.suspect_window_sec:
            time.sleep(cfg.check_interval_sec)
            continue

        # 発火: RECOVERING
        incident_id = str(uuid.uuid4())
        state.last_incident_id = incident_id
        state.status = "RECOVERING"
        save_state(state)

        slack_notify(
            cfg.slack_webhook_url,
            f"【復旧開始】OSフリーズ疑い /ready={ready_code} ping=OK | state=SUSPECT→RECOVERING | action=SMARTPLUG_POWERCYCLE | incident_id={incident_id}",
        )

        # 電断（n8nへ）
        ok, detail = http_post_json(
            cfg.power_cycle_webhook_url,
            {
                "action": "power_cycle",
                "off_seconds": 15,
                "reason": f"watchdog: ping OK but /ready not 200 for {cfg.suspect_window_sec}s ({ready_err or ready_code})",
                "incident_id": incident_id,
            },
            timeout_sec=30,
        )

        if not ok:
            state.consecutive_hard_failures += 1
            state.status = "DEGRADED"
            state.suspect_since = None
            save_state(state)
            slack_notify(
                cfg.slack_webhook_url,
                f"【復旧失敗】powercycle webhook call failed ({detail}) | retries={state.consecutive_hard_failures}/{cfg.max_hard_retries} | state=DEGRADED | incident_id={incident_id}",
            )
            time.sleep(cfg.check_interval_sec)
            continue

        # 復帰待ち（ping→/ready）
        start_wait = now_ts()
        recovered = False
        while now_ts() - start_wait < cfg.boot_wait_max_sec:
            if ping_ok(cfg.host):
                code2, _ = http_get_status(ready_url, timeout_sec=3)
                if code2 == 200:
                    recovered = True
                    break
            time.sleep(5)

        if recovered:
            verify_time = int(now_ts() - start_wait)
            state.status = "HEALTHY"
            state.suspect_since = None
            state.consecutive_hard_failures = 0
            state.cooldown_until = now_ts() + cfg.cooldown_sec
            save_state(state)

            slack_notify(
                cfg.slack_webhook_url,
                f"【復旧成功】action=SMARTPLUG_POWERCYCLE | ping=OK | /ready=200 | verify_time={verify_time}s | incident_id={incident_id}",
            )
        else:
            state.consecutive_hard_failures += 1
            state.status = "DEGRADED"
            state.suspect_since = None
            state.cooldown_until = now_ts() + cfg.cooldown_sec
            save_state(state)

            slack_notify(
                cfg.slack_webhook_url,
                f"【復旧失敗】boot_wait timeout | ping=OK? {ping_ok(cfg.host)} | /ready!=200 | retries={state.consecutive_hard_failures}/{cfg.max_hard_retries} | state=DEGRADED | incident_id={incident_id}",
            )

        # 電断ループ抑止
        if state.consecutive_hard_failures >= cfg.max_hard_retries:
            slack_notify(
                cfg.slack_webhook_url,
                f"【要手動介入】連続復旧失敗が上限に到達 | retries={state.consecutive_hard_failures}/{cfg.max_hard_retries} | incident_id={incident_id}",
            )

        time.sleep(cfg.check_interval_sec)


if __name__ == "__main__":
    main()
