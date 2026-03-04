"""
Stage B フィーチャーフラグ管理
"""

import os
from typing import List
import logging

logger = logging.getLogger(__name__)

class FeatureFlags:
    """フィーチャーフラグ管理"""

    @staticmethod
    def is_write_enabled() -> bool:
        """書き込み有効か"""
        return os.getenv("AISIM_ENABLE_WRITE", "false").lower() == "true"

    @staticmethod
    def get_allowed_tasks() -> List[str]:
        """許可タスクリスト"""
        tasks_str = os.getenv("AISIM_ALLOW_TASKS", "[]")
        try:
            import json
            tasks = json.loads(tasks_str)
            return tasks if isinstance(tasks, list) else []
        except Exception:
            return []

    @staticmethod
    def get_confidence_gate() -> float:
        """信頼度ゲート"""
        return float(os.getenv("AISIM_CONFIDENCE_GATE", "0.75"))

    @staticmethod
    def requires_human_approval() -> bool:
        """人手承認必須か"""
        return os.getenv("AISIM_REQUIRE_HUMAN_APPROVAL", "true").lower() == "true"

    @staticmethod
    def can_execute_task(task_name: str, confidence: float) -> bool:
        """タスク実行可能か"""
        # Stage Aでは常にFalse
        if not FeatureFlags.is_write_enabled():
            logger.info(f"Stage A mode: {task_name} blocked (read-only)")
            return False

        # タスクが許可リストにない場合は拒否
        allowed = FeatureFlags.get_allowed_tasks()

        # Stage C: ["*"]の場合は全タスク許可
        if allowed == ["*"]:
            logger.debug(f"Stage C mode: {task_name} allowed (all tasks permitted)")
        elif task_name not in allowed:
            logger.warning(f"Task not in allow-list: {task_name}")
            return False

        # 信頼度チェック
        gate = FeatureFlags.get_confidence_gate()
        if confidence < gate:
            logger.warning(f"Confidence too low: {confidence} < {gate}")
            return False

        return True

