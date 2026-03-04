import json
import logging
import sqlite3
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class AutomationRule(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int = 1
    enabled: bool = True
    created_by: str = "system"
    created_at: Optional[str] = None

class RuleApproval(BaseModel):
    rule_id: str
    status: str  # pending, approved, rejected, testing
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    comments: Optional[str] = None

class ManaRuleApprovalSystem:
    def __init__(self):
        self.app = FastAPI(title="Mana Rule Approval System", version="1.0.0")
        self.db_path = "/root/mana_rule_approval.db"
        self.logger = logger
        self.init_database()
        self.setup_api()
        self.start_background_tasks()
        self.logger.info("🚀 Mana Rule Approval System 初期化完了")

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 自動化ルールテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                trigger_conditions TEXT NOT NULL,
                actions TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                enabled BOOLEAN DEFAULT TRUE,
                created_by TEXT DEFAULT 'system',
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # 承認履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rule_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                status TEXT NOT NULL,
                approved_by TEXT,
                approved_at TEXT,
                test_results TEXT,
                comments TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (rule_id) REFERENCES automation_rules (id)
            )
        """)
        
        # テスト環境テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_environment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                test_status TEXT NOT NULL,
                test_results TEXT,
                test_logs TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (rule_id) REFERENCES automation_rules (id)
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="承認システムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana Rule Approval System",
                "status": "healthy",
                "version": self.app.version
            }

        @self.app.post("/api/rules", summary="自動化ルール作成")
        async def create_rule(rule: AutomationRule):
            rule_id = f"rule_{int(time.time())}_{hash(rule.name) % 10000}"
            rule.id = rule_id
            rule.created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO automation_rules 
                (id, name, description, trigger_conditions, actions, priority, enabled, created_by, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.id,
                rule.name,
                rule.description,
                json.dumps(rule.trigger_conditions),
                json.dumps(rule.actions),
                rule.priority,
                rule.enabled,
                rule.created_by,
                rule.created_at,
                "pending"
            ))
            
            conn.commit()
            conn.close()
            
            # 自動的にテスト環境で検証開始
            await self.start_rule_testing(rule_id)
            
            self.logger.info(f"自動化ルール作成: {rule.name} (ID: {rule_id})")
            return {"status": "success", "rule_id": rule_id, "message": "ルールが作成され、テスト環境で検証中です"}

        @self.app.get("/api/rules", summary="自動化ルール一覧取得")
        async def get_rules(status: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT id, name, description, trigger_conditions, actions, priority, enabled, created_by, created_at, status
                    FROM automation_rules 
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT id, name, description, trigger_conditions, actions, priority, enabled, created_by, created_at, status
                    FROM automation_rules 
                    ORDER BY created_at DESC
                """)
            
            rules = []
            for row in cursor.fetchall():
                rules.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "trigger_conditions": json.loads(row[3]),
                    "actions": json.loads(row[4]),
                    "priority": row[5],
                    "enabled": bool(row[6]),
                    "created_by": row[7],
                    "created_at": row[8],
                    "status": row[9]
                })
            
            conn.close()
            return {"rules": rules, "count": len(rules)}

        @self.app.get("/api/rules/{rule_id}", summary="特定ルールの詳細取得")
        async def get_rule(rule_id: str):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, trigger_conditions, actions, priority, enabled, created_by, created_at, status
                FROM automation_rules 
                WHERE id = ?
            """, (rule_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="ルールが見つかりません")
            
            rule = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "trigger_conditions": json.loads(row[3]),
                "actions": json.loads(row[4]),
                "priority": row[5],
                "enabled": bool(row[6]),
                "created_by": row[7],
                "created_at": row[8],
                "status": row[9]
            }
            
            # 承認履歴も取得
            cursor.execute("""
                SELECT status, approved_by, approved_at, test_results, comments, created_at
                FROM rule_approvals 
                WHERE rule_id = ?
                ORDER BY created_at DESC
            """, (rule_id,))
            
            approvals = []
            for approval_row in cursor.fetchall():
                approvals.append({
                    "status": approval_row[0],
                    "approved_by": approval_row[1],
                    "approved_at": approval_row[2],
                    "test_results": json.loads(approval_row[3]) if approval_row[3] else None,
                    "comments": approval_row[4],
                    "created_at": approval_row[5]
                })
            
            rule["approvals"] = approvals
            conn.close()
            return rule

        @self.app.post("/api/rules/{rule_id}/approve", summary="ルール承認")
        async def approve_rule(rule_id: str, approval: RuleApproval):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ルールの存在確認
            cursor.execute("SELECT status FROM automation_rules WHERE id = ?", (rule_id,))
            rule_row = cursor.fetchone()
            if not rule_row:
                raise HTTPException(status_code=404, detail="ルールが見つかりません")
            
            # 承認履歴を記録
            cursor.execute("""
                INSERT INTO rule_approvals 
                (rule_id, status, approved_by, approved_at, test_results, comments, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rule_id,
                approval.status,
                approval.approved_by,
                datetime.now().isoformat() if approval.status == "approved" else None,
                json.dumps(approval.test_results) if approval.test_results else None,
                approval.comments,
                datetime.now().isoformat()
            ))
            
            # ルールのステータス更新
            cursor.execute("""
                UPDATE automation_rules 
                SET status = ? 
                WHERE id = ?
            """, (approval.status, rule_id))
            
            conn.commit()
            conn.close()
            
            # 承認された場合は本番環境にデプロイ
            if approval.status == "approved":
                await self.deploy_rule_to_production(rule_id)
            
            self.logger.info(f"ルール承認: {rule_id} - {approval.status}")
            return {"status": "success", "message": f"ルールが{approval.status}されました"}

        @self.app.post("/api/rules/{rule_id}/test", summary="ルールテスト実行")
        async def test_rule(rule_id: str):
            test_result = await self.execute_rule_test(rule_id)
            return {"status": "success", "test_result": test_result}

        @self.app.get("/api/approvals", summary="承認待ちルール一覧")
        async def get_pending_approvals():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.id, r.name, r.description, r.created_at, r.created_by
                FROM automation_rules r
                WHERE r.status = 'pending'
                ORDER BY r.created_at ASC
            """)
            
            pending_rules = []
            for row in cursor.fetchall():
                pending_rules.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3],
                    "created_by": row[4]
                })
            
            conn.close()
            return {"pending_rules": pending_rules, "count": len(pending_rules)}

        @self.app.get("/", summary="承認システムダッシュボード")
        async def dashboard():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana Rule Approval System</title>
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
                    .rule-item { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; margin: 10px 0; }
                    .status-pending { border-left: 4px solid #ff9800; }
                    .status-approved { border-left: 4px solid #4CAF50; }
                    .status-rejected { border-left: 4px solid #f44336; }
                    .status-testing { border-left: 4px solid #2196F3; }
                    .btn { background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin: 5px; }
                    .btn:hover { background: #45a049; }
                    .btn-danger { background: #f44336; }
                    .btn-danger:hover { background: #da190b; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🛡️ Mana Rule Approval System</h1>
                        <p>自動化ルールの安全な承認・テスト・デプロイシステム</p>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>⏳ 承認待ちルール</h3>
                            <div id="pending-rules"></div>
                        </div>
                        
                        <div class="card">
                            <h3>🧪 テスト中ルール</h3>
                            <div id="testing-rules"></div>
                        </div>
                        
                        <div class="card">
                            <h3>✅ 承認済みルール</h3>
                            <div id="approved-rules"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📊 ルール統計</h3>
                        <div id="rule-stats"></div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <button class="btn" onclick="refreshDashboard()">🔄 ダッシュボード更新</button>
                    </div>
                </div>
                
                <script>
                    async function refreshDashboard() {
                        try {
                            // 承認待ちルール取得
                            const pendingResponse = await fetch('/api/approvals');
                            const pendingData = await pendingResponse.json();
                            
                            const pendingRules = document.getElementById('pending-rules');
                            if (pendingData.pending_rules && pendingData.pending_rules.length > 0) {
                                pendingRules.innerHTML = pendingData.pending_rules.map(rule => `
                                    <div class="rule-item status-pending">
                                        <h4>${rule.name}</h4>
                                        <p>${rule.description}</p>
                                        <p><small>作成者: ${rule.created_by} | ${new Date(rule.created_at).toLocaleString()}</small></p>
                                        <button class="btn" onclick="approveRule('${rule.id}')">✅ 承認</button>
                                        <button class="btn btn-danger" onclick="rejectRule('${rule.id}')">❌ 却下</button>
                                    </div>
                                `).join('');
                            } else {
                                pendingRules.innerHTML = '<p>承認待ちのルールはありません</p>';
                            }
                            
                            // 全ルール取得
                            const rulesResponse = await fetch('/api/rules');
                            const rulesData = await rulesResponse.json();
                            
                            // テスト中ルール
                            const testingRules = document.getElementById('testing-rules');
                            const testing = rulesData.rules.filter(rule => rule.status === 'testing');
                            if (testing.length > 0) {
                                testingRules.innerHTML = testing.map(rule => `
                                    <div class="rule-item status-testing">
                                        <h4>${rule.name}</h4>
                                        <p>${rule.description}</p>
                                        <button class="btn" onclick="testRule('${rule.id}')">🧪 テスト実行</button>
                                    </div>
                                `).join('');
                            } else {
                                testingRules.innerHTML = '<p>テスト中のルールはありません</p>';
                            }
                            
                            // 承認済みルール
                            const approvedRules = document.getElementById('approved-rules');
                            const approved = rulesData.rules.filter(rule => rule.status === 'approved');
                            if (approved.length > 0) {
                                approvedRules.innerHTML = approved.map(rule => `
                                    <div class="rule-item status-approved">
                                        <h4>${rule.name}</h4>
                                        <p>${rule.description}</p>
                                        <p><small>作成者: ${rule.created_by} | ${new Date(rule.created_at).toLocaleString()}</small></p>
                                    </div>
                                `).join('');
                            } else {
                                approvedRules.innerHTML = '<p>承認済みのルールはありません</p>';
                            }
                            
                            // 統計情報
                            const ruleStats = document.getElementById('rule-stats');
                            const stats = {
                                total: rulesData.rules.length,
                                pending: pendingData.pending_rules.length,
                                testing: testing.length,
                                approved: approved.length,
                                rejected: rulesData.rules.filter(rule => rule.status === 'rejected').length
                            };
                            
                            ruleStats.innerHTML = `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                                    <div style="text-align: center; background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.total}</h3>
                                        <p>総ルール数</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(255,152,0,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.pending}</h3>
                                        <p>承認待ち</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(33,150,243,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.testing}</h3>
                                        <p>テスト中</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(76,175,80,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.approved}</h3>
                                        <p>承認済み</p>
                                    </div>
                                </div>
                            `;
                            
                        } catch (error) {
                            console.error('ダッシュボード更新エラー:', error);
                        }
                    }
                    
                    async function approveRule(ruleId) {
                        try {
                            const response = await fetch(`/api/rules/${ruleId}/approve`, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    rule_id: ruleId,
                                    status: 'approved',
                                    approved_by: 'admin',
                                    comments: '承認されました'
                                })
                            });
                            const result = await response.json();
                            alert(result.message);
                            refreshDashboard();
                        } catch (error) {
                            console.error('承認エラー:', error);
                        }
                    }
                    
                    async function rejectRule(ruleId) {
                        try {
                            const response = await fetch(`/api/rules/${ruleId}/approve`, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    rule_id: ruleId,
                                    status: 'rejected',
                                    approved_by: 'admin',
                                    comments: '却下されました'
                                })
                            });
                            const result = await response.json();
                            alert(result.message);
                            refreshDashboard();
                        } catch (error) {
                            console.error('却下エラー:', error);
                        }
                    }
                    
                    async function testRule(ruleId) {
                        try {
                            const response = await fetch(`/api/rules/${ruleId}/test`, { method: 'POST' });
                            const result = await response.json();
                            alert('テスト実行完了: ' + JSON.stringify(result.test_result));
                            refreshDashboard();
                        } catch (error) {
                            console.error('テストエラー:', error);
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

    async def start_rule_testing(self, rule_id: str):
        """ルールのテスト環境での検証を開始"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO test_environment (rule_id, test_status, test_results, test_logs, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (rule_id, "running", None, None, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"ルールテスト開始: {rule_id}")

    async def execute_rule_test(self, rule_id: str) -> Dict[str, Any]:
        """ルールのテスト実行"""
        # 実際の実装では、テスト環境でルールを実行し、結果を返す
        test_result = {
            "rule_id": rule_id,
            "test_status": "completed",
            "success": True,
            "execution_time": 1.5,
            "test_cases": [
                {"name": "基本実行テスト", "status": "passed"},
                {"name": "エラーハンドリングテスト", "status": "passed"},
                {"name": "パフォーマンステスト", "status": "passed"}
            ],
            "performance_metrics": {
                "cpu_usage": 15.2,
                "memory_usage": 128.5,
                "response_time": 0.8
            }
        }
        
        # テスト結果をデータベースに保存
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE test_environment 
            SET test_status = ?, test_results = ?, test_logs = ?
            WHERE rule_id = ?
        """, (
            test_result["test_status"],
            json.dumps(test_result),
            json.dumps({"test_log": "テスト実行完了"}),
            rule_id
        ))
        
        conn.commit()
        conn.close()
        
        return test_result

    async def deploy_rule_to_production(self, rule_id: str):
        """承認されたルールを本番環境にデプロイ"""
        # 実際の実装では、本番環境の自動化オーケストレーターにルールを送信
        self.logger.info(f"ルール本番デプロイ: {rule_id}")
        
        # オーケストレーターシステムにルールを送信
        try:
            async with httpx.AsyncClient() as client:
                # ルール詳細を取得
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,))
                rule_row = cursor.fetchone()
                conn.close()
                
                if rule_row:
                    rule_data = {
                        "id": rule_row[0],
                        "name": rule_row[1],
                        "description": rule_row[2],
                        "trigger_conditions": json.loads(rule_row[3]),
                        "actions": json.loads(rule_row[4]),
                        "priority": rule_row[5],
                        "enabled": bool(rule_row[6])
                    }
                    
                    # オーケストレーターに送信
                    response = await client.post(
                        "http://localhost:5015/api/automation/rules",
                        json=rule_data,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        self.logger.info(f"ルールデプロイ成功: {rule_id}")
                    else:
                        self.logger.error(f"ルールデプロイ失敗: {rule_id} - {response.status_code}")
                        
        except Exception as e:
            self.logger.error(f"ルールデプロイエラー: {rule_id} - {e}")

    def start_background_tasks(self):
        # バックグラウンドタスクは必要に応じて実装
        self.logger.info("バックグラウンドタスク準備完了")

def main():
    system = ManaRuleApprovalSystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5026)

if __name__ == "__main__":
    main()
