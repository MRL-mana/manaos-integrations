"""
監査ログ（自動承認評価機能）
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# データディレクトリ
DATA_DIR = Path(os.getenv("AISIM_DATA_DIR", "/root/ai_simulator/data/tasks"))
AUDIT_LOG_FILE = DATA_DIR / "audit_log.json"

def log_auto_approval_evaluation(
    task_id: str,
    task_name: str,
    confidence: float,
    was_good_decision: bool,
    human_feedback: Optional[str] = None
):
    """自動承認の評価を記録"""
    history = []
    if AUDIT_LOG_FILE.exists():
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")
            history = []

    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "task_name": task_name,
        "confidence": confidence,
        "was_good_decision": was_good_decision,
        "human_feedback": human_feedback,
        "evaluated_at": datetime.now().isoformat()
    }

    history.append(audit_entry)
    # 最新500件のみ保持
    history = history[-500:]

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save audit log: {e}")

def get_audit_statistics() -> Dict[str, Any]:
    """監査統計を取得"""
    if not AUDIT_LOG_FILE.exists():
        return {
            "total_evaluations": 0,
            "good_decisions": 0,
            "bad_decisions": 0,
            "approval_rate": 0.0
        }

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        total = len(history)
        good = sum(1 for e in history if e.get("was_good_decision", False))
        bad = total - good
        approval_rate = (good / total * 100) if total > 0 else 0.0

        return {
            "total_evaluations": total,
            "good_decisions": good,
            "bad_decisions": bad,
            "approval_rate": approval_rate,
            "latest_evaluation": history[-1] if history else None
        }
    except Exception as e:
        logger.error(f"Failed to load audit statistics: {e}")
        return {
            "total_evaluations": 0,
            "good_decisions": 0,
            "bad_decisions": 0,
            "approval_rate": 0.0
        }

def get_audit_history(limit: int = 50) -> list:
    """監査履歴を取得"""
    if not AUDIT_LOG_FILE.exists():
        return []

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
            return history[-limit:]
    except Exception as e:
        logger.error(f"Failed to load audit history: {e}")
        return []






