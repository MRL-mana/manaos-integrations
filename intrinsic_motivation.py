#!/usr/bin/env python3
"""
内発的動機づけシステム（Intrinsic Motivation）
Sophia論文に基づく「暇な時間を自己改善のチャンスに変える」機能
"""

import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from _paths import LEARNING_SYSTEM_PORT, METRICS_COLLECTOR_PORT, ORCHESTRATOR_PORT

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("IntrinsicMotivation")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

DEFAULT_ORCHESTRATOR_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}"
DEFAULT_LEARNING_SYSTEM_URL = f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}"
DEFAULT_METRICS_COLLECTOR_URL = f"http://127.0.0.1:{METRICS_COLLECTOR_PORT}"


class TaskCategory(str, Enum):
    """タスクカテゴリ"""

    MEMORY_ORGANIZATION = "memory_organization"  # 記憶の整理
    KNOWLEDGE_ACQUISITION = "knowledge_acquisition"  # 知識の獲得
    PERFORMANCE_IMPROVEMENT = "performance_improvement"  # パフォーマンス改善
    PATTERN_ANALYSIS = "pattern_analysis"  # パターン分析
    DOCUMENTATION = "documentation"  # ドキュメント整理


@dataclass
class IntrinsicTask:
    """内発的タスク"""

    task_id: str
    title: str
    description: str
    category: TaskCategory
    priority: int  # 1-10（10が最高）
    estimated_duration_minutes: int
    long_term_goal_alignment: str  # どの長期目標に貢献するか
    safety_check_passed: bool = False
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class IntrinsicMotivation:
    """内発的動機づけシステム"""

    # ManaOSの長期目標（Sophiaの「知識豊かで信頼できる助手になる」に相当）
    LONG_TERM_GOAL = "知識豊かで信頼できるManaOSアシスタントになる"

    # 5つの憲章（安全性ルール）
    SAFETY_CHARTER = [
        "ユーザーにストレスを与えない",
        "安全でない行動を取らない",
        "重要な設定やデータを変更しない",
        "外部サービスを勝手に操作しない",
        "Autonomy Level 1の範囲内で行動する",
    ]

    def __init__(
        self,
        orchestrator_url: Optional[str] = None,
        learning_system_url: Optional[str] = None,
        metrics_collector_url: Optional[str] = None,
        config_path: Optional[Path] = None,
    ):
        """
        初期化

        Args:
            orchestrator_url: Unified Orchestrator API URL
            learning_system_url: Learning System API URL
            metrics_collector_url: Metrics Collector API URL
            config_path: 設定ファイルのパス
        """
        self.orchestrator_url = orchestrator_url or DEFAULT_ORCHESTRATOR_URL
        self.learning_system_url = learning_system_url or DEFAULT_LEARNING_SYSTEM_URL
        self.metrics_collector_url = metrics_collector_url or DEFAULT_METRICS_COLLECTOR_URL

        self.config_path = config_path or Path(__file__).parent / "intrinsic_motivation_config.json"
        self.config = self._load_config()

        # 内発的タスクのリスト
        self.intrinsic_tasks: List[IntrinsicTask] = []

        # 最後の外部タスク実行時刻
        self.last_external_task_time: Optional[datetime] = None

        # アイドル時間の閾値（デフォルト: 30分）
        self.idle_threshold_minutes = self.config.get("idle_threshold_minutes", 30)

        # メトリクス履歴（24時間）
        self.metrics_history: List[Dict[str, Any]] = []
        self.metrics_storage_path = Path(__file__).parent / "intrinsic_motivation_metrics.json"
        self._load_metrics()

        logger.info("✅ Intrinsic Motivation System初期化完了")

    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました",
                )
                logger.warning(f"設定読み込みエラー: {error.message}")

        return {"idle_threshold_minutes": 30, "max_intrinsic_tasks": 10, "enabled": True}

    def _save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"設定保存エラー: {e}")

    def is_idle(self) -> bool:
        """
        現在が「暇な時間」かどうかを判定

        Returns:
            アイドル状態かどうか
        """
        if not self.last_external_task_time:
            # 外部タスクの履歴がない場合は、一定時間経過後にアイドルと判定
            return True

        idle_duration = datetime.now() - self.last_external_task_time
        idle_minutes = idle_duration.total_seconds() / 60

        return idle_minutes >= self.idle_threshold_minutes

    def record_external_task(self) -> None:
        """外部タスクの実行を記録"""
        self.last_external_task_time = datetime.now()

    def assess_current_capabilities(self) -> Dict[str, Any]:
        """
        現状の能力を評価（長期目標とのギャップ分析）

        Returns:
            能力評価結果
        """
        try:
            # Learning Systemから統計を取得
            response = httpx.get(f"{self.learning_system_url}/api/analyze", timeout=5)
            learning_stats = response.json() if response.status_code == 200 else {}

            # Metrics Collectorから統計を取得
            response = httpx.get(f"{self.metrics_collector_url}/api/metrics/summary", timeout=5)
            metrics_stats = response.json() if response.status_code == 200 else {}

            # 能力評価
            success_rate = metrics_stats.get("success_rate", 0.0)
            total_actions = learning_stats.get("total_actions_recorded", 0)
            patterns_learned = learning_stats.get("patterns_learned", 0)

            # ギャップ分析
            gaps = []
            if success_rate < 0.8:
                gaps.append("成功率を向上させる必要がある")
            if patterns_learned < 10:
                gaps.append("パターン学習を増やす必要がある")
            if total_actions < 100:
                gaps.append("経験を積む必要がある")

            return {
                "success_rate": success_rate,
                "total_actions": total_actions,
                "patterns_learned": patterns_learned,
                "gaps": gaps,
                "assessment_time": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"能力評価エラー: {e}")
            return {
                "success_rate": 0.0,
                "total_actions": 0,
                "patterns_learned": 0,
                "gaps": ["データ取得に失敗"],
                "assessment_time": datetime.now().isoformat(),
            }

    def _passes_quality_filter(self, task: IntrinsicTask, config: Dict[str, Any]) -> bool:
        """
        quality_config に基づきタスクをフィルタ（False＝除外）
        todo_quality_improvement の設定を参照
        """
        banned_categories = set(config.get("banned_categories", []))
        banned_ranges = config.get("banned_time_ranges", [])
        min_gran = config.get("min_granularity", "medium")

        # カテゴリチェック（TaskCategory.value を文字列で比較）
        cat = task.category.value
        if cat in banned_categories:
            return False

        # 粒度チェック（estimated_duration_minutes: high < 30, medium 30-120, low > 120）
        m = task.estimated_duration_minutes
        g = "high" if m < 30 else ("medium" if m <= 120 else "low")
        rank = {"high": 2, "medium": 1, "low": 0}
        if rank.get(g, 0) < rank.get(min_gran, 0):
            return False

        # 禁止時間帯チェック
        now = datetime.now()
        now_m = now.hour * 60 + now.minute
        for r in banned_ranges:
            try:
                sh, sm = map(int, str(r.get("start", "00:00")).split(":")[:2])
                eh, em = map(int, str(r.get("end", "23:59")).split(":")[:2])
            except Exception:
                continue
            start_m, end_m = sh * 60 + sm, eh * 60 + em
            if start_m <= end_m:
                if start_m <= now_m <= end_m:
                    return False
            else:
                if now_m >= start_m or now_m <= end_m:
                    return False
        return True

    def generate_intrinsic_tasks(self) -> List[IntrinsicTask]:
        """
        内発的タスクを生成（やることリスト）
        quality_config で禁止タグ・カテゴリ・時間帯・粒度をフィルタ

        Returns:
            生成されたタスクのリスト
        """
        if not self.is_idle():
            return []

        # quality_config を読み込み（提案側でフィルタに使用）
        try:
            from todo_quality_improvement import load_quality_config

            quality_config = load_quality_config()
        except Exception:
            quality_config = {}

        # 現状の能力を評価
        capabilities = self.assess_current_capabilities()

        tasks = []

        # 1. 記憶の整理
        if capabilities.get("total_actions", 0) > 50:
            tasks.append(
                IntrinsicTask(
                    task_id=f"intrinsic_memory_org_{int(datetime.now().timestamp())}",
                    title="記憶の整理と最適化",
                    description="過去の実行ログを分析し、重要なパターンを抽出して記憶を整理する",
                    category=TaskCategory.MEMORY_ORGANIZATION,
                    priority=7,
                    estimated_duration_minutes=15,
                    long_term_goal_alignment="知識の体系化と効率的な検索",
                )
            )

        # 2. 知識の獲得
        if capabilities.get("patterns_learned", 0) < 10:
            tasks.append(
                IntrinsicTask(
                    task_id=f"intrinsic_knowledge_{int(datetime.now().timestamp())}",
                    title="新しいパターンの学習",
                    description="失敗ログや成功パターンを分析し、新しい知識を獲得する",
                    category=TaskCategory.KNOWLEDGE_ACQUISITION,
                    priority=8,
                    estimated_duration_minutes=20,
                    long_term_goal_alignment="知識の拡充",
                )
            )

        # 3. パフォーマンス改善
        if capabilities.get("success_rate", 0.0) < 0.8:
            tasks.append(
                IntrinsicTask(
                    task_id=f"intrinsic_perf_{int(datetime.now().timestamp())}",
                    title="パフォーマンス分析と改善",
                    description="メトリクスを分析し、ボトルネックを特定して改善案を提案する",
                    category=TaskCategory.PERFORMANCE_IMPROVEMENT,
                    priority=9,
                    estimated_duration_minutes=25,
                    long_term_goal_alignment="信頼性の向上",
                )
            )

        # 4. パターン分析
        tasks.append(
            IntrinsicTask(
                task_id=f"intrinsic_pattern_{int(datetime.now().timestamp())}",
                title="成功/失敗パターンの分析",
                description="最近の実行結果を分析し、成功パターンと失敗パターンを分類する",
                category=TaskCategory.PATTERN_ANALYSIS,
                priority=6,
                estimated_duration_minutes=15,
                long_term_goal_alignment="判断力の向上",
            )
        )

        # 5. ドキュメント整理
        tasks.append(
            IntrinsicTask(
                task_id=f"intrinsic_doc_{int(datetime.now().timestamp())}",
                title="ドキュメントとPlaybookの整理",
                description="Playbookやドキュメントを整理し、再利用可能な知識を体系化する",
                category=TaskCategory.DOCUMENTATION,
                priority=5,
                estimated_duration_minutes=20,
                long_term_goal_alignment="知識の体系化",
            )
        )

        # 安全性チェック
        for task in tasks:
            task.safety_check_passed = self._safety_check(task)

        # 安全性チェックを通過したタスクのみ
        safe_tasks = [t for t in tasks if t.safety_check_passed]

        # quality_config でフィルタ（禁止カテゴリ・時間帯・粒度）
        if quality_config:
            filtered_tasks = [
                t for t in safe_tasks if self._passes_quality_filter(t, quality_config)
            ]
            quality_blocked = len(safe_tasks) - len(filtered_tasks)
            if quality_blocked > 0:
                logger.info(f"✅ quality_config で {quality_blocked} 件の内発タスクを除外しました")
            safe_tasks = filtered_tasks

        # ブロックされたタスク数を記録
        blocked_count = len(tasks) - len(safe_tasks)
        if blocked_count > 0:
            self._record_metric("safety_blocked", blocked_count)

        # 優先度順にソート
        safe_tasks.sort(key=lambda t: t.priority, reverse=True)

        # 最大タスク数を制限
        max_tasks = self.config.get("max_intrinsic_tasks", 10)
        safe_tasks = safe_tasks[:max_tasks]

        self.intrinsic_tasks = safe_tasks

        # メトリクス記録
        if safe_tasks:
            self._record_metric("task_generated", len(safe_tasks))

        logger.info(f"✅ {len(safe_tasks)}個の内発的タスクを生成しました")

        return safe_tasks

    def _safety_check(self, task: IntrinsicTask) -> bool:
        """
        タスクの安全性をチェック（5つの憲章に照らし合わせる）

        Args:
            task: チェックするタスク

        Returns:
            安全かどうか
        """
        # タスクの説明をチェック
        description_lower = task.description.lower()

        # 危険なキーワードをチェック
        dangerous_keywords = [
            "api key",
            "api_key",
            "認証情報",
            "パスワード",
            "設定変更",
            "削除",
            "破壊",
            "外部サービス",
            "autonomy level 2",
            "autonomy level 3",
        ]

        for keyword in dangerous_keywords:
            if keyword in description_lower:
                logger.warning(f"⚠️ 安全性チェック失敗: {keyword}が含まれています")
                return False

        # カテゴリベースのチェック
        if task.category == TaskCategory.MEMORY_ORGANIZATION:
            # 記憶の整理は安全
            return True
        elif task.category == TaskCategory.KNOWLEDGE_ACQUISITION:
            # 知識の獲得は安全
            return True
        elif task.category == TaskCategory.PERFORMANCE_IMPROVEMENT:
            # パフォーマンス改善は安全（設定変更は含まない）
            return True
        elif task.category == TaskCategory.PATTERN_ANALYSIS:
            # パターン分析は安全
            return True
        elif task.category == TaskCategory.DOCUMENTATION:
            # ドキュメント整理は安全
            return True

        return True

    def execute_intrinsic_task(self, task_id: str) -> Dict[str, Any]:
        """
        内発的タスクを実行

        Args:
            task_id: タスクID

        Returns:
            実行結果
        """
        task = next((t for t in self.intrinsic_tasks if t.task_id == task_id), None)
        if not task:
            return {"error": "タスクが見つかりません"}

        if not task.safety_check_passed:
            return {"error": "安全性チェックを通過していません"}

        logger.info(f"🚀 内発的タスク実行開始: {task.title}")

        try:
            # タスクカテゴリに応じて実行
            if task.category == TaskCategory.MEMORY_ORGANIZATION:
                result = self._execute_memory_organization(task)
            elif task.category == TaskCategory.KNOWLEDGE_ACQUISITION:
                result = self._execute_knowledge_acquisition(task)
            elif task.category == TaskCategory.PERFORMANCE_IMPROVEMENT:
                result = self._execute_performance_improvement(task)
            elif task.category == TaskCategory.PATTERN_ANALYSIS:
                result = self._execute_pattern_analysis(task)
            elif task.category == TaskCategory.DOCUMENTATION:
                result = self._execute_documentation(task)
            else:
                result = {"error": "不明なタスクカテゴリ"}

            # メトリクス記録
            self._record_metric("task_executed", 1)

            logger.info(f"✅ 内発的タスク実行完了: {task.title}")
            return result

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"task_id": task_id, "task_title": task.title},
                user_message="内発的タスクの実行に失敗しました",
            )
            logger.error(f"内発的タスク実行エラー: {error.message}")
            return {"error": error.message}

    def _execute_memory_organization(self, task: IntrinsicTask) -> Dict[str, Any]:
        """記憶の整理を実行"""
        logger.warning("_execute_memory_organization: 未実装 — スキップ")
        return {"status": "not_implemented", "message": "記憶の整理は未実装です"}

    def _execute_knowledge_acquisition(self, task: IntrinsicTask) -> Dict[str, Any]:
        """知識の獲得を実行"""
        logger.warning("_execute_knowledge_acquisition: 未実装 — スキップ")
        return {"status": "not_implemented", "message": "知識の獲得は未実装です"}

    def _execute_performance_improvement(self, task: IntrinsicTask) -> Dict[str, Any]:
        """パフォーマンス改善を実行"""
        logger.warning("_execute_performance_improvement: 未実装 — スキップ")
        return {"status": "not_implemented", "message": "パフォーマンス改善は未実装です"}

    def _execute_pattern_analysis(self, task: IntrinsicTask) -> Dict[str, Any]:
        """パターン分析を実行"""
        logger.warning("_execute_pattern_analysis: 未実装 — スキップ")
        return {"status": "not_implemented", "message": "パターン分析は未実装です"}

    def _execute_documentation(self, task: IntrinsicTask) -> Dict[str, Any]:
        """ドキュメント整理を実行"""
        logger.warning("_execute_documentation: 未実装 — スキップ")
        return {"status": "not_implemented", "message": "ドキュメント整理は未実装です"}

    def _load_metrics(self):
        """メトリクスを読み込み"""
        if self.metrics_storage_path.exists():
            try:
                with open(self.metrics_storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metrics_history = data.get("history", [])
            except Exception as e:
                logger.warning(f"メトリクス読み込みエラー: {e}")
                self.metrics_history = []
        else:
            self.metrics_history = []

    def _save_metrics(self):
        """メトリクスを保存"""
        try:
            # 24時間分のみ保持
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history = [
                m
                for m in self.metrics_history
                if datetime.fromisoformat(m.get("timestamp", "")) >= cutoff_time
            ]

            with open(self.metrics_storage_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"history": self.metrics_history, "last_updated": datetime.now().isoformat()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"メトリクス保存エラー: {e}")

    def _record_metric(self, metric_type: str, value: Any):
        """メトリクスを記録"""
        self.metrics_history.append(
            {"timestamp": datetime.now().isoformat(), "type": metric_type, "value": value}
        )
        self._save_metrics()

    def get_metrics(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        メトリクスを取得

        Args:
            window_hours: 時間窓（デフォルト: 24時間）

        Returns:
            メトリクスデータ
        """
        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        recent_metrics = [
            m
            for m in self.metrics_history
            if datetime.fromisoformat(m.get("timestamp", "")) >= cutoff_time
        ]

        # 集計
        idle_minutes = 0
        if self.last_external_task_time:
            idle_duration = datetime.now() - self.last_external_task_time
            idle_minutes = int(idle_duration.total_seconds() / 60)

        generated_tasks = len([m for m in recent_metrics if m.get("type") == "task_generated"])
        accepted_tasks = len([m for m in recent_metrics if m.get("type") == "task_accepted"])
        executed_tasks = len([m for m in recent_metrics if m.get("type") == "task_executed"])
        learning_yield = len([m for m in recent_metrics if m.get("type") == "learning_yield"])
        safety_blocks = len([m for m in recent_metrics if m.get("type") == "safety_blocked"])

        return {
            "window_hours": window_hours,
            "idle_minutes": idle_minutes,
            "generated_tasks": generated_tasks,
            "accepted_tasks": accepted_tasks,
            "executed_tasks": executed_tasks,
            "learning_yield": learning_yield,
            "safety_blocks": safety_blocks,
            "timestamp": datetime.now().isoformat(),
        }

    def calculate_score(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        Intrinsic Motivation Scoreを計算（0-100）

        Args:
            window_hours: 時間窓（デフォルト: 24時間）

        Returns:
            スコアと内訳
        """
        metrics = self.get_metrics(window_hours)

        # スコア計算
        base = 10
        idle_score = 2 * min(metrics["idle_minutes"] / 30, 4)
        executed_score = 8 * min(metrics["executed_tasks"], 5)
        accepted_score = 4 * min(metrics["accepted_tasks"], 5)
        generated_score = 2 * min(metrics["generated_tasks"], 8)
        learning_score = 5 * min(metrics["learning_yield"], 6)
        safety_penalty = -6 * min(metrics["safety_blocks"], 3)

        total_score = (
            base
            + idle_score
            + executed_score
            + accepted_score
            + generated_score
            + learning_score
            + safety_penalty
        )
        # 最低値保証：base=10は必ず反映される（データ無しでも10以上）
        score = max(10, min(100, total_score))

        return {
            "window": f"{window_hours}h",
            "score": round(score, 1),
            "breakdown": {
                "base": base,
                "idle": round(idle_score, 1),
                "executed": round(executed_score, 1),
                "accepted": round(accepted_score, 1),
                "generated": round(generated_score, 1),
                "learning": round(learning_score, 1),
                "safety_penalty": round(safety_penalty, 1),
            },
            **metrics,
        }

    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return {
            "is_idle": self.is_idle(),
            "idle_threshold_minutes": self.idle_threshold_minutes,
            "last_external_task_time": (
                self.last_external_task_time.isoformat() if self.last_external_task_time else None
            ),
            "intrinsic_tasks_count": len(self.intrinsic_tasks),
            "long_term_goal": self.LONG_TERM_GOAL,
            "enabled": self.config.get("enabled", True),
        }


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルインスタンス
intrinsic_motivation = None


def init_intrinsic_motivation() -> 'IntrinsicMotivation':
    """内発的動機づけシステムを初期化"""
    global intrinsic_motivation
    if intrinsic_motivation is None:
        intrinsic_motivation = IntrinsicMotivation()
    return intrinsic_motivation


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Intrinsic Motivation System"})


@app.route("/api/status", methods=["GET"])
def get_status():
    """状態を取得"""
    system = init_intrinsic_motivation()
    return jsonify(system.get_status())


@app.route("/api/record-external-task", methods=["POST"])
def record_external_task():
    """外部タスクの実行を記録"""
    system = init_intrinsic_motivation()
    system.record_external_task()
    return jsonify({"status": "recorded"})


@app.route("/api/generate-tasks", methods=["POST"])
def generate_tasks():
    """内発的タスクを生成"""
    system = init_intrinsic_motivation()
    tasks = system.generate_intrinsic_tasks()
    return jsonify({"tasks": [asdict(t) for t in tasks], "count": len(tasks)})


@app.route("/api/execute-task/<task_id>", methods=["POST"])
def execute_task(task_id: str):
    """内発的タスクを実行"""
    system = init_intrinsic_motivation()
    result = system.execute_intrinsic_task(task_id)
    return jsonify(result)


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """メトリクスを取得"""
    system = init_intrinsic_motivation()
    window_hours = int(request.args.get("window", 24))
    metrics = system.get_metrics(window_hours)
    return jsonify(metrics)


@app.route("/api/score", methods=["GET"])
def get_score():
    """スコアを取得"""
    system = init_intrinsic_motivation()
    window_hours = int(request.args.get("window", 24))
    score_data = system.calculate_score(window_hours)
    return jsonify(score_data)


@app.route("/api/record-metric", methods=["POST"])
def record_metric():
    """メトリクスを記録"""
    system = init_intrinsic_motivation()
    data = request.get_json() or {}
    metric_type = data.get("type")
    value = data.get("value")
    if metric_type and value is not None:
        system._record_metric(metric_type, value)
        return jsonify({"status": "recorded"})
    return jsonify({"error": "type and value are required"}), 400


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5130
    logger.info(f"🚀 Intrinsic Motivation System API Server起動 (ポート: {port})")
    app.run(host="0.0.0.0", port=port, debug=False)
