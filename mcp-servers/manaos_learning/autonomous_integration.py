#!/usr/bin/env python3
"""
自律系 → 学習レイヤー 連携モジュール
自律実行結果を学習レイヤーに記録
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

import importlib.util

# learning_api
spec1 = importlib.util.spec_from_file_location("learning_api", "/root/scripts/learning_api.py")
learning_api = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(learning_api)

log_event = learning_api.log_event
log_correction = learning_api.log_correction


def log_autonomous_action(
    action_type: str,
    action_description: str,
    result: Dict[str, Any],
    success: bool = True
) -> str:
    """
    自律実行アクションを学習レイヤーに記録

    Args:
        action_type: アクションタイプ（例: "email_check", "task_planning"）
        action_description: アクションの説明
        result: 実行結果
        success: 成功したかどうか

    Returns:
        記録されたイベントID
    """
    return log_event(
        tool="autonomous_system",
        task=action_type,
        phase="execution",
        input_data={"description": action_description},
        raw_output=json.dumps(result, ensure_ascii=False),
        corrected_output=None,
        feedback="good" if success else "bad",
        tags=["autonomous", action_type, "auto_logged"],
        meta={
            "source": "autonomous_engine",
            "success": success
        }
    )


def log_autonomous_decision(
    decision_context: str,
    options: list,
    chosen_option: str,
    outcome: Optional[Dict[str, Any]] = None
) -> str:
    """
    自律判断を学習レイヤーに記録

    Args:
        decision_context: 判断の文脈
        options: 選択肢リスト
        chosen_option: 選んだ選択肢
        outcome: 結果（後から追加可能）

    Returns:
        記録されたイベントID
    """
    return log_event(
        tool="autonomous_system",
        task="decision_making",
        phase="decision",
        input_data={
            "context": decision_context,
            "options": options
        },
        raw_output=chosen_option,
        corrected_output=None,
        feedback=None,
        tags=["autonomous", "decision", "auto_logged"],
        meta={
            "source": "autonomous_engine",
            "outcome": outcome
        }
    )


if __name__ == "__main__":
    print("🤖 自律系 → 学習レイヤー 連携テスト")
    print("=" * 60)

    # テスト記録
    event_id = log_autonomous_action(
        action_type="test_action",
        action_description="テストアクション",
        result={"status": "success", "test": True},
        success=True
    )
    print(f"✅ 記録成功: {event_id}")








