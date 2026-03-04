#!/usr/bin/env python3
"""
ManaOS v3 Self Evolution System
自己進化エンジン - Reflectionデータから学習して進化する
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# パス設定
TRINITY_WORKSPACE = Path("/root/trinity_workspace")
REFLECTION_DIR = TRINITY_WORKSPACE / "shared" / "memory"
TASKS_FILE = TRINITY_WORKSPACE / "shared" / "tasks.json"
EVOLUTION_STATE_FILE = TRINITY_WORKSPACE / "shared" / "evolution_state.json"
REWARD_HISTORY_FILE = TRINITY_WORKSPACE / "shared" / "reward_history.json"
PROMETHEUS_EXPORT_DIR = Path("/var/lib/node_exporter/textfile_collector")


class SelfEvolutionEngine:
    """自己進化エンジン"""

    def __init__(self):
        logger.info("🧬 ManaOS Self Evolution Engine 初期化中...")

        self.agents = ["remi", "luna", "mina", "aria"]
        self.evolution_state = self._load_evolution_state()
        self.reward_history = self._load_reward_history()

        logger.info("✅ 進化エンジン準備完了")

    def _load_evolution_state(self) -> Dict:
        """進化状態を読み込み"""
        if EVOLUTION_STATE_FILE.exists():
            try:
                with open(EVOLUTION_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"進化状態読み込みエラー: {e}")

        return {
            "last_run": None,
            "total_cycles": 0,
            "agent_confidence": {agent: 0.5 for agent in self.agents},
            "evolution_rate": 0.0
        }

    def _load_reward_history(self) -> List[Dict]:
        """報酬履歴を読み込み"""
        if REWARD_HISTORY_FILE.exists():
            try:
                with open(REWARD_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"報酬履歴読み込みエラー: {e}")

        return []

    def _save_evolution_state(self):
        """進化状態を保存"""
        try:
            EVOLUTION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(EVOLUTION_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.evolution_state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"進化状態保存エラー: {e}")

    def _save_reward_history(self):
        """報酬履歴を保存"""
        try:
            REWARD_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            # 直近30日分のみ保持
            cutoff = datetime.now() - timedelta(days=30)
            filtered = [
                r for r in self.reward_history
                if datetime.fromisoformat(r.get("timestamp", "2000-01-01")) >= cutoff
            ]
            with open(REWARD_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(filtered, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"報酬履歴保存エラー: {e}")

    def load_tasks(self) -> List[Dict]:
        """タスクデータを読み込み"""
        if not TASKS_FILE.exists():
            logger.warning("タスクファイルが見つかりません")
            return []

        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"タスク読み込みエラー: {e}")
            return []

    def load_reflection_data(self, agent: str, days: int = 7) -> List[Dict]:
        """Reflectionデータを読み込み"""
        reflections = []
        cutoff_date = datetime.now() - timedelta(days=days)

        reflection_files = sorted(
            REFLECTION_DIR.glob(f"reflection_{agent}_*.json"),
            reverse=True
        )

        for file in reflection_files:
            try:
                # ファイル名から日付を抽出
                date_str = file.stem.split('_')[2]  # reflection_remi_20251102.json
                file_date = datetime.strptime(date_str, "%Y%m%d")

                if file_date < cutoff_date:
                    continue

                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    reflections.append({
                        "date": file_date.isoformat(),
                        "agent": agent,
                        "data": data
                    })
            except Exception as e:
                logger.debug(f"Reflection読み込みスキップ: {file.name} - {e}")

        return sorted(reflections, key=lambda x: x["date"])

    def calculate_reward_from_tasks(self, tasks: List[Dict], agent: str) -> float:
        """タスクから報酬を計算"""
        if not tasks:
            return 0.0

        # エージェントに関連するタスクをフィルタ
        agent_tasks = [
            t for t in tasks
            if t.get("assigned_to", "").lower() == agent.lower() or
               t.get("executed_by", "").lower() == agent.lower() or
               t.get("reviewed_by", "").lower() == agent.lower()
        ]

        if not agent_tasks:
            return 0.0

        # 完了したタスクのみ
        completed_tasks = [t for t in agent_tasks if t.get("status") == "done"]

        if not completed_tasks:
            return 0.0

        # 報酬計算
        total_reward = 0.0

        for task in completed_tasks:
            # 基本報酬: タスク完了 = 0.1
            reward = 0.1

            # レビュースコアによるボーナス
            review_result = task.get("review_result", {})
            if review_result.get("passed"):
                score = review_result.get("score", 0.5)
                reward += score * 0.5  # スコアの50%を追加

            # 優先度によるボーナス
            priority = task.get("priority", 2)
            if priority == 3:  # 高優先度
                reward += 0.1

            total_reward += reward

        # 成功率も考慮
        success_rate = len(completed_tasks) / len(agent_tasks)
        total_reward *= success_rate

        # 0.0-1.0に正規化
        return min(1.0, total_reward)

    def calculate_qsr_score(self, reflection_data: List[Dict], reward: float) -> Dict:
        """QSR（Quality Score with Reflection）スコアを計算"""
        if not reflection_data:
            return {
                "qsr_score": 0.5,
                "reflection_confidence": 0.0,
                "learning_delta": 0.0,
                "message": "Insufficient data",
                "total_actions": 0,
                "success_rate": 0.0
            }

        # 最新のReflectionデータを取得
        latest = reflection_data[-1]["data"]
        previous_qsr = latest.get("qsr_metrics", {}).get("qsr_score", 0.5)

        # タスクからの報酬を反映
        task_reward = reward

        # Reflectionログから成功アクション数をカウント
        total_actions = 0
        successful_actions = 0

        for ref in reflection_data:
            qsr = ref["data"].get("qsr_metrics", {})
            actions = qsr.get("total_actions", 0)
            if actions > 0:
                total_actions += actions
                success_rate = qsr.get("success_rate", 0.0)
                successful_actions += actions * success_rate

        success_rate = successful_actions / total_actions if total_actions > 0 else 0.0

        # QSRスコア計算
        # 基本スコア: タスク報酬 * 0.6 + 成功率 * 0.4
        qsr_score = (task_reward * 0.6) + (success_rate * 0.4)

        # 前回との差分
        learning_delta = (qsr_score - previous_qsr) * 100

        # 信頼度: データ量に基づく
        reflection_confidence = min(1.0, len(reflection_data) / 7.0)  # 7日分で最大

        return {
            "qsr_score": round(qsr_score, 2),
            "reflection_confidence": round(reflection_confidence, 2),
            "learning_delta": round(learning_delta, 1),
            "message": "Learning in progress" if total_actions > 0 else "Insufficient data",
            "total_actions": total_actions,
            "success_rate": round(success_rate, 2)
        }

    def generate_improvements(self, qsr_metrics: Dict, agent: str) -> List[str]:
        """改善提案を生成"""
        improvements = []

        if qsr_metrics["reflection_confidence"] < 0.3:
            improvements.append("より多くの行動データを収集することで、学習精度が向上します")

        if qsr_metrics["learning_delta"] < 0:
            improvements.append("最近のパフォーマンスが低下しています。原因の分析が必要です")
        elif qsr_metrics["learning_delta"] > 0:
            improvements.append("順調に学習が進んでいます。現在のアプローチを継続してください")

        if qsr_metrics["success_rate"] < 0.7:
            improvements.append(f"{agent}の成功率が{qsr_metrics['success_rate']:.1%}です。実行方法の見直しを検討してください")

        if qsr_metrics["total_actions"] < 5:
            improvements.append("行動データが不足しています。より多くのタスクを実行してください")

        return improvements

    def update_reflection(self, agent: str):
        """Reflectionデータを更新"""
        logger.info(f"🔄 {agent}のReflection更新中...")

        # データ読み込み
        tasks = self.load_tasks()
        reflection_data = self.load_reflection_data(agent, days=7)

        # 報酬計算
        reward = self.calculate_reward_from_tasks(tasks, agent)

        # QSRスコア計算
        qsr_metrics = self.calculate_qsr_score(reflection_data, reward)

        # 改善提案生成
        improvements = self.generate_improvements(qsr_metrics, agent)

        # 新しいReflectionデータ作成
        today = datetime.now()
        summary = "総合評価: "
        if qsr_metrics["qsr_score"] >= 0.8:
            summary += "優秀"
        elif qsr_metrics["qsr_score"] >= 0.6:
            summary += "良好"
        elif qsr_metrics["qsr_score"] >= 0.4:
            summary += "普通"
        else:
            summary += "要改善"

        summary += f" (QSR: {qsr_metrics['qsr_score']})\n"
        summary += f"学習進捗: {qsr_metrics['learning_delta']:+.1f}%\n\n"

        if improvements:
            summary += "改善提案:\n"
            for imp in improvements:
                summary += f"- {imp}\n"
        else:
            summary += "改善提案: なし（順調）"

        new_reflection = {
            "agent": agent,
            "period_days": 1,
            "timestamp": today.isoformat(),
            "qsr_metrics": qsr_metrics,
            "improvements": improvements,
            "summary": summary
        }

        # 保存
        reflection_file = REFLECTION_DIR / f"reflection_{agent}_{today.strftime('%Y%m%d')}.json"
        try:
            reflection_file.parent.mkdir(parents=True, exist_ok=True)
            with open(reflection_file, 'w', encoding='utf-8') as f:
                json.dump(new_reflection, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ {agent}のReflection更新完了: QSR={qsr_metrics['qsr_score']}, Δ={qsr_metrics['learning_delta']}")
        except Exception as e:
            logger.error(f"❌ Reflection保存エラー: {e}")

        # 報酬履歴に記録
        self.reward_history.append({
            "timestamp": today.isoformat(),
            "agent": agent,
            "reward": reward,
            "qsr_score": qsr_metrics["qsr_score"],
            "learning_delta": qsr_metrics["learning_delta"]
        })

        return new_reflection

    def run_evolution_cycle(self):
        """進化サイクルを実行"""
        logger.info("🚀 進化サイクル開始...")

        cycle_start = datetime.now()
        results = {}

        # 各エージェントのReflection更新
        for agent in self.agents:
            try:
                result = self.update_reflection(agent)
                results[agent] = result
            except Exception as e:
                logger.error(f"❌ {agent}の進化処理エラー: {e}")
                results[agent] = None

        # 進化状態更新
        self.evolution_state["last_run"] = cycle_start.isoformat()
        self.evolution_state["total_cycles"] += 1

        # 平均進化率計算
        deltas = [
            r["qsr_metrics"]["learning_delta"]
            for r in results.values() if r
        ]
        if deltas:
            avg_delta = sum(deltas) / len(deltas)
            self.evolution_state["evolution_rate"] = avg_delta
            logger.info(f"📊 平均進化率: {avg_delta:+.1f}%")

        # エージェント信頼度更新
        for agent, result in results.items():
            if result:
                confidence = result["qsr_metrics"]["reflection_confidence"]
                self.evolution_state["agent_confidence"][agent] = confidence

        # 保存
        self._save_evolution_state()
        self._save_reward_history()

        # Prometheusメトリクスエクスポート
        self._export_prometheus_metrics(results)

        logger.info("✅ 進化サイクル完了")

        return results

    def _export_prometheus_metrics(self, results: Dict):
        """Prometheusメトリクスをエクスポート"""
        try:
            PROMETHEUS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            metrics_file = PROMETHEUS_EXPORT_DIR / "manaos_evolution.prom"

            timestamp = int(time.time() * 1000)
            lines = []

            # 各エージェントのメトリクス
            for agent, result in results.items():
                if not result:
                    continue

                qsr = result["qsr_metrics"]

                # QSRスコア
                lines.append(
                    f'manaos_evolution_qsr_score{{agent="{agent}"}} {qsr["qsr_score"]} {timestamp}'
                )

                # Learning Delta
                lines.append(
                    f'manaos_evolution_learning_delta{{agent="{agent}"}} {qsr["learning_delta"]} {timestamp}'
                )

                # Reflection Confidence
                lines.append(
                    f'manaos_evolution_reflection_confidence{{agent="{agent}"}} {qsr["reflection_confidence"]} {timestamp}'
                )

                # Success Rate
                lines.append(
                    f'manaos_evolution_success_rate{{agent="{agent}"}} {qsr.get("success_rate", 0.0)} {timestamp}'
                )

                # Total Actions
                lines.append(
                    f'manaos_evolution_total_actions{{agent="{agent}"}} {qsr.get("total_actions", 0)} {timestamp}'
                )

            # 全体統計
            if self.evolution_state.get("evolution_rate") is not None:
                lines.append(
                    f'manaos_evolution_rate {self.evolution_state["evolution_rate"]} {timestamp}'
                )

            lines.append(
                f'manaos_evolution_total_cycles {self.evolution_state.get("total_cycles", 0)} {timestamp}'
            )

            # ファイルに書き込み
            with open(metrics_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')

            logger.info(f"📊 Prometheusメトリクスエクスポート完了: {len(lines)}件")

        except Exception as e:
            logger.warning(f"⚠️ Prometheusメトリクスエクスポートエラー: {e}")


def main():
    """メイン関数"""
    try:
        engine = SelfEvolutionEngine()
        results = engine.run_evolution_cycle()

        # 結果サマリー
        logger.info("\n📊 進化結果サマリー:")
        for agent, result in results.items():
            if result:
                qsr = result["qsr_metrics"]
                logger.info(
                    f"  {agent}: QSR={qsr['qsr_score']:.2f}, "
                    f"Δ={qsr['learning_delta']:+.1f}%, "
                    f"Confidence={qsr['reflection_confidence']:.2f}"
                )
            else:
                logger.warning(f"  {agent}: 処理失敗")

        logger.info("\n✅ 進化システム実行完了")
        return 0

    except Exception as e:
        logger.error(f"❌ 進化システムエラー: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

