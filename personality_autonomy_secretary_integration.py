#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎭🤖📋 人格系・自律系・秘書系統合管理システム
3つのシステムを統合管理し、連携を強化
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from personality_system import PersonalitySystem
from autonomy_system import AutonomySystem
from secretary_system_optimized import SecretarySystemOptimized
from learning_memory_integration import LearningMemoryIntegration
from unified_cache_system import get_unified_cache

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PersonalityAutonomySecretaryIntegration")

# キャッシュシステムの取得
cache_system = get_unified_cache()


class PersonalityAutonomySecretaryIntegration:
    """人格系・自律系・秘書系統合管理システム"""

    def __init__(
        self,
        orchestrator_url: str = "http://127.0.0.1:5106",
        learning_system_url: Optional[str] = None,
    ):
        """
        初期化

        Args:
            orchestrator_url: Unified Orchestrator API URL
            learning_system_url: Learning System API URL
        """
        # 各システムを初期化
        self.personality = PersonalitySystem()
        self.autonomy = AutonomySystem(orchestrator_url, learning_system_url)
        self.secretary = SecretarySystemOptimized(orchestrator_url)

        # 学習・記憶統合システム
        self.learning_memory = LearningMemoryIntegration()

        logger.info("✅ 人格系・自律系・秘書系統合管理システム初期化完了")

    def _get_persona_display(self):
        """get_current_persona() の戻り値（dict またはオブジェクト）を共通の表示用に正規化"""
        from types import SimpleNamespace

        p = self.personality.get_current_persona()
        if isinstance(p, dict):
            traits = p.get("traits", [])
            return SimpleNamespace(
                name=p.get("name", "unknown"),
                tone=p.get("tone", ""),
                response_style=p.get("response_style", ""),
                traits=[t if isinstance(t, str) else getattr(t, "value", str(t)) for t in traits],
            )
        return p

    def execute_with_personality(
        self, action: str, context: Dict[str, Any], user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        人格を考慮して実行

        Args:
            action: アクション
            context: コンテキスト
            user_message: ユーザーメッセージ

        Returns:
            実行結果（人格を反映した応答）
        """
        # 人格プロフィールを取得（dict/オブジェクト両対応）
        persona = self._get_persona_display()

        # 実行
        result = {
            "action": action,
            "context": context,
            "personality": {
                "name": persona.name,
                "tone": persona.tone,
                "response_style": persona.response_style,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # 学習・記憶に記録
        self.learning_memory.record_and_learn(
            action=f"personality_{action}", context=context, result=result, save_to_memory=True
        )

        return result

    def execute_autonomous_task(
        self, task_type: str, condition: Dict[str, Any], action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        自律タスクを実行

        Args:
            task_type: タスクタイプ
            condition: 実行条件
            action: 実行アクション

        Returns:
            実行結果
        """
        # 自律レベルをチェック
        if self.autonomy.autonomy_level.value == "disabled":
            return {"status": "disabled", "message": "自律システムが無効です"}

        # タスクを実行
        result = {
            "task_type": task_type,
            "condition": condition,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }

        # 学習・記憶に記録
        self.learning_memory.record_and_learn(
            action=f"autonomy_{task_type}",
            context={"condition": condition, "action": action},
            result=result,
            save_to_memory=True,
        )

        return result

    def submit_file_organize_plan(
        self,
        user_hint: str = "Downloads 一覧取得",
        path: str = "~/Downloads",
        intent: str = "list_only",
    ) -> Dict[str, Any]:
        """
        Moltbot にファイル整理用 Plan を送信（list_only / read_only）。
        まなOS司令塔から Moltbot Gateway 経由で OpenClaw/ローカルフォールバックを実行する。

        Args:
            user_hint: ユーザー指示の要約（監査用）
            path: 対象パス（例: ~/Downloads）
            intent: list_only | read_only

        Returns:
            {"ok": bool, "plan_id": str, "error": str?, "data": {...}?}
        """
        try:
            from moltbot_integration.gateway import MoltbotGatewayClient
            from moltbot_integration.schema import (
                Plan,
                PlanStep,
                PlanScope,
                PlanMetadata,
                PlanConstraints,
                RiskLevel,
            )
        except ImportError as e:
            logger.warning(f"Moltbot integration not available: {e}")
            return {"ok": False, "error": "moltbot_integration not available"}

        plan_id = f"plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        scope = PlanScope.file_organize()
        meta = PlanMetadata(user_hint=user_hint or "file organize (secretary)", phase="1")
        constraints = PlanConstraints.phase1_safe()
        if (intent or "list_only").strip().lower() == "read_only":
            steps = [PlanStep(step_id="read", action="file_read", params={"path": path})]
            plan_intent = "file_read only"
        else:
            steps = [PlanStep(step_id="scan", action="list_files", params={"path": path})]
            plan_intent = "list_files only"

        plan = Plan(
            plan_id=plan_id,
            intent=plan_intent,
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            scope=scope,
            steps=steps,
            metadata=meta,
            constraints=constraints,
        )
        if user_hint:
            plan.metadata.user_hint = user_hint
            plan.intent = (user_hint[:200] if len(user_hint) > 200 else user_hint) or plan_intent

        client = MoltbotGatewayClient()
        resp = client.submit_plan(plan)
        if not resp.get("ok"):
            return {"ok": False, "plan_id": plan_id, "error": resp.get("error", "submit failed")}
        self.learning_memory.record_and_learn(
            action="moltbot_submit_file_organize",
            context={"user_hint": user_hint, "path": path, "intent": intent},
            result={"plan_id": plan_id, "data": resp.get("data", {})},
            save_to_memory=True,
        )
        return {"ok": True, "plan_id": plan_id, "data": resp.get("data", {})}

    def create_smart_reminder(
        self, title: str, description: str, scheduled_time: str, reminder_type: str = "once"
    ) -> Dict[str, Any]:
        """
        スマートリマインダーを作成（人格と学習を考慮）

        Args:
            title: タイトル
            description: 説明
            scheduled_time: スケジュール時間
            reminder_type: リマインダータイプ

        Returns:
            作成されたリマインダー
        """
        from secretary_system_optimized import Reminder, ReminderType

        # リマインダーを作成
        reminder = Reminder(
            reminder_id=f"reminder_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=title,
            description=description,
            scheduled_time=scheduled_time,
            reminder_type=ReminderType(reminder_type),
        )

        # 秘書システムに追加
        self.secretary.add_reminder(reminder)

        # 学習・記憶に記録
        self.learning_memory.record_and_learn(
            action="secretary_create_reminder",
            context={
                "title": title,
                "description": description,
                "scheduled_time": scheduled_time,
                "reminder_type": reminder_type,
            },
            result={"status": "success", "reminder_id": reminder.reminder_id},
            save_to_memory=True,
        )

        return {
            "reminder_id": reminder.reminder_id,
            "title": reminder.title,
            "scheduled_time": reminder.scheduled_time,
            "status": "created",
        }

    def generate_personality_report(self, report_type: str = "daily") -> Dict[str, Any]:
        """
        人格を反映した報告を生成

        Args:
            report_type: 報告タイプ

        Returns:
            生成された報告
        """
        # 人格プロフィールを取得（dict/オブジェクト両対応）
        persona = self._get_persona_display()

        # 最近の活動を取得
        recent_activities = self.learning_memory.get_integrated_stats()

        # 報告を生成（人格を反映）
        report_content = f"""
【{report_type.upper()} Report】

{persona.response_style}

最近の活動:
- 実行されたアクション: {recent_activities.get('learning', {}).get('total_actions', 0)}件
- 記憶エントリ: {recent_activities.get('memory', {}).get('total_entries', 0)}件

{persona.tone}
"""

        from secretary_system_optimized import Report

        report = Report(
            report_id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            report_type=report_type,
            title=f"{report_type.upper()} Report",
            content=report_content,
            generated_at=datetime.now().isoformat(),
            metadata={"personality": persona.name, "tone": persona.tone},
        )

        # 秘書システムに追加
        self.secretary.add_report(report)

        return {
            "report_id": report.report_id,
            "content": report.content,
            "personality": persona.name,
        }

    def get_integrated_status(self) -> Dict[str, Any]:
        """統合状態を取得"""
        persona = self._get_persona_display()
        traits = persona.traits
        traits_str = [t if isinstance(t, str) else getattr(t, "value", str(t)) for t in traits]
        return {
            "personality": {"current_persona": persona.name, "traits": traits_str},
            "autonomy": {
                "level": self.autonomy.autonomy_level.value,
                "tasks_count": len(self.autonomy.tasks),
            },
            "secretary": {
                "pending_reminders": len(self.secretary.get_pending_reminders()),
                "recent_reports": len(self.secretary.get_recent_reports()),
            },
            "learning_memory": self.learning_memory.get_integrated_stats(),
            "timestamp": datetime.now().isoformat(),
        }

    def optimize_based_on_learning(self) -> Dict[str, Any]:
        """学習結果に基づいて最適化"""
        # 分析と最適化提案を取得
        analysis = self.learning_memory.analyze_and_optimize()

        optimizations = []

        # 人格の最適化
        if "personality" in analysis.get("recommendations", []):
            optimizations.append(
                {"system": "personality", "recommendation": "人格プロフィールの調整を検討"}
            )

        # 自律システムの最適化
        if "autonomy" in analysis.get("recommendations", []):
            optimizations.append({"system": "autonomy", "recommendation": "自律レベルの調整を検討"})

        # 秘書システムの最適化
        if "secretary" in analysis.get("recommendations", []):
            optimizations.append(
                {"system": "secretary", "recommendation": "リマインダースケジュールの最適化を検討"}
            )

        return {
            "optimizations": optimizations,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """テスト用メイン関数"""
    print("人格系・自律系・秘書系統合管理システムテスト")
    print("=" * 60)

    integration = PersonalityAutonomySecretaryIntegration()

    # 統合状態を取得
    status = integration.get_integrated_status()
    print(f"\n統合状態:")
    print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
