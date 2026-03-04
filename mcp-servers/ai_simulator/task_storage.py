"""
タスクストレージ（永続化対応）
"""

import json
import os
from typing import Dict, Any
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# データディレクトリ
DATA_DIR = Path(os.getenv("AISIM_DATA_DIR", "/root/ai_simulator/data/tasks"))
PENDING_FILE = DATA_DIR / "pending_approvals.json"
HISTORY_FILE = DATA_DIR / "task_history.json"

# データディレクトリ作成
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_pending_approvals() -> Dict[str, Dict[str, Any]]:
    """承認待ちタスクを読み込む"""
    if not PENDING_FILE.exists():
        return {}

    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # timestampをfloatに変換（JSONでは文字列になる可能性がある）
            for task in data.values():
                if "timestamp" in task and isinstance(task["timestamp"], str):
                    try:
                        task["timestamp"] = float(task["timestamp"])
                    except ValueError:
                        pass
            return data
    except Exception as e:
        logger.error(f"Failed to load pending approvals: {e}")
        return {}

def save_pending_approvals(pending_approvals: Dict[str, Dict[str, Any]]):
    """承認待ちタスクを保存"""
    try:
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(pending_approvals, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save pending approvals: {e}")

def save_task_history(task_id: str, task_data: Dict[str, Any]):
    """タスク実行履歴を保存"""
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load task history: {e}")
            history = []

    # 履歴に追加
    history_entry = {
        "task_id": task_id,
        "task_name": task_data.get("task_name"),
        "status": task_data.get("status"),
        "confidence": task_data.get("confidence"),
        "timestamp": task_data.get("timestamp"),
        "completed_at": datetime.now().isoformat(),
        "result": task_data.get("execution_result"),
        "error": task_data.get("error")
    }

    # 最新100件のみ保持
    history.append(history_entry)
    history = history[-100:]

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save task history: {e}")

def load_task_history(limit: int = 50) -> list:
    """タスク実行履歴を読み込む"""
    if not HISTORY_FILE.exists():
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
            return history[-limit:]
    except Exception as e:
        logger.error(f"Failed to load task history: {e}")
        return []






