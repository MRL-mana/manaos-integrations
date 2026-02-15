#!/usr/bin/env python3
"""
デバイスアラート → 通知の自動連携
アラート取得後に通知ハブへ送信
"""

import os
import httpx
from typing import Dict, Any, List

from _paths import PORTAL_INTEGRATION_PORT, UNIFIED_API_PORT

try:
    from manaos_logger import get_logger, get_service_logger
except ImportError:
    import logging
    def get_logger(n): return logging.getLogger(n)
logger = get_service_logger("device-alert-notify")

# Portal API URL（デバイスアラート取得）
DEFAULT_PORTAL_URL = f"http://127.0.0.1:{PORTAL_INTEGRATION_PORT}"
PORTAL_URL = os.getenv(
    "PORTAL_INTEGRATION_URL", os.getenv("PORTAL_URL", DEFAULT_PORTAL_URL)
).rstrip("/")
# 統合API URL（通知送信）
DEFAULT_UNIFIED_API_URL = f"http://127.0.0.1:{UNIFIED_API_PORT}"
UNIFIED_API_URL = os.getenv("UNIFIED_API_URL", DEFAULT_UNIFIED_API_URL).rstrip("/")


def fetch_alerts() -> Dict[str, Any]:
    """Portal API からデバイスアラートを取得"""
    try:
        r = httpx.get(f"{PORTAL_URL}/api/devices/alerts", timeout=10.0)
        if r.status_code == 200:
            return r.json()
        return {"alerts": [], "summary": {"total_alerts": 0, "critical_alerts": 0, "warning_alerts": 0}}
    except Exception as e:
        logger.warning(f"アラート取得エラー: {e}")
        return {"alerts": [], "summary": {"total_alerts": 0}, "error": str(e)}


def send_notification(message: str, priority: str = "important") -> bool:
    """統合API 経由で通知送信"""
    try:
        r = httpx.post(
            f"{UNIFIED_API_URL}/api/notification/send",
            json={"message": message, "priority": priority},
            timeout=10.0
        )
        return r.status_code == 200
    except Exception as e:
        logger.warning(f"通知送信エラー: {e}")
        return False


def alerts_to_notify() -> bool:
    """
    アラートを取得し、critical/warning があれば通知を送信
    Returns: 通知を送信したかどうか
    """
    data = fetch_alerts()
    alerts = data.get("alerts", [])
    summary = data.get("summary", {})

    if summary.get("critical_alerts", 0) > 0 or summary.get("warning_alerts", 0) > 0:
        lines = [f"⚠️ デバイスアラート: 合計{len(alerts)}件"]
        critical = [a for a in alerts if a.get("status") == "critical"]
        warning = [a for a in alerts if a.get("status") == "warning"]
        for a in critical[:3]:
            device = a.get("device_name", "不明")
            alert_info = a.get("alert", {})
            lines.append(f"🔴 {device}: {alert_info.get('message', alert_info)}")
        for a in warning[:3]:
            device = a.get("device_name", "不明")
            alert_info = a.get("alert", {})
            lines.append(f"🟡 {device}: {alert_info.get('message', alert_info)}")
        priority = "critical" if critical else "important"
        msg = "\n".join(lines)
        if send_notification(msg, priority):
            logger.info(f"アラート通知を送信: {len(alerts)}件")
            return True

    return False


if __name__ == "__main__":
    import sys
    if alerts_to_notify():
        sys.exit(0)
    else:
        sys.exit(0)  # アラートなしでも正常終了
