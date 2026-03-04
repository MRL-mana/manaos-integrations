import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class FieldOperation(BaseModel):
    id: Optional[str] = None
    operation_type: str  # fuel_delivery, maintenance, inspection, emergency
    location: str
    operator_id: str
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = 1
    description: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    data: Dict[str, Any] = {}

class FieldReport(BaseModel):
    id: Optional[str] = None
    operation_id: str
    report_type: str  # daily, incident, maintenance, performance
    content: str
    attachments: List[str] = []
    created_by: str
    created_at: Optional[str] = None

class ManaFieldOperationsSystem:
    def __init__(self):
        self.app = FastAPI(title="Mana Field Operations System", version="1.0.0")
        self.db_path = "/root/mana_field_operations.db"
        self.logger = logger
        self.active_operations = {}
        self.field_operators = {}
        self.init_database()
        self.setup_api()
        self.setup_startup_events()
        self.start_background_tasks()
        self.logger.info("🚀 Mana Field Operations System 初期化完了")

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 現場操作テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_operations (
                id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                location TEXT NOT NULL,
                operator_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 1,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                data TEXT
            )
        """)
        
        # 現場レポートテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_reports (
                id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (operation_id) REFERENCES field_operations (id)
            )
        """)
        
        # 現場オペレーターテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_operators (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT DEFAULT 'available',
                last_activity TEXT,
                skills TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 現場メトリクステーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (operation_id) REFERENCES field_operations (id)
            )
        """)
        
        # 緊急対応テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_responses (
                id TEXT PRIMARY KEY,
                emergency_type TEXT NOT NULL,
                location TEXT NOT NULL,
                severity TEXT NOT NULL,
                reported_by TEXT NOT NULL,
                status TEXT DEFAULT 'reported',
                response_team TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="現場業務システムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana Field Operations System",
                "status": "healthy",
                "version": self.app.version,
                "active_operations": len(self.active_operations),
                "field_operators": len(self.field_operators)
            }

        @self.app.post("/api/operations", summary="現場操作作成")
        async def create_operation(operation: FieldOperation):
            operation_id = f"op_{int(time.time())}_{hash(operation.operation_type) % 10000}"
            operation.id = operation_id
            operation.created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO field_operations 
                (id, operation_type, location, operator_id, status, priority, description, created_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                operation.id,
                operation.operation_type,
                operation.location,
                operation.operator_id,
                operation.status,
                operation.priority,
                operation.description,
                operation.created_at,
                json.dumps(operation.data)
            ))
            
            conn.commit()
            conn.close()
            
            self.active_operations[operation_id] = operation
            
            # 緊急度に応じて通知
            if operation.priority >= 3:
                await self.send_emergency_notification(operation)
            
            self.logger.info(f"現場操作作成: {operation_id} - {operation.operation_type}")
            return {"status": "success", "operation_id": operation_id, "message": "現場操作が作成されました"}

        @self.app.get("/api/operations", summary="現場操作一覧")
        async def get_operations(status: Optional[str] = None, location: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM field_operations WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if location:
                query += " AND location = ?"
                params.append(location)
            
            query += " ORDER BY priority DESC, created_at DESC"
            
            cursor.execute(query, params)
            
            operations = []
            for row in cursor.fetchall():
                operations.append({
                    "id": row[0],
                    "operation_type": row[1],
                    "location": row[2],
                    "operator_id": row[3],
                    "status": row[4],
                    "priority": row[5],
                    "description": row[6],
                    "created_at": row[7],
                    "started_at": row[8],
                    "completed_at": row[9],
                    "data": json.loads(row[10]) if row[10] else {}
                })
            
            conn.close()
            return {"operations": operations, "count": len(operations)}

        @self.app.put("/api/operations/{operation_id}/status", summary="操作ステータス更新")
        async def update_operation_status(operation_id: str, status: str, operator_id: str):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 操作の存在確認
            cursor.execute("SELECT * FROM field_operations WHERE id = ?", (operation_id,))
            operation_row = cursor.fetchone()
            
            if not operation_row:
                raise HTTPException(status_code=404, detail="操作が見つかりません")
            
            # ステータス更新
            update_fields = ["status = ?"]
            params = [status]
            
            if status == "in_progress" and not operation_row[8]:  # started_at
                update_fields.append("started_at = ?")
                params.append(datetime.now().isoformat())
            elif status == "completed":
                update_fields.append("completed_at = ?")
                params.append(datetime.now().isoformat())
            
            params.append(operation_id)
            
            cursor.execute(f"""
                UPDATE field_operations 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, params)
            
            conn.commit()
            conn.close()
            
            # アクティブ操作を更新
            if operation_id in self.active_operations:
                self.active_operations[operation_id].status = status
                if status == "completed":
                    del self.active_operations[operation_id]
            
            self.logger.info(f"操作ステータス更新: {operation_id} - {status}")
            return {"status": "success", "message": f"操作ステータスが {status} に更新されました"}

        @self.app.post("/api/reports", summary="現場レポート作成")
        async def create_report(report: FieldReport):
            report_id = f"report_{int(time.time())}_{hash(report.operation_id) % 10000}"
            report.id = report_id
            report.created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO field_reports 
                (id, operation_id, report_type, content, attachments, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                report.id,
                report.operation_id,
                report.report_type,
                report.content,
                json.dumps(report.attachments),
                report.created_by,
                report.created_at
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"現場レポート作成: {report_id} - {report.report_type}")
            return {"status": "success", "report_id": report_id, "message": "現場レポートが作成されました"}

        @self.app.get("/api/reports", summary="現場レポート一覧")
        async def get_reports(operation_id: Optional[str] = None, report_type: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM field_reports WHERE 1=1"
            params = []
            
            if operation_id:
                query += " AND operation_id = ?"
                params.append(operation_id)
            
            if report_type:
                query += " AND report_type = ?"
                params.append(report_type)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            
            reports = []
            for row in cursor.fetchall():
                reports.append({
                    "id": row[0],
                    "operation_id": row[1],
                    "report_type": row[2],
                    "content": row[3],
                    "attachments": json.loads(row[4]) if row[4] else [],
                    "created_by": row[5],
                    "created_at": row[6]
                })
            
            conn.close()
            return {"reports": reports, "count": len(reports)}

        @self.app.post("/api/emergency", summary="緊急事態報告")
        async def report_emergency(emergency_type: str, location: str, severity: str, reported_by: str, description: str):
            emergency_id = f"emergency_{int(time.time())}_{hash(location) % 10000}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO emergency_responses 
                (id, emergency_type, location, severity, reported_by, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                emergency_id,
                emergency_type,
                location,
                severity,
                reported_by,
                "reported",
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # 緊急対応チームに通知
            await self.activate_emergency_response(emergency_id, emergency_type, location, severity)
            
            self.logger.critical(f"🚨 緊急事態報告: {emergency_type} - {location} - {severity}")
            return {"status": "success", "emergency_id": emergency_id, "message": "緊急事態が報告され、対応チームが派遣されました"}

        @self.app.get("/api/emergency", summary="緊急事態一覧")
        async def get_emergencies(status: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM emergency_responses 
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT * FROM emergency_responses 
                    ORDER BY created_at DESC
                """)
            
            emergencies = []
            for row in cursor.fetchall():
                emergencies.append({
                    "id": row[0],
                    "emergency_type": row[1],
                    "location": row[2],
                    "severity": row[3],
                    "reported_by": row[4],
                    "status": row[5],
                    "response_team": row[6],
                    "created_at": row[7],
                    "resolved_at": row[8]
                })
            
            conn.close()
            return {"emergencies": emergencies, "count": len(emergencies)}

        @self.app.get("/api/dashboard", summary="現場業務ダッシュボード")
        async def get_dashboard():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 統計情報を取得
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_operations,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_operations,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as active_operations,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_operations
                FROM field_operations 
                WHERE created_at > datetime('now', '-24 hours')
            """)
            
            operation_stats = cursor.fetchone()
            
            cursor.execute("""
                SELECT COUNT(*) as active_emergencies
                FROM emergency_responses 
                WHERE status IN ('reported', 'responding')
            """)
            
            emergency_stats = cursor.fetchone()
            
            conn.close()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "operation_stats": {
                    "total_operations": operation_stats[0] or 0,
                    "pending_operations": operation_stats[1] or 0,
                    "active_operations": operation_stats[2] or 0,
                    "completed_operations": operation_stats[3] or 0
                },
                "emergency_stats": {
                    "active_emergencies": emergency_stats[0] or 0
                },
                "field_operators": len(self.field_operators),
                "active_operations": len(self.active_operations)
            }

        @self.app.get("/", summary="現場業務ダッシュボード")
        async def dashboard():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana Field Operations</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{ 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; 
                        min-height: 100vh;
                        padding: 10px;
                    }}
                    .container {{ max-width: 100%; margin: 0 auto; }}
                    .header {{ text-align: center; margin-bottom: 20px; padding: 10px; }}
                    .header h1 {{ font-size: 1.8em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
                    .header p {{ font-size: 0.9em; opacity: 0.9; margin-top: 5px; }}
                    .stats-grid {{ 
                        display: grid; 
                        grid-template-columns: repeat(2, 1fr); 
                        gap: 10px; 
                        margin-bottom: 20px; 
                    }}
                    .stat-card {{ 
                        background: rgba(255,255,255,0.15); 
                        border-radius: 12px; 
                        padding: 15px; 
                        text-align: center;
                        backdrop-filter: blur(10px);
                    }}
                    .stat-number {{ font-size: 1.5em; font-weight: bold; color: #ffd700; }}
                    .stat-label {{ font-size: 0.8em; opacity: 0.9; margin-top: 5px; }}
                    .operations-grid {{ 
                        display: grid; 
                        grid-template-columns: 1fr; 
                        gap: 10px; 
                        margin-bottom: 20px; 
                    }}
                    .operation-card {{ 
                        background: rgba(255,255,255,0.1); 
                        border-radius: 12px; 
                        padding: 15px;
                        backdrop-filter: blur(10px);
                    }}
                    .operation-card.pending {{ border-left: 4px solid #ff9800; }}
                    .operation-card.in_progress {{ border-left: 4px solid #2196F3; }}
                    .operation-card.completed {{ border-left: 4px solid #4CAF50; }}
                    .operation-card.failed {{ border-left: 4px solid #f44336; }}
                    .operation-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
                    .operation-type {{ font-weight: bold; font-size: 1.1em; }}
                    .operation-priority {{ 
                        background: rgba(255,255,255,0.2); 
                        padding: 4px 8px; 
                        border-radius: 12px; 
                        font-size: 0.8em;
                    }}
                    .operation-details {{ font-size: 0.9em; opacity: 0.9; }}
                    .action-buttons {{ 
                        display: grid; 
                        grid-template-columns: repeat(2, 1fr); 
                        gap: 10px; 
                        margin-bottom: 20px; 
                    }}
                    .action-btn {{ 
                        background: rgba(76,175,80,0.8); 
                        color: white; 
                        border: none; 
                        padding: 15px; 
                        border-radius: 12px; 
                        font-size: 0.9em;
                        cursor: pointer;
                        backdrop-filter: blur(10px);
                    }}
                    .action-btn:hover {{ background: rgba(76,175,80,1); }}
                    .action-btn.emergency {{ background: rgba(244,67,54,0.8); }}
                    .action-btn.emergency:hover {{ background: rgba(244,67,54,1); }}
                    .emergency-section {{ 
                        background: rgba(244,67,54,0.2); 
                        border-radius: 12px; 
                        padding: 15px; 
                        margin-bottom: 20px;
                        border: 2px solid rgba(244,67,54,0.5);
                    }}
                    .emergency-btn {{ 
                        background: rgba(244,67,54,0.9); 
                        color: white; 
                        border: none; 
                        padding: 15px; 
                        border-radius: 12px; 
                        font-size: 1em;
                        cursor: pointer;
                        width: 100%;
                        font-weight: bold;
                    }}
                    .emergency-btn:hover {{ background: rgba(244,67,54,1); }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🏭 Mana Field Operations</h1>
                        <p>現場業務統合・リアルタイム監視・緊急対応システム</p>
                    </div>
                    
                    <div class="stats-grid" id="stats-grid">
                        <!-- 統計情報がここに表示されます -->
                    </div>
                    
                    <div class="action-buttons">
                        <button class="action-btn" onclick="createOperation()">➕ 新規操作</button>
                        <button class="action-btn" onclick="viewReports()">📋 レポート</button>
                        <button class="action-btn" onclick="operatorStatus()">👥 オペレーター</button>
                        <button class="action-btn" onclick="systemStatus()">📊 システム状態</button>
                    </div>
                    
                    <div class="emergency-section">
                        <h3 style="margin-bottom: 10px; text-align: center;">🚨 緊急事態報告</h3>
                        <button class="emergency-btn" onclick="reportEmergency()">緊急事態を報告</button>
                    </div>
                    
                    <div class="operations-grid" id="operations-grid">
                        <!-- 操作一覧がここに表示されます -->
                    </div>
                </div>
                
                <script>
                    async function refreshDashboard() {{
                        try {{
                            const response = await fetch('/api/dashboard');
                            const data = await response.json();
                            
                            // 統計情報更新
                            const statsGrid = document.getElementById('stats-grid');
                            statsGrid.innerHTML = `
                                <div class="stat-card">
                                    <div class="stat-number">${{data.operation_stats.total_operations}}</div>
                                    <div class="stat-label">総操作数</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${{data.operation_stats.active_operations}}</div>
                                    <div class="stat-label">進行中</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${{data.operation_stats.completed_operations}}</div>
                                    <div class="stat-label">完了</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${{data.emergency_stats.active_emergencies}}</div>
                                    <div class="stat-label">緊急事態</div>
                                </div>
                            `;
                            
                            // 操作一覧取得
                            const operationsResponse = await fetch('/api/operations');
                            const operationsData = await operationsResponse.json();
                            
                            const operationsGrid = document.getElementById('operations-grid');
                            if (operationsData.operations && operationsData.operations.length > 0) {{
                                operationsGrid.innerHTML = operationsData.operations.slice(0, 10).map(operation => {{
                                    const priorityText = operation.priority === 1 ? '低' : 
                                                       operation.priority === 2 ? '中' : 
                                                       operation.priority === 3 ? '高' : '緊急';
                                    
                                    return `
                                        <div class="operation-card ${{operation.status}}">
                                            <div class="operation-header">
                                                <div class="operation-type">${{operation.operation_type.toUpperCase()}}</div>
                                                <div class="operation-priority">優先度: ${{priorityText}}</div>
                                            </div>
                                            <div class="operation-details">
                                                <strong>場所:</strong> ${{operation.location}}<br>
                                                <strong>オペレーター:</strong> ${{operation.operator_id}}<br>
                                                <strong>説明:</strong> ${{operation.description}}<br>
                                                <strong>ステータス:</strong> ${{operation.status}}<br>
                                                <strong>作成時刻:</strong> ${{new Date(operation.created_at).toLocaleString()}}
                                            </div>
                                        </div>
                                    `;
                                }}).join('');
                            }} else {{
                                operationsGrid.innerHTML = '<div style="text-align: center; opacity: 0.7;">操作はありません</div>';
                            }}
                            
                        }} catch (error) {{
                            console.error('ダッシュボード更新エラー:', error);
                        }}
                    }}
                    
                    async function createOperation() {{
                        const operationType = prompt('操作タイプ (fuel_delivery, maintenance, inspection):');
                        const location = prompt('場所:');
                        const operatorId = prompt('オペレーターID:');
                        const description = prompt('説明:');
                        const priority = prompt('優先度 (1-4):');
                        
                        if (operationType && location && operatorId && description && priority) {{
                            try {{
                                const response = await fetch('/api/operations', {{
                                    method: 'POST',
                                    headers: {{'Content-Type': 'application/json'}},
                                    body: JSON.stringify({{
                                        operation_type: operationType,
                                        location: location,
                                        operator_id: operatorId,
                                        priority: parseInt(priority),
                                        description: description
                                    }})
                                }});
                                const result = await response.json();
                                alert('操作作成: ' + result.message);
                                refreshDashboard();
                            }} catch (error) {{
                                console.error('操作作成エラー:', error);
                            }}
                        }}
                    }}
                    
                    async function reportEmergency() {{
                        const emergencyType = prompt('緊急事態タイプ (fire, gas_leak, equipment_failure, accident):');
                        const location = prompt('場所:');
                        const severity = prompt('深刻度 (low, medium, high, critical):');
                        const reportedBy = prompt('報告者ID:');
                        const description = prompt('詳細説明:');
                        
                        if (emergencyType && location && severity && reportedBy && description) {{
                            try {{
                                const response = await fetch(`/api/emergency?emergency_type=${{emergencyType}}&location=${{location}}&severity=${{severity}}&reported_by=${{reportedBy}}&description=${{description}}`, {{
                                    method: 'POST'
                                }});
                                const result = await response.json();
                                alert('緊急事態報告: ' + result.message);
                                refreshDashboard();
                            }} catch (error) {{
                                console.error('緊急事態報告エラー:', error);
                            }}
                        }}
                    }}
                    
                    async function viewReports() {{
                        try {{
                            const response = await fetch('/api/reports');
                            const data = await response.json();
                            alert(`レポート数: ${{data.count}}`);
                        }} catch (error) {{
                            console.error('レポート取得エラー:', error);
                        }}
                    }}
                    
                    async function operatorStatus() {{
                        alert('オペレーター状況: ' + '{{field_operators}}' + '名のオペレーターが活動中');
                    }}
                    
                    async function systemStatus() {{
                        try {{
                            const response = await fetch('/api/status');
                            const data = await response.json();
                            alert(`システム状態: ${{data.status}} - アクティブ操作: ${{data.active_operations}}`);
                        }} catch (error) {{
                            console.error('システム状態取得エラー:', error);
                        }}
                    }}
                    
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
            asyncio.create_task(self._operation_monitor_worker())
            asyncio.create_task(self._emergency_monitor_worker())
            asyncio.create_task(self._field_metrics_worker())
            self.logger.info("バックグラウンドタスク開始")

    async def send_emergency_notification(self, operation: FieldOperation):
        """緊急通知を送信"""
        self.logger.warning(f"🚨 緊急操作: {operation.operation_type} - {operation.location} - 優先度: {operation.priority}")

    async def activate_emergency_response(self, emergency_id: str, emergency_type: str, location: str, severity: str):
        """緊急対応を活性化"""
        # 実際の実装では、緊急対応チームに通知し、自動的にリソースを割り当て
        self.logger.critical(f"🚨 緊急対応開始: {emergency_type} - {location} - {severity}")

    async def _operation_monitor_worker(self):
        """操作監視ワーカー"""
        while True:
            try:
                await self.monitor_operations()
                await asyncio.sleep(60)  # 1分ごとに監視
            except Exception as e:
                self.logger.error(f"操作監視ワーカーエラー: {e}")
                await asyncio.sleep(60)

    async def monitor_operations(self):
        """操作を監視"""
        for operation_id, operation in self.active_operations.items():
            # 長時間進行中の操作をチェック
            if operation.status == "in_progress" and operation.started_at:
                start_time = datetime.fromisoformat(operation.started_at)
                if (datetime.now() - start_time).seconds > 3600:  # 1時間以上
                    self.logger.warning(f"長時間進行中の操作: {operation_id}")

    async def _emergency_monitor_worker(self):
        """緊急事態監視ワーカー"""
        while True:
            try:
                await self.monitor_emergencies()
                await asyncio.sleep(30)  # 30秒ごとに監視
            except Exception as e:
                self.logger.error(f"緊急事態監視ワーカーエラー: {e}")
                await asyncio.sleep(30)

    async def monitor_emergencies(self):
        """緊急事態を監視"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM emergency_responses 
            WHERE status IN ('reported', 'responding')
        """)
        
        active_emergencies = cursor.fetchall()
        conn.close()
        
        for emergency in active_emergencies:
            # 緊急事態の進行状況をチェック
            self.logger.info(f"緊急事態監視: {emergency[1]} - {emergency[2]} - {emergency[5]}")

    async def _field_metrics_worker(self):
        """現場メトリクスワーカー"""
        while True:
            try:
                await self.collect_field_metrics()
                await asyncio.sleep(300)  # 5分ごとに収集
            except Exception as e:
                self.logger.error(f"現場メトリクスワーカーエラー: {e}")
                await asyncio.sleep(300)

    async def collect_field_metrics(self):
        """現場メトリクスを収集"""
        # 実際の実装では、現場のセンサーやデバイスからメトリクスを収集
        for operation_id, operation in self.active_operations.items():
            if operation.status == "in_progress":
                # メトリクスをデータベースに記録
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO field_metrics 
                    (operation_id, metric_type, value, unit, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    operation_id,
                    "progress",
                    75.0,  # 仮の値
                    "percent",
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                conn.close()

    def start_background_tasks(self):
        # バックグラウンドタスクはFastAPIのstartupイベントで開始
        self.logger.info("バックグラウンドタスク準備完了")

def main():
    system = ManaFieldOperationsSystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5032)

if __name__ == "__main__":
    main()
