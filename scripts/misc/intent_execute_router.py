#!/usr/bin/env python3
"""
Intent Router → 実行パス強化
意図分類に応じて直接 API を呼び出すショートカット
音声・チャットからそのまま動かせる
"""

import os
import httpx
from typing import Dict, Any, Optional

from _paths import INTENT_ROUTER_PORT, ORCHESTRATOR_PORT, UNIFIED_API_PORT

try:
    from manaos_logger import get_logger, get_service_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(n): return logging.getLogger(n)
logger = get_service_logger("intent-execute-router")  # type: ignore[possibly-unbound]

DEFAULT_UNIFIED_API_URL = f"http://127.0.0.1:{UNIFIED_API_PORT}"
DEFAULT_INTENT_ROUTER_URL = f"http://127.0.0.1:{INTENT_ROUTER_PORT}"
DEFAULT_ORCHESTRATOR_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}"

# 統合API URL（自サーバー）
UNIFIED_API_URL = os.getenv("UNIFIED_API_URL", DEFAULT_UNIFIED_API_URL).rstrip("/")
# Intent Router URL
INTENT_ROUTER_URL = os.getenv("INTENT_ROUTER_URL", DEFAULT_INTENT_ROUTER_URL).rstrip("/")


def classify_intent(text: str) -> Dict[str, Any]:
    """Intent Router で意図を分類"""
    try:
        r = httpx.post(
            f"{INTENT_ROUTER_URL}/api/classify",
            json={"text": text},
            timeout=10.0
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.warning(f"Intent Router 分類エラー: {e}")
    return {"intent_type": "unknown", "confidence": 0.0}


def execute_by_intent(
    text: str,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    意図に応じて直接実行し、結果を返す
    device_status → /api/devices/status または /api/pixel7/resources
    file_management → secretary_file_organize (MoltBot)
    file_status → /api/file-secretary/inbox/status
    その他 → オーケストレーターに転送
    """
    base = (base_url or UNIFIED_API_URL).rstrip("/")

    # 1. 意図分類
    intent_result = classify_intent(text)
    intent_type = intent_result.get("intent_type", "unknown")
    confidence = float(intent_result.get("confidence", 0))

    # 2. ショートカット実行（高信頼度時）
    if confidence >= 0.7:
        try:
            if intent_type == "device_status":
                # デバイス状態
                if "pixel" in text.lower() or "ピクセル" in text or "バッテリー" in text or "スマホ" in text:
                    r = httpx.get(f"{base}/api/pixel7/resources", timeout=10.0)
                else:
                    r = httpx.get(f"{base}/api/devices/status", timeout=10.0)
                if r.status_code == 200:
                    return {"intent_type": intent_type, "result": r.json(), "shortcut": True}
            elif intent_type == "file_management" and "整理" in text:
                # ファイル整理（MoltBot）
                r = httpx.post(
                    f"{base}/api/secretary/file-organize",
                    json={"path": "~/Downloads", "intent": "list_only", "user_hint": text},
                    timeout=15.0
                )
                if r.status_code == 200:
                    return {"intent_type": intent_type, "result": r.json(), "shortcut": True}
            elif intent_type == "file_status":
                # INBOX 状況
                r = httpx.get(f"{base}/api/file-secretary/inbox/status", timeout=10.0)
                if r.status_code == 200:
                    return {"intent_type": intent_type, "result": r.json(), "shortcut": True}
        except Exception as e:
            logger.debug(f"ショートカット実行エラー: {e}")

    # 3. フォールバック: オーケストレーターに転送
    try:
        orch_url = os.getenv("ORCHESTRATOR_URL", DEFAULT_ORCHESTRATOR_URL).rstrip("/")
        r = httpx.post(
            f"{orch_url}/api/execute",
            json={"query": text, "auto_evaluate": True},
            timeout=30.0
        )
        if r.status_code == 200:
            return {"intent_type": intent_type, "result": r.json(), "shortcut": False}
    except Exception as e:
        logger.warning(f"オーケストレーター転送エラー: {e}")

    return {"intent_type": intent_type, "error": "実行に失敗しました", "shortcut": False}
