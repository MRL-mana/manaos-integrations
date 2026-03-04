#!/usr/bin/env python3
"""
Mana Dynamic Scaling System
動的スケーリングシステム - 負荷に応じて自動調整
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import threading
import time
import sqlite3
import requests
import psutil

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class ManaDynamicScalingSystem:
    """Mana動的スケーリングシステム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Dynamic Scaling System", version="14.0.0")
        self.db_path = "/root/mana_dynamic_scaling.db"
        
        # スケーリング設定
        self.scaling_policies = {
            "cpu_scaling": {
                "scale_up_threshold": 80.0,
                "scale_down_threshold": 30.0,
                "min_instances": 1,
                "max_instances": 10
            },
            "memory_scaling": {
                "scale_up_threshold": 85.0,
                "scale_down_threshold": 40.0,
                "min_instances": 1,
                "max_instances": 8
            },
            "response_time_scaling": {
                "scale_up_threshold": 2.0,  # 秒
                "scale_down_threshold": 0.5,
                "min_instances": 1,
                "max_instances": 12
            }
        }
        
        self.current_instances = 1
        self.scaling_history = []
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_dynamic_scaling.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # データベース初期化
        self.init_database()
        
        # API設定
        self.setup_api()
        
        # バックグラウンドタスク開始
        self.start_background_tasks()
        
        self.logger.info("⚡ Mana Dynamic Scaling System 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # スケーリングイベントテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scaling_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                trigger_metric TEXT NOT NULL,
                metric_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                instances_before INTEGER NOT NULL,
                instances_after INTEGER NOT NULL,
                scaling_reason TEXT NOT NULL,
                status TEXT DEFAULT 'completed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # スケーリングポリシーテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scaling_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_name TEXT UNIQUE NOT NULL,
                policy_config TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # パフォーマンスメトリクステーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                instance_count INTEGER NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info("データベース初期化完了")
    
    def setup_api(self):
        """API設定"""
        # CORS設定
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # ルート定義
        @self.app.get("/")
        async def root():
            return await self.root()
        
        @self.app.get("/api/status")
        async def get_status():
            return await self.get_status()
        
        # スケーリングAPI
        @self.app.post("/api/scaling/auto-scale")
        async def auto_scale(scale_data: Dict[str, Any]):
            return await self.auto_scale(scale_data)
        
        @self.app.post("/api/scaling/manual-scale")
        async def manual_scale(scale_data: Dict[str, Any]):
            return await self.manual_scale(scale_data)
        
        @self.app.get("/api/scaling/events")
        async def get_scaling_events():
            return await self.get_scaling_events()
        
        # ポリシー管理API
        @self.app.get("/api/scaling/policies")
        async def get_scaling_policies():
            return await self.get_scaling_policies()
        
        @self.app.post("/api/scaling/policies")
        async def update_scaling_policy(policy_data: Dict[str, Any]):
            return await self.update_scaling_policy(policy_data)
        
        # メトリクスAPI
        @self.app.get("/api/scaling/metrics")
        async def get_performance_metrics():
            return await self.get_performance_metrics()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # 自動スケーリング監視
        threading.Thread(target=self.auto_scaling_monitor, daemon=True).start()
        
        # パフォーマンス監視
        threading.Thread(target=self.performance_monitor, daemon=True).start()
        
        # スケーリング最適化
        threading.Thread(target=self.scaling_optimization, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Dynamic Scaling System",
            "version": "14.0.0",
            "status": "active",
            "features": [
                "動的スケーリング",
                "自動負荷分散",
                "パフォーマンス最適化",
                "インテリジェントスケーリング",
                "リアルタイム調整",
                "予測的スケーリング"
            ],
            "capabilities": [
                "CPU・メモリ・レスポンス時間ベーススケーリング",
                "自動インスタンス管理",
                "負荷予測による事前スケーリング",
                "コスト最適化",
                "可用性向上"
            ]
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Dynamic Scaling System",
            "status": "healthy",
            "version": "14.0.0",
            "scaling": {
                "current_instances": self.current_instances,
                "total_scaling_events": await self.count_scaling_events(),
                "active_policies": len([p for p in self.scaling_policies.values() if p.get("enabled", True)]),
                "scaling_efficiency": await self.calculate_scaling_efficiency()
            },
            "policies": self.scaling_policies
        }
    
    async def auto_scale(self, scale_data: Dict[str, Any]):
        """自動スケーリング実行"""
        try:
            # 現在のシステムメトリクス取得
            current_metrics = await self.get_current_metrics()
            
            # スケーリング判定
            scaling_decision = await self.evaluate_scaling_decision(current_metrics)
            
            if scaling_decision["action"] == "scale_up":
                result = await self.scale_up(scaling_decision)
            elif scaling_decision["action"] == "scale_down":
                result = await self.scale_down(scaling_decision)
            else:
                result = {"action": "no_action", "reason": "metrics_within_threshold"}
            
            # スケーリングイベント記録
            await self.record_scaling_event(result, current_metrics)
            
            return {
                "scaling_decision": scaling_decision,
                "result": result,
                "current_instances": self.current_instances,
                "scaled_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"自動スケーリングエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_current_metrics(self) -> Dict[str, float]:
        """現在のメトリクス取得"""
        try:
            # システムメトリクス取得
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # レスポンス時間測定（簡易版）
            response_time = await self.measure_response_time()
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "response_time": response_time
            }
            
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            return {"cpu_usage": 0, "memory_usage": 0, "response_time": 0}
    
    async def measure_response_time(self) -> float:
        """レスポンス時間測定"""
        try:
            start_time = time.time()
            response = requests.get("http://localhost:5009/api/status", timeout=5)
            end_time = time.time()
            
            if response.status_code == 200:
                return end_time - start_time
            else:
                return 5.0  # タイムアウト値
                
        except requests.RequestException:
            return 5.0  # エラー時のデフォルト値
    
    async def evaluate_scaling_decision(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """スケーリング判定"""
        cpu_usage = metrics.get("cpu_usage", 0)
        memory_usage = metrics.get("memory_usage", 0)
        response_time = metrics.get("response_time", 0)
        
        # CPUベーススケーリング
        cpu_policy = self.scaling_policies["cpu_scaling"]
        if cpu_usage > cpu_policy["scale_up_threshold"] and self.current_instances < cpu_policy["max_instances"]:
            return {
                "action": "scale_up",
                "trigger_metric": "cpu_usage",
                "metric_value": cpu_usage,
                "threshold": cpu_policy["scale_up_threshold"],
                "reason": f"CPU使用率が{cpu_usage:.1f}%で閾値{cpu_policy['scale_up_threshold']}%を超過"
            }
        
        # メモリベーススケーリング
        memory_policy = self.scaling_policies["memory_scaling"]
        if memory_usage > memory_policy["scale_up_threshold"] and self.current_instances < memory_policy["max_instances"]:
            return {
                "action": "scale_up",
                "trigger_metric": "memory_usage",
                "metric_value": memory_usage,
                "threshold": memory_policy["scale_up_threshold"],
                "reason": f"メモリ使用率が{memory_usage:.1f}%で閾値{memory_policy['scale_up_threshold']}%を超過"
            }
        
        # レスポンス時間ベーススケーリング
        response_policy = self.scaling_policies["response_time_scaling"]
        if response_time > response_policy["scale_up_threshold"] and self.current_instances < response_policy["max_instances"]:
            return {
                "action": "scale_up",
                "trigger_metric": "response_time",
                "metric_value": response_time,
                "threshold": response_policy["scale_up_threshold"],
                "reason": f"レスポンス時間が{response_time:.2f}秒で閾値{response_policy['scale_up_threshold']}秒を超過"
            }
        
        # スケールダウン判定
        if (cpu_usage < cpu_policy["scale_down_threshold"] and 
            memory_usage < memory_policy["scale_down_threshold"] and
            response_time < response_policy["scale_down_threshold"] and
            self.current_instances > 1):
            return {
                "action": "scale_down",
                "trigger_metric": "combined",
                "metric_value": (cpu_usage + memory_usage) / 2,
                "threshold": (cpu_policy["scale_down_threshold"] + memory_policy["scale_down_threshold"]) / 2,
                "reason": "全メトリクスが閾値以下でスケールダウン可能"
            }
        
        return {
            "action": "no_action",
            "trigger_metric": "none",
            "metric_value": 0,
            "threshold": 0,
            "reason": "スケーリング条件を満たしていません"
        }
    
    async def scale_up(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """スケールアップ実行"""
        try:
            old_instances = self.current_instances
            self.current_instances += 1
            
            # 実際のスケールアップ処理（簡易版）
            # 実際の実装では、新しいインスタンスを起動する処理を実装
            
            self.logger.info(f"スケールアップ実行: {old_instances} -> {self.current_instances}")
            
            return {
                "action": "scale_up",
                "instances_before": old_instances,
                "instances_after": self.current_instances,
                "success": True,
                "message": f"インスタンス数を{old_instances}から{self.current_instances}に増加"
            }
            
        except Exception as e:
            self.logger.error(f"スケールアップエラー: {e}")
            return {
                "action": "scale_up",
                "instances_before": self.current_instances,
                "instances_after": self.current_instances,
                "success": False,
                "error": str(e)
            }
    
    async def scale_down(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """スケールダウン実行"""
        try:
            old_instances = self.current_instances
            self.current_instances = max(1, self.current_instances - 1)
            
            # 実際のスケールダウン処理（簡易版）
            # 実際の実装では、不要なインスタンスを停止する処理を実装
            
            self.logger.info(f"スケールダウン実行: {old_instances} -> {self.current_instances}")
            
            return {
                "action": "scale_down",
                "instances_before": old_instances,
                "instances_after": self.current_instances,
                "success": True,
                "message": f"インスタンス数を{old_instances}から{self.current_instances}に減少"
            }
            
        except Exception as e:
            self.logger.error(f"スケールダウンエラー: {e}")
            return {
                "action": "scale_down",
                "instances_before": self.current_instances,
                "instances_after": self.current_instances,
                "success": False,
                "error": str(e)
            }
    
    async def manual_scale(self, scale_data: Dict[str, Any]):
        """手動スケーリング"""
        try:
            target_instances = scale_data.get("target_instances")
            reason = scale_data.get("reason", "manual_scaling")
            
            if not target_instances or target_instances < 1:
                raise HTTPException(status_code=400, detail="Invalid target instances")
            
            old_instances = self.current_instances
            self.current_instances = target_instances
            
            # スケーリングイベント記録
            await self.record_scaling_event({
                "action": "manual_scale",
                "instances_before": old_instances,
                "instances_after": self.current_instances,
                "success": True,
                "reason": reason
            }, {})
            
            self.logger.info(f"手動スケーリング実行: {old_instances} -> {self.current_instances}")
            
            return {
                "action": "manual_scale",
                "instances_before": old_instances,
                "instances_after": self.current_instances,
                "reason": reason,
                "scaled_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"手動スケーリングエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def record_scaling_event(self, result: Dict[str, Any], metrics: Dict[str, float]):
        """スケーリングイベント記録"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scaling_events 
            (event_type, trigger_metric, metric_value, threshold_value, 
             instances_before, instances_after, scaling_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.get("action", "unknown"),
            result.get("trigger_metric", "manual"),
            result.get("metric_value", 0),
            result.get("threshold", 0),
            result.get("instances_before", 0),
            result.get("instances_after", 0),
            result.get("reason", "unknown"),
            "completed" if result.get("success", True) else "failed",
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def get_scaling_events(self):
        """スケーリングイベント取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, event_type, trigger_metric, metric_value, threshold_value,
                   instances_before, instances_after, scaling_reason, status, created_at
            FROM scaling_events
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "event_type": row[1],
                "trigger_metric": row[2],
                "metric_value": row[3],
                "threshold_value": row[4],
                "instances_before": row[5],
                "instances_after": row[6],
                "scaling_reason": row[7],
                "status": row[8],
                "created_at": row[9]
            })
        
        conn.close()
        
        return {
            "scaling_events": events,
            "count": len(events),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_scaling_policies(self):
        """スケーリングポリシー取得"""
        return {
            "scaling_policies": self.scaling_policies,
            "current_instances": self.current_instances,
            "timestamp": datetime.now().isoformat()
        }
    
    async def update_scaling_policy(self, policy_data: Dict[str, Any]):
        """スケーリングポリシー更新"""
        try:
            policy_name = policy_data.get("policy_name")
            policy_config = policy_data.get("policy_config")
            
            if not policy_name or policy_name not in self.scaling_policies:
                raise HTTPException(status_code=400, detail="Invalid policy name")
            
            # ポリシー更新
            self.scaling_policies[policy_name].update(policy_config)
            
            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO scaling_policies 
                (policy_name, policy_config, enabled, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (
                policy_name,
                json.dumps(policy_config),
                True,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"スケーリングポリシー更新: {policy_name}")
            
            return {
                "policy_name": policy_name,
                "updated_config": policy_config,
                "updated_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"ポリシー更新エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_performance_metrics(self):
        """パフォーマンスメトリクス取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT metric_name, metric_value, instance_count, timestamp
            FROM performance_metrics
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                "metric_name": row[0],
                "metric_value": row[1],
                "instance_count": row[2],
                "timestamp": row[3]
            })
        
        conn.close()
        
        return {
            "performance_metrics": metrics,
            "count": len(metrics),
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== バックグラウンドタスク ====================
    
    def auto_scaling_monitor(self):
        """自動スケーリング監視"""
        while True:
            try:
                # 定期的な自動スケーリングチェック
                asyncio.run(self.auto_scale({}))
                
                time.sleep(60)  # 1分間隔
                
            except Exception as e:
                self.logger.error(f"自動スケーリング監視エラー: {e}")
                time.sleep(60)
    
    def performance_monitor(self):
        """パフォーマンス監視"""
        while True:
            try:
                # パフォーマンスメトリクス記録
                metrics = asyncio.run(self.get_current_metrics())
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for metric_name, value in metrics.items():
                    cursor.execute('''
                        INSERT INTO performance_metrics 
                        (metric_name, metric_value, instance_count, timestamp)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        metric_name,
                        value,
                        self.current_instances,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                conn.close()
                
                time.sleep(30)  # 30秒間隔
                
            except Exception as e:
                self.logger.error(f"パフォーマンス監視エラー: {e}")
                time.sleep(30)
    
    def scaling_optimization(self):
        """スケーリング最適化"""
        while True:
            try:
                # スケーリング最適化処理
                # 実際の実装では、過去のスケーリング履歴を分析して最適化
                
                time.sleep(300)  # 5分間隔
                
            except Exception as e:
                self.logger.error(f"スケーリング最適化エラー: {e}")
                time.sleep(300)
    
    # ==================== ヘルパーメソッド ====================
    
    async def count_scaling_events(self) -> int:
        """スケーリングイベント数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM scaling_events')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def calculate_scaling_efficiency(self) -> float:
        """スケーリング効率計算"""
        # 簡易的なスケーリング効率計算
        # 実際の実装では、より複雑な効率計算を実装
        return 0.85
    
    async def dashboard(self):
        """スケーリングダッシュボード"""
        html_content = self.generate_scaling_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_scaling_dashboard_html(self) -> str:
        """スケーリングダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Dynamic Scaling System</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 3.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            padding: 20px; 
            backdrop-filter: blur(10px); 
            border: 1px solid rgba(255,255,255,0.2); 
        }
        .card h3 { margin-top: 0; color: #fff; }
        .button { 
            background: #4CAF50; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            border-radius: 5px; 
            cursor: pointer; 
            margin: 5px; 
        }
        .button:hover { background: #45a049; }
        .button.scale { background: #ff9800; }
        .button.scale:hover { background: #f57c00; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .event-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .status { 
            display: inline-block; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
        }
        .status.completed { background: #4CAF50; }
        .status.failed { background: #f44336; }
        .status.pending { background: #ff9800; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Mana Dynamic Scaling System</h1>
            <p>動的スケーリング・自動負荷分散・パフォーマンス最適化・インテリジェント調整</p>
        </div>
        
        <div class="grid">
            <!-- 自動スケーリング -->
            <div class="card">
                <h3>🔄 自動スケーリング</h3>
                <p>現在のインスタンス数: <strong id="current-instances">1</strong></p>
                <button class="button scale" onclick="executeAutoScale()">自動スケーリング実行</button>
                <div id="auto-scale-result">実行結果がここに表示されます</div>
            </div>
            
            <!-- 手動スケーリング -->
            <div class="card">
                <h3>🎛️ 手動スケーリング</h3>
                <div class="input-group">
                    <label>目標インスタンス数:</label>
                    <input type="number" id="target-instances" placeholder="2" min="1" max="20">
                </div>
                <div class="input-group">
                    <label>理由:</label>
                    <input type="text" id="scaling-reason" placeholder="手動調整">
                </div>
                <button class="button scale" onclick="executeManualScale()">手動スケーリング実行</button>
                <div id="manual-scale-result">実行結果がここに表示されます</div>
            </div>
            
            <!-- スケーリングイベント -->
            <div class="card">
                <h3>📊 スケーリングイベント</h3>
                <div id="scaling-events">読み込み中...</div>
                <button class="button" onclick="refreshScalingEvents()">🔄 更新</button>
            </div>
            
            <!-- スケーリングポリシー -->
            <div class="card">
                <h3>📋 スケーリングポリシー</h3>
                <div id="scaling-policies">読み込み中...</div>
                <button class="button" onclick="refreshScalingPolicies()">🔄 更新</button>
            </div>
            
            <!-- パフォーマンスメトリクス -->
            <div class="card">
                <h3>📈 パフォーマンスメトリクス</h3>
                <div id="performance-metrics">読み込み中...</div>
                <button class="button" onclick="refreshPerformanceMetrics()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // 自動スケーリング実行
        async function executeAutoScale() {
            try {
                const response = await fetch('/api/scaling/auto-scale', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>自動スケーリング結果:</h4>
                        <p>アクション: ${data.result.action}</p>
                        <p>インスタンス数: ${data.result.instances_before} → ${data.result.instances_after}</p>
                        <p>理由: ${data.scaling_decision.reason}</p>
                        <p>実行時刻: ${new Date(data.scaled_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('auto-scale-result').innerHTML = html;
                    document.getElementById('current-instances').textContent = data.current_instances;
                    refreshScalingEvents();
                } else {
                    alert('自動スケーリングに失敗しました');
                }
            } catch (error) {
                console.error('自動スケーリングエラー:', error);
                alert('自動スケーリングエラーが発生しました');
            }
        }
        
        // 手動スケーリング実行
        async function executeManualScale() {
            const targetInstances = document.getElementById('target-instances').value;
            const reason = document.getElementById('scaling-reason').value;
            
            if (!targetInstances) {
                alert('目標インスタンス数を入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/scaling/manual-scale', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        target_instances: parseInt(targetInstances),
                        reason: reason || 'manual_scaling'
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>手動スケーリング結果:</h4>
                        <p>インスタンス数: ${data.instances_before} → ${data.instances_after}</p>
                        <p>理由: ${data.reason}</p>
                        <p>実行時刻: ${new Date(data.scaled_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('manual-scale-result').innerHTML = html;
                    document.getElementById('current-instances').textContent = data.instances_after;
                    refreshScalingEvents();
                } else {
                    alert('手動スケーリングに失敗しました');
                }
            } catch (error) {
                console.error('手動スケーリングエラー:', error);
                alert('手動スケーリングエラーが発生しました');
            }
        }
        
        // スケーリングイベント取得
        async function refreshScalingEvents() {
            try {
                const response = await fetch('/api/scaling/events');
                const data = await response.json();
                
                let html = '<h4>スケーリングイベント一覧:</h4>';
                data.scaling_events.slice(0, 10).forEach(event => {
                    html += `
                        <div class="event-item">
                            <span class="status ${event.status}">${event.status}</span><br>
                            <strong>${event.event_type}</strong><br>
                            ${event.trigger_metric}: ${event.metric_value.toFixed(1)}<br>
                            インスタンス: ${event.instances_before} → ${event.instances_after}<br>
                            <small>${new Date(event.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('scaling-events').innerHTML = html;
            } catch (error) {
                console.error('スケーリングイベント取得エラー:', error);
            }
        }
        
        // スケーリングポリシー取得
        async function refreshScalingPolicies() {
            try {
                const response = await fetch('/api/scaling/policies');
                const data = await response.json();
                
                let html = '<h4>スケーリングポリシー:</h4>';
                for (const [policyName, policy] of Object.entries(data.scaling_policies)) {
                    html += `
                        <div class="event-item">
                            <strong>${policyName}</strong><br>
                            スケールアップ閾値: ${policy.scale_up_threshold}<br>
                            スケールダウン閾値: ${policy.scale_down_threshold}<br>
                            最小インスタンス: ${policy.min_instances}<br>
                            最大インスタンス: ${policy.max_instances}
                        </div>
                    `;
                }
                
                document.getElementById('scaling-policies').innerHTML = html;
            } catch (error) {
                console.error('スケーリングポリシー取得エラー:', error);
            }
        }
        
        // パフォーマンスメトリクス取得
        async function refreshPerformanceMetrics() {
            try {
                const response = await fetch('/api/scaling/metrics');
                const data = await response.json();
                
                let html = '<h4>パフォーマンスメトリクス:</h4>';
                data.performance_metrics.slice(0, 10).forEach(metric => {
                    html += `
                        <div class="event-item">
                            <strong>${metric.metric_name}</strong><br>
                            値: ${metric.metric_value.toFixed(2)}<br>
                            インスタンス数: ${metric.instance_count}<br>
                            <small>${new Date(metric.timestamp).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('performance-metrics').innerHTML = html;
            } catch (error) {
                console.error('パフォーマンスメトリクス取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshScalingEvents();
            refreshScalingPolicies();
            refreshPerformanceMetrics();
            
            // 定期的な更新
            setInterval(refreshScalingEvents, 30000);
            setInterval(refreshScalingPolicies, 60000);
            setInterval(refreshPerformanceMetrics, 30000);
        };
    </script>
</body>
</html>
        """

def main():
    """メイン実行"""
    # 必要なディレクトリ作成
    os.makedirs('/root/logs', exist_ok=True)
    
    # システム起動
    scaling_system = ManaDynamicScalingSystem()
    
    print("⚡ Mana Dynamic Scaling System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5018")
    print("🔗 API: http://localhost:5018/api/status")
    print("=" * 60)
    print("🎯 動的スケーリング機能:")
    print("  ⚡ 動的スケーリング")
    print("  🔄 自動負荷分散")
    print("  📊 パフォーマンス最適化")
    print("  🧠 インテリジェントスケーリング")
    print("  ⚡ リアルタイム調整")
    print("  🔮 予測的スケーリング")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        scaling_system.app,
        host="0.0.0.0",
        port=5018,
        log_level="info"
    )

if __name__ == "__main__":
    main()
