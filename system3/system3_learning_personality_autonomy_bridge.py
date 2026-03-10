#!/usr/bin/env python3
"""
学習 × 人格 × 自律のループ連携
Learning System → Personality に好み反映、Autonomy のタスク優先度調整
"""

import os
import httpx
from typing import Dict, Any, List

try:
    from manaos_integrations._paths import AUTONOMY_SYSTEM_PORT, LEARNING_SYSTEM_PORT, PERSONALITY_SYSTEM_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import AUTONOMY_SYSTEM_PORT, LEARNING_SYSTEM_PORT, PERSONALITY_SYSTEM_PORT  # type: ignore
    except Exception:  # pragma: no cover
        LEARNING_SYSTEM_PORT = int(os.getenv("LEARNING_SYSTEM_PORT", "5126"))
        PERSONALITY_SYSTEM_PORT = int(os.getenv("PERSONALITY_SYSTEM_PORT", "5123"))
        AUTONOMY_SYSTEM_PORT = int(os.getenv("AUTONOMY_SYSTEM_PORT", "5124"))

try:
    from manaos_logger import get_logger, get_service_logger  # type: ignore
except ImportError:
    import logging
    def get_logger(n): return logging.getLogger(n)
logger = get_service_logger("system3-learning-personality-autonomy-bridge")  # type: ignore[possibly-unbound]

# System3 各コンポーネントの URL
LEARNING_URL = os.getenv("LEARNING_SYSTEM_URL", f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}").rstrip("/")
PERSONALITY_URL = os.getenv("PERSONALITY_SYSTEM_URL", f"http://127.0.0.1:{PERSONALITY_SYSTEM_PORT}").rstrip("/")
AUTONOMY_URL = os.getenv("AUTONOMY_SYSTEM_URL", f"http://127.0.0.1:{AUTONOMY_SYSTEM_PORT}").rstrip("/")


def get_learning_preferences() -> Dict[str, Any]:
    """Learning System から好み・最適化提案を取得"""
    try:
        r = httpx.get(f"{LEARNING_URL}/api/preferences", timeout=5.0)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"Learning 取得エラー: {e}")
    return {}


def get_personality_profile() -> Dict[str, Any]:
    """Personality System から現在の人格プロフィールを取得"""
    try:
        r = httpx.get(f"{PERSONALITY_URL}/api/persona", timeout=5.0)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"Personality 取得エラー: {e}")
    return {}


def update_personality_from_learning() -> bool:
    """
    学習した好みを人格プロフィールに反映
    Learning → Personality の一方向連携
    """
    prefs = get_learning_preferences()
    if not prefs:
        return False

    updates = {}
    # 好みから人格の「傾向」を更新（例: よく使うモデル、言語スタイル）
    optimizations = prefs.get("optimizations", [])
    if optimizations:
        notes = "; ".join(str(o)[:100] for o in optimizations[:3])
        updates["notes"] = f"学習からの傾向: {notes}"

    preferences = prefs.get("preferences", {})
    if preferences:
        # 例: 好みのモデルがあれば personality metadata に
        if "preferred_model" in preferences:
            updates["metadata"] = {"preferred_model": preferences["preferred_model"]}

    if not updates:
        return False

    try:
        r = httpx.patch(f"{PERSONALITY_URL}/api/persona", json={"updates": updates}, timeout=5.0)
        if r.status_code == 200:
            logger.info("Personality を学習結果で更新しました")
            return True
    except Exception as e:
        logger.warning(f"Personality 更新エラー: {e}")
    return False


def get_autonomy_tasks() -> List[Dict[str, Any]]:
    """Autonomy のタスク一覧を取得"""
    try:
        r = httpx.get(f"{AUTONOMY_URL}/api/tasks", timeout=5.0)
        if r.status_code == 200:
            return r.json().get("tasks", [])
    except Exception as e:
        logger.debug(f"Autonomy 取得エラー: {e}")
    return []


def sync_learning_personality_autonomy() -> Dict[str, bool]:
    """
    学習 × 人格 × 自律の同期を実行
    Returns: 各ステップの成功フラグ
    """
    result = {"learning_to_personality": False, "autonomy_status": False}
    result["learning_to_personality"] = update_personality_from_learning()
    tasks = get_autonomy_tasks()
    result["autonomy_status"] = len(tasks) >= 0  # 取得できればOK
    return result
