#!/usr/bin/env python3
"""
ask_orchestrator 本格運用: メトリクス集計＋抑制付きアラート。

- status 別カウンタ（ok / skill_not_found / tool_error / error）
- tool_error の error_code 別カウンタ
- Portal タイムアウト件数
- アラート抑制（同一 error_code 30分に1回、等）＋ Slack 通知
  ※ 渡してある Slack を利用: slack_integration.send_to_slack を優先、未利用時は SLACK_WEBHOOK_URL にフォールバック
"""

import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

try:
    from manaos_logger import get_logger
except ImportError:
    import logging

    get_logger = lambda n: logging.getLogger(n)

logger = get_logger(__name__)

# 設定（環境変数で上書き可）
SUPPRESSION_MINUTES = int(os.getenv("ORCHESTRATOR_ALERT_SUPPRESSION_MINUTES", "30"))
PORTAL_TIMEOUT_WINDOW_MINUTES = 5
PORTAL_TIMEOUT_THRESHOLD = 3
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
ORCHESTRATOR_ALERT_CHANNEL = os.getenv("ORCHESTRATOR_ALERT_CHANNEL", "")

# メトリクス（スレッド安全）
_lock = threading.Lock()
_status_counts: Dict[str, int] = defaultdict(int)
_error_code_counts: Dict[str, int] = defaultdict(int)
_portal_timeout_count = 0
_portal_timeout_timestamps: deque = deque(maxlen=500)
_recent_results: deque = deque(maxlen=1000)  # (ts, status, error_code) 傾向用

# アラート抑制: key -> 最後に通知した時刻
_last_notified_path = Path(__file__).parent / "data" / "orchestrator_alerts.json"
_last_notified: Dict[str, float] = {}
_last_notified_loaded = False


def _load_last_notified() -> Dict[str, float]:
    global _last_notified_loaded
    with _lock:
        if _last_notified_loaded:
            return _last_notified
        if _last_notified_path.exists():
            try:
                with open(_last_notified_path, "r", encoding="utf-8") as f:
                    _last_notified.update(json.load(f))
            except Exception as e:
                logger.warning(f"orchestrator_alerts.json 読み込みエラー: {e}")
        _last_notified_loaded = True
        return _last_notified


def _save_last_notified() -> None:
    _last_notified_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_last_notified_path, "w", encoding="utf-8") as f:
            json.dump(_last_notified, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"orchestrator_alerts.json 保存エラー: {e}")


def record_result(
    status: str,
    error_code: Optional[str] = None,
    portal_trace_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    query: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    """1件のオーケストレータ結果を記録。"""
    with _lock:
        _status_counts[status] += 1
        if status == "tool_error" and error_code:
            _error_code_counts[error_code] += 1
        ts = time.time()
        _recent_results.append((ts, status, error_code or ""))


def record_portal_timeout() -> None:
    """Portal → 5106 のタイムアウトを1件記録。"""
    global _portal_timeout_count
    with _lock:
        _portal_timeout_count += 1
        _portal_timeout_timestamps.append(time.time())


def get_stats() -> Dict[str, Any]:
    """ダッシュボード用の集計を返す。"""
    with _lock:
        now = time.time()
        window_5min = now - 5 * 60
        portal_timeouts_5min = sum(1 for t in _portal_timeout_timestamps if t >= window_5min)
        recent_by_status = defaultdict(int)
        recent_skill_not_found_queries: Dict[str, int] = defaultdict(int)
        for ts, st, ec in _recent_results:
            if ts >= window_5min:
                recent_by_status[st] += 1
        return {
            "status": dict(_status_counts),
            "error_code": dict(_error_code_counts),
            "portal_timeout_total": _portal_timeout_count,
            "portal_timeout_last_5min": portal_timeouts_5min,
            "last_5min_by_status": dict(recent_by_status),
            "updated_at": datetime.now().isoformat(),
        }


def _suppression_key(status: str, error_code: Optional[str], portal_timeout: bool) -> str:
    if portal_timeout:
        return "portal_timeout"
    if status == "tool_error" and error_code:
        return f"tool_error:{error_code}"
    return status


def should_notify(
    status: str,
    error_code: Optional[str] = None,
    portal_timeout: bool = False,
) -> bool:
    """
    叩き台に基づく通知要否。
    - error: 即通知（抑制: 30分に1回）
    - tool_error AUTH_EXPIRED: 即通知（抑制: 30分に1回）
    - tool_error DEVICE_UNREACHABLE: 即通知（抑制: 30分に1回）
    - portal_timeout 連続: 直近5分でN回超なら通知（抑制: 30分に1回）
    """
    now = time.time()
    key = _suppression_key(status, error_code, portal_timeout)
    if status == "ok" or status == "skill_not_found":
        return False
    if status == "tool_error" and error_code in ("RATE_LIMITED",):
        return False  # 閾値超え時だけ別途判定する想定
    if portal_timeout:
        with _lock:
            window = now - PORTAL_TIMEOUT_WINDOW_MINUTES * 60
            n = sum(1 for t in _portal_timeout_timestamps if t >= window)
        if n < PORTAL_TIMEOUT_THRESHOLD:
            return False
    _load_last_notified()
    with _lock:
        last = _last_notified.get(key, 0)
        if now - last < SUPPRESSION_MINUTES * 60:
            return False
        _last_notified[key] = now
        _save_last_notified()
    return True


def _format_slack_message(
    status: str,
    error_code: Optional[str],
    query: Optional[str],
    portal_trace_id: Optional[str],
    trace_id: Optional[str],
    message: Optional[str],
    action_hint: str = "",
) -> str:
    """Slack 用1行＋対処の次の一手。"""
    parts = [f"[{status}]"]
    if error_code:
        parts.append(f"error_code={error_code}")
    if message:
        parts.append(message)
    q_short = (query or "")[:50] + ("..." if len(query or "") > 50 else "")
    if q_short:
        parts.append(f'query="{q_short}"')
    if portal_trace_id:
        parts.append(f"portal_trace_id={portal_trace_id}")
    if trace_id:
        parts.append(f"trace_id={trace_id}")
    if action_hint:
        parts.append(f"対応: {action_hint}")
    return "\n".join(parts)


def notify_slack(
    status: str,
    error_code: Optional[str] = None,
    query: Optional[str] = None,
    portal_trace_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    message: Optional[str] = None,
    portal_timeout: bool = False,
) -> bool:
    """Slack に通知（Webhook または send_to_slack）。抑制は呼び出し側で should_notify 済み前提。"""
    action_hint = ""
    if status == "error":
        action_hint = "再試行 or 内部ログ確認"
    elif status == "tool_error":
        if error_code == "AUTH_EXPIRED":
            action_hint = "トークン更新 → 再起動"
        elif error_code == "DEVICE_UNREACHABLE":
            action_hint = "電源/ネットワーク確認"
        elif error_code == "TIMEOUT":
            action_hint = "負荷 or 外部API遅延の可能性"
    if portal_timeout:
        action_hint = "Portal→5106 タイムアウト連続。5106/ネット確認"

    text = _format_slack_message(
        status, error_code, query, portal_trace_id, trace_id, message, action_hint
    )

    # 既存の slack_integration（SLACK_BOT_TOKEN / 渡してあるSlack）を優先して利用
    try:
        from slack_integration import send_to_slack

        channel = (ORCHESTRATOR_ALERT_CHANNEL or "").strip() or None
        send_to_slack(text, channel=channel)
        logger.info("orchestrator アラートを Slack に送信しました（slack_integration 経由）")
        return True
    except ImportError:
        pass  # フォールバックへ
    except Exception as e:
        logger.warning(f"Slack（slack_integration）送信エラー: {e}")

    # フォールバック: 直接 Webhook
    if SLACK_WEBHOOK_URL:
        try:
            import httpx

            r = httpx.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
            if r.status_code == 200:
                logger.info("orchestrator アラートを Slack に送信しました（Webhook）")
                return True
        except Exception as e:
            logger.warning(f"Slack Webhook 送信エラー: {e}")
        return False

    logger.debug("Slack 未設定。SLACK_BOT_TOKEN または SLACK_WEBHOOK_URL を設定してください")
    return False


def record_and_maybe_alert(
    body: Dict[str, Any],
    is_portal_timeout: bool = False,
) -> None:
    """
    Portal から呼ぶ一括処理: メトリクス記録＋通知要否判定＋Slack 送信。
    body は 5106 の共通レスポンス（status, meta, result, message）。
    """
    if is_portal_timeout:
        record_portal_timeout()
        if should_notify("error", None, portal_timeout=True):
            notify_slack(
                status="error",
                message="Portal→5106 タイムアウト連続",
                portal_timeout=True,
            )
        return

    status = body.get("status", "")
    meta = body.get("meta") or {}
    result = body.get("result") or {}
    message = body.get("message") or ""
    query = (body.get("input_text") or "")[:200]
    portal_trace_id = meta.get("portal_trace_id")
    trace_id = meta.get("trace_id")
    error_code = result.get("error_code") if isinstance(result, dict) else None

    record_result(
        status=status,
        error_code=error_code,
        portal_trace_id=portal_trace_id,
        trace_id=trace_id,
        query=query or None,
        message=message or None,
    )

    if not should_notify(status, error_code, portal_timeout=False):
        return
    notify_slack(
        status=status,
        error_code=error_code,
        query=query or None,
        portal_trace_id=portal_trace_id,
        trace_id=trace_id,
        message=message or None,
    )
