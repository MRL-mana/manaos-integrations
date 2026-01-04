#!/usr/bin/env python3
"""
📦 Task Queue System - 汎用タスクキューシステム
Redis/SQLiteベースのキューシステム、Priority制御、Rate Limit管理
"""

import os
import json
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from queue import PriorityQueue, Queue
import hashlib

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("TaskQueue")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("TaskQueue")


class TaskPriority(int, Enum):
    """タスク優先度（数値が大きいほど優先度高）"""
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    URGENT = 20


class TaskStatus(str, Enum):
    """タスクステータス"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """タスク"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def __lt__(self, other):
        """優先度キュー用の比較"""
        if self.priority != other.priority:
            return self.priority.value < other.priority.value
        # 優先度が同じ場合は作成時刻で比較（古い方が優先）
        return self.created_at > other.created_at


@dataclass
class RateLimitRule:
    """レート制限ルール"""
    task_type: str
    max_requests: int  # 時間窓内の最大リクエスト数
    window_seconds: int  # 時間窓（秒）
    current_requests: int = 0
    window_start: str = ""
    
    def __post_init__(self):
        if not self.window_start:
            self.window_start = datetime.now().isoformat()


class TaskQueueSystem:
    """タスクキューシステム"""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        use_redis: bool = False,
        redis_url: str = "redis://localhost:6379",
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            db_path: SQLiteデータベースパス
            use_redis: Redisを使用するか
            redis_url: Redis URL
            config_path: 設定ファイルのパス
        """
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.config_path = config_path or Path(__file__).parent / "task_queue_config.json"
        self.config = self._load_config()
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "task_queue.db"
        self._init_database()
        
        # メモリ内キュー（優先度キュー）
        self.priority_queue: PriorityQueue = PriorityQueue()
        
        # レート制限ルール
        self.rate_limit_rules: Dict[str, RateLimitRule] = {}
        self._load_rate_limit_rules()
        
        # ワーカースレッド
        self.workers: List[threading.Thread] = []
        self.running = False
        self.worker_count = self.config.get("worker_count", 3)
        
        # タスクハンドラー
        self.task_handlers: Dict[str, Callable] = {}
        
        logger.info(f"✅ Task Queue System初期化完了 (ワーカー数: {self.worker_count})")
    
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
                        "worker_count": {"type": int, "default": 3},
                        "max_queue_size": {"type": int, "default": 10000},
                        "default_priority": {"type": str, "default": "medium"},
                        "default_max_retries": {"type": int, "default": 3}
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
            "worker_count": 3,
            "max_queue_size": 10000,
            "default_priority": "medium",
            "default_max_retries": 3,
            "rate_limit_rules": {
                "api_call": {
                    "max_requests": 100,
                    "window_seconds": 60
                },
                "image_generation": {
                    "max_requests": 10,
                    "window_seconds": 60
                },
                "workflow_execution": {
                    "max_requests": 50,
                    "window_seconds": 60
                }
            }
        }
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # タスクテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                metadata TEXT
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON tasks(priority DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at DESC)")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def _load_rate_limit_rules(self):
        """レート制限ルールを読み込む"""
        rules = self.config.get("rate_limit_rules", {})
        for task_type, rule_config in rules.items():
            self.rate_limit_rules[task_type] = RateLimitRule(
                task_type=task_type,
                max_requests=rule_config.get("max_requests", 100),
                window_seconds=rule_config.get("window_seconds", 60)
            )
        logger.info(f"✅ レート制限ルール読み込み完了: {len(self.rate_limit_rules)}件")
    
    def _check_rate_limit(self, task_type: str) -> bool:
        """レート制限をチェック"""
        if task_type not in self.rate_limit_rules:
            return True  # ルールがない場合は制限なし
        
        rule = self.rate_limit_rules[task_type]
        
        # 時間窓をチェック
        window_start = datetime.fromisoformat(rule.window_start)
        window_end = window_start + timedelta(seconds=rule.window_seconds)
        now = datetime.now()
        
        # 時間窓が過ぎた場合はリセット
        if now > window_end:
            rule.current_requests = 0
            rule.window_start = now.isoformat()
        
        # レート制限チェック
        if rule.current_requests >= rule.max_requests:
            logger.warning(f"⚠️ レート制限に達しました: {task_type} ({rule.current_requests}/{rule.max_requests})")
            return False
        
        # リクエスト数を増やす
        rule.current_requests += 1
        return True
    
    def register_handler(self, task_type: str, handler: Callable):
        """タスクハンドラーを登録"""
        self.task_handlers[task_type] = handler
        logger.info(f"✅ タスクハンドラー登録: {task_type}")
    
    def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: Optional[TaskPriority] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        タスクをエンキュー
        
        Args:
            task_type: タスクタイプ
            payload: タスクペイロード
            priority: 優先度
            max_retries: 最大リトライ回数
            metadata: メタデータ
        
        Returns:
            Task: 作成されたタスク
        """
        # レート制限チェック
        if not self._check_rate_limit(task_type):
            raise Exception(f"レート制限に達しました: {task_type}")
        
        # 優先度を決定
        if priority is None:
            priority_str = self.config.get("default_priority", "medium")
            priority = TaskPriority[priority_str.upper()]
        
        # タスクIDを生成
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(json.dumps(payload, sort_keys=True)) % 10000}"
        
        # タスクを作成
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            status=TaskStatus.PENDING,
            max_retries=max_retries or self.config.get("default_max_retries", 3),
            metadata=metadata or {}
        )
        
        # データベースに保存
        self._save_task(task)
        
        # キューに追加
        self.priority_queue.put(task)
        
        logger.info(f"✅ タスクエンキュー: {task_id} (優先度: {priority.name})")
        
        return task
    
    def _save_task(self, task: Task):
        """タスクをデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO tasks (
                task_id, task_type, payload, priority, status,
                created_at, started_at, completed_at, result, error,
                retry_count, max_retries, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.task_type,
            json.dumps(task.payload, ensure_ascii=False),
            task.priority.value,
            task.status.value,
            task.created_at,
            task.started_at,
            task.completed_at,
            json.dumps(task.result, ensure_ascii=False) if task.result else None,
            task.error,
            task.retry_count,
            task.max_retries,
            json.dumps(task.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def _update_task_status(self, task: Task, status: TaskStatus, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """タスクステータスを更新"""
        task.status = status
        if status == TaskStatus.RUNNING:
            task.started_at = datetime.now().isoformat()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.now().isoformat()
        
        if result:
            task.result = result
        if error:
            task.error = error
        
        self._save_task(task)
    
    def _worker_loop(self, worker_id: int):
        """ワーカーループ"""
        logger.info(f"🚀 ワーカー {worker_id} 開始")
        
        while self.running:
            try:
                # キューからタスクを取得（タイムアウト付き）
                try:
                    task = self.priority_queue.get(timeout=1)
                except:
                    continue
                
                # タスクを実行
                self._execute_task(task, worker_id)
                
            except Exception as e:
                logger.error(f"ワーカー {worker_id} エラー: {e}")
                time.sleep(1)
        
        logger.info(f"🛑 ワーカー {worker_id} 停止")
    
    def _execute_task(self, task: Task, worker_id: int):
        """タスクを実行"""
        logger.info(f"📋 タスク実行開始: {task.task_id} (ワーカー: {worker_id})")
        
        # ステータスを更新
        self._update_task_status(task, TaskStatus.RUNNING)
        
        try:
            # ハンドラーを取得
            if task.task_type not in self.task_handlers:
                raise Exception(f"タスクハンドラーが見つかりません: {task.task_type}")
            
            handler = self.task_handlers[task.task_type]
            
            # タスクを実行
            result = handler(task.payload)
            
            # 成功
            self._update_task_status(task, TaskStatus.COMPLETED, result=result)
            logger.info(f"✅ タスク完了: {task.task_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ タスク失敗: {task.task_id} - {error_msg}")
            
            # リトライ可能かチェック
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(f"🔄 タスクリトライ: {task.task_id} ({task.retry_count}/{task.max_retries})")
                
                # キューに再追加
                self.priority_queue.put(task)
                self._update_task_status(task, TaskStatus.QUEUED)
            else:
                # リトライ上限に達した
                self._update_task_status(task, TaskStatus.FAILED, error=error_msg)
    
    def start_workers(self):
        """ワーカーを開始"""
        if self.running:
            logger.warning("ワーカーは既に実行中です")
            return
        
        self.running = True
        
        for i in range(self.worker_count):
            worker = threading.Thread(target=self._worker_loop, args=(i + 1,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"✅ ワーカー開始: {self.worker_count}個")
    
    def stop_workers(self):
        """ワーカーを停止"""
        self.running = False
        
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
        logger.info("🛑 ワーカー停止")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """タスクを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_task(row)
    
    def _row_to_task(self, row) -> Task:
        """データベース行をTaskオブジェクトに変換"""
        return Task(
            task_id=row[0],
            task_type=row[1],
            payload=json.loads(row[2]),
            priority=TaskPriority(row[3]),
            status=TaskStatus(row[4]),
            created_at=row[5],
            started_at=row[6],
            completed_at=row[7],
            result=json.loads(row[8]) if row[8] else None,
            error=row[9],
            retry_count=row[10],
            max_retries=row[11],
            metadata=json.loads(row[12]) if row[12] else {}
        )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """キュー状態を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ステータス別のタスク数
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM tasks 
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 優先度別のタスク数
        cursor.execute("""
            SELECT priority, COUNT(*) 
            FROM tasks 
            WHERE status IN ('pending', 'queued', 'running')
            GROUP BY priority
        """)
        priority_counts = {TaskPriority(row[0]).name: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "queue_size": self.priority_queue.qsize(),
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "worker_count": len(self.workers),
            "running": self.running
        }


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルキューシステムインスタンス
queue_system = None

def init_queue_system():
    """キューシステムを初期化"""
    global queue_system
    if queue_system is None:
        queue_system = TaskQueueSystem()
        queue_system.start_workers()
    return queue_system

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Task Queue System"})

@app.route('/api/enqueue', methods=['POST'])
def enqueue_endpoint():
    """タスクエンキューエンドポイント"""
    data = request.get_json() or {}
    
    task_type = data.get("task_type")
    payload = data.get("payload", {})
    priority_str = data.get("priority", "medium")
    max_retries = data.get("max_retries")
    metadata = data.get("metadata")
    
    if not task_type:
        return jsonify({"error": "task_type is required"}), 400
    
    try:
        priority = TaskPriority[priority_str.upper()]
    except KeyError:
        priority = TaskPriority.MEDIUM
    
    queue_system = init_queue_system()
    
    try:
        task = queue_system.enqueue(
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            metadata=metadata
        )
        return jsonify(asdict(task))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_endpoint(task_id: str):
    """タスク取得エンドポイント"""
    queue_system = init_queue_system()
    task = queue_system.get_task(task_id)
    
    if not task:
        return jsonify({"error": "Task not found"}), 404
    
    return jsonify(asdict(task))

@app.route('/api/status', methods=['GET'])
def get_status_endpoint():
    """キュー状態取得エンドポイント"""
    queue_system = init_queue_system()
    status = queue_system.get_queue_status()
    return jsonify(status)

@app.route('/api/register', methods=['POST'])
def register_handler_endpoint():
    """タスクハンドラー登録エンドポイント"""
    data = request.get_json() or {}
    
    task_type = data.get("task_type")
    handler_url = data.get("handler_url")  # Webhook URL
    
    if not task_type:
        return jsonify({"error": "task_type is required"}), 400
    
    # Webhookハンドラーを作成
    def webhook_handler(payload):
        import httpx
        response = httpx.post(handler_url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    
    queue_system = init_queue_system()
    queue_system.register_handler(task_type, webhook_handler)
    
    return jsonify({"status": "registered", "task_type": task_type})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5104))
    logger.info(f"📦 Task Queue System起動中... (ポート: {port})")
    init_queue_system()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

