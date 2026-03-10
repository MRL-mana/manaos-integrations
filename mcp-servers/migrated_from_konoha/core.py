#!/usr/bin/env python3
"""
Trinity Orchestrator - Core
PACTS制御ループ（Propose → Authorize → Carry out → Test → Switch）
"""

import json
import os
import sys
from typing import Dict, Optional, Tuple
from datetime import datetime

from ticket_manager import TicketManager
from agent_caller import AgentCaller

# 再利用モジュールを試みる
try:
    sys.path.insert(0, '/root/trinity_legacy/reusable')
    from notification import Notification, NotificationType
    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False


class TrinityOrchestrator:
    """Trinity Orchestrator - マルチエージェント制御エンジン"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, openai_api_key=None, enable_notifications=True):
        """
        初期化
        
        Args:
            redis_host: Redisホスト
            redis_port: Redisポート
            openai_api_key: OpenAI APIキー
            enable_notifications: 通知機能を有効にするか
        """
        self.ticket_manager = TicketManager(redis_host, redis_port)
        self.agent_caller = AgentCaller(openai_api_key)
        
        self.verbose = True  # デバッグ出力
        
        # 通知機能初期化
        self.enable_notifications = enable_notifications
        if enable_notifications:
            self._init_notifications()
    
    def _init_notifications(self):
        """通知システム初期化"""
        self.notifier = None
        
        if not NOTIFICATION_AVAILABLE:
            return
        
        try:
            # Slack Webhook URLを取得
            slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
            if not slack_webhook:
                try:
                    with open("/root/.mana_vault/slack_webhook.txt", "r") as f:
                        slack_webhook = f.read().strip()
                        if slack_webhook and "hooks.slack.com" in slack_webhook:
                            os.environ["SLACK_WEBHOOK_URL"] = slack_webhook
                except:
                    pass
            
            if slack_webhook and "hooks.slack.com" in slack_webhook:
                self.notifier = Notification(NotificationType.SLACK)  # type: ignore[possibly-unbound]
                self.log("✅ Slack通知が有効になりました", "INFO")
        except Exception as e:
            self.log(f"⚠️ 通知初期化に失敗: {e}", "WARNING")
    
    def _notify_slack(self, message: str, title: str = "Trinity Orchestrator", color: str = "good"):
        """Slack通知送信"""
        if self.notifier:
            try:
                if color == "good":
                    self.notifier.send_success(message, title)
                elif color == "warning":
                    self.notifier.send_warning(message, title)
                elif color == "danger":
                    self.notifier.send_error(message, title)
                else:
                    self.notifier.send(message, title)
            except Exception as e:
                self.log(f"⚠️ Slack通知送信失敗: {e}", "WARNING")
    
    def log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def run(self, goal: str, context: list = None, budget_turns: int = 12) -> Dict:  # type: ignore
        """
        オーケストレーション実行
        
        Args:
            goal: 達成目標
            context: 前提条件・制約
            budget_turns: 最大ターン数
            
        Returns:
            実行結果（辞書）
        """
        self.log(f"🚀 Starting orchestration for goal: {goal}")
        
        # チケット作成
        ticket_id = self.ticket_manager.create_ticket(goal, context, budget_turns)
        self.log(f"🎫 Created ticket: {ticket_id}")
        
        # Slack通知: タスク開始
        if self.enable_notifications:
            self._notify_slack(
                f"🚀 *新しいタスク開始*\n\n*Ticket*: `{ticket_id}`\n*Goal*: {goal}\n*Budget*: {budget_turns} turns",
                title="🎯 Orchestrator Started",
                color="#2196F3"
            )
        
        # PACTS制御ループ
        while True:
            ticket = self.ticket_manager.get_ticket(ticket_id)
            
            # 終了判定
            should_stop, reason = self.ticket_manager.should_stop(ticket_id)
            if should_stop:
                self.log(f"🛑 Stopping: {reason}", "INFO")
                self.ticket_manager.close_ticket(
                    ticket_id,
                    "completed" if "achieved" in reason.lower() or "done" in reason.lower() else "failed"  # type: ignore[union-attr]
                )
                break
            
            # 次の役割とアクションを決定
            next_role, next_action = self.decide_next_action(ticket)  # type: ignore
            self.log(f"👤 Next: {next_role} - {next_action}")
            
            # アクション実行
            result = self.execute_action(ticket_id, next_role, next_action)
            
            if not result.get("success"):
                self.log(f"❌ Action failed: {result.get('error')}", "ERROR")
                # 失敗をカウントして、3回連続なら停止
                ticket = self.ticket_manager.get_ticket(ticket_id)
                failure_count = ticket.get("failure_count", 0) + 1  # type: ignore[union-attr]
                self.ticket_manager.update_ticket(ticket_id, {"failure_count": failure_count})
                
                if failure_count >= 3:
                    self.log("❌ Too many failures. Stopping.", "ERROR")
                    self.ticket_manager.close_ticket(ticket_id, "failed")
                    break
            else:
                # 成功したら失敗カウントリセット
                self.ticket_manager.update_ticket(ticket_id, {"failure_count": 0})
            
            # 停滞検知
            if self.ticket_manager.detect_stagnation(ticket_id):
                self.log("⚠️ Stagnation detected", "WARNING")
        
        # 最終結果
        ticket = self.ticket_manager.get_ticket(ticket_id)
        summary = self.ticket_manager.get_summary(ticket_id)
        
        self.log(f"\n{summary}")
        self.log("✅ Orchestration complete")
        
        # Slack通知: タスク完了
        if self.enable_notifications:
            final_status = ticket.get("final_status", "unknown")  # type: ignore[union-attr]
            confidence = ticket["status"]["confidence"]  # type: ignore[index]
            artifacts = ticket.get("artifacts", [])  # type: ignore[union-attr]
            
            if final_status == "completed":
                emoji = "✅"
                color = "good"
                title = "🎉 Task Completed"
            else:
                emoji = "❌"
                color = "danger"
                title = "⚠️ Task Failed"
            
            files_text = "\n".join([f"• `{a['path']}`" for a in artifacts]) if artifacts else "なし"
            
            message = f"""
{emoji} *タスク完了*

*Ticket*: `{ticket_id}`
*Goal*: {goal}
*Status*: {final_status.upper()}
*Confidence*: {confidence:.0%}
*Turns*: {ticket["status"]["turn"]}/{budget_turns}  # type: ignore
*Files*: {len(artifacts)}個

*生成ファイル*:
{files_text}
            """.strip()
            
            self._notify_slack(message, title=title, color=color)
        
        return {
            "ticket_id": ticket_id,
            "goal": goal,
            "final_status": ticket.get("final_status", "unknown"),  # type: ignore[union-attr]
            "confidence": ticket["status"]["confidence"],  # type: ignore[index]
            "turns": ticket["status"]["turn"],  # type: ignore[index]
            "artifacts": ticket["artifacts"],  # type: ignore[index]
            "summary": summary
        }
    
    def decide_next_action(self, ticket: Dict) -> Tuple[str, str]:
        """
        次の役割とアクションを決定
        
        Args:
            ticket: チケットデータ
            
        Returns:
            (role, action)
        """
        status = ticket["status"]
        stage = status["stage"]
        confidence = status["confidence"]
        
        # 低信頼度 → 再計画
        if confidence < 0.5 and stage not in ["init", "plan"]:
            return "remi", "plan"
        
        # ステージに応じた役割決定
        if stage == "init":
            return "remi", "plan"
        elif stage == "plan":
            # 計画ステージでは必ず実装へ進む（confidence関係なく）
            return "luna", "execute"
        elif stage == "execute":
            return "mina", "review"
        elif stage == "review":
            # レビュー後の判定
            if confidence >= 0.9:
                return "done", "done"
            elif confidence >= 0.7:
                return "remi", "review"  # 最終レビュー
            else:
                return "luna", "execute"  # 改善実装
        else:
            # デフォルト
            return "remi", "plan"
    
    def execute_action(self, ticket_id: str, role: str, action: str) -> Dict:
        """
        アクション実行
        
        Args:
            ticket_id: チケットID
            role: 役割（remi/luna/mina）
            action: アクション（plan/execute/review）
            
        Returns:
            実行結果（辞書）
        """
        ticket = self.ticket_manager.get_ticket(ticket_id)
        
        if role == "done":
            self.ticket_manager.update_status(ticket_id, stage="done")
            return {"success": True, "result": "Completed"}
        
        # 履歴サマリー作成
        history_summary = self._create_history_summary(ticket["history"])  # type: ignore[index]
        
        # 役割とアクションに応じて実行
        if role == "remi" and action == "plan":
            return self._execute_remi_plan(ticket_id, ticket, history_summary)  # type: ignore
        elif role == "remi" and action == "review":
            return self._execute_remi_review(ticket_id, ticket)  # type: ignore
        elif role == "luna" and action == "execute":
            return self._execute_luna(ticket_id, ticket)  # type: ignore
        elif role == "mina" and action == "review":
            return self._execute_mina(ticket_id, ticket)  # type: ignore
        else:
            return {"success": False, "error": f"Unknown action: {role}/{action}"}
    
    def _execute_remi_plan(self, ticket_id: str, ticket: Dict, history_summary: str) -> Dict:
        """Remi プランニング実行"""
        self.log("🎯 Remi: Planning...")
        
        result = self.agent_caller.call_remi_plan(
            goal=ticket["goal"],
            context=ticket["context"],
            history_summary=history_summary
        )
        
        if result["success"]:
            plan = result["result"]
            confidence = plan.get("confidence", 0.5)
            
            # 履歴に追加
            self.ticket_manager.add_history(ticket_id, "remi", "plan", plan)
            self.ticket_manager.update_status(ticket_id, stage="plan", confidence=confidence)
            
            self.log(f"✅ Plan created (confidence: {confidence:.2f})")
            return result
        else:
            self.log(f"❌ Planning failed: {result.get('error')}")
            return result
    
    def _execute_remi_review(self, ticket_id: str, ticket: Dict) -> Dict:
        """Remi 最終レビュー実行"""
        self.log("🎯 Remi: Final review...")
        
        # 実行ログ作成
        execution_log = self._create_execution_log(ticket["history"])
        
        result = self.agent_caller.call_remi_review(
            goal=ticket["goal"],
            artifacts=ticket["artifacts"],
            execution_log=execution_log
        )
        
        if result["success"]:
            review = result["result"]
            achievement = review.get("achievement_score", 0.5)
            
            # 履歴に追加
            self.ticket_manager.add_history(ticket_id, "remi", "review", review)
            self.ticket_manager.update_status(ticket_id, confidence=achievement)
            
            # next_actionに応じてステージ更新
            next_action = review.get("next_action", "done")
            if next_action == "done":
                self.ticket_manager.update_status(ticket_id, stage="done")
            elif next_action == "improve":
                self.ticket_manager.update_status(ticket_id, stage="execute")
            
            self.log(f"✅ Review complete (achievement: {achievement:.2f}, next: {next_action})")
            return result
        else:
            self.log(f"❌ Review failed: {result.get('error')}")
            return result
    
    def _execute_luna(self, ticket_id: str, ticket: Dict) -> Dict:
        """Luna 実行"""
        self.log("⚙️ Luna: Executing...")
        
        # プランから最初のステップを取得
        plan = self._get_latest_plan(ticket["history"])
        if not plan:
            self.log("❌ No plan found")
            return {"success": False, "error": "No plan found"}
        
        steps = plan.get("plan", {}).get("steps", [])
        if not steps:
            self.log("❌ No steps in plan")
            return {"success": False, "error": "No steps in plan"}
        
        # 最初のステップを実行
        step = steps[0]
        
        result = self.agent_caller.call_luna_execute(
            goal=ticket["goal"],
            step=step,
            context=ticket["context"]
        )
        
        if result["success"]:
            execution = result["result"]
            
            # 成果物を保存
            if execution.get("code"):
                artifacts = execution.get("artifacts", [])
                for artifact in artifacts:
                    if artifact.get("type") == "file":
                        # ファイルに保存
                        file_path = artifact.get("path")
                        if file_path:
                            os.makedirs(os.path.dirname(file_path), exist_ok=True)
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(execution["code"])
                            
                            self.ticket_manager.add_artifact(
                                ticket_id,
                                "file",
                                file_path,
                                artifact.get("description", "")
                            )
                            self.log(f"💾 Saved: {file_path}")
            
            # 履歴に追加
            self.ticket_manager.add_history(ticket_id, "luna", "execute", execution)
            self.ticket_manager.update_status(ticket_id, stage="execute", confidence=0.6)
            
            self.log("✅ Execution complete")
            return result
        else:
            self.log(f"❌ Execution failed: {result.get('error')}")
            return result
    
    def _execute_mina(self, ticket_id: str, ticket: Dict) -> Dict:
        """Mina QAレビュー実行"""
        self.log("🔍 Mina: Reviewing...")
        
        # プランとコードを取得
        plan = self._get_latest_plan(ticket["history"])
        code = self._get_latest_code(ticket["history"])
        
        result = self.agent_caller.call_mina_review(
            goal=ticket["goal"],
            artifacts=ticket["artifacts"],
            plan=plan,  # type: ignore
            code=code  # type: ignore
        )
        
        if result["success"]:
            review = result["result"]
            achievement = review.get("achievement_score", 0.5)
            
            # 履歴に追加
            self.ticket_manager.add_history(ticket_id, "mina", "review", review)
            self.ticket_manager.update_status(ticket_id, stage="review", confidence=achievement)
            
            self.log(f"✅ QA complete (achievement: {achievement:.2f})")
            return result
        else:
            self.log(f"❌ QA failed: {result.get('error')}")
            return result
    
    def _create_history_summary(self, history: list) -> str:
        """履歴サマリー作成"""
        if not history:
            return "新規プロジェクト"
        
        summary_parts = []
        for entry in history[-3:]:  # 最新3件
            role = entry.get("role", "unknown")
            action = entry.get("action", "unknown")
            summary_parts.append(f"{role}が{action}を実行")
        
        return ", ".join(summary_parts)
    
    def _create_execution_log(self, history: list) -> str:
        """実行ログ作成"""
        log_parts = []
        for entry in history:
            role = entry.get("role", "unknown")
            action = entry.get("action", "unknown")
            timestamp = entry.get("timestamp", "N/A")
            log_parts.append(f"[{timestamp}] {role}: {action}")
        
        return "\n".join(log_parts)
    
    def _get_latest_plan(self, history: list) -> Optional[Dict]:
        """最新のプランを取得"""
        for entry in reversed(history):
            if entry.get("role") == "remi" and entry.get("action") == "plan":
                return entry.get("output")
        return None
    
    def _get_latest_code(self, history: list) -> Optional[str]:
        """最新のコードを取得"""
        for entry in reversed(history):
            if entry.get("role") == "luna" and entry.get("action") == "execute":
                output = entry.get("output", {})
                return output.get("code", "")
        return None


if __name__ == "__main__":
    import sys
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # テスト実行
    orchestrator = TrinityOrchestrator()
    
    result = orchestrator.run(
        goal="シンプルな計算機アプリを作成（加算・減算のみ）",
        context=["Python", "CLI", "関数化すること"],
        budget_turns=10
    )
    
    print("\n" + "="*60)
    print("📊 Final Result:")
    print("="*60)
    print(json.dumps(result, ensure_ascii=False, indent=2))

