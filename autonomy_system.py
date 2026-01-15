#!/usr/bin/env python3
"""
🤖 ManaOS 自律システム
自動的な判断・実行・改善サイクル
"""

import os
import json
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, jsonify, request
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("AutonomySystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("AutonomySystem")


class AutonomyLevel(str, Enum):
    """自律レベル"""
    DISABLED = "disabled"  # 無効
    LOW = "low"  # 低（確認が必要）
    MEDIUM = "medium"  # 中（一部自動）
    HIGH = "high"  # 高（ほぼ自動）
    FULL = "full"  # 完全自動


@dataclass
class AutonomyTask:
    """自律タスク"""
    task_id: str
    task_type: str
    priority: str
    condition: Dict[str, Any]  # 実行条件
    action: Dict[str, Any]  # 実行アクション
    schedule: Optional[str]  # スケジュール（cron形式）
    enabled: bool = True
    last_executed: Optional[str] = None
    execution_count: int = 0
    success_count: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AutonomySystem:
    """自律システム"""

    def __init__(
        self,
        orchestrator_url: str = "http://localhost:5106",
        learning_system_url: Optional[str] = None,
        intrinsic_motivation_url: Optional[str] = None,
        config_path: Optional[Path] = None
    ):
        """
        初期化

        Args:
            orchestrator_url: Unified Orchestrator API URL
            learning_system_url: Learning System API URL（オプション）
            config_path: 設定ファイルのパス
        """
        self.orchestrator_url = orchestrator_url
        self.learning_system_url = learning_system_url
        self.intrinsic_motivation_url = intrinsic_motivation_url or "http://localhost:5130"

        self.config_path = config_path or Path(__file__).parent / "autonomy_config.json"
        self.config = self._load_config()

        # 自律レベル
        self.autonomy_level = AutonomyLevel(self.config.get("autonomy_level", "medium"))

        # 自律タスク
        self.tasks: Dict[str, AutonomyTask] = {}
        self._load_tasks()

        # 実行履歴
        self.execution_history: List[Dict[str, Any]] = []

        logger.info(f"✅ Autonomy System初期化完了 (レベル: {self.autonomy_level.value})")

    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 設定ファイルの検証
                schema = {
                    "required": [],
                    "fields": {
                        "autonomy_level": {"type": str, "default": "medium"},
                        "max_concurrent_tasks": {"type": int, "default": 3},
                        "check_interval_seconds": {"type": int, "default": 60}
                    }
                }

                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
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
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")

        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "autonomy_level": "medium",
            "max_concurrent_tasks": 3,
            "check_interval_seconds": 60,
            "tasks_storage_path": "autonomy_tasks.json"
        }

    def _load_tasks(self):
        """自律タスクを読み込む"""
        storage_path = Path(self.config.get("tasks_storage_path", "autonomy_tasks.json"))
        if storage_path.exists():
            try:
                with open(storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = AutonomyTask(**task_data)
                        self.tasks[task.task_id] = task
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"storage_path": str(storage_path)},
                    user_message="自律タスクの読み込みに失敗しました"
                )
                logger.warning(f"自律タスク読み込みエラー: {error.message}")

    def _save_tasks(self):
        """自律タスクを保存"""
        storage_path = Path(self.config.get("tasks_storage_path", "autonomy_tasks.json"))
        try:
            data = {
                "tasks": [asdict(task) for task in self.tasks.values()],
                "last_updated": datetime.now().isoformat()
            }
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"storage_path": str(storage_path)},
                user_message="自律タスクの保存に失敗しました"
            )
            logger.error(f"自律タスク保存エラー: {error.message}")

    def add_task(self, task: AutonomyTask) -> AutonomyTask:
        """
        自律タスクを追加

        Args:
            task: 自律タスク

        Returns:
            追加されたタスク
        """
        self.tasks[task.task_id] = task
        self._save_tasks()
        logger.info(f"✅ 自律タスク追加: {task.task_id}")
        return task

    def check_and_execute_tasks(self) -> List[Dict[str, Any]]:
        """
        条件をチェックしてタスクを実行

        Returns:
            実行結果のリスト
        """
        if self.autonomy_level == AutonomyLevel.DISABLED:
            return []

        results = []

        # 内発的動機づけとの連携：アイドル時間をチェックして内発的タスクを生成
        if self.intrinsic_motivation_url and self.autonomy_level.value in ["medium", "high"]:
            try:
                response = httpx.get(f"{self.intrinsic_motivation_url}/api/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    if status.get("is_idle", False) and status.get("enabled", True):
                        # 内発的タスクを生成
                        task_response = httpx.post(f"{self.intrinsic_motivation_url}/api/generate-tasks", timeout=10)
                        if task_response.status_code == 200:
                            tasks_data = task_response.json()
                            logger.info(f"✅ 内発的タスク生成: {tasks_data.get('count', 0)}件")
            except Exception as e:
                logger.debug(f"内発的動機づけ連携エラー（無視）: {e}")

        for task_id, task in self.tasks.items():
            if not task.enabled:
                continue

            # 条件チェック
            if self._check_condition(task.condition):
                # タスク実行
                result = self._execute_task(task)
                results.append(result)

                # 実行履歴に追加
                self.execution_history.append({
                    "task_id": task_id,
                    "executed_at": datetime.now().isoformat(),
                    "result": result
                })

                # 最新100件のみ保持
                if len(self.execution_history) > 100:
                    self.execution_history = self.execution_history[-100:]

        return results

    def _check_condition(self, condition: Dict[str, Any]) -> bool:
        """
        条件をチェック

        Args:
            condition: 条件

        Returns:
            条件を満たしているか
        """
        condition_type = condition.get("type", "always")

        if condition_type == "always":
            return True
        elif condition_type == "time_based":
            # 時間ベースの条件
            hour = datetime.now().hour
            target_hours = condition.get("hours", [])
            return hour in target_hours
        elif condition_type == "interval":
            # 間隔ベースの条件
            last_executed = condition.get("last_executed")
            interval_seconds = condition.get("interval_seconds", 3600)
            if not last_executed:
                return True
            try:
                last_time = datetime.fromisoformat(last_executed)
                elapsed = (datetime.now() - last_time).total_seconds()
                return elapsed >= interval_seconds
            except:
                return True
        elif condition_type == "service_status":
            # サービス状態ベースの条件
            service_name = condition.get("service_name")
            expected_status = condition.get("expected_status", "healthy")
            # 実装が必要（Service Monitor APIを呼び出す）
            return True

        return False

    def _execute_task(self, task: AutonomyTask) -> Dict[str, Any]:
        """
        タスクを実行

        Args:
            task: 自律タスク

        Returns:
            実行結果
        """
        try:
            action_type = task.action.get("type", "orchestrator")

            if action_type == "orchestrator":
                # Unified Orchestrator経由で実行
                timeout = timeout_config.get("workflow_execution", 300.0)
                response = httpx.post(
                    f"{self.orchestrator_url}/api/execute",
                    json={
                        "text": task.action.get("text", ""),
                        "mode": task.action.get("mode", "auto"),
                        "auto_evaluate": True,
                        "save_to_memory": True
                    },
                    timeout=timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    task.execution_count += 1
                    task.success_count += 1
                    task.last_executed = datetime.now().isoformat()
                    self._save_tasks()

                    return {
                        "task_id": task.task_id,
                        "status": "success",
                        "result": result
                    }
                else:
                    task.execution_count += 1
                    task.last_executed = datetime.now().isoformat()
                    self._save_tasks()

                    error = error_handler.handle_exception(
                        Exception(f"Orchestrator接続失敗: HTTP {response.status_code}"),
                        context={"task_id": task.task_id, "service": "Unified Orchestrator"},
                        user_message="自律タスクの実行に失敗しました"
                    )
                    return {
                        "task_id": task.task_id,
                        "status": "failed",
                        "error": error.message
                    }
            else:
                # その他のアクションタイプ
                task.execution_count += 1
                task.last_executed = datetime.now().isoformat()
                self._save_tasks()

                return {
                    "task_id": task.task_id,
                    "status": "skipped",
                    "reason": f"Unknown action type: {action_type}"
                }

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"task_id": task.task_id},
                user_message="自律タスクの実行に失敗しました"
            )
            task.execution_count += 1
            task.last_executed = datetime.now().isoformat()
            self._save_tasks()

            return {
                "task_id": task.task_id,
                "status": "error",
                "error": error.message
            }

    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "autonomy_level": self.autonomy_level.value,
            "total_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "total_executions": sum(t.execution_count for t in self.tasks.values()),
            "total_successes": sum(t.success_count for t in self.tasks.values()),
            "recent_executions": self.execution_history[-10:] if self.execution_history else [],
            "timestamp": datetime.now().isoformat()
        }


# Flask APIサーバー
app = Flask(__name__)
CORS(app)

# グローバル自律システムインスタンス
autonomy_system = None

def init_autonomy_system():
    """自律システムを初期化"""
    global autonomy_system
    if autonomy_system is None:
        autonomy_system = AutonomySystem()
    return autonomy_system

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Autonomy System"})

@app.route('/api/status', methods=['GET'])
def get_status():
    """状態を取得"""
    try:
        system = init_autonomy_system()
        status = system.get_status()
        return jsonify(status)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/status"},
            user_message="状態の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """自律タスク一覧を取得"""
    try:
        system = init_autonomy_system()
        tasks = [asdict(task) for task in system.tasks.values()]
        return jsonify({"tasks": tasks, "count": len(tasks)})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/tasks"},
            user_message="自律タスク一覧の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/tasks', methods=['POST'])
def add_task():
    """自律タスクを追加"""
    try:
        data = request.get_json() or {}

        task = AutonomyTask(
            task_id=data.get("task_id", f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            task_type=data.get("task_type", "general"),
            priority=data.get("priority", "medium"),
            condition=data.get("condition", {"type": "always"}),
            action=data.get("action", {}),
            schedule=data.get("schedule"),
            enabled=data.get("enabled", True)
        )

        system = init_autonomy_system()
        added_task = system.add_task(task)

        return jsonify(asdict(added_task))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/tasks"},
            user_message="自律タスクの追加に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/execute', methods=['POST'])
def execute_tasks():
    """条件をチェックしてタスクを実行"""
    try:
        system = init_autonomy_system()
        results = system.check_and_execute_tasks()
        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/execute"},
            user_message="自律タスクの実行に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5124))
    logger.info(f"🤖 Autonomy System起動中... (ポート: {port})")
    init_autonomy_system()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
