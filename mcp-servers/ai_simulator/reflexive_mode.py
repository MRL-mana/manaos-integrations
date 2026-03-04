"""
Stage D: Reflexive Mode（反応・予測）
行動ログから次の行動を提案する機能
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

# データディレクトリ
DATA_DIR = Path(os.getenv("AISIM_DATA_DIR", "/root/ai_simulator/data/tasks"))
ACTION_LOG_FILE = DATA_DIR / "action_log.json"

class ReflexiveAnalyzer:
    """反応分析エンジン"""

    def __init__(self):
        self.action_log = []
        self.load_action_log()

    def load_action_log(self):
        """行動ログを読み込む"""
        if ACTION_LOG_FILE.exists():
            try:
                with open(ACTION_LOG_FILE, "r", encoding="utf-8") as f:
                    self.action_log = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load action log: {e}")
                self.action_log = []

    def log_action(self, action_type: str, task_name: str, parameters: Dict[str, Any],
                   confidence: float, outcome: str):
        """行動を記録"""
        action = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,  # task_execution, auto_approval, manual_approval
            "task_name": task_name,
            "parameters": parameters,
            "confidence": confidence,
            "outcome": outcome,  # success, failure, pending
        }

        self.action_log.append(action)
        # 最新5000件のみ保持
        self.action_log = self.action_log[-5000:]

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(ACTION_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.action_log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save action log: {e}")

    def analyze_patterns(self, days: int = 7) -> Dict[str, Any]:
        """行動パターンを分析"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_actions = [
            a for a in self.action_log
            if datetime.fromisoformat(a["timestamp"]) >= cutoff
        ]

        if not recent_actions:
            return {
                "total_actions": 0,
                "patterns": {},
                "recommendations": []
            }

        # タスク実行頻度
        task_counts = Counter(a["task_name"] for a in recent_actions)

        # 成功/失敗率
        success_rate = sum(1 for a in recent_actions if a["outcome"] == "success") / len(recent_actions)

        # 時間帯別パターン
        time_patterns = defaultdict(int)
        for action in recent_actions:
            hour = datetime.fromisoformat(action["timestamp"]).hour
            time_patterns[hour] += 1

        # 信頼度トレンド
        confidences = [a["confidence"] for a in recent_actions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7

        return {
            "total_actions": len(recent_actions),
            "patterns": {
                "task_frequency": dict(task_counts.most_common(5)),
                "success_rate": success_rate,
                "time_distribution": dict(time_patterns),
                "avg_confidence": avg_confidence
            },
            "recommendations": self._generate_recommendations(recent_actions, task_counts, success_rate)
        }

    def _generate_recommendations(self, actions: List[Dict], task_counts: Counter,
                                 success_rate: float) -> List[Dict[str, Any]]:
        """推奨行動を生成"""
        recommendations = []

        # よく使われるタスクの定期実行提案
        for task_name, count in task_counts.most_common(3):
            if count >= 3:  # 3回以上実行されている
                recommendations.append({
                    "type": "scheduled_task",
                    "task_name": task_name,
                    "reason": f"過去7日間で{count}回実行されています。定期実行を検討してください。",
                    "priority": "medium",
                    "confidence": min(0.8, success_rate + 0.1)
                })

        # 成功率高すぎるタスクの自動化提案
        if success_rate > 0.9:
            most_successful = Counter(
                a["task_name"] for a in actions
                if a["outcome"] == "success"
            ).most_common(1)
            if most_successful:
                task_name, _ = most_successful[0]
                recommendations.append({
                    "type": "auto_approval",
                    "task_name": task_name,
                    "reason": "成功率が高いため、自動承認の検討をお勧めします。",
                    "priority": "high",
                    "confidence": 0.85
                })

        # 失敗率が高いタスクの調査提案
        failed_tasks = Counter(
            a["task_name"] for a in actions
            if a["outcome"] == "failure"
        )
        if failed_tasks:
            most_failed = failed_tasks.most_common(1)[0]
            recommendations.append({
                "type": "investigation",
                "task_name": most_failed[0],
                "reason": f"過去に{most_failed[1]}回失敗しています。原因調査を推奨します。",
                "priority": "high",
                "confidence": 0.75
            })

        return recommendations

    def suggest_next_action(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """次の行動を提案"""
        analysis = self.analyze_patterns(days=7)

        if not analysis["recommendations"]:
            return {
                "suggestion": None,
                "message": "現時点で推奨される行動はありません"
            }

        # 優先度順にソート
        recommendations = sorted(
            analysis["recommendations"],
            key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]],
            reverse=True
        )

        top_recommendation = recommendations[0]

        return {
            "suggestion": top_recommendation,
            "all_recommendations": recommendations,
            "analysis_summary": {
                "total_actions": analysis["total_actions"],
                "success_rate": analysis["patterns"]["success_rate"],
                "avg_confidence": analysis["patterns"]["avg_confidence"]
            }
        }

    def auto_nudge(self) -> Optional[Dict[str, Any]]:
        """自動お節介（重要度が高い場合のみ提案）"""
        suggestion = self.suggest_next_action()

        if suggestion["suggestion"] and suggestion["suggestion"]["priority"] == "high":
            return suggestion

        return None

    def predict_next_actions(self, horizon_hours: int = 24) -> List[Dict[str, Any]]:
        """未来の行動を予測"""
        analysis = self.analyze_patterns(days=7)

        if not analysis["patterns"]:
            return []

        predictions = []

        # 時間帯パターンから予測
        time_patterns = analysis["patterns"].get("time_distribution", {})
        if time_patterns:
            peak_hours = sorted(time_patterns.items(), key=lambda x: x[1], reverse=True)[:3]
            for hour, count in peak_hours:
                predictions.append({
                    "type": "predicted_task_execution",
                    "hour": hour,
                    "confidence": min(0.8, count / 10.0),  # 簡易信頼度
                    "reason": f"過去7日間で{hour}時台に{count}回実行されました"
                })

        # 頻繁なタスクから予測
        task_frequency = analysis["patterns"].get("task_frequency", {})
        if task_frequency:
            for task_name, count in list(task_frequency.items())[:3]:
                predictions.append({
                    "type": "predicted_task",
                    "task_name": task_name,
                    "confidence": min(0.9, count / 20.0),
                    "reason": f"過去7日間で{count}回実行されました"
                })

        return predictions

    def get_context_aware_suggestions(self, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """文脈を理解した提案"""
        suggestions = []

        # 現在の時刻を考慮
        current_hour = datetime.now().hour
        analysis = self.analyze_patterns(days=7)
        time_patterns = analysis["patterns"].get("time_distribution", {})

        if current_hour in time_patterns:
            suggestions.append({
                "type": "time_based",
                "message": f"この時間帯（{current_hour}時）は通常タスク実行が多い時間です",
                "confidence": 0.7,
                "priority": "medium"
            })

        # Evolution Mode状態を考慮
        evolution_mode = current_context.get("evolution_mode", "off")
        if evolution_mode == "shadow":
            suggestions.append({
                "type": "evolution_aware",
                "message": "Shadow Mode中: 安全に実験できる絶好の機会です",
                "confidence": 0.9,
                "priority": "high"
            })

        # Vision Goalsを考慮
        active_goals_count = current_context.get("active_goals_count", 0)
        if active_goals_count > 0:
            avg_progress = current_context.get("average_progress", 0)
            if avg_progress < 50:
                suggestions.append({
                    "type": "goal_aware",
                    "message": f"アクティブなゴールが{active_goals_count}件ありますが、平均進捗が{avg_progress:.1f}%と低いです",
                    "confidence": 0.8,
                    "priority": "high"
                })

        return suggestions



