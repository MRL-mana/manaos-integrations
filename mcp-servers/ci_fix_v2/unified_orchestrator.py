#!/usr/bin/env python3
"""
🎯 Unified Orchestrator - 統合オーケストレーター
Intent Router + Planner + Critic + Executorの統合システム
"""

import os
import json
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator
from _paths import (
    INTENT_ROUTER_PORT,
    LEARNING_SYSTEM_PORT,
    METRICS_COLLECTOR_PORT,
    RAG_MEMORY_PORT,
    TASK_CRITIC_PORT,
    TASK_PLANNER_PORT,
    TASK_QUEUE_PORT,
)

# ロガーの初期化（インポート前に必要）
logger = get_service_logger("unified-orchestrator")

# 強化モジュールのインポート
try:
    from metrics_collector import MetricsCollector, MetricType

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    MetricType = None  # ダミー値
    logger.warning("⚠️ Metrics Collectorが利用できません")

try:
    from intelligent_retry import IntelligentRetry, RetryConfig, CircuitBreakerConfig

    RETRY_AVAILABLE = True
except ImportError:
    RETRY_AVAILABLE = False
    logger.warning("⚠️ Intelligent Retryが利用できません")

try:
    from response_cache import ResponseCache

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("⚠️ Response Cacheが利用できません")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedOrchestrator")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("UnifiedOrchestrator")

DEFAULT_INTENT_ROUTER_URL = f"http://127.0.0.1:{INTENT_ROUTER_PORT}"
DEFAULT_TASK_PLANNER_URL = f"http://127.0.0.1:{TASK_PLANNER_PORT}"
DEFAULT_TASK_CRITIC_URL = f"http://127.0.0.1:{TASK_CRITIC_PORT}"
DEFAULT_TASK_QUEUE_URL = f"http://127.0.0.1:{TASK_QUEUE_PORT}"
DEFAULT_RAG_MEMORY_URL = f"http://127.0.0.1:{RAG_MEMORY_PORT}"
DEFAULT_LEARNING_SYSTEM_URL = f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}"
DEFAULT_METRICS_COLLECTOR_URL = f"http://127.0.0.1:{METRICS_COLLECTOR_PORT}"


class ExecutionStatus(str, Enum):
    """実行ステータス"""

    PENDING = "pending"
    CLASSIFYING = "classifying"
    PLANNING = "planning"
    QUEUED = "queued"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OrchestrationResult:
    """オーケストレーション結果"""

    execution_id: str
    input_text: str
    intent_type: str
    plan_id: str
    task_id: Optional[str]
    status: ExecutionStatus
    result: Optional[Dict[str, Any]]
    evaluation: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[float]


def to_unified_response(result: OrchestrationResult) -> Dict[str, Any]:
    """
    全入口で共通のレスポンス仕様に正規化する。
    status: ok | skill_not_found | tool_error | error
    - skill_not_found: 該当スキルなし → LLM フォールバック
    - tool_error: スキル実行はしたが失敗（デバイス死、認証切れ等）→ ユーザーへ説明
    - error: システムエラー（例外・HTTP失敗）→ 再試行を促す
    meta.trace_id: ログ突合用（execution_id）
    """
    trace_id = result.execution_id
    meta = {
        "trace_id": trace_id,
        "confidence": 0.0,
        "assumption": "",
    }
    # result.result 内の confidence/assumption があれば流し込む（将来拡張）
    if result.result and isinstance(result.result, dict):
        if "confidence" in result.result:
            meta["confidence"] = result.result.get("confidence", 0.0)
        if "assumption" in result.result:
            meta["assumption"] = result.result.get("assumption", "") or ""

    if (
        result.status == ExecutionStatus.COMPLETED
        and result.result
        and isinstance(result.result, dict)
    ):
        if result.result.get("status") == "skill_not_found":
            return {
                "status": "skill_not_found",
                "message": result.result.get("message", "SKILL_NOT_FOUND"),
                "input_text": result.input_text,
                "result": result.result,
                "meta": meta,
            }
    if result.status == ExecutionStatus.COMPLETED:
        return {
            "status": "ok",
            "message": "",
            "input_text": result.input_text,
            "result": result.result,
            "meta": meta,
        }
    # FAILED: result.result に status: tool_error があればツール側の失敗
    if (
        result.status == ExecutionStatus.FAILED
        and result.result
        and isinstance(result.result, dict)
        and result.result.get("status") == "tool_error"
    ):
        return {
            "status": "tool_error",
            "message": result.result.get("message", result.error) or "tool failed",
            "input_text": result.input_text,
            "result": result.result,
            "meta": meta,
        }
    return {
        "status": "error",
        "message": result.error or "failed",
        "input_text": result.input_text,
        "result": result.result,
        "meta": meta,
    }


class UnifiedOrchestrator:
    """統合オーケストレーター"""

    def __init__(
        self,
        intent_router_url: Optional[str] = None,
        task_planner_url: Optional[str] = None,
        task_critic_url: Optional[str] = None,
        task_queue_url: Optional[str] = None,
        executor_url: Optional[str] = None,
        rag_memory_url: Optional[str] = None,
        learning_system_url: Optional[str] = None,
        config_path: Optional[Path] = None,
    ):
        """
        初期化

        Args:
            intent_router_url: Intent Router API URL
            task_planner_url: Task Planner API URL
            task_critic_url: Task Critic API URL
            task_queue_url: Task Queue API URL
            executor_url: Executor API URL（Noneの場合はTask Queueを使用）
            rag_memory_url: RAG Memory API URL
            learning_system_url: Learning System API URL（オプション）
            config_path: 設定ファイルのパス
        """
        self.intent_router_url = intent_router_url or DEFAULT_INTENT_ROUTER_URL
        self.task_planner_url = task_planner_url or DEFAULT_TASK_PLANNER_URL
        self.task_critic_url = task_critic_url or DEFAULT_TASK_CRITIC_URL
        self.task_queue_url = task_queue_url or DEFAULT_TASK_QUEUE_URL
        self.executor_url = executor_url
        self.rag_memory_url = rag_memory_url or DEFAULT_RAG_MEMORY_URL
        self.learning_system_url = learning_system_url

        self.config_path = config_path or Path(__file__).parent / "unified_orchestrator_config.json"
        self.config = self._load_config()

        # 学習システムの統合（オプション）
        # デフォルトでLearning System API URLを設定（設定ファイルで上書き可能）
        if not self.learning_system_url:
            self.learning_system_url = self.config.get(
                "learning_system_url", DEFAULT_LEARNING_SYSTEM_URL
            )

        # Learning Systemを直接インポートして使用（APIサーバーがない場合のフォールバック）
        try:
            from learning_system import LearningSystem

            self.learning_system = LearningSystem()
            logger.info("✅ Learning System統合完了（直接インポート）")
        except ImportError:
            self.learning_system = None
            logger.info(f"✅ Learning System URL設定: {self.learning_system_url}")

        # メトリクス収集システムの統合
        self.metrics_collector = None
        if METRICS_AVAILABLE and self.config.get("enable_metrics", True):
            try:
                metrics_url = self.config.get(
                    "metrics_collector_url", DEFAULT_METRICS_COLLECTOR_URL
                )
                # API経由で使用（直接インポートも可能）
                self.metrics_collector_url = metrics_url
                logger.info(f"✅ Metrics Collector統合完了: {metrics_url}")
            except Exception as e:
                logger.warning(f"⚠️ Metrics Collector統合エラー: {e}")

        # インテリジェントリトライシステムの統合
        self.intelligent_retry = None
        if RETRY_AVAILABLE and self.config.get("enable_retry", True):
            try:
                retry_config = RetryConfig(
                    max_retries=self.config.get("max_retries", 3),
                    initial_delay=self.config.get("retry_initial_delay", 1.0),
                    max_delay=self.config.get("retry_max_delay", 60.0),
                    exponential_base=self.config.get("retry_exponential_base", 2.0),
                )
                circuit_breaker_config = CircuitBreakerConfig(
                    failure_threshold=self.config.get("circuit_breaker_failure_threshold", 5),
                    success_threshold=self.config.get("circuit_breaker_success_threshold", 2),
                    timeout_seconds=self.config.get("circuit_breaker_timeout", 60.0),
                )
                self.intelligent_retry = IntelligentRetry(
                    retry_config=retry_config, circuit_breaker_config=circuit_breaker_config
                )
                logger.info("✅ Intelligent Retry統合完了")
            except Exception as e:
                logger.warning(f"⚠️ Intelligent Retry統合エラー: {e}")

        # レスポンスキャッシュシステムの統合
        self.response_cache = None
        if CACHE_AVAILABLE and self.config.get("enable_cache", True):
            try:
                cache_ttl = self.config.get("cache_ttl_seconds", 3600)
                self.response_cache = ResponseCache(default_ttl_seconds=cache_ttl)
                logger.info(f"✅ Response Cache統合完了（TTL: {cache_ttl}秒）")
            except Exception as e:
                logger.warning(f"⚠️ Response Cache統合エラー: {e}")

        # 実行履歴
        self.execution_history: Dict[str, OrchestrationResult] = {}

        logger.info(f"✅ Unified Orchestrator初期化完了")

    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 設定ファイルの検証
                schema = {
                    "required": ["auto_evaluate", "save_to_memory"],
                    "fields": {
                        "auto_evaluate": {"type": bool},
                        "auto_retry": {"type": bool, "default": True},
                        "max_retries": {"type": int, "default": 3},
                        "save_to_memory": {"type": bool},
                        "memory_importance_threshold": {"type": (int, float), "default": 0.6},
                    },
                }

                is_valid, errors = config_validator.validate_config(
                    config, schema, self.config_path
                )
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                    # エラーがあってもデフォルト設定にマージして続行
                    default_config = self._get_default_config()
                    default_config.update(config)
                    return default_config

                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました",
                )
                logger.warning(f"設定読み込みエラー: {error.message}")

        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "auto_evaluate": True,
            "auto_retry": True,
            "max_retries": 3,
            "save_to_memory": True,
            "memory_importance_threshold": 0.6,
            "learning_system_url": DEFAULT_LEARNING_SYSTEM_URL,
            "enable_learning": True,
            "enable_metrics": True,
            "metrics_collector_url": DEFAULT_METRICS_COLLECTOR_URL,
            "enable_retry": True,
            "retry_initial_delay": 1.0,
            "retry_max_delay": 60.0,
            "retry_exponential_base": 2.0,
            "circuit_breaker_failure_threshold": 5,
            "circuit_breaker_success_threshold": 2,
            "circuit_breaker_timeout": 60.0,
            "enable_cache": True,
            "cache_ttl_seconds": 3600,
        }

    async def execute(
        self,
        input_text: str,
        mode: Optional[str] = None,
        auto_evaluate: Optional[bool] = None,
        save_to_memory: Optional[bool] = None,
    ) -> OrchestrationResult:
        """
        タスクを実行（エンドツーエンド）

        Args:
            input_text: 入力テキスト
            mode: システムモード
            auto_evaluate: 自動評価するか
            save_to_memory: 記憶に保存するか

        Returns:
            OrchestrationResult: 実行結果
        """
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(input_text) % 10000}"
        start_time = datetime.now()

        result = OrchestrationResult(
            execution_id=execution_id,
            input_text=input_text,
            intent_type="unknown",
            plan_id="",
            task_id=None,
            status=ExecutionStatus.PENDING,
            result=None,
            evaluation=None,
            error=None,
            created_at=start_time.isoformat(),
            completed_at=None,
            duration_seconds=None,
        )

        try:
            # 1. 意図分類
            logger.info(f"🎯 [{execution_id}] 意図分類開始")
            result.status = ExecutionStatus.CLASSIFYING

            intent_result = await self._classify_intent(input_text)
            if not intent_result:
                raise Exception("意図分類に失敗しました")

            result.intent_type = intent_result.get("intent_type", "unknown")
            logger.info(f"✅ [{execution_id}] 意図分類完了: {result.intent_type}")

            # 1.5. 意図が unknown のときは SKILL_NOT_FOUND を返し、クライアントが LLM に戻せるようにする（フォールバック）
            if result.intent_type == "unknown":
                result.status = ExecutionStatus.COMPLETED
                result.result = {
                    "status": "skill_not_found",
                    "message": "SKILL_NOT_FOUND",
                    "input_text": input_text,
                }
                result.completed_at = datetime.now().isoformat()
                result.duration_seconds = (datetime.now() - start_time).total_seconds()
                self.execution_history[execution_id] = result
                logger.info(
                    f"📤 [{execution_id}] 該当スキルなし → SKILL_NOT_FOUND（LLMフォールバック用）"
                )
                return result

            # 2. 実行計画作成
            logger.info(f"📋 [{execution_id}] 実行計画作成開始")
            result.status = ExecutionStatus.PLANNING

            plan = await self._create_plan(input_text)
            if not plan:
                raise Exception("実行計画の作成に失敗しました")

            result.plan_id = plan.get("plan_id", "")
            logger.info(f"✅ [{execution_id}] 実行計画作成完了: {result.plan_id}")

            # 3. タスクをキューに追加
            logger.info(f"📦 [{execution_id}] タスクエンキュー開始")
            result.status = ExecutionStatus.QUEUED

            task = await self._enqueue_task(
                intent_type=result.intent_type, input_text=input_text, plan=plan, mode=mode
            )
            if not task:
                raise Exception("タスクのエンキューに失敗しました")

            result.task_id = task.get("task_id")
            logger.info(f"✅ [{execution_id}] タスクエンキュー完了: {result.task_id}")

            # 4. タスク実行を待つ（簡易版：実際にはExecutorが実行）
            # ここではタスクが完了するまで待機
            logger.info(f"⚙️ [{execution_id}] タスク実行待機中...")
            result.status = ExecutionStatus.EXECUTING

            # タスクの完了を待つ（ポーリング）
            execution_result = await self._wait_for_task_completion(result.task_id)
            result.result = execution_result

            if execution_result and execution_result.get("status") == "completed":
                result.status = ExecutionStatus.COMPLETED
                logger.info(f"✅ [{execution_id}] タスク実行完了")
            else:
                result.status = ExecutionStatus.FAILED
                result.error = (
                    execution_result.get("error") if execution_result else "タスク実行失敗"
                )
                logger.error(f"❌ [{execution_id}] タスク実行失敗")

            # 5. 実行結果評価（オプション）
            if (
                auto_evaluate
                if auto_evaluate is not None
                else self.config.get("auto_evaluate", True)
            ):
                logger.info(f"🔍 [{execution_id}] 実行結果評価開始")
                result.status = ExecutionStatus.EVALUATING

                evaluation = await self._evaluate_result(
                    intent_type=result.intent_type,
                    input_text=input_text,
                    plan=plan,
                    execution_result=execution_result,
                )
                result.evaluation = evaluation
                logger.info(f"✅ [{execution_id}] 実行結果評価完了")

            # 6. 記憶に保存（オプション）
            if (
                save_to_memory
                if save_to_memory is not None
                else self.config.get("save_to_memory", True)
            ):
                await self._save_to_memory(
                    input_text=input_text,
                    intent_type=result.intent_type,
                    result=execution_result,
                    evaluation=result.evaluation,
                )

            result.completed_at = datetime.now().isoformat()
            result.duration_seconds = (datetime.now() - start_time).total_seconds()

            # 実行履歴に保存
            self.execution_history[execution_id] = result

            # 7. メトリクス記録（オプション）
            if self.config.get("enable_metrics", True):
                await self._record_metric(
                    "UnifiedOrchestrator",
                    MetricType.RESPONSE_TIME,
                    result.duration_seconds,
                    metadata={
                        "execution_id": execution_id,
                        "intent_type": result.intent_type,
                        "status": result.status.value,
                    },
                )
                await self._record_metric(
                    "UnifiedOrchestrator",
                    MetricType.SUCCESS_RATE,
                    1.0 if result.status == ExecutionStatus.COMPLETED else 0.0,
                    metadata={"execution_id": execution_id, "intent_type": result.intent_type},
                )

            # 8. 学習システムに記録（オプション）
            if self.config.get("enable_learning", True):
                await self._record_to_learning_system(
                    execution_id=execution_id,
                    intent_type=result.intent_type,
                    input_text=input_text,
                    plan=plan,
                    execution_result=execution_result,
                    evaluation=result.evaluation,
                    duration_seconds=result.duration_seconds,
                    success=result.status == ExecutionStatus.COMPLETED,
                )

            return result

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"execution_id": execution_id, "input_text": input_text},
                user_message="タスクの実行に失敗しました",
            )

            result.status = ExecutionStatus.FAILED
            result.error = error.user_message or error.message
            result.completed_at = datetime.now().isoformat()
            result.duration_seconds = (datetime.now() - start_time).total_seconds()

            logger.error(f"❌ [{execution_id}] オーケストレーション失敗: {error.message}")

            # 実行履歴に保存
            self.execution_history[execution_id] = result

            return result

    async def _classify_intent(self, input_text: str) -> Optional[Dict[str, Any]]:
        """意図を分類"""
        start_time = datetime.now()

        # キャッシュから取得を試みる
        if self.response_cache:
            cached_result = self.response_cache.get(
                cache_type="intent_classification", input_text=input_text
            )
            if cached_result:
                logger.debug("✅ 意図分類キャッシュヒット")
                return cached_result

        # リトライ付きで実行
        async def _call_intent_api():
            timeout = timeout_config.get("api_call", 10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.intent_router_url}/api/classify", json={"text": input_text}
                )
                if response.status_code == 200:
                    return response.json()
                raise Exception(f"Intent Router returned status {response.status_code}")

        try:
            if self.intelligent_retry:
                retry_result = await self.intelligent_retry.execute_with_retry(
                    _call_intent_api, circuit_breaker_key="intent_router"
                )
                if retry_result.success:
                    result = retry_result.result
                else:
                    raise Exception(f"リトライ失敗: {', '.join(retry_result.errors)}")
            else:
                result = await _call_intent_api()

            # メトリクス記録
            duration = (datetime.now() - start_time).total_seconds()
            await self._record_metric("IntentRouter", MetricType.RESPONSE_TIME, duration)
            await self._record_metric("IntentRouter", MetricType.SUCCESS_RATE, 1.0)

            # キャッシュに保存
            if self.response_cache and result:
                self.response_cache.set(
                    cache_type="intent_classification",
                    value=result,
                    input_text=input_text,
                    ttl_seconds=self.config.get("cache_ttl_seconds", 3600),
                )

            return result

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Intent Router", "url": self.intent_router_url},
                user_message="意図分類サービスへの接続に失敗しました",
            )
            logger.error(f"Intent Router接続エラー: {error.message}")

            # エラーメトリクス記録
            duration = (datetime.now() - start_time).total_seconds()
            await self._record_metric("IntentRouter", MetricType.RESPONSE_TIME, duration)
            await self._record_metric("IntentRouter", MetricType.ERROR_RATE, 1.0)
            await self._record_metric("IntentRouter", MetricType.SUCCESS_RATE, 0.0)

        return None

    async def _create_plan(self, input_text: str) -> Optional[Dict[str, Any]]:
        """実行計画を作成"""
        start_time = datetime.now()

        # キャッシュから取得を試みる
        if self.response_cache:
            cached_result = self.response_cache.get(
                cache_type="task_planning", input_text=input_text
            )
            if cached_result:
                logger.debug("✅ 実行計画キャッシュヒット")
                return cached_result

        # リトライ付きで実行
        async def _call_planner_api():
            timeout = timeout_config.get("llm_call", 30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.task_planner_url}/api/plan", json={"text": input_text}
                )
                if response.status_code == 200:
                    return response.json()
                raise Exception(f"Task Planner returned status {response.status_code}")

        try:
            if self.intelligent_retry:
                retry_result = await self.intelligent_retry.execute_with_retry(
                    _call_planner_api, circuit_breaker_key="task_planner"
                )
                if retry_result.success:
                    result = retry_result.result
                else:
                    raise Exception(f"リトライ失敗: {', '.join(retry_result.errors)}")
            else:
                result = await _call_planner_api()

            # メトリクス記録
            duration = (datetime.now() - start_time).total_seconds()
            await self._record_metric("TaskPlanner", MetricType.RESPONSE_TIME, duration)
            await self._record_metric("TaskPlanner", MetricType.SUCCESS_RATE, 1.0)

            # キャッシュに保存
            if self.response_cache and result:
                self.response_cache.set(
                    cache_type="task_planning",
                    value=result,
                    input_text=input_text,
                    ttl_seconds=self.config.get("cache_ttl_seconds", 3600),
                )

            return result

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Task Planner", "url": self.task_planner_url},
                user_message="実行計画作成サービスへの接続に失敗しました",
            )
            logger.error(f"Task Planner接続エラー: {error.message}")

            # エラーメトリクス記録
            duration = (datetime.now() - start_time).total_seconds()
            await self._record_metric("TaskPlanner", MetricType.RESPONSE_TIME, duration)
            await self._record_metric("TaskPlanner", MetricType.ERROR_RATE, 1.0)
            await self._record_metric("TaskPlanner", MetricType.SUCCESS_RATE, 0.0)

        return None

    async def _enqueue_task(
        self, intent_type: str, input_text: str, plan: Dict[str, Any], mode: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """タスクをキューに追加"""
        try:
            # 優先度を決定
            priority_map = {"urgent": "urgent", "high": "high", "medium": "medium", "low": "low"}
            priority = priority_map.get(plan.get("priority", "medium").lower(), "medium")

            timeout = timeout_config.get("api_call", 10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.task_queue_url}/api/enqueue",
                    json={
                        "task_type": intent_type,
                        "payload": {"input": input_text, "plan": plan, "intent_type": intent_type},
                        "priority": priority,
                        "metadata": {"mode": mode, "created_at": datetime.now().isoformat()},
                    },
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Task Queue", "url": self.task_queue_url},
                user_message="タスクキューサービスへの接続に失敗しました",
            )
            logger.error(f"Task Queue接続エラー: {error.message}")
        return None

    async def _wait_for_task_completion(
        self, task_id: str, timeout: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """タスクの完了を待つ"""
        import time

        if timeout is None:
            timeout = int(timeout_config.get("workflow_execution", 300))

        start_time = time.time()
        poll_timeout = timeout_config.get("health_check", 5.0)

        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient(timeout=poll_timeout) as client:
                    response = await client.get(f"{self.task_queue_url}/api/task/{task_id}")
                    if response.status_code == 200:
                        task = response.json()
                        status = task.get("status")

                        if status in ["completed", "failed"]:
                            return {
                                "status": status,
                                "result": task.get("result"),
                                "error": task.get("error"),
                            }

                        # まだ実行中
                        await asyncio.sleep(2)
            except asyncio.TimeoutError:
                logger.debug(f"タスク状態確認タイムアウト: {task_id}")
                await asyncio.sleep(2)
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"service": "Task Queue", "task_id": task_id},
                    user_message="タスク状態の確認に失敗しました",
                )
                logger.debug(f"タスク状態確認エラー（再試行します）: {error.message}")
                await asyncio.sleep(2)

        return {"status": "timeout", "error": "タイムアウト"}

    async def _evaluate_result(
        self,
        intent_type: str,
        input_text: str,
        plan: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """実行結果を評価"""
        if not execution_result:
            return None

        start_time = datetime.now()

        # リトライ付きで実行
        async def _call_critic_api():
            timeout = timeout_config.get("llm_call", 30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.task_critic_url}/api/evaluate",
                    json={
                        "intent_type": intent_type,
                        "original_input": input_text,
                        "plan": plan,
                        "status": execution_result.get("status", "unknown"),
                        "output": execution_result.get("result"),
                        "error": execution_result.get("error"),
                    },
                )
                if response.status_code == 200:
                    return response.json()
                raise Exception(f"Task Critic returned status {response.status_code}")

        try:
            if self.intelligent_retry:
                retry_result = await self.intelligent_retry.execute_with_retry(
                    _call_critic_api, circuit_breaker_key="task_critic"
                )
                if retry_result.success:
                    result = retry_result.result
                else:
                    raise Exception(f"リトライ失敗: {', '.join(retry_result.errors)}")
            else:
                result = await _call_critic_api()

            # メトリクス記録
            duration = (datetime.now() - start_time).total_seconds()
            await self._record_metric("TaskCritic", MetricType.RESPONSE_TIME, duration)
            await self._record_metric("TaskCritic", MetricType.SUCCESS_RATE, 1.0)

            return result

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Task Critic", "url": self.task_critic_url},
                user_message="実行結果評価サービスへの接続に失敗しました",
            )
            logger.error(f"Task Critic接続エラー: {error.message}")

            # エラーメトリクス記録
            duration = (datetime.now() - start_time).total_seconds()
            await self._record_metric("TaskCritic", MetricType.RESPONSE_TIME, duration)
            await self._record_metric("TaskCritic", MetricType.ERROR_RATE, 1.0)
            await self._record_metric("TaskCritic", MetricType.SUCCESS_RATE, 0.0)

        return None

    async def _save_to_memory(
        self,
        input_text: str,
        intent_type: str,
        result: Optional[Dict[str, Any]],
        evaluation: Optional[Dict[str, Any]],
    ):
        """記憶に保存"""
        if not result:
            return

        # 重要度を決定
        importance = 0.5
        if evaluation:
            score = evaluation.get("score", 0.5)
            importance = max(0.3, score)  # 最低0.3

        # 重要度が閾値以上の場合のみ保存
        threshold = self.config.get("memory_importance_threshold", 0.6)
        if importance < threshold:
            logger.info(f"重要度が低いため記憶に保存しません: {importance:.2f} < {threshold}")
            return

        # 記憶内容を構築
        content = f"意図: {intent_type}\n入力: {input_text}\n"
        if result.get("result"):
            content += f"結果: {json.dumps(result.get('result'), ensure_ascii=False)}\n"
        if evaluation:
            content += f"評価: {evaluation.get('reasoning', '')}\n"

        try:
            timeout = timeout_config.get("api_call", 10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.rag_memory_url}/api/add",
                    json={
                        "content": content,
                        "importance_score": importance,
                        "metadata": {"intent_type": intent_type, "evaluation": evaluation},
                    },
                )
                if response.status_code == 200:
                    logger.info(f"✅ 記憶に保存完了")
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "RAG Memory", "url": self.rag_memory_url},
                user_message="記憶保存サービスへの接続に失敗しました",
            )
            logger.warning(f"RAG Memory接続エラー: {error.message}")

    async def _record_metric(
        self,
        service_name: str,
        metric_type: Any,  # MetricType or str
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """メトリクスを記録"""
        if not METRICS_AVAILABLE or not self.metrics_collector_url:
            return

        try:
            # MetricTypeが利用可能な場合はvalueを取得、そうでない場合は文字列として扱う
            metric_type_value = (
                metric_type.value if hasattr(metric_type, "value") else str(metric_type)
            )

            timeout = timeout_config.get("api_call", 10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                await client.post(
                    f"{self.metrics_collector_url}/api/metrics",
                    json={
                        "service_name": service_name,
                        "metric_type": metric_type_value,
                        "value": value,
                        "metadata": metadata or {},
                    },
                )
        except Exception as e:
            # メトリクス記録の失敗は警告のみ（非同期処理のため）
            logger.debug(f"メトリクス記録エラー: {e}")

    async def _record_to_learning_system(
        self,
        execution_id: str,
        intent_type: str,
        input_text: str,
        plan: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]],
        evaluation: Optional[Dict[str, Any]],
        duration_seconds: float,
        success: bool,
    ):
        """学習システムに記録"""
        if not self.learning_system and not self.learning_system_url:
            return

        try:
            # 学習用のコンテキストを構築
            context = {
                "intent_type": intent_type,
                "input_text": input_text,
                "plan_id": plan.get("plan_id", ""),
                "steps_count": len(plan.get("steps", [])),
                "duration_seconds": duration_seconds,
            }

            # 実行結果を構築
            result = {
                "status": "success" if success else "failed",
                "execution_id": execution_id,
                "evaluation_score": evaluation.get("score", 0.5) if evaluation else 0.5,
                "duration_seconds": duration_seconds,
            }

            # 直接インポートの場合
            if self.learning_system:
                self.learning_system.record_usage(
                    action=intent_type, context=context, result=result
                )
                logger.info(f"✅ 学習システムに記録完了: {intent_type}")

            # API経由の場合
            elif self.learning_system_url:
                timeout = timeout_config.get("api_call", 10.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.learning_system_url}/api/record",
                        json={"action": intent_type, "context": context, "result": result},
                    )
                    if response.status_code == 200:
                        logger.info(f"✅ 学習システムに記録完了（API経由）: {intent_type}")

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"execution_id": execution_id, "intent_type": intent_type},
                user_message="学習システムへの記録に失敗しました",
            )
            logger.warning(f"学習システム記録エラー: {error.message}")

    def get_execution_history(self, limit: int = 10) -> List[OrchestrationResult]:
        """実行履歴を取得"""
        results = list(self.execution_history.values())
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def get_execution(self, execution_id: str) -> Optional[OrchestrationResult]:
        """実行結果を取得"""
        return self.execution_history.get(execution_id)


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルオーケストレーターインスタンス
orchestrator = None


def init_orchestrator():
    """オーケストレーターを初期化"""
    global orchestrator
    if orchestrator is None:
        orchestrator = UnifiedOrchestrator()
    return orchestrator


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Unified Orchestrator"})


@app.route("/api/execute", methods=["POST"])
def execute_endpoint():
    """タスク実行エンドポイント"""
    try:
        data = request.get_json() or {}
        # ask_orchestrator(query) 互換: text または query で自然文を受け付ける
        input_text = data.get("text") or data.get("query") or ""

        if not input_text:
            error = error_handler.handle_exception(
                ValueError("text is required"),
                context={"endpoint": "/api/execute"},
                user_message="入力テキストが必要です",
            )
            return jsonify(error.to_json_response()), 400

        orchestrator = init_orchestrator()

        # 非同期実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            orchestrator.execute(
                input_text=input_text,
                mode=data.get("mode"),
                auto_evaluate=data.get("auto_evaluate"),
                save_to_memory=data.get("save_to_memory"),
            )
        )
        loop.close()

        return jsonify(to_unified_response(result))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/execute"},
            user_message="タスク実行エンドポイントでエラーが発生しました",
        )
        error_response = error.to_json_response()
        return jsonify(error_response), 500


@app.route("/api/history", methods=["GET"])
def get_history_endpoint():
    """実行履歴取得エンドポイント"""
    limit = request.args.get("limit", 10, type=int)

    orchestrator = init_orchestrator()
    history = orchestrator.get_execution_history(limit)

    return jsonify({"results": [asdict(r) for r in history], "count": len(history)})


@app.route("/api/execution/<execution_id>", methods=["GET"])
def get_execution_endpoint(execution_id: str):
    """実行結果取得エンドポイント"""
    orchestrator = init_orchestrator()
    result = orchestrator.get_execution(execution_id)

    if not result:
        return jsonify({"error": "Execution not found"}), 404

    return jsonify(asdict(result))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5106))
    logger.info(f"🎯 Unified Orchestrator起動中... (ポート: {port})")
    init_orchestrator()
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
