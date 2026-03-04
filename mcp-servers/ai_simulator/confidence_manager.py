"""
信頼度成長管理
"""

import os
import json
import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# データディレクトリ
DATA_DIR = Path(os.getenv("AISIM_DATA_DIR", "/root/ai_simulator/data/tasks"))
CONFIDENCE_FILE = DATA_DIR / "confidence_history.json"

# 信頼度成長設定
CONFIDENCE_BOOST_SUCCESS = float(os.getenv("AISIM_CONFIDENCE_BOOST_SUCCESS", "0.01"))  # 成功で+0.01
CONFIDENCE_PENALTY_FAILURE = float(os.getenv("AISIM_CONFIDENCE_PENALTY_FAILURE", "0.02"))  # 失敗で-0.02
CONFIDENCE_PENALTY_RISK = float(os.getenv("AISIM_CONFIDENCE_PENALTY_RISK", "0.05"))  # リスク行動で-0.05
CONFIDENCE_MIN = float(os.getenv("AISIM_CONFIDENCE_MIN", "0.1"))  # 最小信頼度
CONFIDENCE_MAX = float(os.getenv("AISIM_CONFIDENCE_MAX", "0.99"))  # 最大信頼度

def load_confidence_history() -> list:
    """信頼度履歴を読み込む"""
    if not CONFIDENCE_FILE.exists():
        return []

    try:
        with open(CONFIDENCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load confidence history: {e}")
        return []

def save_confidence_event(event_type: str, task_name: str, confidence_before: float,
                          confidence_after: float, reason: str = ""):
    """信頼度イベントを記録"""
    history = load_confidence_history()

    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,  # success, failure, risk_action
        "task_name": task_name,
        "confidence_before": confidence_before,
        "confidence_after": confidence_after,
        "delta": confidence_after - confidence_before,
        "reason": reason
    }

    history.append(event)
    # 最新1000件のみ保持
    history = history[-1000:]

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIDENCE_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save confidence event: {e}")

def calculate_new_confidence(current_confidence: float, event_type: str,
                            task_name: str = "", is_risk_action: bool = False) -> float:
    """新しい信頼度を計算"""
    if event_type == "success":
        new_confidence = current_confidence + CONFIDENCE_BOOST_SUCCESS
    elif event_type == "failure":
        new_confidence = current_confidence - CONFIDENCE_PENALTY_FAILURE
    elif event_type == "risk_action" or is_risk_action:
        new_confidence = current_confidence - CONFIDENCE_PENALTY_RISK
    else:
        return current_confidence

    # 範囲制限
    new_confidence = max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, new_confidence))

    # 履歴保存
    save_confidence_event(
        event_type=event_type,
        task_name=task_name,
        confidence_before=current_confidence,
        confidence_after=new_confidence,
        reason=f"{event_type} event"
    )

    return new_confidence

def get_confidence_stats() -> Dict[str, Any]:
    """信頼度統計を取得"""
    history = load_confidence_history()

    if not history:
        return {
            "total_events": 0,
            "current_confidence": 0.7,  # デフォルト
            "trend": "stable"
        }

    # 最新の信頼度
    latest = history[-1]
    current = latest["confidence_after"]

    # トレンド計算（直近10件の平均変化）
    recent = history[-10:] if len(history) >= 10 else history
    avg_delta = sum(e["delta"] for e in recent) / len(recent) if recent else 0

    if avg_delta > 0.001:
        trend = "increasing"
    elif avg_delta < -0.001:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "total_events": len(history),
        "current_confidence": current,
        "trend": trend,
        "success_count": sum(1 for e in history if e["event_type"] == "success"),
        "failure_count": sum(1 for e in history if e["event_type"] == "failure"),
        "risk_actions": sum(1 for e in history if e["event_type"] == "risk_action"),
        "latest_event": latest
    }






