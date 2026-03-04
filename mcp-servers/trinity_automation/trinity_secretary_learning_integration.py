#!/usr/bin/env python3
"""
Trinity Enhanced Secretary - 学習系・記憶系連携モジュール
秘書システムの動作を学習レイヤーに記録し、記憶システムに保存
"""

import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

import importlib.util

# learning_api
spec1 = importlib.util.spec_from_file_location("learning_api", "/root/scripts/learning_api.py")
learning_api = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(learning_api)

log_event = learning_api.log_event

# 記憶系連携
try:
    spec2 = importlib.util.spec_from_file_location(
        "memory_integration",
        "/root/manaos_learning/memory_integration.py"
    )
    memory_module = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(memory_module)
    memory_bridge = memory_module.get_memory_bridge()
except Exception:
    memory_bridge = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecretaryLearningIntegration:
    """秘書システムの学習系・記憶系連携"""

    def __init__(self):
        """初期化"""
        self.memory_bridge = memory_bridge
        self.enabled = True

    def log_task_creation(self, task_data: Dict[str, Any]) -> str:
        """
        タスク作成を学習レイヤーに記録

        Args:
            task_data: タスクデータ

        Returns:
            記録されたイベントID
        """
        try:
            event_id = log_event(
                tool="trinity_secretary",
                task="task_creation",
                phase="creation",
                input_data={
                    "title": task_data.get("title", ""),
                    "description": task_data.get("description", ""),
                    "priority": task_data.get("priority", "medium"),
                    "category": task_data.get("category", "general")
                },
                raw_output=json.dumps(task_data, ensure_ascii=False),
                tags=["secretary", "task", task_data.get("category", "general")],
                meta={
                    "source": "trinity_secretary",
                    "auto_detected": task_data.get("auto_detected", False)
                }
            )

            # 記憶システムにも送信
            if self.memory_bridge and self.memory_bridge.enabled:
                try:
                    self.memory_bridge.send_learning_pattern_to_memory(
                        tool="trinity_secretary",
                        pattern={
                            "pattern": f"タスク作成: {task_data.get('title', '')}",
                            "description": task_data.get("description", ""),
                            "occurrences": 1,
                            "confidence": 0.8
                        },
                        pattern_type="task_pattern"
                    )
                except Exception as e:
                    logger.warning(f"記憶システムへの送信失敗: {e}")

            logger.info(f"✅ タスク作成を記録: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"タスク作成記録エラー: {e}")
            return ""

    def log_email_analysis(self, email_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> str:
        """
        メール分析を学習レイヤーに記録

        Args:
            email_data: メールデータ
            analysis_result: 分析結果

        Returns:
            記録されたイベントID
        """
        try:
            event_id = log_event(
                tool="trinity_secretary",
                task="email_analysis",
                phase="analysis",
                input_data={
                    "sender": email_data.get("sender", ""),
                    "subject": email_data.get("subject", "")
                },
                raw_output=json.dumps(email_data, ensure_ascii=False),
                corrected_output=json.dumps(analysis_result, ensure_ascii=False),
                tags=["secretary", "email", analysis_result.get("category", "general")],
                meta={
                    "source": "trinity_secretary",
                    "priority": analysis_result.get("priority", "medium"),
                    "action_required": analysis_result.get("action_required", False)
                }
            )

            # 記憶システムにも送信
            if self.memory_bridge and self.memory_bridge.enabled:
                try:
                    self.memory_bridge.send_learning_pattern_to_memory(
                        tool="trinity_secretary",
                        pattern={
                            "pattern": f"メール分析: {analysis_result.get('category', 'general')}",
                            "description": email_data.get("subject", ""),
                            "occurrences": 1,
                            "confidence": 0.7
                        },
                        pattern_type="email_pattern"
                    )
                except Exception as e:
                    logger.warning(f"記憶システムへの送信失敗: {e}")

            logger.info(f"✅ メール分析を記録: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"メール分析記録エラー: {e}")
            return ""

    def log_calendar_event(self, event_data: Dict[str, Any]) -> str:
        """
        カレンダー予定を学習レイヤーに記録

        Args:
            event_data: 予定データ

        Returns:
            記録されたイベントID
        """
        try:
            event_id = log_event(
                tool="trinity_secretary",
                task="calendar_event_creation",
                phase="creation",
                input_data={
                    "title": event_data.get("title", ""),
                    "start_time": event_data.get("start_time", ""),
                    "location": event_data.get("location", "")
                },
                raw_output=json.dumps(event_data, ensure_ascii=False),
                tags=["secretary", "calendar", "event"],
                meta={
                    "source": "trinity_secretary",
                    "auto_created": event_data.get("auto_created", False)
                }
            )

            logger.info(f"✅ カレンダー予定を記録: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"カレンダー予定記録エラー: {e}")
            return ""

    def log_report_generation(self, report_data: Dict[str, Any]) -> str:
        """
        レポート生成を学習レイヤーに記録

        Args:
            report_data: レポートデータ

        Returns:
            記録されたイベントID
        """
        try:
            event_id = log_event(
                tool="trinity_secretary",
                task="report_generation",
                phase="generation",
                input_data={
                    "report_type": report_data.get("report_type", "daily"),
                    "period": report_data.get("period", "")
                },
                raw_output=json.dumps(report_data, ensure_ascii=False),
                tags=["secretary", "report", report_data.get("report_type", "daily")],
                meta={
                    "source": "trinity_secretary",
                    "timestamp": datetime.now().isoformat()
                }
            )

            logger.info(f"✅ レポート生成を記録: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"レポート生成記録エラー: {e}")
            return ""


# グローバルインスタンス
_secretary_learning: Optional[SecretaryLearningIntegration] = None


def get_secretary_learning() -> SecretaryLearningIntegration:
    """秘書学習統合のシングルトンインスタンスを取得"""
    global _secretary_learning
    if _secretary_learning is None:
        _secretary_learning = SecretaryLearningIntegration()
    return _secretary_learning


if __name__ == "__main__":
    print("🤖 秘書システム - 学習系・記憶系連携テスト")
    print("=" * 60)

    integration = get_secretary_learning()

    # テスト: タスク作成
    task_data = {
        "title": "テストタスク",
        "description": "これはテストです",
        "priority": "high",
        "category": "work",
        "auto_detected": True
    }
    event_id = integration.log_task_creation(task_data)
    print(f"✅ タスク作成記録: {event_id}")

    # テスト: メール分析
    email_data = {
        "sender": "test@example.com",
        "subject": "重要: 会議の確認",
        "body": "明日の会議について確認をお願いします"
    }
    analysis_result = {
        "priority": "high",
        "category": "work",
        "action_required": True,
        "summary": "会議の確認が必要"
    }
    event_id = integration.log_email_analysis(email_data, analysis_result)
    print(f"✅ メール分析記録: {event_id}")








