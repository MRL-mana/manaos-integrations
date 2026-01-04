#!/usr/bin/env python3
"""
⚙️ Task Executor Enhanced - 拡張タスク実行エンジン
Task Plannerの実行計画に対応、実行結果をTask Criticに連携
"""

import os
import json
import httpx
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("TaskExecutor")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("TaskExecutor")


class ExecutionAction(str, Enum):
    """実行アクション"""
    EXECUTE_WORKFLOW = "execute_workflow"  # n8nワークフロー実行
    CALL_API = "call_api"  # API呼び出し
    RUN_SCRIPT = "run_script"  # スクリプト実行
    EXECUTE_COMMAND = "execute_command"  # コマンド実行


@dataclass
class ExecutionStepResult:
    """実行ステップ結果"""
    step_id: str
    action: str
    target: str
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    duration_seconds: float
    started_at: str
    completed_at: str


@dataclass
class ExecutionResult:
    """実行結果"""
    execution_id: str
    plan_id: str
    status: str
    steps: List[ExecutionStepResult]
    total_duration_seconds: float
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    started_at: str
    completed_at: str


class TaskExecutorEnhanced:
    """拡張タスク実行エンジン"""
    
    def __init__(
        self,
        n8n_url: str = "http://localhost:5678",
        task_critic_url: str = "http://localhost:5102",
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            n8n_url: n8n API URL
            task_critic_url: Task Critic API URL
            config_path: 設定ファイルのパス
        """
        self.n8n_url = n8n_url
        self.task_critic_url = task_critic_url
        self.config_path = config_path or Path(__file__).parent / "task_executor_config.json"
        self.config = self._load_config()
        
        logger.info(f"✅ Task Executor Enhanced初期化完了")
    
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
                        "n8n_url": {"type": str, "default": "http://localhost:5678"},
                        "task_critic_url": {"type": str, "default": "http://localhost:5102"},
                        "timeout_seconds": {"type": int, "default": 300},
                        "retry_on_failure": {"type": bool, "default": True},
                        "max_retries": {"type": int, "default": 3}
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
            "n8n_url": "http://localhost:5678",
            "task_critic_url": "http://localhost:5102",
            "timeout_seconds": 300,
            "retry_on_failure": True,
            "max_retries": 3
        }
    
    def execute_plan(
        self,
        plan: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> ExecutionResult:
        """
        実行計画を実行
        
        Args:
            plan: Task Plannerが作成した実行計画
            execution_id: 実行ID（Noneの場合は自動生成）
        
        Returns:
            ExecutionResult: 実行結果
        """
        if not execution_id:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(json.dumps(plan, sort_keys=True)) % 10000}"
        
        plan_id = plan.get("plan_id", "")
        steps = plan.get("steps", [])
        
        start_time = datetime.now()
        step_results: List[ExecutionStepResult] = []
        
        try:
            # ステップを依存関係順にソート
            sorted_steps = self._sort_steps_by_dependencies(steps)
            
            # 各ステップを実行
            for step in sorted_steps:
                step_result = self._execute_step(step, execution_id)
                step_results.append(step_result)
                
                # ステップが失敗した場合、依存するステップをスキップ
                if step_result.status == "failed":
                    logger.warning(f"ステップ失敗: {step_result.step_id}")
                    # 依存するステップをスキップ
                    dependent_steps = [s for s in sorted_steps if step_result.step_id in s.get("dependencies", [])]
                    for dep_step in dependent_steps:
                        skipped_result = ExecutionStepResult(
                            step_id=dep_step.get("step_id", ""),
                            action=dep_step.get("action", ""),
                            target=dep_step.get("target", ""),
                            status="skipped",
                            result=None,
                            error=f"依存ステップ {step_result.step_id} が失敗したためスキップ",
                            duration_seconds=0.0,
                            started_at=datetime.now().isoformat(),
                            completed_at=datetime.now().isoformat()
                        )
                        step_results.append(skipped_result)
            
            # 全体の結果を構築
            all_succeeded = all(s.status == "completed" for s in step_results)
            all_failed = all(s.status == "failed" for s in step_results)
            
            if all_succeeded:
                status = "completed"
                result = {
                    "steps": [asdict(s) for s in step_results],
                    "summary": f"{len(step_results)}ステップ全て成功"
                }
                error = None
            elif all_failed:
                status = "failed"
                result = None
                error = "全てのステップが失敗しました"
            else:
                status = "partial_success"
                result = {
                    "steps": [asdict(s) for s in step_results],
                    "summary": f"{sum(1 for s in step_results if s.status == 'completed')}/{len(step_results)}ステップ成功"
                }
                error = None
            
            completed_time = datetime.now()
            duration = (completed_time - start_time).total_seconds()
            
            execution_result = ExecutionResult(
                execution_id=execution_id,
                plan_id=plan_id,
                status=status,
                steps=step_results,
                total_duration_seconds=duration,
                result=result,
                error=error,
                started_at=start_time.isoformat(),
                completed_at=completed_time.isoformat()
            )
            
            logger.info(f"✅ 実行計画完了: {execution_id} (ステータス: {status})")
            
            return execution_result
            
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"execution_id": execution_id, "plan_id": plan_id},
                user_message="実行計画の実行に失敗しました"
            )
            logger.error(f"❌ 実行計画失敗: {execution_id} - {error.message}")
            error_msg = error.user_message or error.message
            
            completed_time = datetime.now()
            duration = (completed_time - start_time).total_seconds()
            
            return ExecutionResult(
                execution_id=execution_id,
                plan_id=plan_id,
                status="failed",
                steps=step_results,
                total_duration_seconds=duration,
                result=None,
                error=error_msg,
                started_at=start_time.isoformat(),
                completed_at=completed_time.isoformat()
            )
    
    def _sort_steps_by_dependencies(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ステップを依存関係順にソート"""
        # 依存関係がないステップから順に実行
        sorted_steps = []
        remaining_steps = steps.copy()
        processed_step_ids = set()
        
        while remaining_steps:
            # 依存関係が全て処理済みのステップを探す
            ready_steps = [
                s for s in remaining_steps
                if all(dep_id in processed_step_ids for dep_id in s.get("dependencies", []))
            ]
            
            if not ready_steps:
                # 循環依存の可能性がある場合は残りをそのまま追加
                sorted_steps.extend(remaining_steps)
                break
            
            # 優先度順にソート
            ready_steps.sort(key=lambda s: self._get_priority_value(s.get("priority", "medium")))
            
            for step in ready_steps:
                sorted_steps.append(step)
                processed_step_ids.add(step.get("step_id", ""))
                remaining_steps.remove(step)
        
        return sorted_steps
    
    def _get_priority_value(self, priority: str) -> int:
        """優先度を数値に変換"""
        priority_map = {
            "urgent": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_map.get(priority.lower(), 2)
    
    def _execute_step(self, step: Dict[str, Any], execution_id: str) -> ExecutionStepResult:
        """ステップを実行"""
        step_id = step.get("step_id", "")
        action = step.get("action", "")
        target = step.get("target", "")
        parameters = step.get("parameters", {})
        
        start_time = datetime.now()
        
        logger.info(f"⚙️ ステップ実行開始: {step_id} ({action})")
        
        try:
            if action == ExecutionAction.EXECUTE_WORKFLOW.value:
                result = self._execute_workflow(target, parameters)
            elif action == ExecutionAction.CALL_API.value:
                result = self._call_api(target, parameters)
            elif action == ExecutionAction.RUN_SCRIPT.value:
                result = self._run_script(target, parameters)
            elif action == ExecutionAction.EXECUTE_COMMAND.value:
                result = self._execute_command(target, parameters)
            else:
                raise Exception(f"未知のアクション: {action}")
            
            completed_time = datetime.now()
            duration = (completed_time - start_time).total_seconds()
            
            return ExecutionStepResult(
                step_id=step_id,
                action=action,
                target=target,
                status="completed",
                result=result,
                error=None,
                duration_seconds=duration,
                started_at=start_time.isoformat(),
                completed_at=completed_time.isoformat()
            )
            
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"step_id": step_id, "action": action, "target": target},
                user_message="ステップの実行に失敗しました"
            )
            logger.error(f"❌ ステップ実行失敗: {step_id} - {error.message}")
            error_msg = error.user_message or error.message
            
            completed_time = datetime.now()
            duration = (completed_time - start_time).total_seconds()
            
            return ExecutionStepResult(
                step_id=step_id,
                action=action,
                target=target,
                status="failed",
                result=None,
                error=error_msg,
                duration_seconds=duration,
                started_at=start_time.isoformat(),
                completed_at=completed_time.isoformat()
            )
    
    def _execute_workflow(self, workflow_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """n8nワークフローを実行"""
        # n8n Webhook URLを構築
        webhook_url = f"{self.n8n_url}/webhook/{workflow_name}"
        
        try:
            timeout = timeout_config.get("workflow_execution", 300.0)
            response = httpx.post(
                webhook_url,
                json=parameters,
                timeout=timeout
            )
            response.raise_for_status()
            
            return {
                "workflow": workflow_name,
                "status_code": response.status_code,
                "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }
        except Exception as e:
            raise Exception(f"ワークフロー実行失敗: {e}")
    
    def _call_api(self, api_url: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """APIを呼び出す"""
        method = parameters.get("method", "POST")
        headers = parameters.get("headers", {})
        data = parameters.get("data", {})
        
        try:
            timeout = timeout_config.get("api_call", 10.0)
            if method.upper() == "GET":
                response = httpx.get(
                    api_url,
                    headers=headers,
                    params=data,
                    timeout=timeout
                )
            else:
                response = httpx.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=timeout
                )
            
            response.raise_for_status()
            
            return {
                "url": api_url,
                "method": method,
                "status_code": response.status_code,
                "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }
        except Exception as e:
            raise Exception(f"API呼び出し失敗: {e}")
    
    def _run_script(self, script_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """スクリプトを実行"""
        script_args = parameters.get("args", [])
        env = parameters.get("env", {})
        
        try:
            result = subprocess.run(
                [script_path] + script_args,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout_seconds", 300),
                env={**os.environ, **env}
            )
            
            if result.returncode != 0:
                raise Exception(f"スクリプト実行失敗: {result.stderr}")
            
            return {
                "script": script_path,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            raise Exception(f"スクリプト実行失敗: {e}")
    
    def _execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """コマンドを実行"""
        shell = parameters.get("shell", True)
        env = parameters.get("env", {})
        
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout_seconds", 300),
                env={**os.environ, **env}
            )
            
            if result.returncode != 0:
                raise Exception(f"コマンド実行失敗: {result.stderr}")
            
            return {
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            raise Exception(f"コマンド実行失敗: {e}")
    
    def evaluate_result(
        self,
        intent_type: str,
        original_input: str,
        plan: Dict[str, Any],
        execution_result: ExecutionResult
    ) -> Optional[Dict[str, Any]]:
        """実行結果をTask Criticで評価"""
        try:
            response = httpx.post(
                f"{self.task_critic_url}/api/evaluate",
                json={
                    "intent_type": intent_type,
                    "original_input": original_input,
                    "plan": plan,
                    "status": execution_result.status,
                    "output": execution_result.result,
                    "error": execution_result.error,
                    "duration": execution_result.total_duration_seconds
                },
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Task Critic評価エラー: {e}")
        
        return None


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルExecutorインスタンス
executor = None

def init_executor():
    """Executorを初期化"""
    global executor
    if executor is None:
        executor = TaskExecutorEnhanced()
    return executor

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Task Executor Enhanced"})

@app.route('/api/execute', methods=['POST'])
def execute_endpoint():
    """実行計画実行エンドポイント"""
    data = request.get_json() or {}
    plan = data.get("plan")
    
    if not plan:
        return jsonify({"error": "plan is required"}), 400
    
    executor = init_executor()
    result = executor.execute_plan(plan, data.get("execution_id"))
    
    return jsonify(asdict(result))

@app.route('/api/evaluate', methods=['POST'])
def evaluate_endpoint():
    """実行結果評価エンドポイント"""
    data = request.get_json() or {}
    
    intent_type = data.get("intent_type", "unknown")
    original_input = data.get("original_input", "")
    plan = data.get("plan", {})
    execution_result_dict = data.get("execution_result", {})
    
    # ExecutionResultオブジェクトに変換
    execution_result = ExecutionResult(**execution_result_dict)
    
    executor = init_executor()
    evaluation = executor.evaluate_result(intent_type, original_input, plan, execution_result)
    
    if not evaluation:
        return jsonify({"error": "評価に失敗しました"}), 500
    
    return jsonify(evaluation)


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5107))
    logger.info(f"⚙️ Task Executor Enhanced起動中... (ポート: {port})")
    init_executor()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

