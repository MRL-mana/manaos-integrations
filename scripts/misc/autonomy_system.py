#!/usr/bin/env python3
"""
🤖 ManaOS 自律システム
自動的な判断・実行・改善サイクル

自律レベル L0〜L6 = 権限セット（Scope + Guards）
- Scope: 通知だけ / 調査まで / 実行まで / 破壊的操作まで
- Guards: Action Class・Confirm Token・予算・監査
"""

import os
import json
import secrets
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, jsonify, request
from flask_cors import CORS

# sys.path: repo root (scripts/misc/ -> scripts/ -> repo_root)
import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator
from _paths import INTRINSIC_MOTIVATION_PORT, ORCHESTRATOR_PORT

# ロガーの初期化
logger = get_service_logger("autonomy-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("AutonomySystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("AutonomySystem")

DEFAULT_ORCHESTRATOR_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}"
DEFAULT_INTRINSIC_MOTIVATION_URL = f"http://127.0.0.1:{INTRINSIC_MOTIVATION_PORT}"

# L0〜L6 ラベル（get_status 用）
LEVEL_NAMES = {
    0: "L0_OFF",
    1: "L1_Observe",
    2: "L2_Notify",
    3: "L3_Assist",
    4: "L4_Act",
    5: "L5_Autopilot",
    6: "L6_Ops",
}


class AutonomyLevel(str, Enum):
    """自律レベル（旧名称互換）"""
    DISABLED = "disabled"  # L0
    LOW = "low"            # L2
    MEDIUM = "medium"      # L3
    HIGH = "high"          # L4
    FULL = "full"          # L5


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
        orchestrator_url: Optional[str] = None,
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
        self.orchestrator_url = orchestrator_url or DEFAULT_ORCHESTRATOR_URL
        self.learning_system_url = learning_system_url
        self.intrinsic_motivation_url = intrinsic_motivation_url or DEFAULT_INTRINSIC_MOTIVATION_URL

        self.config_path = config_path or Path(__file__).parent / "autonomy_config.json"
        self.config = self._load_config()

        # レベル設定を config/autonomy_level_config.json からマージ（存在すれば）
        level_config_path = Path(__file__).parent / "config" / "autonomy_level_config.json"
        if level_config_path.exists():
            try:
                with open(level_config_path, "r", encoding="utf-8") as f:
                    level_config = json.load(f)
                self.config.update(level_config)
            except Exception as e:
                logger.warning(f"autonomy_level_config 読み込みスキップ: {e}")

        # 不足キーをデフォルトで補う（degrade_policy, runbooks_enabled 等）
        default = self._get_default_config()
        for k, v in default.items():
            if k not in self.config:
                self.config[k] = v

        # 自律レベル: 整数 0〜6（L0=OFF 〜 L6=Ops）
        raw_level = self.config.get("autonomy_level", 4)
        if isinstance(raw_level, int):
            self._level_int = max(0, min(6, raw_level))
        else:
            # 旧文字列互換
            self._level_int = self._parse_legacy_level(str(raw_level))

        self.autonomy_level = self._level_to_legacy_enum(self._level_int)

        # 自律タスク
        self.tasks: Dict[str, AutonomyTask] = {}
        self._load_tasks()

        # 実行履歴
        self.execution_history: List[Dict[str, Any]] = []
        # 連続失敗カウンタ（降格用）
        self._consecutive_failures = 0

        logger.info(f"✅ Autonomy System初期化完了 (レベル: {LEVEL_NAMES.get(self._level_int, 'L?')} = {self._level_int})")

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
            "autonomy_level": 4,
            "max_concurrent_tasks": 3,
            "check_interval_seconds": 60,
            "tasks_storage_path": "autonomy_tasks.json",
            "require_confirm_token_classes": ["C3", "C4"],
            "degrade_policy": {"on_budget_exceeded": 2, "on_repeated_failures": 3},
            "runbooks_enabled": ["health_recover", "log_rotate", "inbox_scan"],
            "runbook_flags": {"health_recover_allow_restart": False, "pixel7_bridge_allow_restart": False},
        }

    def _parse_legacy_level(self, s: str) -> int:
        """旧 autonomy_level 文字列を 0〜6 に変換"""
        m = {"disabled": 0, "low": 2, "medium": 3, "high": 4, "full": 5}
        return m.get(s.lower(), 4)

    def _level_to_legacy_enum(self, level_int: int) -> AutonomyLevel:
        """0〜6 を旧 AutonomyLevel に変換"""
        if level_int <= 0:
            return AutonomyLevel.DISABLED
        if level_int <= 2:
            return AutonomyLevel.LOW
        if level_int <= 3:
            return AutonomyLevel.MEDIUM
        if level_int <= 4:
            return AutonomyLevel.HIGH
        return AutonomyLevel.FULL

    def get_level_int(self) -> int:
        """現在の自律レベルを整数 0〜6 で返す"""
        return self._level_int

    def set_level_int(self, level: int) -> None:
        """自律レベルを 0〜6 で設定（一時的な降格・復帰用）"""
        self._level_int = max(0, min(6, level))
        self.autonomy_level = self._level_to_legacy_enum(self._level_int)
        logger.info(f"自律レベル変更: {LEVEL_NAMES.get(self._level_int, 'L?')}")

    def _approvals_path(self) -> Path:
        """一時承認トークン保存先"""
        base = Path(self.config.get("budget_usage_dir", Path(__file__).parent))
        return base / "autonomy_pending_approvals.json"

    def _load_approvals(self) -> Dict[str, Dict[str, Any]]:
        """保留中承認トークン一覧"""
        path = self._approvals_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("tokens", {})
        except Exception:
            return {}

    def _save_approvals(self, tokens: Dict[str, Dict[str, Any]]) -> None:
        path = self._approvals_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"tokens": tokens, "updated": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

    def _consume_ephemeral_token(self, token: str, tool_name: str) -> bool:
        """
        一時承認トークンを検証し、使用済みなら削除する。1回限り有効。
        Returns: 使用可能だったか
        """
        if not token or not token.strip():
            return False
        token = token.strip()
        tokens = self._load_approvals()
        entry = tokens.get(token)
        if not entry:
            return False
        expires = entry.get("expires_at")
        if expires:
            try:
                exp_dt = datetime.fromisoformat(expires.replace("Z", ""))
                if exp_dt < datetime.now():
                    del tokens[token]
                    self._save_approvals(tokens)
                    return False
            except (ValueError, TypeError) as e:
                logger.debug("承認トークン期限パース失敗: %s", e)
        allowed_tool = entry.get("tool_name")
        if allowed_tool and allowed_tool != tool_name:
            return False
        del tokens[token]
        self._save_approvals(tokens)
        return True

    def check_can_execute_tool(
        self, tool_name: str, confirm_token: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Gate A+B: 現在レベルでツール実行が許可されているかチェック。
        一時承認トークンがあれば消費して許可。
        Returns:
            (allowed, reason_message)
        """
        if confirm_token and self._consume_ephemeral_token(confirm_token, tool_name):
            return True, ""
        try:
            from autonomy_gates import check_gate
            return check_gate(self._level_int, tool_name, confirm_token, self.config)
        except ImportError:
            if self._level_int <= 0:
                return False, "自律は無効（L0）です"
            return True, ""

    def record_cost(
        self, usage_key: str, period: str = "per_hour", amount: int = 1
    ) -> bool:
        """
        Gate C: コストを記録。予算超過なら degrade_policy に従い降格。
        usage_key: llm_calls | image_jobs | video_jobs
        Returns: 記録後も予算内なら True
        """
        try:
            from autonomy_gates import (
                increment_budget_usage,
                check_budget,
                get_degraded_level,
            )
            increment_budget_usage(self.config, usage_key, period, amount)
            ok, _ = check_budget(self.config, usage_key, period)
            if not ok:
                new_level = get_degraded_level(self.config, "on_budget_exceeded")
                self.set_level_int(new_level)
                logger.warning(f"予算超過のためレベル降格: {LEVEL_NAMES.get(new_level)}")
            return ok
        except ImportError:
            return True

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
        if self._level_int <= 0:
            return []

        results = []

        # 内発的動機づけとの連携：L3以上でアイドル時間をチェックして内発的タスクを生成
        if self.intrinsic_motivation_url and self._level_int >= 3:
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

                # 監査ログ（Gate D）
                self._audit_task(task_id, task, result)

                # 失敗時は連続失敗カウント＋降格チェック
                if result.get("status") in ("failed", "error"):
                    self._consecutive_failures += 1
                    policy = self.config.get("degrade_policy") or {}
                    threshold = policy.get("on_repeated_failures_threshold", 5)
                    if self._consecutive_failures >= threshold:
                        try:
                            from autonomy_gates import get_degraded_level
                            new_level = get_degraded_level(self.config, "on_repeated_failures")
                            if new_level < self._level_int:
                                self.set_level_int(new_level)
                                logger.warning(f"連続失敗のためレベル降格: {LEVEL_NAMES.get(new_level)}")
                        except ImportError:
                            pass
                else:
                    self._consecutive_failures = 0

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

    def _audit_task(self, task_id: str, task: AutonomyTask, result: Dict[str, Any]) -> None:
        """自律タスク実行を監査ログに記録"""
        try:
            from autonomy_gates import audit_log, input_hash_for_audit
            audit_log(
                self.config,
                plan_id=task_id,
                action_id=task_id,
                tool_name=task.action.get("type", "orchestrator"),
                action_class="task",
                input_hash=input_hash_for_audit(task.action),
                result=result.get("status", "unknown"),
                message=result.get("error", ""),
                level=self._level_int,
            )
        except ImportError:
            pass

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
            except (ValueError, TypeError) as e:
                logger.debug("時刻パース失敗 (last_executed=%s): %s", last_executed, e)
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
        """状態を取得（L0〜L6 と旧名称の両方を含む）"""
        try:
            from autonomy_gates import load_budget_usage, get_audit_log_path
            budget_usage = load_budget_usage(self.config)
            audit_path = get_audit_log_path(self.config)
            audit_path_str = str(audit_path) if audit_path else None
        except ImportError:
            budget_usage = {}
            audit_path_str = None

        return {
            "autonomy_level": self.autonomy_level.value,
            "autonomy_level_int": self._level_int,
            "autonomy_level_name": LEVEL_NAMES.get(self._level_int, "L?"),
            "total_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "total_executions": sum(t.execution_count for t in self.tasks.values()),
            "total_successes": sum(t.success_count for t in self.tasks.values()),
            "consecutive_failures": getattr(self, "_consecutive_failures", 0),
            "recent_executions": self.execution_history[-10:] if self.execution_history else [],
            "budget_usage": budget_usage,
            "audit_log_path": audit_path_str,
            "timestamp": datetime.now().isoformat(),
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
    """条件をチェックしてタスクを実行（Runbook の due 分 → 通常タスク）"""
    try:
        system = init_autonomy_system()
        runbook_results = []
        if system.get_level_int() >= 4:
            try:
                from runbook_engine import run_runbooks_due
                runbook_results = run_runbooks_due(
                    system.orchestrator_url,
                    system.config,
                    system.get_level_int(),
                )
            except ImportError:
                pass
        results = system.check_and_execute_tasks()
        return jsonify({
            "results": results,
            "count": len(results),
            "runbook_results": runbook_results,
            "runbook_count": len(runbook_results),
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/execute"},
            user_message="自律タスクの実行に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/level', methods=['GET'])
def get_level():
    """現在の自律レベル（0〜6）を取得"""
    try:
        system = init_autonomy_system()
        return jsonify({
            "autonomy_level": system.get_level_int(),
            "autonomy_level_name": LEVEL_NAMES.get(system.get_level_int(), "L?"),
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/level"},
            user_message="レベルの取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/level', methods=['POST'])
def set_level():
    """
    自律レベルを変更（0〜6）。
    L5/L6 への変更は body に confirm_token を付与することを推奨。
    """
    try:
        data = request.get_json() or {}
        level = data.get("level") if "level" in data else data.get("autonomy_level")
        if level is None:
            return jsonify({"error": "level または autonomy_level を指定してください"}), 400
        level = int(level)
        if level < 0 or level > 6:
            return jsonify({"error": "level は 0〜6 の整数で指定してください"}), 400
        confirm_token = data.get("confirm_token")
        system = init_autonomy_system()
        if level >= 5 and not confirm_token:
            logger.warning("L5/L6 への変更に confirm_token がありません")
        system.set_level_int(level)
        return jsonify({
            "autonomy_level": system.get_level_int(),
            "autonomy_level_name": LEVEL_NAMES.get(system.get_level_int(), "L?"),
        })
    except ValueError as e:
        return jsonify({"error": f"無効な level: {e}"}), 400
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/level"},
            user_message="レベルの変更に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/check-tool', methods=['POST'])
def check_tool():
    """
    ツール実行が現在の自律レベルで許可されているかチェック（Gate A+B）。
    body: {"tool_name": "...", "confirm_token": "...?"}
    """
    try:
        data = request.get_json() or {}
        tool_name = data.get("tool_name")
        if not tool_name:
            return jsonify({"allowed": False, "reason": "tool_name は必須です"}), 400
        confirm_token = data.get("confirm_token")
        system = init_autonomy_system()
        allowed, reason = system.check_can_execute_tool(tool_name, confirm_token)
        return jsonify(
            {
                "allowed": allowed,
                "reason": reason,
                "level": system.get_level_int(),
            }
        )
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/check-tool"},
            user_message="ツール実行可否チェックに失敗しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/approvals', methods=['POST'])
def create_approval():
    """
    1回限り有効な Confirm Token を発行する（「この1回だけ許可」用）。
    body: {"tool_name": "llm_chat"?, "expires_in_seconds": 300?}
    """
    try:
        data = request.get_json() or {}
        tool_name = data.get("tool_name")
        expires_in = int(data.get("expires_in_seconds", 300))
        expires_in = max(60, min(3600, expires_in))
        system = init_autonomy_system()
        token = secrets.token_hex(8)
        tokens = system._load_approvals()
        tokens[token] = {
            "tool_name": tool_name,
            "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        }
        system._save_approvals(tokens)
        return jsonify({
            "confirm_token": token,
            "expires_in": expires_in,
            "tool_name": tool_name,
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/approvals"},
            user_message="承認トークンの発行に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    """
    Portal/ダッシュボード用: レベル・予算・Runbook 最終実行・監査ログ末尾をまとめて返す。
    """
    try:
        system = init_autonomy_system()
        status = system.get_status()
        base = Path(system.config.get("budget_usage_dir", Path(__file__).parent))
        runbook_state_path = base / "autonomy_runbook_state.json"
        runbook_last_runs = {}
        if runbook_state_path.exists():
            try:
                runbook_last_runs = json.loads(runbook_state_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.debug("runbook state読み込み失敗: %s", e)
        audit_tail = []
        try:
            from autonomy_gates import get_audit_log_path
            path = get_audit_log_path(system.config)
            if path and path.exists():
                lines = path.read_text(encoding="utf-8").strip().split("\n")
                for line in lines[-50:]:
                    line = line.strip()
                    if line:
                        try:
                            audit_tail.append(json.loads(line))
                        except (json.JSONDecodeError, ValueError):
                            pass  # 不正行はスキップ
        except Exception as e:
            logger.debug("監査ログ取得失敗: %s", e)
        return jsonify({
            "autonomy_level": status.get("autonomy_level_int", 0),
            "autonomy_level_name": status.get("autonomy_level_name", "L?"),
            "budget_usage": status.get("budget_usage", {}),
            "runbook_last_runs": runbook_last_runs,
            "audit_tail": audit_tail[-30:],
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/dashboard"},
            user_message="ダッシュボード取得に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/record-cost', methods=['POST'])
def record_cost_api():
    """
    コスト使用量を記録し、必要であれば降格する。
    body: {"usage_key": "llm_calls|image_jobs|video_jobs", "period": "per_hour|per_day", "amount": 1}
    """
    try:
        data = request.get_json() or {}
        usage_key = data.get("usage_key")
        if usage_key not in {"llm_calls", "image_jobs", "video_jobs"}:
            return jsonify({"ok": False, "error": "usage_key は llm_calls|image_jobs|video_jobs のいずれか"}), 400
        period = data.get("period", "per_hour")
        amount = int(data.get("amount", 1))
        system = init_autonomy_system()
        ok = system.record_cost(usage_key, period, amount)
        return jsonify(
            {
                "ok": ok,
                "autonomy_level": system.get_level_int(),
                "autonomy_level_name": LEVEL_NAMES.get(system.get_level_int(), "L?"),
            }
        )
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/record-cost"},
            user_message="コスト記録に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5124))
    logger.info(f"🤖 Autonomy System起動中... (ポート: {port})")
    init_autonomy_system()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
