import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class ProcessingTask(BaseModel):
    id: Optional[str] = None
    task_type: str  # ai_inference, data_processing, model_training, etc.
    priority: int = 1
    payload: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    assigned_worker: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class WorkerNode(BaseModel):
    id: str
    node_type: str  # gpu, cpu, hybrid
    status: str  # available, busy, offline
    capabilities: List[str]
    current_load: float = 0.0
    last_heartbeat: Optional[str] = None
    region: str = "us-east-1"

class ManaDistributedProcessingSystem:
    def __init__(self):
        self.app = FastAPI(title="Mana Distributed Processing System", version="1.0.0")
        self.db_path = "/root/mana_distributed_processing.db"
        self.logger = logger
        self.worker_nodes = {}
        self.task_queue = []
        self.completed_tasks = []
        self.init_database()
        self.setup_api()
        self.setup_startup_events()
        self.start_background_tasks()
        self.logger.info("🚀 Mana Distributed Processing System 初期化完了")

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # タスクテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                assigned_worker TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error_message TEXT
            )
        """)
        
        # ワーカーノードテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS worker_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                status TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                current_load REAL DEFAULT 0.0,
                last_heartbeat TEXT,
                region TEXT NOT NULL
            )
        """)
        
        # タスク実行履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                execution_time REAL,
                success BOOLEAN,
                error_message TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES processing_tasks (id)
            )
        """)
        
        # パフォーマンスメトリクステーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT NOT NULL,
                cpu_usage REAL,
                gpu_usage REAL,
                memory_usage REAL,
                network_usage REAL,
                task_throughput REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (worker_id) REFERENCES worker_nodes (id)
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="分散処理システムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana Distributed Processing System",
                "status": "healthy",
                "version": self.app.version,
                "active_workers": len([w for w in self.worker_nodes.values() if w.status == "available"]),
                "pending_tasks": len(self.task_queue),
                "completed_tasks": len(self.completed_tasks)
            }

        @self.app.post("/api/tasks", summary="処理タスク作成")
        async def create_task(task: ProcessingTask):
            task_id = f"task_{int(time.time())}_{hash(task.task_type) % 10000}"
            task.id = task_id
            task.created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO processing_tasks 
                (id, task_type, priority, payload, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.task_type,
                task.priority,
                json.dumps(task.payload),
                task.status,
                task.created_at
            ))
            
            conn.commit()
            conn.close()
            
            # タスクをキューに追加
            self.task_queue.append(task)
            self.task_queue.sort(key=lambda x: x.priority, reverse=True)
            
            # 即座にワーカーに割り当てを試行
            await self.assign_task_to_worker(task)
            
            self.logger.info(f"処理タスク作成: {task_id} - {task.task_type}")
            return {"status": "success", "task_id": task_id, "message": "タスクが作成され、処理キューに追加されました"}

        @self.app.get("/api/tasks", summary="タスク一覧取得")
        async def get_tasks(status: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM processing_tasks 
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT * FROM processing_tasks 
                    ORDER BY created_at DESC
                """)
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row[0],
                    "task_type": row[1],
                    "priority": row[2],
                    "payload": json.loads(row[3]),
                    "status": row[4],
                    "assigned_worker": row[5],
                    "created_at": row[6],
                    "started_at": row[7],
                    "completed_at": row[8],
                    "result": json.loads(row[9]) if row[9] else None,
                    "error_message": row[10]
                })
            
            conn.close()
            return {"tasks": tasks, "count": len(tasks)}

        @self.app.get("/api/tasks/{task_id}", summary="特定タスクの詳細取得")
        async def get_task(task_id: str):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM processing_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="タスクが見つかりません")
            
            task = {
                "id": row[0],
                "task_type": row[1],
                "priority": row[2],
                "payload": json.loads(row[3]),
                "status": row[4],
                "assigned_worker": row[5],
                "created_at": row[6],
                "started_at": row[7],
                "completed_at": row[8],
                "result": json.loads(row[9]) if row[9] else None,
                "error_message": row[10]
            }
            
            conn.close()
            return task

        @self.app.post("/api/workers/register", summary="ワーカーノード登録")
        async def register_worker(worker: WorkerNode):
            worker.last_heartbeat = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO worker_nodes 
                (id, node_type, status, capabilities, current_load, last_heartbeat, region)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                worker.id,
                worker.node_type,
                worker.status,
                json.dumps(worker.capabilities),
                worker.current_load,
                worker.last_heartbeat,
                worker.region
            ))
            
            conn.commit()
            conn.close()
            
            self.worker_nodes[worker.id] = worker
            self.logger.info(f"ワーカーノード登録: {worker.id} - {worker.node_type}")
            return {"status": "success", "worker_id": worker.id, "message": "ワーカーノードが登録されました"}

        @self.app.get("/api/workers", summary="ワーカーノード一覧")
        async def get_workers():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM worker_nodes ORDER BY last_heartbeat DESC")
            
            workers = []
            for row in cursor.fetchall():
                workers.append({
                    "id": row[0],
                    "node_type": row[1],
                    "status": row[2],
                    "capabilities": json.loads(row[3]),
                    "current_load": row[4],
                    "last_heartbeat": row[5],
                    "region": row[6]
                })
            
            conn.close()
            return {"workers": workers, "count": len(workers)}

        @self.app.post("/api/workers/{worker_id}/heartbeat", summary="ワーカーハートビート")
        async def worker_heartbeat(worker_id: str, metrics: Dict[str, Any]):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ハートビート更新
            cursor.execute("""
                UPDATE worker_nodes 
                SET last_heartbeat = ?, current_load = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), metrics.get("load", 0.0), worker_id))
            
            # パフォーマンスメトリクス記録
            cursor.execute("""
                INSERT INTO performance_metrics 
                (worker_id, cpu_usage, gpu_usage, memory_usage, network_usage, task_throughput, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                worker_id,
                metrics.get("cpu_usage", 0.0),
                metrics.get("gpu_usage", 0.0),
                metrics.get("memory_usage", 0.0),
                metrics.get("network_usage", 0.0),
                metrics.get("task_throughput", 0.0),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # ワーカーの状態を更新
            if worker_id in self.worker_nodes:
                self.worker_nodes[worker_id].last_heartbeat = datetime.now().isoformat()
                self.worker_nodes[worker_id].current_load = metrics.get("load", 0.0)
            
            return {"status": "success", "message": "ハートビート受信"}

        @self.app.get("/api/performance", summary="パフォーマンス分析")
        async def get_performance_analysis(hours: int = 24):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute("""
                SELECT 
                    w.id,
                    w.node_type,
                    AVG(pm.cpu_usage) as avg_cpu,
                    AVG(pm.gpu_usage) as avg_gpu,
                    AVG(pm.memory_usage) as avg_memory,
                    AVG(pm.task_throughput) as avg_throughput,
                    COUNT(te.task_id) as tasks_completed
                FROM worker_nodes w
                LEFT JOIN performance_metrics pm ON w.id = pm.worker_id AND pm.timestamp > ?
                LEFT JOIN task_execution_history te ON w.id = te.worker_id AND te.timestamp > ?
                GROUP BY w.id, w.node_type
                ORDER BY tasks_completed DESC
            """, (since_time, since_time))
            
            performance_data = []
            for row in cursor.fetchall():
                performance_data.append({
                    "worker_id": row[0],
                    "node_type": row[1],
                    "avg_cpu_usage": row[2] or 0.0,
                    "avg_gpu_usage": row[3] or 0.0,
                    "avg_memory_usage": row[4] or 0.0,
                    "avg_throughput": row[5] or 0.0,
                    "tasks_completed": row[6] or 0
                })
            
            conn.close()
            return {"performance_data": performance_data, "period_hours": hours}

        @self.app.get("/", summary="分散処理ダッシュボード")
        async def dashboard():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana Distributed Processing System</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .header { text-align: center; margin-bottom: 30px; }
                    .header h1 { font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
                    .header p { font-size: 1.2em; opacity: 0.9; }
                    .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
                    .card { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); }
                    .card h3 { margin-top: 0; color: #ffd700; }
                    .task-item { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; margin: 10px 0; }
                    .status-pending { border-left: 4px solid #ff9800; }
                    .status-running { border-left: 4px solid #2196F3; }
                    .status-completed { border-left: 4px solid #4CAF50; }
                    .status-failed { border-left: 4px solid #f44336; }
                    .worker-item { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; margin: 10px 0; }
                    .status-available { border-left: 4px solid #4CAF50; }
                    .status-busy { border-left: 4px solid #ff9800; }
                    .status-offline { border-left: 4px solid #f44336; }
                    .btn { background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin: 5px; }
                    .btn:hover { background: #45a049; }
                    .btn-danger { background: #f44336; }
                    .btn-danger:hover { background: #da190b; }
                    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔄 Mana Distributed Processing System</h1>
                        <p>分散処理・負荷分散・フェイルオーバーシステム</p>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>📋 タスクキュー</h3>
                            <div id="task-queue"></div>
                        </div>
                        
                        <div class="card">
                            <h3>🖥️ ワーカーノード</h3>
                            <div id="worker-nodes"></div>
                        </div>
                        
                        <div class="card">
                            <h3>📊 パフォーマンス分析</h3>
                            <div id="performance-analysis"></div>
                        </div>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>✅ 完了タスク</h3>
                            <div id="completed-tasks"></div>
                        </div>
                        
                        <div class="card">
                            <h3>❌ 失敗タスク</h3>
                            <div id="failed-tasks"></div>
                        </div>
                        
                        <div class="card">
                            <h3>📈 システム統計</h3>
                            <div id="system-stats"></div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <button class="btn" onclick="refreshDashboard()">🔄 ダッシュボード更新</button>
                        <button class="btn" onclick="createAITask()">🤖 AI推論タスク作成</button>
                        <button class="btn" onclick="createDataTask()">📊 データ処理タスク作成</button>
                    </div>
                </div>
                
                <script>
                    async function refreshDashboard() {
                        try {
                            // タスクキュー取得
                            const tasksResponse = await fetch('/api/tasks');
                            const tasksData = await tasksResponse.json();
                            
                            const taskQueue = document.getElementById('task-queue');
                            const pendingTasks = tasksData.tasks.filter(task => task.status === 'pending');
                            if (pendingTasks.length > 0) {
                                taskQueue.innerHTML = pendingTasks.slice(0, 5).map(task => `
                                    <div class="task-item status-${task.status}">
                                        <h4>${task.task_type.toUpperCase()}</h4>
                                        <p><strong>優先度:</strong> ${task.priority}</p>
                                        <p><strong>作成時刻:</strong> ${new Date(task.created_at).toLocaleString()}</p>
                                        <p><strong>ワーカー:</strong> ${task.assigned_worker || '未割り当て'}</p>
                                    </div>
                                `).join('');
                            } else {
                                taskQueue.innerHTML = '<p>待機中のタスクはありません</p>';
                            }
                            
                            // ワーカーノード取得
                            const workersResponse = await fetch('/api/workers');
                            const workersData = await workersResponse.json();
                            
                            const workerNodes = document.getElementById('worker-nodes');
                            if (workersData.workers && workersData.workers.length > 0) {
                                workerNodes.innerHTML = workersData.workers.map(worker => `
                                    <div class="worker-item status-${worker.status}">
                                        <h4>${worker.id}</h4>
                                        <p><strong>タイプ:</strong> ${worker.node_type}</p>
                                        <p><strong>ステータス:</strong> ${worker.status}</p>
                                        <p><strong>負荷:</strong> ${worker.current_load.toFixed(1)}%</p>
                                        <p><strong>機能:</strong> ${worker.capabilities.join(', ')}</p>
                                        <p><strong>最終ハートビート:</strong> ${new Date(worker.last_heartbeat).toLocaleString()}</p>
                                    </div>
                                `).join('');
                            } else {
                                workerNodes.innerHTML = '<p>登録されたワーカーはありません</p>';
                            }
                            
                            // パフォーマンス分析取得
                            const performanceResponse = await fetch('/api/performance?hours=24');
                            const performanceData = await performanceResponse.json();
                            
                            const performanceAnalysis = document.getElementById('performance-analysis');
                            if (performanceData.performance_data && performanceData.performance_data.length > 0) {
                                performanceAnalysis.innerHTML = performanceData.performance_data.slice(0, 3).map(perf => `
                                    <div style="background: rgba(255,255,255,0.1); border-radius: 5px; padding: 10px; margin: 5px 0;">
                                        <strong>${perf.worker_id}</strong><br>
                                        CPU: ${perf.avg_cpu_usage.toFixed(1)}%<br>
                                        GPU: ${perf.avg_gpu_usage.toFixed(1)}%<br>
                                        メモリ: ${perf.avg_memory_usage.toFixed(1)}%<br>
                                        完了タスク: ${perf.tasks_completed}
                                    </div>
                                `).join('');
                            } else {
                                performanceAnalysis.innerHTML = '<p>パフォーマンスデータはありません</p>';
                            }
                            
                            // 完了タスク
                            const completedTasks = document.getElementById('completed-tasks');
                            const completed = tasksData.tasks.filter(task => task.status === 'completed');
                            if (completed.length > 0) {
                                completedTasks.innerHTML = completed.slice(0, 3).map(task => `
                                    <div class="task-item status-${task.status}">
                                        <h4>${task.task_type.toUpperCase()}</h4>
                                        <p><strong>完了時刻:</strong> ${new Date(task.completed_at).toLocaleString()}</p>
                                        <p><strong>ワーカー:</strong> ${task.assigned_worker}</p>
                                    </div>
                                `).join('');
                            } else {
                                completedTasks.innerHTML = '<p>完了したタスクはありません</p>';
                            }
                            
                            // 失敗タスク
                            const failedTasks = document.getElementById('failed-tasks');
                            const failed = tasksData.tasks.filter(task => task.status === 'failed');
                            if (failed.length > 0) {
                                failedTasks.innerHTML = failed.slice(0, 3).map(task => `
                                    <div class="task-item status-${task.status}">
                                        <h4>${task.task_type.toUpperCase()}</h4>
                                        <p><strong>エラー:</strong> ${task.error_message}</p>
                                        <p><strong>ワーカー:</strong> ${task.assigned_worker}</p>
                                    </div>
                                `).join('');
                            } else {
                                failedTasks.innerHTML = '<p>失敗したタスクはありません</p>';
                            }
                            
                            // 統計情報
                            const systemStats = document.getElementById('system-stats');
                            const stats = {
                                total_tasks: tasksData.tasks.length,
                                pending_tasks: pendingTasks.length,
                                running_tasks: tasksData.tasks.filter(task => task.status === 'running').length,
                                completed_tasks: completed.length,
                                failed_tasks: failed.length,
                                total_workers: workersData.workers.length,
                                available_workers: workersData.workers.filter(w => w.status === 'available').length
                            };
                            
                            systemStats.innerHTML = `
                                <div class="stats-grid">
                                    <div style="text-align: center; background: rgba(255,152,0,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.pending_tasks}</h3>
                                        <p>待機中タスク</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(33,150,243,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.running_tasks}</h3>
                                        <p>実行中タスク</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(76,175,80,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.completed_tasks}</h3>
                                        <p>完了タスク</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(156,39,176,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.available_workers}</h3>
                                        <p>利用可能ワーカー</p>
                                    </div>
                                </div>
                            `;
                            
                        } catch (error) {
                            console.error('ダッシュボード更新エラー:', error);
                        }
                    }
                    
                    async function createAITask() {
                        try {
                            const response = await fetch('/api/tasks', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    task_type: 'ai_inference',
                                    priority: 1,
                                    payload: {
                                        model: 'llama3.2',
                                        prompt: 'Hello, how are you?',
                                        max_tokens: 100
                                    }
                                })
                            });
                            const result = await response.json();
                            alert('AI推論タスク作成: ' + result.message);
                            refreshDashboard();
                        } catch (error) {
                            console.error('AIタスク作成エラー:', error);
                        }
                    }
                    
                    async function createDataTask() {
                        try {
                            const response = await fetch('/api/tasks', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    task_type: 'data_processing',
                                    priority: 2,
                                    payload: {
                                        dataset: 'sample_data.csv',
                                        operation: 'aggregation',
                                        parameters: {
                                            group_by: 'category',
                                            aggregate: 'sum'
                                        }
                                    }
                                })
                            });
                            const result = await response.json();
                            alert('データ処理タスク作成: ' + result.message);
                            refreshDashboard();
                        } catch (error) {
                            console.error('データタスク作成エラー:', error);
                        }
                    }
                    
                    // 初期読み込み
                    refreshDashboard();
                    
                    // 30秒ごとに自動更新
                    setInterval(refreshDashboard, 30000);
                </script>
            </body>
            </html>
            """

    def setup_startup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._task_scheduler_worker())
            asyncio.create_task(self._worker_monitor_worker())
            asyncio.create_task(self._load_balancer_worker())
            self.logger.info("バックグラウンドタスク開始")

    async def assign_task_to_worker(self, task: ProcessingTask):
        """タスクをワーカーに割り当て"""
        # 利用可能なワーカーを検索
        available_workers = [w for w in self.worker_nodes.values() 
                           if w.status == "available" and task.task_type in w.capabilities]
        
        if available_workers:
            # 負荷が最も低いワーカーを選択
            best_worker = min(available_workers, key=lambda w: w.current_load)
            
            # タスクを割り当て
            task.assigned_worker = best_worker.id
            task.status = "running"
            task.started_at = datetime.now().isoformat()
            
            # ワーカーの状態を更新
            best_worker.status = "busy"
            best_worker.current_load += 10.0  # 仮の負荷値
            
            # データベースを更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE processing_tasks 
                SET status = ?, assigned_worker = ?, started_at = ?
                WHERE id = ?
            """, (task.status, task.assigned_worker, task.started_at, task.id))
            
            cursor.execute("""
                UPDATE worker_nodes 
                SET status = ?, current_load = ?
                WHERE id = ?
            """, (best_worker.status, best_worker.current_load, best_worker.id))
            
            conn.commit()
            conn.close()
            
            # タスク実行をシミュレート
            asyncio.create_task(self.execute_task(task))
            
            self.logger.info(f"タスク割り当て: {task.id} -> {best_worker.id}")

    async def execute_task(self, task: ProcessingTask):
        """タスク実行をシミュレート"""
        try:
            # 実際の実装では、ワーカーノードでタスクを実行
            await asyncio.sleep(5)  # 実行時間をシミュレート
            
            # タスク完了
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
            task.result = {"output": f"Task {task.id} completed successfully"}
            
            # ワーカーの状態を更新
            if task.assigned_worker in self.worker_nodes:
                worker = self.worker_nodes[task.assigned_worker]
                worker.status = "available"
                worker.current_load = max(0.0, worker.current_load - 10.0)
            
            # データベースを更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE processing_tasks 
                SET status = ?, completed_at = ?, result = ?
                WHERE id = ?
            """, (task.status, task.completed_at, json.dumps(task.result), task.id))
            
            if task.assigned_worker in self.worker_nodes:
                worker = self.worker_nodes[task.assigned_worker]
                cursor.execute("""
                    UPDATE worker_nodes 
                    SET status = ?, current_load = ?
                    WHERE id = ?
                """, (worker.status, worker.current_load, task.assigned_worker))
            
            # 実行履歴を記録
            cursor.execute("""
                INSERT INTO task_execution_history 
                (task_id, worker_id, execution_time, success, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (task.id, task.assigned_worker, 5.0, True, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            self.completed_tasks.append(task)
            self.logger.info(f"タスク完了: {task.id}")
            
        except Exception as e:
            # タスク失敗
            task.status = "failed"
            task.error_message = str(e)
            
            # ワーカーの状態を更新
            if task.assigned_worker in self.worker_nodes:
                worker = self.worker_nodes[task.assigned_worker]
                worker.status = "available"
                worker.current_load = max(0.0, worker.current_load - 10.0)
            
            self.logger.error(f"タスク実行エラー: {task.id} - {e}")

    async def _task_scheduler_worker(self):
        """タスクスケジューラーワーカー"""
        while True:
            try:
                # 待機中のタスクを処理
                pending_tasks = [t for t in self.task_queue if t.status == "pending"]
                for task in pending_tasks:
                    await self.assign_task_to_worker(task)
                
                await asyncio.sleep(10)  # 10秒ごとにチェック
            except Exception as e:
                self.logger.error(f"タスクスケジューラーワーカーエラー: {e}")
                await asyncio.sleep(10)

    async def _worker_monitor_worker(self):
        """ワーカーモニターワーカー"""
        while True:
            try:
                # オフラインのワーカーを検出
                current_time = datetime.now()
                for worker_id, worker in self.worker_nodes.items():
                    if worker.last_heartbeat:
                        last_heartbeat = datetime.fromisoformat(worker.last_heartbeat)
                        if (current_time - last_heartbeat).seconds > 300:  # 5分以上
                            worker.status = "offline"
                            self.logger.warning(f"ワーカーオフライン検出: {worker_id}")
                
                await asyncio.sleep(60)  # 1分ごとにチェック
            except Exception as e:
                self.logger.error(f"ワーカーモニターワーカーエラー: {e}")
                await asyncio.sleep(60)

    async def _load_balancer_worker(self):
        """ロードバランサーワーカー"""
        while True:
            try:
                # 負荷分散の最適化
                await self.optimize_load_distribution()
                await asyncio.sleep(30)  # 30秒ごとに最適化
            except Exception as e:
                self.logger.error(f"ロードバランサーワーカーエラー: {e}")
                await asyncio.sleep(30)

    async def optimize_load_distribution(self):
        """負荷分散の最適化"""
        # 実際の実装では、より高度な負荷分散アルゴリズムを実装
        pass

    def start_background_tasks(self):
        # バックグラウンドタスクはFastAPIのstartupイベントで開始
        self.logger.info("バックグラウンドタスク準備完了")

def main():
    system = ManaDistributedProcessingSystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5029)

if __name__ == "__main__":
    main()
