#!/usr/bin/env python3
"""
📋 Task Planner - タスク分解・実行計画作成システム
意図から具体的な実行計画を作成
"""

import os
import json
import httpx
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
error_handler = ManaOSErrorHandler("TaskPlanner")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("TaskPlanner")


class TaskStatus(str, Enum):
    """タスクステータス"""
    PENDING = "pending"  # 待機中
    IN_PROGRESS = "in_progress"  # 実行中
    COMPLETED = "completed"  # 完了
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # キャンセル


class TaskPriority(str, Enum):
    """タスク優先度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TaskStep:
    """タスクステップ"""
    step_id: str
    description: str
    action: str  # 実行アクション（例: "call_api", "run_script", "execute_workflow"）
    target: str  # ターゲット（例: "n8n_workflow", "api_endpoint", "script_path"）
    parameters: Dict[str, Any]  # パラメータ
    dependencies: List[str]  # 依存するステップID
    estimated_duration: int  # 推定実行時間（秒）
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ExecutionPlan:
    """実行計画"""
    plan_id: str
    intent_type: str
    original_input: str
    steps: List[TaskStep]
    total_estimated_duration: int
    priority: TaskPriority
    created_at: str
    status: TaskStatus = TaskStatus.PENDING
    completed_at: Optional[str] = None


class TaskPlanner:
    """タスクプランナー"""
    
    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:14b",  # 中型モデル（推論が必要）
        intent_router_url: str = "http://127.0.0.1:5100",
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            ollama_url: Ollama API URL
            model: 使用するモデル
            intent_router_url: Intent Router API URL
            config_path: 設定ファイルのパス
        """
        self.ollama_url = ollama_url
        self.model = model
        self.intent_router_url = intent_router_url
        self.config_path = config_path or Path(__file__).parent / "task_planner_config.json"
        self.config = self._load_config()
        
        # アクションテンプレート
        self.action_templates = self.config.get("action_templates", self._get_default_action_templates())
        
        # プランニングプロンプトテンプレート
        self.planning_prompt_template = self.config.get(
            "planning_prompt_template",
            self._get_default_planning_prompt_template()
        )
        
        logger.info(f"✅ Task Planner初期化完了 (モデル: {model})")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": ["model"],
                    "fields": {
                        "ollama_url": {"type": str, "default": "http://127.0.0.1:11434"},
                        "model": {"type": str},
                        "intent_router_url": {"type": str, "default": "http://127.0.0.1:5100"},
                        "max_steps": {"type": int, "default": 10},
                        "default_priority": {"type": str, "default": "medium"}
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
            "ollama_url": "http://127.0.0.1:11434",
            "model": "qwen2.5:14b",
            "intent_router_url": "http://127.0.0.1:5100",
            "action_templates": self._get_default_action_templates(),
            "planning_prompt_template": self._get_default_planning_prompt_template(),
            "max_steps": 10,
            "default_priority": "medium"
        }
    
    def _get_default_action_templates(self) -> Dict[str, Dict[str, Any]]:
        """デフォルトアクションテンプレート"""
        return {
            "image_generation": {
                "action": "execute_workflow",
                "target": "n8n_workflow",
                "workflow_name": "image_generation",
                "default_params": {
                    "steps": 20,
                    "cfg_scale": 7.0,
                    "sampler": "Euler a"
                }
            },
            "code_generation": {
                "action": "call_api",
                "target": "code_generation_api",
                "default_params": {}
            },
            "information_search": {
                "action": "call_api",
                "target": "rag_api",
                "default_params": {}
            },
            "task_execution": {
                "action": "execute_workflow",
                "target": "n8n_workflow",
                "default_params": {}
            },
            "system_control": {
                "action": "call_api",
                "target": "system_control_api",
                "default_params": {}
            },
            "scheduling": {
                "action": "execute_workflow",
                "target": "n8n_workflow",
                "workflow_name": "calendar_generation",
                "default_params": {}
            },
            "data_analysis": {
                "action": "call_api",
                "target": "data_analysis_api",
                "default_params": {}
            }
        }
    
    def _get_default_planning_prompt_template(self) -> str:
        """デフォルトプランニングプロンプトテンプレート"""
        return """あなたはタスクプランニングシステムです。ユーザーの意図から具体的な実行計画を作成してください。

意図タイプ: {intent_type}
ユーザー入力: {input}
意図分類結果: {intent_result}

利用可能なアクション:
- execute_workflow: n8nワークフローを実行
- call_api: APIを呼び出す
- run_script: スクリプトを実行
- execute_command: コマンドを実行

以下のJSON形式で実行計画を作成してください:
{{
    "steps": [
        {{
            "step_id": "step_1",
            "description": "ステップの説明",
            "action": "アクションタイプ",
            "target": "ターゲット（ワークフロー名、APIエンドポイントなど）",
            "parameters": {{"key": "value"}},
            "dependencies": [],
            "estimated_duration": 60,
            "priority": "high|medium|low"
        }}
    ],
    "total_estimated_duration": 120,
    "priority": "high|medium|low"
}}

重要:
- ステップは順序立てて、依存関係を明確に
- 各ステップの推定実行時間を設定
- 優先度を適切に設定
- パラメータは具体的に"""
    
    def _get_intent(self, input_text: str) -> Optional[Dict[str, Any]]:
        """Intent Routerから意図を取得"""
        try:
            timeout = timeout_config.get("api_call", 10.0)
            response = httpx.post(
                f"{self.intent_router_url}/api/classify",
                json={"text": input_text},
                timeout=timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Intent Router", "url": self.intent_router_url},
                user_message="意図分類サービスへの接続に失敗しました"
            )
            logger.warning(f"Intent Router接続エラー: {error.message}")
        
        return None
    
    def _is_simple_plan(self, input_text: str, intent_result: Dict[str, Any]) -> bool:
        """計画が簡単かどうかを判定"""
        intent_type = intent_result.get("intent_type", "unknown")
        
        # 簡単な意図タイプ
        simple_intents = [
            "conversation",
            "file_search",
            "file_status"
        ]
        
        if intent_type in simple_intents:
            return True
        
        # 入力テキストの長さと複雑度で判定
        if len(input_text) < 50:  # 短い入力は簡単と判断
            return True
        
        # 複雑なキーワードが含まれているかチェック
        complex_keywords = [
            "複雑", "複数", "統合", "分析", "設計", "アーキテクチャ",
            "複雑な", "複数の", "統合する", "分析する", "設計する"
        ]
        
        if any(keyword in input_text for keyword in complex_keywords):
            return False
        
        return True
    
    def _plan_with_llm(
        self,
        input_text: str,
        intent_result: Dict[str, Any]
    ) -> ExecutionPlan:
        """LLMで実行計画を作成"""
        intent_type = intent_result.get("intent_type", "unknown")
        
        prompt = self.planning_prompt_template.format(
            intent_type=intent_type,
            input=input_text,
            intent_result=json.dumps(intent_result, ensure_ascii=False, indent=2)
        )
        
        # 簡単な計画はLFM 2.5を使用
        is_simple = self._is_simple_plan(input_text, intent_result)
        if is_simple:
            # LFM 2.5を使用（lightweight_conversation経由）
            try:
                import manaos_core_api as manaos
                result = manaos.act("llm_call", {
                    "task_type": "lightweight_conversation",
                    "prompt": prompt
                })
                result_text = result.get("response", "")
            except Exception as e:
                logger.warning(f"LFM 2.5呼び出し失敗、従来モデルにフォールバック: {e}")
                result_text = None
        else:
            result_text = None
        
        # LFM 2.5が失敗した場合、または複雑な計画の場合は従来通り
        if not result_text:
            try:
                timeout = timeout_config.get("llm_call_heavy", 60.0)
                response = httpx.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.5,
                            "num_predict": 2000
                        }
                    },
                    timeout=timeout
                )
            
                if response.status_code != 200:
                    error = error_handler.handle_exception(
                        Exception(f"LLMプランニング失敗: HTTP {response.status_code}"),
                        context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                        user_message="実行計画の作成に失敗しました"
                    )
                    logger.warning(f"LLMプランニング失敗: {error.message}")
                    return self._create_fallback_plan(input_text, intent_result)
                
                result_text = response.json().get("response", "")
            except httpx.TimeoutException as e:
                error = error_handler.handle_exception(
                    e,
                    context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                    user_message="実行計画の作成がタイムアウトしました"
                )
                logger.warning(f"LLMプランニングタイムアウト - フォールバック計画を使用: {error.message}")
                return self._create_fallback_plan(input_text, intent_result)
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                    user_message="実行計画の作成に失敗しました"
                )
                logger.error(f"LLMプランニングエラー: {error.message}")
                return self._create_fallback_plan(input_text, intent_result)
        
        # レスポンス処理（正常な場合）
        
        # JSONを抽出
        try:
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                plan_data = json.loads(json_str)
            else:
                return self._create_fallback_plan(input_text, intent_result)
        except json.JSONDecodeError as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "TaskPlanner", "method": "_plan_with_llm"},
                user_message="実行計画の解析に失敗しました"
            )
            logger.warning(f"JSON解析失敗、フォールバック計画を使用: {error.message}")
            return self._create_fallback_plan(input_text, intent_result)
        
        # ExecutionPlanに変換
        steps = []
        for step_data in plan_data.get("steps", []):
            step = TaskStep(
                step_id=step_data.get("step_id", f"step_{len(steps) + 1}"),
                description=step_data.get("description", ""),
                action=step_data.get("action", "call_api"),
                target=step_data.get("target", ""),
                parameters=step_data.get("parameters", {}),
                dependencies=step_data.get("dependencies", []),
                estimated_duration=int(step_data.get("estimated_duration", 60)),
                priority=TaskPriority(step_data.get("priority", "medium"))
            )
            steps.append(step)
        
        priority_str = plan_data.get("priority", "medium")
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.MEDIUM
        
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(input_text) % 10000}"
        
        return ExecutionPlan(
            plan_id=plan_id,
            intent_type=intent_type,
            original_input=input_text,
            steps=steps,
            total_estimated_duration=int(plan_data.get("total_estimated_duration", sum(s.estimated_duration for s in steps))),
            priority=priority,
            created_at=datetime.now().isoformat()
        )
    
    def _create_fallback_plan(
        self,
        input_text: str,
        intent_result: Dict[str, Any]
    ) -> ExecutionPlan:
        """フォールバック計画を作成"""
        intent_type = intent_result.get("intent_type", "unknown")
        
        # アクションテンプレートから計画を作成
        template = self.action_templates.get(intent_type, {})
        
        step = TaskStep(
            step_id="step_1",
            description=f"{intent_type}を実行",
            action=template.get("action", "call_api"),
            target=template.get("target", ""),
            parameters=template.get("default_params", {}),
            dependencies=[],
            estimated_duration=60,
            priority=TaskPriority.MEDIUM
        )
        
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(input_text) % 10000}"
        
        return ExecutionPlan(
            plan_id=plan_id,
            intent_type=intent_type,
            original_input=input_text,
            steps=[step],
            total_estimated_duration=60,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.now().isoformat()
        )
    
    def create_plan(self, input_text: str) -> ExecutionPlan:
        """
        実行計画を作成
        
        Args:
            input_text: ユーザー入力テキスト
        
        Returns:
            ExecutionPlan: 実行計画
        """
        # 意図を取得
        intent_result = self._get_intent(input_text)
        if not intent_result:
            # フォールバック
            intent_result = {
                "intent_type": "unknown",
                "confidence": 0.0,
                "entities": {},
                "reasoning": "Intent Router接続失敗",
                "suggested_actions": []
            }
        
        # LLMで計画を作成
        plan = self._plan_with_llm(input_text, intent_result)
        
        logger.info(f"✅ 実行計画作成完了: {plan.plan_id} ({len(plan.steps)}ステップ)")
        return plan
    
    def save_plan(self, plan: ExecutionPlan, output_path: Optional[Path] = None):
        """計画を保存"""
        if output_path is None:
            output_path = Path(__file__).parent / "plans" / f"{plan.plan_id}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(plan), f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 計画保存完了: {output_path}")
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"output_path": str(output_path)},
                user_message="実行計画の保存に失敗しました"
            )
            logger.error(f"計画保存エラー: {error.message}")


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルプランナーインスタンス
planner = None

def init_planner():
    """プランナーを初期化"""
    global planner
    if planner is None:
        planner = TaskPlanner()
    return planner

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Task Planner"})

@app.route('/api/plan', methods=['POST'])
def create_plan_endpoint():
    """実行計画作成エンドポイント"""
    try:
        data = request.get_json() or {}
        input_text = data.get("text", "")
        
        if not input_text:
            error = error_handler.handle_exception(
                ValueError("text is required"),
                context={"endpoint": "/api/plan"},
                user_message="入力テキストが必要です"
            )
            return jsonify(error.to_json_response()), 400
        
        planner = init_planner()
        plan = planner.create_plan(input_text)
        
        # 計画を保存
        planner.save_plan(plan)
        
        return jsonify(asdict(plan))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/plan"},
            user_message="実行計画作成エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/plan/<plan_id>', methods=['GET'])
def get_plan_endpoint(plan_id: str):
    """計画取得エンドポイント"""
    try:
        plan_path = Path(__file__).parent / "plans" / f"{plan_id}.json"
        
        if not plan_path.exists():
            error = error_handler.handle_exception(
                FileNotFoundError(f"Plan not found: {plan_id}"),
                context={"endpoint": "/api/plan/<plan_id>", "plan_id": plan_id},
                user_message="実行計画が見つかりません"
            )
            return jsonify(error.to_json_response()), 404
        
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)
        return jsonify(plan_data)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/plan/<plan_id>", "plan_id": plan_id},
            user_message="実行計画の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """設定を取得"""
    planner = init_planner()
    return jsonify(planner.config)


if __name__ == '__main__':
    import sys
    
    # コマンドライン引数で直接計画作成
    if len(sys.argv) > 1:
        planner = TaskPlanner()
        text = " ".join(sys.argv[1:])
        plan = planner.create_plan(text)
        print(f"\n📋 実行計画:")
        print(f"  計画ID: {plan.plan_id}")
        print(f"  意図: {plan.intent_type}")
        print(f"  ステップ数: {len(plan.steps)}")
        print(f"  推定時間: {plan.total_estimated_duration}秒")
        print(f"  優先度: {plan.priority.value}")
        print(f"\nステップ:")
        for i, step in enumerate(plan.steps, 1):
            print(f"  {i}. {step.description}")
            print(f"     アクション: {step.action}")
            print(f"     ターゲット: {step.target}")
            print(f"     依存: {', '.join(step.dependencies) if step.dependencies else 'なし'}")
    else:
        # APIサーバーとして起動
        port = int(os.getenv("PORT", 5101))
        logger.info(f"📋 Task Planner起動中... (ポート: {port})")
        init_planner()
        app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

