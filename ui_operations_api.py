#!/usr/bin/env python3
"""
🎮 UI操作機能API
実行ボタン・モード切替・コストメーター
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from manaos_integrations._paths import INTENT_ROUTER_PORT, TASK_PLANNER_PORT, TASK_QUEUE_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import INTENT_ROUTER_PORT, TASK_PLANNER_PORT, TASK_QUEUE_PORT  # type: ignore
    except Exception:  # pragma: no cover
        INTENT_ROUTER_PORT = int(os.getenv("INTENT_ROUTER_PORT", "5100"))
        TASK_PLANNER_PORT = int(os.getenv("TASK_PLANNER_PORT", "5101"))
        TASK_QUEUE_PORT = int(os.getenv("TASK_QUEUE_PORT", "5104"))

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_service_logger("ui-operations-api")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UIOperations")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("UIOperations")


class SystemMode(str, Enum):
    """システムモード"""
    WORK = "work"  # 仕事モード
    CREATIVE = "creative"  # 創作モード
    FUN = "fun"  # ムフフモード
    AUTO = "auto"  # 自動モード


@dataclass
class CostEntry:
    """コストエントリ"""
    timestamp: str
    service: str
    operation: str
    cost: float
    currency: str = "JPY"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class UIOperationsAPI:
    """UI操作機能API"""
    
    def __init__(
        self,
        intent_router_url: str = f"http://127.0.0.1:{INTENT_ROUTER_PORT}",
        task_planner_url: str = f"http://127.0.0.1:{TASK_PLANNER_PORT}",
        task_queue_url: str = f"http://127.0.0.1:{TASK_QUEUE_PORT}",
        cost_db_path: Optional[Path] = None,
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            intent_router_url: Intent Router API URL
            task_planner_url: Task Planner API URL
            task_queue_url: Task Queue API URL
            cost_db_path: コストデータベースパス
            config_path: 設定ファイルのパス
        """
        self.intent_router_url = intent_router_url
        self.task_planner_url = task_planner_url
        self.task_queue_url = task_queue_url
        
        self.config_path = config_path or Path(__file__).parent / "ui_operations_config.json"
        self.config = self._load_config()
        
        # コストデータベース
        self.cost_db_path = cost_db_path or Path(__file__).parent / "cost_tracking.db"
        self._init_cost_database()
        
        # 現在のモード
        self.current_mode = SystemMode(self.config.get("default_mode", "auto"))
        
        # コスト追跡
        self.cost_tracking_enabled = self.config.get("cost_tracking_enabled", True)
        
        logger.info(f"✅ UI操作機能API初期化完了 (モード: {self.current_mode.value})")
    
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
                        "default_mode": {"type": str, "default": "auto"},
                        "cost_tracking_enabled": {"type": bool, "default": True}
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
            "default_mode": "auto",
            "cost_tracking_enabled": True,
            "cost_limits": {
                "daily": 1000.0,
                "monthly": 30000.0
            },
            "service_costs": {
                "llm_api": 0.01,
                "image_generation": 0.05,
                "workflow_execution": 0.02
            }
        }
    
    def _init_cost_database(self):
        """コストデータベースを初期化"""
        import sqlite3
        
        conn = sqlite3.connect(self.cost_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                service TEXT NOT NULL,
                operation TEXT NOT NULL,
                cost REAL NOT NULL,
                currency TEXT DEFAULT 'JPY',
                metadata TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON cost_entries(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service ON cost_entries(service)")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ コストデータベース初期化完了: {self.cost_db_path}")
    
    def execute_task(self, input_text: str, mode: Optional[SystemMode] = None) -> Dict[str, Any]:
        """
        タスクを実行
        
        Args:
            input_text: 入力テキスト
            mode: システムモード（Noneの場合は現在のモードを使用）
        
        Returns:
            Dict: 実行結果
        """
        if mode is None:
            mode = self.current_mode
        
        # 意図を分類
        try:
            timeout = timeout_config.get("api_call", 10.0)
            response = httpx.post(
                f"{self.intent_router_url}/api/classify",
                json={"text": input_text},
                timeout=timeout
            )
            if response.status_code == 200:
                intent_result = response.json()
            else:
                intent_result = {"intent_type": "unknown", "confidence": 0.0}
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Intent Router", "url": self.intent_router_url},
                user_message="意図分類サービスへの接続に失敗しました"
            )
            logger.warning(f"Intent Router接続エラー: {error.message}")
            intent_result = {"intent_type": "unknown", "confidence": 0.0}
        
        # モードに応じたフィルタリング
        if not self._is_allowed_in_mode(intent_result.get("intent_type"), mode):
            return {
                "success": False,
                "error": f"この操作は{mode.value}モードでは許可されていません",
                "intent_type": intent_result.get("intent_type")
            }
        
        # 実行計画を作成
        try:
            timeout = timeout_config.get("llm_call", 30.0)
            response = httpx.post(
                f"{self.task_planner_url}/api/plan",
                json={"text": input_text},
                timeout=timeout
            )
            if response.status_code == 200:
                plan = response.json()
            else:
                error = error_handler.handle_exception(
                    Exception(f"Task Planner接続失敗: HTTP {response.status_code}"),
                    context={"service": "Task Planner", "url": self.task_planner_url},
                    user_message="実行計画の作成に失敗しました"
                )
                return {
                    "success": False,
                    "error": error.user_message or "実行計画の作成に失敗しました",
                    "intent_type": intent_result.get("intent_type")
                }
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Task Planner", "url": self.task_planner_url},
                user_message="実行計画の作成に失敗しました"
            )
            logger.error(f"Task Planner接続エラー: {error.message}")
            return {
                "success": False,
                "error": error.user_message or "実行計画の作成に失敗しました",
                "intent_type": intent_result.get("intent_type")
            }
        
        # タスクをキューに追加
        try:
            priority = self._get_priority_for_mode(mode)
            response = httpx.post(
                f"{self.task_queue_url}/api/enqueue",
                json={
                    "task_type": intent_result.get("intent_type", "unknown"),
                    "payload": {
                        "input": input_text,
                        "plan": plan,
                        "intent": intent_result
                    },
                    "priority": priority.lower(),
                    "metadata": {
                        "mode": mode.value,
                        "created_at": datetime.now().isoformat()
                    }
                },
                timeout=5
            )
            
            if response.status_code == 200:
                task = response.json()
                
                # コストを記録
                if self.cost_tracking_enabled:
                    self._record_cost(
                        service=intent_result.get("intent_type", "unknown"),
                        operation="task_execution",
                        cost=self._estimate_cost(intent_result.get("intent_type"))
                    )
                
                return {
                    "success": True,
                    "task_id": task.get("task_id"),
                    "plan_id": plan.get("plan_id"),
                    "intent_type": intent_result.get("intent_type"),
                    "mode": mode.value
                }
            else:
                return {
                    "success": False,
                    "error": "タスクのエンキューに失敗しました",
                    "intent_type": intent_result.get("intent_type")
                }
        except Exception as e:
            logger.error(f"Task Queue接続エラー: {e}")
            return {
                "success": False,
                "error": f"Task Queue接続エラー: {e}",
                "intent_type": intent_result.get("intent_type")
            }
    
    def _is_allowed_in_mode(self, intent_type: str, mode: SystemMode) -> bool:
        """モードで許可されているかチェック"""
        mode_rules = {
            SystemMode.WORK: [
                "task_execution", "information_search", "code_generation",
                "scheduling", "data_analysis", "system_control"
            ],
            SystemMode.CREATIVE: [
                "image_generation", "code_generation", "information_search"
            ],
            SystemMode.FUN: [
                "image_generation", "conversation", "information_search"
            ],
            SystemMode.AUTO: []  # すべて許可
        }
        
        allowed_types = mode_rules.get(mode, [])
        return len(allowed_types) == 0 or intent_type in allowed_types
    
    def _get_priority_for_mode(self, mode: SystemMode) -> str:
        """モードに応じた優先度を取得"""
        priority_map = {
            SystemMode.WORK: "high",
            SystemMode.CREATIVE: "medium",
            SystemMode.FUN: "low",
            SystemMode.AUTO: "medium"
        }
        return priority_map.get(mode, "medium")
    
    def set_mode(self, mode: SystemMode):
        """モードを設定"""
        self.current_mode = mode
        self.config["default_mode"] = mode.value
        self._save_config()
        logger.info(f"✅ モード変更: {mode.value}")
    
    def get_mode(self) -> SystemMode:
        """現在のモードを取得"""
        return self.current_mode
    
    def _estimate_cost(self, service: str) -> float:
        """コストを推定"""
        service_costs = self.config.get("service_costs", {})
        return service_costs.get(service, 0.01)
    
    def _record_cost(self, service: str, operation: str, cost: float, metadata: Optional[Dict[str, Any]] = None):
        """コストを記録"""
        import sqlite3
        
        conn = sqlite3.connect(self.cost_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cost_entries (timestamp, service, operation, cost, currency, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            service,
            operation,
            cost,
            "JPY",
            json.dumps(metadata or {}, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def get_cost_summary(self, days: int = 1) -> Dict[str, Any]:
        """コストサマリーを取得"""
        import sqlite3
        
        conn = sqlite3.connect(self.cost_db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 合計コスト
        cursor.execute("""
            SELECT SUM(cost) FROM cost_entries
            WHERE timestamp >= ?
        """, (cutoff_date,))
        total_cost = cursor.fetchone()[0] or 0.0
        
        # サービス別コスト
        cursor.execute("""
            SELECT service, SUM(cost) FROM cost_entries
            WHERE timestamp >= ?
            GROUP BY service
        """, (cutoff_date,))
        service_costs = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 今日のコスト
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        cursor.execute("""
            SELECT SUM(cost) FROM cost_entries
            WHERE timestamp >= ?
        """, (today_start,))
        today_cost = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            "total_cost": total_cost,
            "today_cost": today_cost,
            "service_costs": service_costs,
            "currency": "JPY",
            "days": days
        }
    
    def _save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")


# Flask APIサーバー
app = Flask(__name__)
CORS(app)

# グローバルAPIインスタンス
ui_api = None

def init_ui_api():
    """UI APIを初期化"""
    global ui_api
    if ui_api is None:
        ui_api = UIOperationsAPI()
    return ui_api

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "UI Operations API"})

@app.route('/api/execute', methods=['POST'])
def execute_endpoint():
    """タスク実行エンドポイント"""
    data = request.get_json() or {}
    input_text = data.get("text", "")
    mode_str = data.get("mode")
    
    if not input_text:
        return jsonify({"error": "text is required"}), 400
    
    ui_api = init_ui_api()
    
    mode = None
    if mode_str:
        try:
            mode = SystemMode(mode_str)
        except ValueError:
            mode = None
    
    result = ui_api.execute_task(input_text, mode)
    return jsonify(result)

@app.route('/api/mode', methods=['GET'])
def get_mode_endpoint():
    """モード取得エンドポイント"""
    ui_api = init_ui_api()
    return jsonify({"mode": ui_api.get_mode().value})

@app.route('/api/mode', methods=['POST'])
def set_mode_endpoint():
    """モード設定エンドポイント"""
    data = request.get_json() or {}
    mode_str = data.get("mode")
    
    if not mode_str:
        return jsonify({"error": "mode is required"}), 400
    
    try:
        mode = SystemMode(mode_str)
    except ValueError:
        return jsonify({"error": f"Invalid mode: {mode_str}"}), 400
    
    ui_api = init_ui_api()
    ui_api.set_mode(mode)
    
    return jsonify({"mode": mode.value, "status": "updated"})

@app.route('/api/cost', methods=['GET'])
def get_cost_endpoint():
    """コスト取得エンドポイント"""
    days = request.args.get("days", 1, type=int)
    
    ui_api = init_ui_api()
    summary = ui_api.get_cost_summary(days)
    
    return jsonify(summary)


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5110))
    logger.info(f"🎮 UI操作機能API起動中... (ポート: {port})")
    init_ui_api()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

