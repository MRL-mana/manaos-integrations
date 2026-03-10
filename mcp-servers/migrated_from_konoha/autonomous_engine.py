#!/usr/bin/env python3
"""
Trinity Living System - Autonomous Engine
完全自律意思決定エンジン
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import requests

sys.path.insert(0, '/root/trinity_workspace/orchestrator')
from ticket_manager import TicketManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autonomous_engine")


class AutonomousEngine:
    """完全自律意思決定エンジン"""
    
    def __init__(self, orchestrator_url="http://127.0.0.1:9400"):
        """初期化"""
        self.orchestrator_url = orchestrator_url
        self.ticket_manager = TicketManager()
        
        # 状態管理
        self.last_actions = {
            "email_check": None,
            "task_planning": None,
            "system_health": None
        }
        
        logger.info("✅ Autonomous Engine initialized")
    
    def assess_situation(self) -> Dict[str, float]:
        """
        現在の状況を評価
        
        Returns:
            状況評価（各項目0-1のスコア）
        """
        assessment = {}
        
        # 1. 未処理メールの確認（モック）
        # TODO: 実際のGmail API統合
        pending_emails = 0  # gmail.get_unread_count()
        assessment["email_urgency"] = min(pending_emails / 20.0, 1.0)
        
        # 2. 未完了タスクの確認（モック）
        # TODO: 実際のNotion API統合
        pending_tasks = 0  # notion.get_todo_count()
        assessment["task_urgency"] = min(pending_tasks / 10.0, 1.0)
        
        # 3. システムヘルス確認
        try:
            response = requests.get(f"{self.orchestrator_url}/health", timeout=2)
            assessment["system_health"] = 1.0 if response.status_code == 200 else 0.3
        except:
            assessment["system_health"] = 0.0
        
        # 4. 実行中のチケット確認
        active_tickets = self.ticket_manager.list_active_tickets()
        assessment["workload"] = min(len(active_tickets) / 5.0, 1.0)
        
        logger.info(f"📊 Situation assessment: {assessment}")
        return assessment
    
    def decide_next_action(self, assessment: Dict[str, float]) -> Tuple[Optional[str], float]:
        """
        次のアクションを自律的に決定
        
        Args:
            assessment: 状況評価
            
        Returns:
            (アクション名, 優先度)
        """
        priorities = []
        
        # システムヘルス最優先
        if assessment["system_health"] < 0.5:
            priorities.append(("fix_system", 1.0))
        
        # メール処理
        if assessment["email_urgency"] > 0.7:
            priorities.append(("process_emails", 0.9))
        
        # タスク実行
        if assessment["task_urgency"] > 0.5:
            priorities.append(("work_on_tasks", 0.7))
        
        # 現在の負荷が高い場合は何もしない
        if assessment["workload"] > 0.8:
            priorities.append(("wait", 0.1))
        
        # 定期タスク計画（毎朝9時）
        now = datetime.now()
        if now.hour == 9 and now.minute < 10:
            if not self.last_actions.get("task_planning") or \
               (datetime.now() - self.last_actions["task_planning"]).days >= 1:  # type: ignore[operator]
                priorities.append(("daily_planning", 0.95))
        
        # 優先度最高のアクションを選択
        if priorities:
            action, priority = max(priorities, key=lambda x: x[1])
            logger.info(f"🎯 Decision: {action} (priority: {priority:.2f})")
            return action, priority
        
        return None, 0.0
    
    def execute_action(self, action: str) -> bool:
        """
        アクションを実行
        
        Args:
            action: アクション名
            
        Returns:
            成功したらTrue
        """
        logger.info(f"🚀 Executing autonomous action: {action}")
        
        action_map = {
            "fix_system": self._fix_system,
            "process_emails": self._process_emails,
            "work_on_tasks": self._work_on_tasks,
            "daily_planning": self._daily_planning,
            "wait": lambda: time.sleep(60)
        }
        
        handler = action_map.get(action)
        if handler:
            try:
                handler()
                self.last_actions[action] = datetime.now()  # type: ignore
                logger.info(f"✅ Action completed: {action}")
                return True
            except Exception as e:
                logger.error(f"❌ Action failed: {action} - {e}")
                return False
        else:
            logger.warning(f"⚠️ Unknown action: {action}")
            return False
    
    def _fix_system(self):
        """システム修復"""
        logger.info("🔧 システムヘルスチェック・修復中...")
        # TODO: 実際の修復ロジック実装
    
    def _process_emails(self):
        """メール処理"""
        logger.info("📧 未読メール処理中...")
        # TODO: Gmail API統合
    
    def _work_on_tasks(self):
        """タスク実行"""
        logger.info("📋 タスク実行中...")
        # TODO: Notion TODO統合
    
    def _daily_planning(self):
        """毎日のタスク計画"""
        logger.info("📅 今日のタスク計画中...")
        
        # Orchestratorを呼び出し
        try:
            response = requests.post(
                f"{self.orchestrator_url}/api/orchestrate",
                json={
                    "goal": "今日のタスクを計画して優先順位付け",
                    "context": [
                        "カレンダー確認",
                        "Gmail確認",
                        "Notion TODO確認",
                        "過去パターン参考"
                    ],
                    "budget_turns": 15
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Daily planning complete: {result['ticket_id']}")
        except Exception as e:
            logger.error(f"❌ Daily planning failed: {e}")
    
    def autonomous_loop(self, interval: int = 300):
        """
        完全自律ループ（24時間運転）
        
        Args:
            interval: チェック間隔（秒、デフォルト5分）
        """
        logger.info(f"🧠 Starting autonomous loop (interval: {interval}s)")
        logger.info("🤖 Trinity Living System is now AUTONOMOUS")
        
        try:
            while True:
                # 状況評価
                assessment = self.assess_situation()
                
                # 次のアクション決定
                action, priority = self.decide_next_action(assessment)
                
                # アクション実行
                if action and priority > 0.3:
                    self.execute_action(action)
                else:
                    logger.info("😌 すべて順調。次のチェックまで待機...")
                
                # 待機
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("👋 Autonomous loop stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Trinity Autonomous Engine")
    parser.add_argument("--mode", choices=["autonomous", "assess", "test"], default="autonomous")
    parser.add_argument("--interval", type=int, default=300, help="自律ループ間隔（秒）")
    
    args = parser.parse_args()
    
    engine = AutonomousEngine()
    
    if args.mode == "autonomous":
        # 完全自律モード
        engine.autonomous_loop(interval=args.interval)
    
    elif args.mode == "assess":
        # 現在の状況評価のみ
        assessment = engine.assess_situation()
        action, priority = engine.decide_next_action(assessment)
        
        print(f"\n📊 Current Assessment:")
        for key, value in assessment.items():
            print(f"  {key}: {value:.2f}")
        
        print(f"\n🎯 Recommended Action: {action} (priority: {priority:.2f})")
    
    elif args.mode == "test":
        # テスト実行
        logger.info("🧪 Test mode: Executing daily planning...")
        engine._daily_planning()

