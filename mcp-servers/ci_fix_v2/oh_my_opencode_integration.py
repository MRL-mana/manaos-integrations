#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 OH MY OPENCODE統合モジュール
ManaOS × OH MY OPENCODE統合システム
"""

import os
import yaml
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# asdict関数のインポート（既にdataclassesからインポート済み）

# 統一モジュールのインポート
from base_integration import BaseIntegration
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# LLMルーティング統合（オプション）
try:
    from llm_routing import LLMRouter
    LLM_ROUTING_AVAILABLE = True
except ImportError:
    LLM_ROUTING_AVAILABLE = False
    LLMRouter = None

# コスト管理統合（オプション）
try:
    from cost_optimization import CostOptimization
    COST_MANAGEMENT_AVAILABLE = True
except ImportError:
    COST_MANAGEMENT_AVAILABLE = False
    CostOptimization = None

# OH MY OPENCODEコスト管理
try:
    from oh_my_opencode_cost_manager import OHMyOpenCodeCostManager
    OH_MY_OPENCODE_COST_MANAGER_AVAILABLE = True
except ImportError:
    OH_MY_OPENCODE_COST_MANAGER_AVAILABLE = False
    OHMyOpenCodeCostManager = None

# Trinity統合ブリッジ
try:
    from oh_my_opencode_trinity_bridge import TrinityBridge, RemiAnalysis, LunaMonitoring, MinaMemory
    TRINITY_BRIDGE_AVAILABLE = True
except ImportError:
    TRINITY_BRIDGE_AVAILABLE = False
    TrinityBridge = None
    RemiAnalysis = None
    LunaMonitoring = None
    MinaMemory = None

# Kill Switch
try:
    from oh_my_opencode_kill_switch import OHMyOpenCodeKillSwitch, KillSwitchReason
    KILL_SWITCH_AVAILABLE = True
except ImportError:
    KILL_SWITCH_AVAILABLE = False
    OHMyOpenCodeKillSwitch = None
    KillSwitchReason = None

# 最適化システム
try:
    from oh_my_opencode_optimizer import OHMyOpenCodeOptimizer
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False
    OHMyOpenCodeOptimizer = None

# コスト見える化システム
try:
    from oh_my_opencode_cost_visibility import OHMyOpenCodeCostVisibility
    COST_VISIBILITY_AVAILABLE = True
except ImportError:
    COST_VISIBILITY_AVAILABLE = False
    OHMyOpenCodeCostVisibility = None

# 成功パターンテンプレート
try:
    from oh_my_opencode_templates import OHMyOpenCodeTemplates
    TEMPLATES_AVAILABLE = True
except ImportError:
    TEMPLATES_AVAILABLE = False
    OHMyOpenCodeTemplates = None

# 観測設計システム
try:
    from oh_my_opencode_observability import OHMyOpenCodeObservability
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    OHMyOpenCodeObservability = None

# 本番運用ルールセット（Policy）
POLICY_AVAILABLE = False
OHMyOpenCodePolicy = None
try:
    from oh_my_opencode_policy import OHMyOpenCodePolicy
    POLICY_AVAILABLE = True
except ImportError:
    POLICY_AVAILABLE = False
    OHMyOpenCodePolicy = None


class ExecutionMode(str, Enum):
    """実行モード"""
    NORMAL = "normal"  # 通常モード（コスト最適化）
    ULTRA_WORK = "ultra_work"  # Ultra Workモード（品質優先）


class TaskType(str, Enum):
    """タスクタイプ"""
    SPECIFICATION = "specification"  # 仕様策定
    COMPLEX_BUG = "complex_bug"  # 難解バグ
    ARCHITECTURE_DESIGN = "architecture_design"  # 初期アーキ設計
    CODE_GENERATION = "code_generation"  # コード生成
    CODE_REVIEW = "code_review"  # コードレビュー
    REFACTORING = "refactoring"  # リファクタリング
    GENERAL = "general"  # 一般タスク


@dataclass
class OHMyOpenCodeTask:
    """OH MY OPENCODEタスク"""
    task_id: str
    description: str
    mode: ExecutionMode = ExecutionMode.NORMAL
    task_type: TaskType = TaskType.GENERAL
    max_iterations: Optional[int] = None
    max_execution_time: Optional[int] = None
    max_cost: Optional[float] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class OHMyOpenCodeResult:
    """OH MY OPENCODE実行結果"""
    task_id: str
    status: str  # "success", "failed", "timeout", "cost_limit_exceeded"
    result: Optional[Dict[str, Any]] = None
    cost: float = 0.0
    execution_time: float = 0.0
    iterations: int = 0
    error: Optional[str] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class CostLimitExceededError(Exception):
    """コスト上限超過エラー"""
    pass


class UltraWorkNotAllowedError(Exception):
    """Ultra Workモード使用不可エラー"""
    pass


class OHMyOpenCodeIntegration(BaseIntegration):
    """OH MY OPENCODE統合クラス"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        if config_path is None:
            config_path = Path(__file__).parent / "oh_my_opencode_config.yaml"  # type: ignore
        
        super().__init__("OHMyOpenCode", str(config_path))
        
        # API設定
        # OH MY OPENCODEは既存のLLMプロバイダのAPIキーを使用します
        # OpenRouter / OpenAI / Anthropic などのAPIキーを設定してください
        api_config = self._config.get("api", {})
        self.api_base_url = api_config.get("base_url", "https://openrouter.ai/api/v1")
        
        # HTTPクライアントのbase_urlを設定（末尾の/api/v1を削除）
        # OH MY OPENCODEは独自のエンドポイントを使用するため、base_urlはドメインのみ
        base_url_for_client = self.api_base_url.rstrip("/api/v1").rstrip("/api").rstrip("/v1")
        if not base_url_for_client:
            base_url_for_client = "https://openrouter.ai"
        
        # 環境変数からAPIキーを取得（優先順位: OpenRouter > OpenAI > Anthropic > OH_MY_OPENCODE_API_KEY）
        self.api_key = (
            os.getenv("OPENROUTER_API_KEY") or
            os.getenv("OPENAI_API_KEY") or
            os.getenv("ANTHROPIC_API_KEY") or
            os.getenv("OH_MY_OPENCODE_API_KEY") or
            api_config.get("api_key", "")
        )
        
        # 設定ファイルから直接指定されている場合
        config_api_key = api_config.get("api_key", "")
        if config_api_key and config_api_key.startswith("${") and config_api_key.endswith("}"):
            # 環境変数参照形式（例: ${OPENROUTER_API_KEY}）
            env_var_name = config_api_key[2:-1]
            self.api_key = os.getenv(env_var_name) or self.api_key
        
        self.api_timeout = api_config.get("timeout", 300.0)
        
        # 実行設定
        exec_config = self._config.get("execution", {})
        self.default_mode = ExecutionMode(exec_config.get("default_mode", "normal"))
        self.max_iterations = exec_config.get("max_iterations", 10)
        self.max_execution_time = exec_config.get("max_execution_time", 3600)
        
        # Ultra Workモード設定
        ultra_config = self._config.get("ultra_work", {})
        self.ultra_work_enabled = ultra_config.get("enabled", False)
        self.ultra_work_allowed_types = ultra_config.get("allowed_task_types", [])
        self.ultra_work_require_approval = ultra_config.get("require_approval", True)
        self.ultra_work_cost_limit = ultra_config.get("cost_limit_per_task", 100.0)
        # Ultra Work途中降格設定
        self.ultra_work_downgrade_enabled = ultra_config.get("downgrade_enabled", True)
        self.ultra_work_downgrade_cost_threshold = ultra_config.get("downgrade_cost_threshold", 0.7)  # 70%で降格
        self.ultra_work_downgrade_time_threshold = ultra_config.get("downgrade_time_threshold", 0.8)  # 80%で降格
        self.ultra_work_downgrade_iteration_threshold = ultra_config.get("downgrade_iteration_threshold", 0.75)  # 75%で降格
        
        # コスト管理設定
        cost_config = self._config.get("cost_management", {})
        self.cost_management_enabled = cost_config.get("enabled", True)
        self.daily_cost_limit = cost_config.get("daily_limit", 100.0)
        self.monthly_cost_limit = cost_config.get("monthly_limit", 2000.0)
        self.cost_warning_threshold = cost_config.get("warning_threshold", 0.8)
        self.cost_auto_stop = cost_config.get("auto_stop", True)
        
        # Kill Switch設定
        kill_config = self._config.get("kill_switch", {})
        self.kill_switch_enabled = kill_config.get("enabled", True)
        self.kill_switch_max_time = kill_config.get("max_execution_time", 3600)
        self.kill_switch_max_iterations = kill_config.get("max_iterations", 20)
        self.kill_switch_detect_loop = kill_config.get("detect_infinite_loop", True)
        
        # Trinity統合設定
        trinity_config = self._config.get("trinity", {})
        self.trinity_enabled = trinity_config.get("enabled", True)
        self.trinity_remi = trinity_config.get("remi_integration", True)
        self.trinity_luna = trinity_config.get("luna_integration", True)
        self.trinity_mina = trinity_config.get("mina_integration", True)
        
        # LLMルーティング統合設定
        routing_config = self._config.get("llm_routing", {})
        self.llm_routing_enabled = routing_config.get("enabled", True) and LLM_ROUTING_AVAILABLE
        self.use_manaos_routing = routing_config.get("use_manaos_routing", True)
        self.fallback_to_local = routing_config.get("fallback_to_local", True)
        
        # HTTPクライアント
        # base_urlはドメインのみ（エンドポイントは相対パスで指定）
        self.base_url_for_client = self.api_base_url.rstrip("/api/v1").rstrip("/api").rstrip("/v1")
        if not self.base_url_for_client or self.base_url_for_client == self.api_base_url:
            # デフォルトはOpenRouter
            self.base_url_for_client = "https://openrouter.ai"
        
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url_for_client,
            timeout=self.api_timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            } if self.api_key else {}
        )
        
        # LLMルーター（オプション）
        self.llm_router = None
        if self.llm_routing_enabled and LLM_ROUTING_AVAILABLE:
            try:
                self.llm_router = LLMRouter()  # type: ignore[operator]
                self.logger.info("LLMルーターを初期化しました")
            except Exception as e:
                self.logger.warning(f"LLMルーターの初期化に失敗: {e}")
        
        # Trinity統合ブリッジ（オプション）
        self.trinity_bridge = None
        if self.trinity_enabled and TRINITY_BRIDGE_AVAILABLE:
            try:
                self.trinity_bridge = TrinityBridge()  # type: ignore[operator]
                self.logger.info("Trinity統合ブリッジを初期化しました")
            except Exception as e:
                self.logger.warning(f"Trinity統合ブリッジの初期化に失敗: {e}")
        
        # コスト管理（オプション）
        self.cost_manager = None
        if self.cost_management_enabled:
            # OH MY OPENCODE専用コスト管理を優先
            if OH_MY_OPENCODE_COST_MANAGER_AVAILABLE:
                try:
                    self.cost_manager = OHMyOpenCodeCostManager(  # type: ignore[operator]
                        daily_limit=self.daily_cost_limit,
                        monthly_limit=self.monthly_cost_limit,
                        warning_threshold=self.cost_warning_threshold,
                        auto_stop=self.cost_auto_stop
                    )
                    self.logger.info("OH MY OPENCODEコスト管理を初期化しました")
                except Exception as e:
                    self.logger.warning(f"OH MY OPENCODEコスト管理の初期化に失敗: {e}")
            # フォールバック: ManaOS標準コスト管理
            elif COST_MANAGEMENT_AVAILABLE:
                try:
                    self.cost_manager = CostOptimization()  # type: ignore[operator]
                    self.logger.info("ManaOSコスト管理を初期化しました")
                except Exception as e:
                    self.logger.warning(f"ManaOSコスト管理の初期化に失敗: {e}")
        
        # 実行履歴
        self.execution_history: List[OHMyOpenCodeResult] = []
        
        # Kill Switch状態
        self._kill_switch_active = False
        self._active_tasks: Dict[str, OHMyOpenCodeTask] = {}
        
        # Kill Switch（オプション）
        self.kill_switch = None
        if self.kill_switch_enabled and KILL_SWITCH_AVAILABLE:
            try:
                self.kill_switch = OHMyOpenCodeKillSwitch(  # type: ignore[operator]
                    max_execution_time=self.kill_switch_max_time,
                    max_iterations=self.kill_switch_max_iterations,
                    detect_infinite_loop=self.kill_switch_detect_loop,
                    auto_kill_on_error=False  # デフォルトはFalse
                )
                self.logger.info("Kill Switchを初期化しました")
            except Exception as e:
                self.logger.warning(f"Kill Switchの初期化に失敗: {e}")
        
        # 最適化システム（オプション）
        self.optimizer = None
        if OPTIMIZER_AVAILABLE:
            try:
                self.optimizer = OHMyOpenCodeOptimizer()  # type: ignore[operator]
                self.logger.info("最適化システムを初期化しました")
            except Exception as e:
                self.logger.warning(f"最適化システムの初期化に失敗: {e}")
        
        # コスト見える化システム（オプション）
        self.cost_visibility = None
        if COST_VISIBILITY_AVAILABLE:
            try:
                self.cost_visibility = OHMyOpenCodeCostVisibility(  # type: ignore[operator]
                    cost_manager=self.cost_manager,
                    optimizer=self.optimizer
                )
                self.logger.info("コスト見える化システムを初期化しました")
            except Exception as e:
                self.logger.warning(f"コスト見える化システムの初期化に失敗: {e}")
        
        # 成功パターンテンプレート（オプション）
        self.templates = None
        if TEMPLATES_AVAILABLE:
            try:
                self.templates = OHMyOpenCodeTemplates()  # type: ignore[operator]
                self.logger.info("成功パターンテンプレートを初期化しました")
            except Exception as e:
                self.logger.warning(f"成功パターンテンプレートの初期化に失敗: {e}")
        
        # 観測設計システム（オプション）
        self.observability = None
        if OBSERVABILITY_AVAILABLE:
            try:
                self.observability = OHMyOpenCodeObservability()  # type: ignore[operator]
                self.logger.info("観測設計システムを初期化しました")
            except Exception as e:
                self.logger.warning(f"観測設計システムの初期化に失敗: {e}")
        
        # 本番運用ルールセット（Policy）
        self.policy = None
        if POLICY_AVAILABLE:
            try:
                self.policy = OHMyOpenCodePolicy()  # type: ignore[operator]
                self.logger.info("Policyを初期化しました")
            except Exception as e:
                self.logger.warning(f"Policyの初期化に失敗: {e}")
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        # APIキーのチェック
        if not self.api_key:
            self.logger.warning("OH MY OPENCODE APIキーが設定されていません")
            return False
        
        # API接続テスト
        try:
            # ここでAPI接続テストを実装
            # 現在はスキップ
            return True
        except Exception as e:
            self.logger.error(f"API接続テストに失敗: {e}")
            return False
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        # APIキーのチェック
        if not self.api_key:
            return False
        
        # HTTPクライアントのチェック
        if not self.http_client:
            return False
        
        return True
    
    def _can_use_ultra_work(self, task_type: TaskType) -> bool:
        """
        Ultra Workモードを使用できるかチェック
        
        Args:
            task_type: タスクタイプ
        
        Returns:
            使用可能かどうか
        """
        if not self.ultra_work_enabled:
            return False
        
        # 許可されたタスクタイプかチェック
        if task_type.value in self.ultra_work_allowed_types:
            # 承認が必要な場合は承認プロセスを実行
            if self.ultra_work_require_approval:
                return self._request_ultra_work_approval(task_type)
            return True
        
        # 許可されていないタスクタイプの場合、承認が必要
        if self.ultra_work_require_approval:
            return self._request_ultra_work_approval(task_type)
        
        return False
    
    def _request_ultra_work_approval(self, task_type: TaskType) -> bool:
        """
        Ultra Workモードの承認をリクエスト
        Slack通知を送信し、承認待ちキューに追加
        
        Args:
            task_type: タスクタイプ
        
        Returns:
            承認されたかどうか（現在は常にFalse、承認は別のエンドポイントで処理）
        """
        import uuid
        
        # 承認リクエストIDを生成
        approval_request_id = str(uuid.uuid4())
        
        # 承認待ちキューに追加（メモリベース）
        if not hasattr(self, '_approval_queue'):
            self._approval_queue = {}
        
        self._approval_queue[approval_request_id] = {
            "task_type": task_type.value,
            "requested_at": datetime.now().isoformat(),
            "status": "pending",
            "approved": False
        }
        
        # Slack通知を送信
        try:
            # slack_integrationモジュールを使用
            try:
                from slack_integration import send_to_slack  # type: ignore[attr-defined]
                slack_available = True
            except ImportError:
                # notification_systemやnotification_hub_enhancedも試す
                try:
                    from notification_system import NotificationSystem
                    notification_system = NotificationSystem()
                    slack_available = True
                except ImportError:
                    try:
                        from notification_hub_enhanced import NotificationHubEnhanced
                        notification_hub = NotificationHubEnhanced()
                        slack_available = True
                    except ImportError:
                        slack_available = False
            
            if slack_available:
                # 承認メッセージを作成
                approval_message = f"""🚨 *Ultra Workモード承認リクエスト*

*タスクタイプ*: {task_type.value}
*リクエストID*: `{approval_request_id}`
*リクエスト時刻*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

このタスクをUltra Workモードで実行するには承認が必要です。

承認する場合は、以下のエンドポイントにPOSTリクエストを送信してください:
```
POST /api/oh_my_opencode/approve
Body: {{"approval_request_id": "{approval_request_id}"}}
```

または、Slackで以下のコマンドを実行:
`/approve_ultra_work {approval_request_id}`
"""
                
                # Slack通知を送信
                try:
                    send_to_slack(approval_message, channel="#manaos-notifications")  # type: ignore[possibly-unbound]
                except Exception:
                    try:
                        notification_system.send_slack(approval_message)  # type: ignore[possibly-unbound]
                    except Exception:
                        try:
                            notification_hub.notify(approval_message, priority="important")  # type: ignore[possibly-unbound]
                        except Exception:
                            pass
                
                self.logger.info(f"Ultra Work承認リクエストを送信しました: {approval_request_id}")
            else:
                self.logger.warning("Slack統合が利用できません。ログのみに記録します。")
        except Exception as e:
            self.logger.error(f"Slack通知の送信エラー: {e}")
        
        # 承認待ちのためFalseを返す
        # 承認は別のエンドポイント（/api/oh_my_opencode/approve）で処理される
        self.logger.warning(
            f"Ultra Workモードの承認が必要です（タスクタイプ: {task_type.value}, リクエストID: {approval_request_id}）"
        )
        return False
    
    def _check_ultra_work_downgrade(
        self,
        task_id: str,
        current_cost: float,
        execution_time: float,
        iterations: int,
        max_cost: float,
        max_time: float,
        max_iterations: int
    ) -> bool:
        """
        Ultra Workモードの途中降格チェック
        
        Args:
            task_id: タスクID
            current_cost: 現在のコスト
            execution_time: 実行時間
            iterations: 反復回数
            max_cost: 最大コスト
            max_time: 最大実行時間
            max_iterations: 最大反復回数
        
        Returns:
            降格が必要かどうか
        """
        if not self.ultra_work_downgrade_enabled:
            return False
        
        # コスト閾値チェック
        if max_cost > 0 and current_cost >= max_cost * self.ultra_work_downgrade_cost_threshold:
            self.logger.warning(
                f"Ultra Workモードを降格: {task_id} "
                f"(コスト: ${current_cost:.2f} / ${max_cost:.2f}, "
                f"閾値: {self.ultra_work_downgrade_cost_threshold*100:.0f}%)"
            )
            return True
        
        # 実行時間閾値チェック
        if max_time > 0 and execution_time >= max_time * self.ultra_work_downgrade_time_threshold:
            self.logger.warning(
                f"Ultra Workモードを降格: {task_id} "
                f"(実行時間: {execution_time:.1f}秒 / {max_time:.1f}秒, "
                f"閾値: {self.ultra_work_downgrade_time_threshold*100:.0f}%)"
            )
            return True
        
        # 反復回数閾値チェック
        if max_iterations > 0 and iterations >= max_iterations * self.ultra_work_downgrade_iteration_threshold:
            self.logger.warning(
                f"Ultra Workモードを降格: {task_id} "
                f"(反復回数: {iterations} / {max_iterations}, "
                f"閾値: {self.ultra_work_downgrade_iteration_threshold*100:.0f}%)"
            )
            return True
        
        return False
    
    def _check_cost_limit(self, estimated_cost: float = 0.0) -> bool:
        """
        コスト上限をチェック
        
        Args:
            estimated_cost: 推定コスト
        
        Returns:
            実行可能かどうか
        
        Raises:
            CostLimitExceededError: コスト上限超過
        """
        if not self.cost_management_enabled:
            return True
        
        # コスト管理が利用可能な場合はチェック
        if self.cost_manager:
            # OH MY OPENCODE専用コスト管理の場合
            if hasattr(self.cost_manager, 'check_limit'):
                can_execute, warning = self.cost_manager.check_limit(estimated_cost)  # type: ignore
                if not can_execute:
                    raise CostLimitExceededError(warning or "コスト上限に達しました")
                if warning:
                    self.logger.warning(warning)
                return True
        
        # 簡易チェック（日次・月次上限）
        # デフォルトでは許可（詳細チェックはコスト管理システムに委譲）
        return True
    
    async def execute_task(
        self,
        task_description: str,
        mode: Optional[ExecutionMode] = None,
        task_type: Optional[TaskType] = None,
        use_trinity: Optional[bool] = None
    ) -> OHMyOpenCodeResult:
        """
        タスクを実行
        
        Args:
            task_description: タスクの説明
            mode: 実行モード（Noneの場合はデフォルト）
            task_type: タスクタイプ（Noneの場合はGENERAL）
            use_trinity: Trinity統合を使用するか（Noneの場合は設定値）
        
        Returns:
            実行結果
        
        Raises:
            CostLimitExceededError: コスト上限超過
            UltraWorkNotAllowedError: Ultra Workモード使用不可
        """
        # パラメータの設定
        if mode is None:
            mode = self.default_mode
        if task_type is None:
            task_type = TaskType.GENERAL
        if use_trinity is None:
            use_trinity = self.trinity_enabled
        
        # タスクID生成
        task_id = f"oh_my_opencode_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        # Policyチェック（本番運用ルール）
        if self.policy:
            can_use, reason = self.policy.can_use_mode(mode.value)
            if not can_use:
                return OHMyOpenCodeResult(
                    task_id=task_id,
                    status="failed",
                    result=None,
                    error=f"Policy違反: {reason}",
                    cost=0.0,
                    execution_time=0.0
                )
            
            # 承認が必要な場合はチェック（タスクにapproved属性がない場合は承認不要とみなす）
            if self.policy.requires_approval(mode.value):
                # 承認チェックはタスク実行時に確認（現時点では警告のみ）
                self.logger.warning(f"Policy: {mode.value}モードには承認が必要です")
        
        # プロンプトをテンプレートで強化（成功パターン）
        enhanced_description = task_description
        if self.templates:
            try:
                enhanced_description = self.templates.enhance_prompt(
                    task_type,  # type: ignore
                    task_description,
                    use_requirement_analysis=True,
                    use_implementation_template=True,
                    use_verification_template=True
                )
                self.logger.debug(f"プロンプトをテンプレートで強化しました: {task_type.value}")
            except Exception as e:
                self.logger.warning(f"プロンプト強化エラー: {e}")
                enhanced_description = task_description
        
        # タスク作成
        task = OHMyOpenCodeTask(
            task_id=task_id,
            description=enhanced_description,  # 強化されたプロンプトを使用
            mode=mode,
            task_type=task_type,
            max_iterations=self.max_iterations if mode == ExecutionMode.NORMAL else self.kill_switch_max_iterations,
            max_execution_time=self.max_execution_time if mode == ExecutionMode.NORMAL else self.kill_switch_max_time
        )
        
        # コスト見積り（見える化）
        cost_estimate = None
        if self.cost_visibility:
            try:
                cost_estimate = self.cost_visibility.estimate_cost(
                    task_type.value,
                    mode.value,
                    task_description
                )
                self.logger.info(
                    f"コスト見積り: ${cost_estimate.estimated_cost_min:.2f} - "
                    f"${cost_estimate.estimated_cost_max:.2f} "
                    f"(平均: ${cost_estimate.estimated_cost_avg:.2f}, "
                    f"信頼度: {cost_estimate.confidence:.2f})"
                )
            except Exception as e:
                self.logger.warning(f"コスト見積りエラー: {e}")
        
        # コストチェック
        if not self._check_cost_limit(cost_estimate.estimated_cost_avg if cost_estimate else 0.0):
            raise CostLimitExceededError("コスト上限に達しました")
        
        # Ultra Workモードの制限チェック
        if mode == ExecutionMode.ULTRA_WORK:
            if not self._can_use_ultra_work(task_type):
                raise UltraWorkNotAllowedError(
                    f"Ultra Workモードは仕様策定・難解バグ・初期アーキ設計のみ使用可能です（現在のタスクタイプ: {task_type.value}）"
                )
        
        # アクティブタスクに追加
        self._active_tasks[task_id] = task
        
        # Kill Switchにタスクを登録（停止時情報用）
        if self.kill_switch:
            self.kill_switch.register_task(
                task_id,
                max_execution_time=task.max_execution_time,
                max_iterations=task.max_iterations,
                task_description=task_description,
                execution_context={
                    "mode": mode.value,
                    "task_type": task_type.value,
                    "trinity_enabled": use_trinity
                }
            )
        
        # 実行開始時刻
        start_time = datetime.now()
        
        # Kill Switchチェック
        if self.kill_switch and self.kill_switch.is_task_killed(task_id):
            return OHMyOpenCodeResult(
                task_id=task_id,
                status="killed",
                execution_time=0.0,
                error="タスクは既に停止されています"
            )
        
        try:
            # Trinity統合（オプション）
            trinity_context = {}
            if use_trinity:
                trinity_context = await self._prepare_trinity_context(task_description, task_type)
            
            # OH MY OPENCODE実行（Kill Switch監視付き・Ultra Work降格チェック付き）
            result = await self._execute_oh_my_opencode_with_monitoring(
                task, trinity_context, task_id, mode, task_type
            )
            
            # 実行時間計算
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Ultra Work途中降格チェック（弱体化の連鎖防止）
            if mode == ExecutionMode.ULTRA_WORK and self.ultra_work_downgrade_enabled:
                # 降格回数をチェック（最大1回/タスク）
                if self.kill_switch and task_id in self.kill_switch.active_tasks:
                    monitor = self.kill_switch.active_tasks[task_id]
                    if monitor.downgrade_count >= 1:
                        # 既に降格済みの場合は降格しない
                        self.logger.warning(f"降格回数上限に達しています: {task_id} (降格回数: {monitor.downgrade_count})")
                    else:
                        result_cost = result.get("cost", 0.0) if isinstance(result, dict) else 0.0
                        result_iterations = result.get("iterations", 0) if isinstance(result, dict) else 0
                        
                        if self._check_ultra_work_downgrade(
                            task_id=task_id,
                            current_cost=result_cost,
                            execution_time=execution_time,
                            iterations=result_iterations,
                            max_cost=self.ultra_work_cost_limit,
                            max_time=task.max_execution_time,  # type: ignore
                            max_iterations=task.max_iterations  # type: ignore
                        ):
                            # Ultra WorkからNORMALに降格（再実行ではなく、結果に降格フラグを付ける）
                            if isinstance(result, dict):
                                result["mode_downgraded"] = True
                                result["original_mode"] = "ultra_work"
                                result["downgraded_to"] = "normal"
                                
                                # 降格回数をインクリメント
                                monitor.downgrade_count += 1
                                
                                # 降格後は目標を縮める（スコープ縮小）
                                result["scope_reduced"] = True
                                result["reduced_scope"] = "タスクを小さなステップに分割することを推奨します"
                                
                                self.logger.info(f"Ultra WorkモードをNORMALに降格しました: {task_id} (降格回数: {monitor.downgrade_count})")
            
            # Kill Switchチェック（実行中に停止された場合）
            if self.kill_switch and self.kill_switch.is_task_killed(task_id):
                kill_status = self.kill_switch.get_task_status(task_id)
                resume_context = self.kill_switch.get_resume_context(task_id)
                
                # 停止時情報を結果に含める
                error_message = f"Kill Switchにより停止されました（理由: {kill_status.reason if kill_status else 'unknown'}）"
                if kill_status and kill_status.last_error:
                    error_message += f"\n最後のエラー: {kill_status.last_error[:200]}"
                if kill_status and kill_status.resume_context_id:
                    error_message += f"\n再開ID: {kill_status.resume_context_id}"
                
                result_dict = {
                    "status": "killed",
                    "kill_reason": kill_status.reason if kill_status else None,
                    "resume_context_id": kill_status.resume_context_id if kill_status else None,
                    "last_prompt": kill_status.last_prompt if kill_status else None,
                    "last_error": kill_status.last_error if kill_status else None,
                    "resume_context": resume_context
                }
                
                return OHMyOpenCodeResult(
                    task_id=task_id,
                    status="killed",
                    execution_time=execution_time,
                    iterations=kill_status.iterations if kill_status else 0,
                    error=error_message,
                    result=result_dict
                )
            
            # 結果作成
            oh_result = OHMyOpenCodeResult(
                task_id=task_id,
                status="success",
                result=result,
                cost=result.get("cost", 0.0) if isinstance(result, dict) else 0.0,
                execution_time=execution_time,
                iterations=result.get("iterations", 0) if isinstance(result, dict) else 0
            )
            
            # 実行履歴に追加
            self.execution_history.append(oh_result)
            
            # コスト記録
            if self.cost_manager:
                if hasattr(self.cost_manager, 'record_cost'):
                    self.cost_manager.record_cost(  # type: ignore
                        task_id=task_id,
                        cost=oh_result.cost,
                        task_type=task_type.value,
                        mode=mode.value
                    )
            
            # コスト内訳分析（見える化）
            if self.cost_visibility and isinstance(result, dict):
                try:
                    execution_data = {
                        "iterations": oh_result.iterations,
                        "search_count": result.get("search_count", 0),
                        "model": result.get("model", "unknown"),
                        "context_length": result.get("context_length", 0)
                    }
                    
                    cost_breakdown = self.cost_visibility.analyze_cost_breakdown(
                        task_id,
                        oh_result.cost,
                        execution_data
                    )
                    
                    # 原因分類
                    causes = self.cost_visibility.classify_cost_cause(
                        cost_breakdown,
                        execution_data
                    )
                    
                    self.logger.info(
                        f"コスト内訳: 検索={cost_breakdown.breakdown_percentages.get('search', 0):.1f}%, "
                        f"ループ={cost_breakdown.breakdown_percentages.get('loop', 0):.1f}%, "
                        f"モデル={cost_breakdown.breakdown_percentages.get('model', 0):.1f}%, "
                        f"コンテキスト={cost_breakdown.breakdown_percentages.get('context', 0):.1f}%"
                    )
                    
                    if causes:
                        self.logger.info(f"高コストの原因: {', '.join(causes)}")
                    
                    # 結果にコスト内訳を追加
                    if isinstance(oh_result.result, dict):
                        oh_result.result["cost_breakdown"] = asdict(cost_breakdown)
                        oh_result.result["cost_causes"] = causes
                
                except Exception as e:
                    self.logger.warning(f"コスト内訳分析エラー: {e}")
            
            # Kill Switch: タスク完了
            if self.kill_switch:
                self.kill_switch.complete_task(task_id)
            
            # 最適化システム: 実行履歴を記録
            if self.optimizer:
                self.optimizer.record_execution(
                    task_id=task_id,
                    task_type=task_type.value,
                    mode=mode.value,
                    status=oh_result.status,
                    cost=oh_result.cost,
                    execution_time=oh_result.execution_time,
                    iterations=oh_result.iterations,
                    error=oh_result.error
                )
            
            # 観測設計システム: メトリクスを記録
            if self.observability:
                kill_reason = None
                cost_breakdown = None
                cost_causes = None
                
                if isinstance(oh_result.result, dict):
                    kill_reason = oh_result.result.get("kill_reason")
                    cost_breakdown = oh_result.result.get("cost_breakdown")
                    cost_causes = oh_result.result.get("cost_causes")
                
                self.observability.record_execution(
                    task_id=task_id,
                    task_type=task_type.value,
                    mode=mode.value,
                    status=oh_result.status,
                    execution_time=oh_result.execution_time,
                    cost=oh_result.cost,
                    iterations=oh_result.iterations,
                    errors=1 if oh_result.error else 0,
                    kill_reason=kill_reason,
                    cost_breakdown=cost_breakdown,
                    cost_causes=cost_causes
                )
            
            return oh_result
            
        except CostLimitExceededError:
            execution_time = (datetime.now() - start_time).total_seconds()
            return OHMyOpenCodeResult(
                task_id=task_id,
                status="cost_limit_exceeded",
                execution_time=execution_time,
                error="コスト上限に達しました"
            )
        
        except UltraWorkNotAllowedError as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return OHMyOpenCodeResult(
                task_id=task_id,
                status="failed",
                execution_time=execution_time,
                error=str(e)
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error = self.error_handler.handle_exception(
                e,
                context={"task_id": task_id, "task_description": task_description[:100]},
                user_message="タスクの実行に失敗しました"
            )
            
            return OHMyOpenCodeResult(
                task_id=task_id,
                status="failed",
                execution_time=execution_time,
                error=error.message
            )
        
        finally:
            # Kill Switch: タスククリーンアップ
            if self.kill_switch:
                self.kill_switch.cleanup_task(task_id)
            
            # アクティブタスクから削除
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
    
    async def _prepare_trinity_context(
        self,
        task_description: str,
        task_type: TaskType
    ) -> Dict[str, Any]:
        """
        Trinity統合のコンテキストを準備
        
        Args:
            task_description: タスクの説明
            task_type: タスクタイプ
        
        Returns:
            Trinityコンテキスト
        """
        context = {
            "remi": {},
            "luna": {},
            "mina": {}
        }
        
        # Trinity統合ブリッジが利用可能な場合
        if self.trinity_bridge:
            # Remi統合（判断）
            if self.trinity_remi:
                try:
                    remi_analysis = await self.trinity_bridge.remi_analyze(
                        task_description,
                        task_type.value
                    )
                    context["remi"] = asdict(remi_analysis)
                    self.logger.info(f"Remi分析完了: 優先度={remi_analysis.task_priority}, 推奨モード={remi_analysis.recommended_mode}")
                except Exception as e:
                    error = self.error_handler.handle_exception(
                        e,
                        context={"task_description": task_description[:100]},
                        user_message="Remi分析に失敗しました"
                    )
                    self.logger.warning(f"Remi分析エラー: {error.message}")
                    context["remi"] = {}
            
            # Luna統合（監視）
            if self.trinity_luna:
                try:
                    # Remi分析結果から推定時間を取得
                    estimated_time = context.get("remi", {}).get("estimated_time", 300)
                    luna_monitoring = await self.trinity_bridge.luna_monitor(
                        task_description,
                        task_id="",  # タスクIDは後で設定
                        estimated_time=estimated_time
                    )
                    context["luna"] = asdict(luna_monitoring)
                    self.logger.info(f"Luna監視設定完了: チェック間隔={luna_monitoring.check_interval}秒")
                except Exception as e:
                    error = self.error_handler.handle_exception(
                        e,
                        context={"task_description": task_description[:100]},
                        user_message="Luna監視設定に失敗しました"
                    )
                    self.logger.warning(f"Luna監視設定エラー: {error.message}")
                    context["luna"] = {}
            
            # Mina統合（記憶）
            if self.trinity_mina:
                try:
                    mina_memory = await self.trinity_bridge.mina_search(
                        task_description,
                        task_type.value
                    )
                    context["mina"] = asdict(mina_memory)
                    similar_count = len(mina_memory.similar_tasks)
                    pattern_count = len(mina_memory.learned_patterns)
                    self.logger.info(f"Mina検索完了: 類似タスク={similar_count}件, 学習パターン={pattern_count}件")
                except Exception as e:
                    error = self.error_handler.handle_exception(
                        e,
                        context={"task_description": task_description[:100]},
                        user_message="Mina検索に失敗しました"
                    )
                    self.logger.warning(f"Mina検索エラー: {error.message}")
                    context["mina"] = {}
        else:
            # Trinity統合ブリッジが利用不可な場合のフォールバック
            if self.trinity_remi:
                context["remi"] = {
                    "task_priority": "medium",
                    "estimated_time": 300,
                    "complexity": "medium",
                    "recommended_mode": "normal",
                    "risk_assessment": "medium",
                    "suggestions": [],
                    "confidence": 0.5
                }
            
            if self.trinity_luna:
                context["luna"] = {
                    "monitoring_enabled": True,
                    "check_interval": 60,
                    "failure_threshold": 3,
                    "alert_on_error": True,
                    "metrics_to_track": ["execution_time", "cost", "errors"]
                }
            
            if self.trinity_mina:
                context["mina"] = {
                    "similar_tasks": [],
                    "learned_patterns": [],
                    "relevant_knowledge": [],
                    "success_rate": None
                }
        
        return context
    
    async def _execute_oh_my_opencode_with_monitoring(
        self,
        task: OHMyOpenCodeTask,
        trinity_context: Dict[str, Any],
        task_id: str,
        mode: ExecutionMode,
        task_type: TaskType
    ) -> Dict[str, Any]:
        """
        OH MY OPENCODEを実行（Kill Switch監視付き・Ultra Work降格チェック付き）
        
        Args:
            task: タスク
            trinity_context: Trinityコンテキスト
            task_id: タスクID
            mode: 実行モード
            task_type: タスクタイプ
        
        Returns:
            実行結果
        """
        # Kill Switch監視付きで実行
        return await self._execute_oh_my_opencode(task, trinity_context, task_id)
    
    async def _execute_oh_my_opencode(
        self,
        task: OHMyOpenCodeTask,
        trinity_context: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        OH MY OPENCODEを実行
        
        Args:
            task: タスク
            trinity_context: Trinityコンテキスト
            task_id: タスクID（Kill Switch監視用）
        
        Returns:
            実行結果
        """
        # モデル選択（LLMルーティング統合）
        model_config = await self._select_model(task)
        
        # APIリクエスト準備
        request_data = {
            "task_description": task.description,
            "mode": task.mode.value,
            "task_type": task.task_type.value,
            "max_iterations": task.max_iterations,
            "max_execution_time": task.max_execution_time,
            "model_config": model_config,
            "trinity_context": trinity_context
        }
        
        # API呼び出し（Kill Switch監視付き）
        try:
            # Kill Switchチェック（実行前）
            if task_id and self.kill_switch:
                if not self.kill_switch.update_task(
                    task_id,
                    iteration=0,
                    last_prompt=task.description[:500]  # 直前のプロンプト（要点）
                ):
                    raise Exception("Kill Switchにより実行が停止されました")
            
            # OH MY OPENCODEの実際のエンドポイントを使用
            # OpenRouterの標準エンドポイントを使用（OH MY OPENCODEはLLMプロバイダのAPIキーを使用）
            response = await self.http_client.post(
                "/api/v1/chat/completions",
                json=request_data
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Kill Switchチェック（実行後）
            if task_id and self.kill_switch:
                iterations = result.get("iterations", 0) if isinstance(result, dict) else 0
                cost = result.get("cost", 0.0) if isinstance(result, dict) else 0.0
                error = result.get("error") if isinstance(result, dict) else None
                
                # 実行状態を記録
                execution_state = {
                    "iterations": iterations,
                    "cost": cost,
                    "status": result.get("status", "unknown") if isinstance(result, dict) else "unknown"
                }
                
                if not self.kill_switch.update_task(
                    task_id,
                    iteration=iterations,
                    error=error,
                    cost=cost,
                    last_prompt=task.description[:500],
                    execution_state=execution_state
                ):
                    raise Exception("Kill Switchにより実行が停止されました")
            
            return result
        
        except httpx.HTTPStatusError as e:
            error = self.error_handler.handle_httpx_error(
                e,
                url=f"{self.base_url_for_client}/api/v1/chat/completions",
                method="POST",
                context={"task_id": task.task_id}
            )
            raise Exception(error.message)
        
        except httpx.RequestError as e:
            error = self.error_handler.handle_httpx_error(
                e,
                url=f"{self.base_url_for_client}/api/v1/chat/completions",
                method="POST",
                context={"task_id": task.task_id}
            )
            raise Exception(error.message)
    
    async def _select_model(self, task: OHMyOpenCodeTask) -> Dict[str, Any]:
        """
        モデルを選択（LLMルーティング統合）
        
        Args:
            task: タスク
        
        Returns:
            モデル設定
        """
        if self.llm_routing_enabled and self.llm_router:
            # ManaOS LLMルーティングを使用
            try:
                # タスクタイプに応じたルーティング
                task_type_mapping = {
                    TaskType.SPECIFICATION: "reasoning",
                    TaskType.COMPLEX_BUG: "reasoning",
                    TaskType.ARCHITECTURE_DESIGN: "reasoning",
                    TaskType.CODE_GENERATION: "automation",
                    TaskType.CODE_REVIEW: "reasoning",
                    TaskType.REFACTORING: "automation",
                    TaskType.GENERAL: "automation"
                }
                
                routing_task_type = task_type_mapping.get(task.task_type, "automation")
                
                # LLMルーターでモデル選択
                routing_result = self.llm_router.route(
                    task_type=routing_task_type,
                    prompt=task.description
                )
                
                return {
                    "model": routing_result.get("model", "default"),
                    "provider": routing_result.get("provider", "openai"),
                    "use_manaos_routing": True
                }
            
            except Exception as e:
                self.logger.warning(f"LLMルーティングに失敗: {e}")
                # フォールバック
                if self.fallback_to_local:
                    return {
                        "model": "local_default",
                        "provider": "local",
                        "use_manaos_routing": False
                    }
        
        # デフォルト設定
        return {
            "model": "gpt-4",
            "provider": "openai",
            "use_manaos_routing": False
        }
    
    def kill_task(self, task_id: str) -> bool:
        """
        タスクを強制停止（Kill Switch）
        
        Args:
            task_id: タスクID
        
        Returns:
            停止成功かどうか
        """
        # Kill Switchを使用
        if self.kill_switch:
            success = self.kill_switch.kill_task(task_id, KillSwitchReason.MANUAL)  # type: ignore[union-attr]
            if success:
                self._kill_switch_active = True
                self.logger.warning(f"タスクを強制停止しました: {task_id}")
                return True
        
        # フォールバック: アクティブタスクから削除
        if task_id in self._active_tasks:
            self._kill_switch_active = True
            del self._active_tasks[task_id]
            self.logger.warning(f"タスクを強制停止しました: {task_id}")
            return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        状態を取得
        
        Returns:
            状態情報
        """
        status = {
            "name": self.name,
            "available": self.is_available(),
            "initialized": self._initialized,
            "active_tasks": len(self._active_tasks),
            "execution_history_count": len(self.execution_history),
            "kill_switch_active": self._kill_switch_active,
            "trinity_enabled": self.trinity_enabled,
            "llm_routing_enabled": self.llm_routing_enabled,
            "cost_management_enabled": self.cost_management_enabled
        }
        
        # 最適化システムの統計情報を追加
        if self.optimizer:
            optimizer_stats = self.optimizer.get_statistics()
            status["optimizer"] = optimizer_stats
        
        # 観測設計システムの統計情報を追加
        if self.observability:
            system_metrics = self.observability.get_system_metrics()
            status["observability"] = asdict(system_metrics)
        
        return status
    
    def get_dashboard_data(self) -> Optional[Dict[str, Any]]:
        """
        ダッシュボードデータを取得
        
        Returns:
            ダッシュボードデータ（Noneの場合は観測設計システムが利用不可）
        """
        if not self.observability:
            return None
        
        try:
            return self.observability.get_dashboard_data()
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={},
                user_message="ダッシュボードデータの取得に失敗しました"
            )
            self.logger.warning(f"ダッシュボードデータ取得エラー: {error.message}")
            return None
    
    def get_optimization_recommendation(
        self,
        task_type: TaskType,
        task_description: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        最適化推奨事項を取得
        
        Args:
            task_type: タスクタイプ
            task_description: タスクの説明
        
        Returns:
            最適化推奨事項（Noneの場合は最適化システムが利用不可）
        """
        if not self.optimizer:
            return None
        
        try:
            recommendation = self.optimizer.get_optimization_recommendation(
                task_type.value,
                task_description
            )
            return asdict(recommendation)
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"task_type": task_type.value},
                user_message="最適化推奨事項の取得に失敗しました"
            )
            self.logger.warning(f"最適化推奨事項取得エラー: {error.message}")
            return None
    
    def get_cost_estimate(
        self,
        task_type: TaskType,
        mode: ExecutionMode,
        task_description: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        コスト見積りを取得
        
        Args:
            task_type: タスクタイプ
            mode: 実行モード
            task_description: タスクの説明
        
        Returns:
            コスト見積り（Noneの場合は見える化システムが利用不可）
        """
        if not self.cost_visibility:
            return None
        
        try:
            estimate = self.cost_visibility.estimate_cost(
                task_type.value,
                mode.value,
                task_description
            )
            return asdict(estimate)
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"task_type": task_type.value, "mode": mode.value},
                user_message="コスト見積りの取得に失敗しました"
            )
            self.logger.warning(f"コスト見積り取得エラー: {error.message}")
            return None
    
    def get_budget_meter(self) -> Optional[Dict[str, Any]]:
        """
        残予算メーターを取得
        
        Returns:
            残予算メーター（Noneの場合は見える化システムが利用不可）
        """
        if not self.cost_visibility:
            return None
        
        try:
            meter = self.cost_visibility.get_budget_meter()
            return asdict(meter)
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={},
                user_message="残予算メーターの取得に失敗しました"
            )
            self.logger.warning(f"残予算メーター取得エラー: {error.message}")
            return None
    
    def get_resume_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        再開用コンテキストを取得
        
        Args:
            task_id: タスクID
        
        Returns:
            再開用コンテキスト（Noneの場合はKill Switchが利用不可）
        """
        if not self.kill_switch:
            return None
        
        try:
            return self.kill_switch.get_resume_context(task_id)
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"task_id": task_id},
                user_message="再開用コンテキストの取得に失敗しました"
            )
            self.logger.warning(f"再開用コンテキスト取得エラー: {error.message}")
            return None


# 使用例
if __name__ == "__main__":
    async def main():
        integration = OHMyOpenCodeIntegration()
        
        if not integration.initialize():
            print("初期化に失敗しました")
            return
        
        # タスク実行
        result = await integration.execute_task(
            task_description="PythonでREST APIを作成してください",
            mode=ExecutionMode.NORMAL,
            task_type=TaskType.CODE_GENERATION
        )
        
        print(f"実行結果: {result.status}")
        print(f"コスト: ${result.cost:.2f}")
        print(f"実行時間: {result.execution_time:.2f}秒")
    
    asyncio.run(main())
