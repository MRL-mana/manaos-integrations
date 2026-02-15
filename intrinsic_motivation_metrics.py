#!/usr/bin/env python3
"""
内発的動機づけの数値化システム
改善意欲スコア、自己改善実行率、週次トレンド可視化
"""

import json
import httpx
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger

logger = get_logger(__name__)


@dataclass
class MotivationMetrics:
    """内発的動機づけメトリクス"""
    date: str
    improvement_desire_score: float  # 改善意欲スコア（0-100）
    self_improvement_execution_rate: float  # 自己改善実行率（0-1）
    tasks_generated: int  # 生成されたタスク数
    tasks_executed: int  # 実行されたタスク数
    playbooks_created: int  # 作成されたPlaybook数
    learning_actions: int  # 学習アクション数


class IntrinsicMotivationMetrics:
    """内発的動機づけメトリクスシステム"""

    def __init__(
        self,
        intrinsic_motivation_url: str = "http://127.0.0.1:5130",
        learning_system_url: str = "http://127.0.0.1:5126",
        storage_path: Optional[Path] = None
    ):
        """
        初期化

        Args:
            intrinsic_motivation_url: Intrinsic Motivation API URL
            learning_system_url: Learning System API URL
            storage_path: メトリクス保存パス
        """
        self.intrinsic_motivation_url = intrinsic_motivation_url
        self.learning_system_url = learning_system_url
        self.storage_path = storage_path or Path(__file__).parent / "intrinsic_motivation_metrics.json"

        # メトリクスデータ
        self.metrics_history: List[MotivationMetrics] = []
        self._load_metrics()

        logger.info("✅ Intrinsic Motivation Metrics System初期化完了")

    def _load_metrics(self):
        """メトリクスを読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metrics_history = [
                        MotivationMetrics(**m) for m in data.get("metrics", [])
                    ]
            except Exception as e:
                logger.warning(f"メトリクス読み込みエラー: {e}")
                self.metrics_history = []
        else:
            self.metrics_history = []

    def _save_metrics(self):
        """メトリクスを保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "metrics": [asdict(m) for m in self.metrics_history],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"メトリクス保存エラー: {e}")

    def calculate_improvement_desire_score(self) -> float:
        """
        改善意欲スコアを計算（0-100）

        計算要素:
        - アイドル時間の活用率
        - 生成されたタスク数
        - 実行されたタスク数
        - Playbook作成数
        - 学習アクション数
        """
        try:
            # Intrinsic Motivation Systemから状態を取得
            response = httpx.get(f"{self.intrinsic_motivation_url}/api/status", timeout=5)
            if response.status_code != 200:
                return 0.0

            status = response.json()

            # 基本スコア（アイドル時間を活用しているか）
            is_idle = status.get("is_idle", False)
            base_score = 50.0 if is_idle else 30.0

            # タスク生成スコア
            tasks_count = status.get("intrinsic_tasks_count", 0)
            task_score = min(tasks_count * 10, 30.0)

            # Learning Systemから学習統計を取得
            try:
                learning_response = httpx.get(f"{self.learning_system_url}/api/analyze", timeout=5)
                if learning_response.status_code == 200:
                    learning_stats = learning_response.json()
                    patterns_learned = learning_stats.get("patterns_learned", 0)
                    learning_score = min(patterns_learned * 2, 20.0)
                else:
                    learning_score = 0.0
            except Exception:
                learning_score = 0.0

            total_score = base_score + task_score + learning_score
            return min(total_score, 100.0)

        except Exception as e:
            logger.warning(f"改善意欲スコア計算エラー: {e}")
            return 0.0

    def calculate_execution_rate(self) -> float:
        """
        自己改善実行率を計算（0-1）

        Returns:
            実行率（生成されたタスクのうち実行された割合）
        """
        if not self.metrics_history:
            return 0.0

        # 直近7日間のデータを使用
        recent_metrics = [
            m for m in self.metrics_history
            if (date.today() - date.fromisoformat(m.date)).days <= 7
        ]

        if not recent_metrics:
            return 0.0

        total_generated = sum(m.tasks_generated for m in recent_metrics)
        total_executed = sum(m.tasks_executed for m in recent_metrics)

        if total_generated == 0:
            return 0.0

        return total_executed / total_generated

    def collect_daily_metrics(self) -> MotivationMetrics:
        """
        今日のメトリクスを収集

        Returns:
            今日のメトリクス
        """
        today = date.today().isoformat()

        # 既存のメトリクスをチェック
        existing = next((m for m in self.metrics_history if m.date == today), None)
        if existing:
            return existing

        # 新しいメトリクスを計算
        improvement_desire_score = self.calculate_improvement_desire_score()
        execution_rate = self.calculate_execution_rate()

        # Intrinsic Motivation Systemからタスク情報を取得
        try:
            response = httpx.post(f"{self.intrinsic_motivation_url}/api/generate-tasks", timeout=10)
            if response.status_code == 200:
                tasks_data = response.json()
                tasks_generated = tasks_data.get("count", 0)
            else:
                tasks_generated = 0
        except Exception:
            tasks_generated = 0

        # Learning Systemから学習統計を取得
        tasks_executed = 0
        learning_actions = 0
        try:
            response = httpx.get(f"{self.learning_system_url}/api/analyze", timeout=5)
            if response.status_code == 200:
                learning_stats = response.json()
                learning_actions = learning_stats.get("total_actions_recorded", 0)
                # 成功率データからタスク実行数を集計
                success_rates = learning_stats.get("success_rates", {})
                tasks_executed = sum(
                    v.get("total", 0) for v in success_rates.values()
                )
        except Exception:
            pass

        # Playbook数を取得（Obsidianから）
        playbooks_count = self._count_playbooks()

        metrics = MotivationMetrics(
            date=today,
            improvement_desire_score=improvement_desire_score,
            self_improvement_execution_rate=execution_rate,
            tasks_generated=tasks_generated,
            tasks_executed=tasks_executed,
            playbooks_created=playbooks_count,
            learning_actions=learning_actions
        )

        # 履歴に追加
        self.metrics_history.append(metrics)

        # 最新30日分のみ保持
        self.metrics_history = self.metrics_history[-30:]

        # 保存
        self._save_metrics()

        return metrics

    def _count_playbooks(self) -> int:
        """Playbook数をカウント"""
        try:
            vault_path = Path.home() / "Documents" / "Obsidian Vault"
            if not vault_path.exists():
                vault_path = Path.home() / "Documents" / "Obsidian"
            if not vault_path.exists():
                return 0

            playbooks_dir = vault_path / "ManaOS" / "System" / "Playbooks"
            if not playbooks_dir.exists():
                return 0

            # .mdファイルをカウント
            playbook_files = list(playbooks_dir.glob("*.md"))
            return len(playbook_files)
        except Exception:
            return 0

    def get_weekly_trend(self) -> Dict[str, Any]:
        """
        週次トレンドを取得

        Returns:
            週次トレンドデータ
        """
        if not self.metrics_history:
            return {
                "trend": [],
                "average_score": 0.0,
                "average_execution_rate": 0.0
            }

        # 直近7日間のデータ
        recent_metrics = [
            m for m in self.metrics_history
            if (date.today() - date.fromisoformat(m.date)).days <= 7
        ]

        if not recent_metrics:
            return {
                "trend": [],
                "average_score": 0.0,
                "average_execution_rate": 0.0
            }

        trend = [
            {
                "date": m.date,
                "improvement_desire_score": m.improvement_desire_score,
                "execution_rate": m.self_improvement_execution_rate,
                "tasks_generated": m.tasks_generated,
                "tasks_executed": m.tasks_executed
            }
            for m in recent_metrics
        ]

        avg_score = sum(m.improvement_desire_score for m in recent_metrics) / len(recent_metrics)
        avg_execution_rate = sum(m.self_improvement_execution_rate for m in recent_metrics) / len(recent_metrics)

        return {
            "trend": trend,
            "average_score": avg_score,
            "average_execution_rate": avg_execution_rate,
            "total_tasks_generated": sum(m.tasks_generated for m in recent_metrics),
            "total_tasks_executed": sum(m.tasks_executed for m in recent_metrics)
        }

    def get_summary(self) -> Dict[str, Any]:
        """サマリーを取得"""
        today_metrics = self.collect_daily_metrics()
        weekly_trend = self.get_weekly_trend()

        return {
            "today": {
                "improvement_desire_score": today_metrics.improvement_desire_score,
                "execution_rate": today_metrics.self_improvement_execution_rate,
                "tasks_generated": today_metrics.tasks_generated,
                "tasks_executed": today_metrics.tasks_executed,
                "playbooks_created": today_metrics.playbooks_created,
                "learning_actions": today_metrics.learning_actions
            },
            "weekly": weekly_trend,
            "timestamp": datetime.now().isoformat()
        }


# Flask APIサーバー
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

metrics_system = None

def init_metrics_system():
    """メトリクスシステムを初期化"""
    global metrics_system
    if metrics_system is None:
        metrics_system = IntrinsicMotivationMetrics()
    return metrics_system

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Intrinsic Motivation Metrics"})

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """サマリーを取得"""
    system = init_metrics_system()
    return jsonify(system.get_summary())

@app.route('/api/weekly-trend', methods=['GET'])
def get_weekly_trend():
    """週次トレンドを取得"""
    system = init_metrics_system()
    return jsonify(system.get_weekly_trend())

@app.route('/api/collect', methods=['POST'])
def collect_metrics():
    """今日のメトリクスを収集"""
    system = init_metrics_system()
    metrics = system.collect_daily_metrics()
    return jsonify(asdict(metrics))

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5131
    logger.info(f"🚀 Intrinsic Motivation Metrics API Server起動 (ポート: {port})")
    app.run(host="0.0.0.0", port=port, debug=False)
