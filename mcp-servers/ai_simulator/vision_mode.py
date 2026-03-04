"""
Stage E: Vision Mode（長期戦略・自己PDCA）
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# データディレクトリ
DATA_DIR = Path(os.getenv("AISIM_DATA_DIR", "/root/ai_simulator/data/tasks"))
GOALS_FILE = DATA_DIR / "goals.json"
PDCA_LOG_FILE = DATA_DIR / "pdca_log.json"

class VisionMode:
    """長期戦略・自己PDCAエンジン"""

    def __init__(self):
        self.goals = []
        self.pdca_history = []
        self.load_data()

    def load_data(self):
        """データを読み込む"""
        # ゴール読み込み
        if GOALS_FILE.exists():
            try:
                with open(GOALS_FILE, "r", encoding="utf-8") as f:
                    self.goals = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load goals: {e}")
                self.goals = []

        # PDCA履歴読み込み
        if PDCA_LOG_FILE.exists():
            try:
                with open(PDCA_LOG_FILE, "r", encoding="utf-8") as f:
                    self.pdca_history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load PDCA history: {e}")
                self.pdca_history = []

    def set_goal(self, goal_name: str, description: str, target_date: str,
                 metrics: Dict[str, Any]) -> Dict[str, Any]:
        """ゴールを設定"""
        goal = {
            "goal_id": f"goal_{int(datetime.now().timestamp())}",
            "goal_name": goal_name,
            "description": description,
            "target_date": target_date,
            "metrics": metrics,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "progress": 0.0
        }

        self.goals.append(goal)
        self.save_goals()

        return goal

    def update_goal_progress(self, goal_id: str, progress: float,
                             evidence: Optional[Dict[str, Any]] = None):
        """ゴールの進捗を更新"""
        for goal in self.goals:
            if goal["goal_id"] == goal_id:
                goal["progress"] = min(100.0, max(0.0, progress))
                if evidence:
                    goal.setdefault("evidence", []).append({
                        "timestamp": datetime.now().isoformat(),
                        **evidence
                    })

                # 進捗100%で完了
                if goal["progress"] >= 100.0:
                    goal["status"] = "completed"
                    goal["completed_at"] = datetime.now().isoformat()

        self.save_goals()

    def save_goals(self):
        """ゴールを保存"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(GOALS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.goals, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save goals: {e}")

    def run_pdca_cycle(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """PDCAサイクルを実行"""
        # Plan: 計画
        plan = self._plan(context)

        # Do: 実行（実際の実行は外部で行われる）
        do_result = {
            "status": "ready",
            "planned_actions": plan["actions"]
        }

        # Check: チェック（実行結果を評価）
        check_result = self._check(context, plan, do_result)

        # Act: 改善
        act_result = self._act(check_result)

        # 履歴に記録
        pdca_entry = {
            "cycle_id": f"pdca_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "plan": plan,
            "do": do_result,
            "check": check_result,
            "act": act_result
        }

        self.pdca_history.append(pdca_entry)
        # 最新100件のみ保持
        self.pdca_history = self.pdca_history[-100:]

        self.save_pdca_history()

        return pdca_entry

    def _plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan: 計画を立てる"""
        # アクティブなゴールから計画を生成
        active_goals = [g for g in self.goals if g["status"] == "active"]

        actions = []
        for goal in active_goals:
            progress = goal["progress"]
            if progress < 100.0:
                # ゴール達成のための推奨アクション
                actions.append({
                    "goal_id": goal["goal_id"],
                    "goal_name": goal["goal_name"],
                    "action_type": "progress_goal",
                    "description": f"{goal['goal_name']}の進捗を進める",
                    "priority": "high" if progress < 50.0 else "medium"
                })

        return {
            "goals_count": len(active_goals),
            "actions": actions,
            "plan_date": datetime.now().isoformat()
        }

    def _check(self, context: Dict[str, Any], plan: Dict[str, Any],
              do_result: Dict[str, Any]) -> Dict[str, Any]:
        """Check: 実行結果を評価"""
        # 簡易評価（実際はもっと詳細な評価が必要）
        evaluation = {
            "success_rate": context.get("success_rate", 0.0),
            "goals_progress": sum(g["progress"] for g in self.goals if g["status"] == "active") / len(self.goals) if self.goals else 0,
            "issues": []
        }

        # 進捗が遅れているゴールを検出
        for goal in self.goals:
            if goal["status"] == "active":
                target_date = datetime.fromisoformat(goal["target_date"])
                days_remaining = (target_date - datetime.now()).days
                if days_remaining < 0 and goal["progress"] < 100:
                    evaluation["issues"].append({
                        "type": "overdue",
                        "goal_id": goal["goal_id"],
                        "message": f"{goal['goal_name']}が期限を超過しています"
                    })

        return evaluation

    def _act(self, check_result: Dict[str, Any]) -> Dict[str, Any]:
        """Act: 改善アクションを決定"""
        improvements = []

        # 成功率が低い場合の改善提案
        if check_result["success_rate"] < 0.7:
            improvements.append({
                "type": "improve_success_rate",
                "action": "信頼度ゲートの調整を検討",
                "priority": "high"
            })

        # ゴール進捗が遅れている場合の改善提案
        if check_result["goals_progress"] < 50.0:
            improvements.append({
                "type": "accelerate_progress",
                "action": "タスク実行頻度の増加を検討",
                "priority": "medium"
            })

        # 問題がある場合の対応
        for issue in check_result["issues"]:
            improvements.append({
                "type": "resolve_issue",
                "issue": issue,
                "action": f"{issue['message']}への対応が必要です",
                "priority": "high"
            })

        return {
            "improvements": improvements,
            "next_cycle_focus": improvements[0]["type"] if improvements else None
        }

    def save_pdca_history(self):
        """PDCA履歴を保存"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(PDCA_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.pdca_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save PDCA history: {e}")

    def get_strategic_summary(self) -> Dict[str, Any]:
        """戦略サマリーを取得"""
        active_goals = [g for g in self.goals if g["status"] == "active"]
        completed_goals = [g for g in self.goals if g["status"] == "completed"]

        avg_progress = sum(g["progress"] for g in active_goals) / len(active_goals) if active_goals else 0

        return {
            "active_goals_count": len(active_goals),
            "completed_goals_count": len(completed_goals),
            "average_progress": avg_progress,
            "recent_pdca_cycles": len([p for p in self.pdca_history
                                      if datetime.fromisoformat(p["timestamp"]) > datetime.now() - timedelta(days=7)]),
            "goals": active_goals[:5]  # 最新5件
        }






