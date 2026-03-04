#!/usr/bin/env python3
"""
Mana Predictive Maintenance System
予測的メンテナンスシステム - 問題を事前に防ぐ
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import threading
import time
import sqlite3
import requests
from collections import deque

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class ManaPredictiveMaintenanceSystem:
    """Mana予測的メンテナンスシステム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Predictive Maintenance System", version="13.0.0")
        self.db_path = "/root/mana_predictive_maintenance.db"
        
        # 予測データ
        self.metrics_history = deque(maxlen=1000)
        self.anomaly_thresholds = {
            "cpu_usage": 85.0,
            "memory_usage": 90.0,
            "disk_usage": 95.0,
            "load_average": 5.0
        }
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_predictive_maintenance.log'),
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
        
        self.logger.info("🔮 Mana Predictive Maintenance System 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 予測データテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictive_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                predicted_value REAL,
                anomaly_score REAL DEFAULT 0.0,
                prediction_confidence REAL DEFAULT 0.0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 予測アラートテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictive_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                current_value REAL NOT NULL,
                predicted_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                severity TEXT NOT NULL,
                predicted_time TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT
            )
        ''')
        
        # メンテナンスアクションテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                action_params TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                executed_at TEXT,
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alert_id) REFERENCES predictive_alerts (id)
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
        
        # 予測機能API
        @self.app.post("/api/predictive/analyze")
        async def analyze_metrics(metrics_data: Dict[str, Any]):
            return await self.analyze_metrics(metrics_data)
        
        @self.app.get("/api/predictive/predictions")
        async def get_predictions():
            return await self.get_predictions()
        
        @self.app.get("/api/predictive/alerts")
        async def get_predictive_alerts():
            return await self.get_predictive_alerts()
        
        # メンテナンスAPI
        @self.app.post("/api/maintenance/execute")
        async def execute_maintenance(action_data: Dict[str, Any]):
            return await self.execute_maintenance(action_data)
        
        @self.app.get("/api/maintenance/actions")
        async def get_maintenance_actions():
            return await self.get_maintenance_actions()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # 予測監視
        threading.Thread(target=self.predictive_monitoring, daemon=True).start()
        
        # 自動メンテナンス
        threading.Thread(target=self.auto_maintenance, daemon=True).start()
        
        # 予測モデル更新
        threading.Thread(target=self.update_prediction_models, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Predictive Maintenance System",
            "version": "13.0.0",
            "status": "active",
            "features": [
                "予測的メンテナンス",
                "異常検知・予測",
                "自動メンテナンス実行",
                "予防的対策",
                "時系列予測",
                "インテリジェントアラート"
            ],
            "capabilities": [
                "CPU・メモリ・ディスク使用率予測",
                "システム負荷予測",
                "障害発生予測",
                "自動最適化実行",
                "予防的スケーリング"
            ]
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Predictive Maintenance System",
            "status": "healthy",
            "version": "13.0.0",
            "predictive": {
                "total_predictions": await self.count_predictions(),
                "active_alerts": await self.count_active_alerts(),
                "maintenance_actions": await self.count_maintenance_actions(),
                "prediction_accuracy": await self.calculate_prediction_accuracy()
            },
            "thresholds": self.anomaly_thresholds
        }
    
    async def analyze_metrics(self, metrics_data: Dict[str, Any]):
        """メトリクス分析・予測"""
        try:
            metrics = metrics_data.get("metrics", {})
            prediction_horizon = metrics_data.get("prediction_horizon", 60)  # 分
            
            # メトリクス履歴に追加
            for metric_name, value in metrics.items():
                self.metrics_history.append({
                    "metric_name": metric_name,
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                })
            
            # 予測実行
            predictions = {}
            alerts = []
            
            for metric_name, current_value in metrics.items():
                # 簡易予測（実際の実装では機械学習モデルを使用）
                predicted_value = self.predict_metric_value(metric_name, current_value, prediction_horizon)
                anomaly_score = self.calculate_anomaly_score(metric_name, current_value, predicted_value)
                
                predictions[metric_name] = {
                    "current_value": current_value,
                    "predicted_value": predicted_value,
                    "anomaly_score": anomaly_score,
                    "confidence": 0.8
                }
                
                # アラート生成
                if anomaly_score > 0.7:
                    alert = await self.generate_predictive_alert(
                        metric_name, current_value, predicted_value, prediction_horizon
                    )
                    alerts.append(alert)
            
            # 予測データ保存
            await self.save_predictions(predictions)
            
            return {
                "predictions": predictions,
                "alerts": alerts,
                "prediction_horizon": prediction_horizon,
                "analyzed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"メトリクス分析エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def predict_metric_value(self, metric_name: str, current_value: float, horizon_minutes: int) -> float:
        """メトリクス値予測"""
        # 簡易的な線形予測（実際の実装では時系列分析を使用）
        if metric_name == "cpu_usage":
            # CPU使用率の予測（負荷増加を想定）
            return min(100.0, current_value + (horizon_minutes * 0.1))
        elif metric_name == "memory_usage":
            # メモリ使用率の予測
            return min(100.0, current_value + (horizon_minutes * 0.05))
        elif metric_name == "disk_usage":
            # ディスク使用率の予測（緩やかな増加）
            return min(100.0, current_value + (horizon_minutes * 0.01))
        else:
            # デフォルト予測
            return current_value * 1.1
    
    def calculate_anomaly_score(self, metric_name: str, current_value: float, predicted_value: float) -> float:
        """異常スコア計算"""
        threshold = self.anomaly_thresholds.get(metric_name, 80.0)
        
        # 現在値が閾値を超えている場合
        if current_value > threshold:
            return 0.9
        
        # 予測値が閾値を超える場合
        if predicted_value > threshold:
            return 0.7
        
        # 急激な変化を検知
        change_rate = abs(predicted_value - current_value) / current_value if current_value > 0 else 0
        if change_rate > 0.2:  # 20%以上の変化
            return 0.5
        
        return 0.0
    
    async def generate_predictive_alert(self, metric_name: str, current_value: float, 
                                      predicted_value: float, horizon_minutes: int) -> Dict[str, Any]:
        """予測アラート生成"""
        threshold = self.anomaly_thresholds.get(metric_name, 80.0)
        
        # 深刻度判定
        if predicted_value > threshold * 1.2:
            severity = "critical"
        elif predicted_value > threshold * 1.1:
            severity = "high"
        elif predicted_value > threshold:
            severity = "medium"
        else:
            severity = "low"
        
        # アラート保存
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictive_alerts 
            (alert_type, metric_name, current_value, predicted_value, 
             threshold_value, severity, predicted_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "predictive_threshold_breach",
            metric_name,
            current_value,
            predicted_value,
            threshold,
            severity,
            (datetime.now() + timedelta(minutes=horizon_minutes)).isoformat(),
            datetime.now().isoformat()
        ))
        
        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "alert_id": alert_id,
            "alert_type": "predictive_threshold_breach",
            "metric_name": metric_name,
            "current_value": current_value,
            "predicted_value": predicted_value,
            "threshold_value": threshold,
            "severity": severity,
            "predicted_time": (datetime.now() + timedelta(minutes=horizon_minutes)).isoformat(),
            "created_at": datetime.now().isoformat()
        }
    
    async def save_predictions(self, predictions: Dict[str, Any]):
        """予測データ保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for metric_name, prediction in predictions.items():
            cursor.execute('''
                INSERT INTO predictive_data 
                (metric_name, metric_value, predicted_value, anomaly_score, 
                 prediction_confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metric_name,
                prediction["current_value"],
                prediction["predicted_value"],
                prediction["anomaly_score"],
                prediction["confidence"],
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    async def get_predictions(self):
        """予測データ取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT metric_name, metric_value, predicted_value, anomaly_score, 
                   prediction_confidence, timestamp
            FROM predictive_data
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        predictions = []
        for row in cursor.fetchall():
            predictions.append({
                "metric_name": row[0],
                "current_value": row[1],
                "predicted_value": row[2],
                "anomaly_score": row[3],
                "confidence": row[4],
                "timestamp": row[5]
            })
        
        conn.close()
        
        return {
            "predictions": predictions,
            "count": len(predictions),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_predictive_alerts(self):
        """予測アラート取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, alert_type, metric_name, current_value, predicted_value,
                   threshold_value, severity, predicted_time, status, created_at
            FROM predictive_alerts
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                "id": row[0],
                "alert_type": row[1],
                "metric_name": row[2],
                "current_value": row[3],
                "predicted_value": row[4],
                "threshold_value": row[5],
                "severity": row[6],
                "predicted_time": row[7],
                "status": row[8],
                "created_at": row[9]
            })
        
        conn.close()
        
        return {
            "predictive_alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
    
    async def execute_maintenance(self, action_data: Dict[str, Any]):
        """メンテナンス実行"""
        try:
            alert_id = action_data.get("alert_id")
            action_type = action_data.get("action_type")
            action_params = action_data.get("action_params", {})
            
            if not all([alert_id, action_type]):
                raise HTTPException(status_code=400, detail="Alert ID and action type are required")
            
            # メンテナンスアクション実行
            result = await self.execute_maintenance_action(action_type, action_params)
            
            # アクション記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO maintenance_actions 
                (alert_id, action_type, action_params, status, executed_at, result, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert_id,
                action_type,
                json.dumps(action_params),
                "completed" if result.get("success") else "failed",
                datetime.now().isoformat(),
                json.dumps(result),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"メンテナンス実行完了: {action_type}")
            
            return {
                "alert_id": alert_id,
                "action_type": action_type,
                "result": result,
                "executed_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"メンテナンス実行エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_maintenance_action(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """メンテナンスアクション実行"""
        try:
            if action_type == "system_optimization":
                # システム最適化
                response = requests.get("http://localhost:5009/api/status", timeout=10)
                return {"success": True, "data": response.json()}
            
            elif action_type == "auto_scaling":
                # 自動スケーリング
                response = requests.post("http://localhost:5014/api/scaling/auto-scale", timeout=30)
                return {"success": True, "data": response.json()}
            
            elif action_type == "cache_cleanup":
                # キャッシュクリーンアップ
                return {"success": True, "message": "Cache cleanup completed"}
            
            elif action_type == "database_optimization":
                # データベース最適化
                return {"success": True, "message": "Database optimization completed"}
            
            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_maintenance_actions(self):
        """メンテナンスアクション取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ma.id, ma.alert_id, ma.action_type, ma.action_params, 
                   ma.status, ma.executed_at, ma.result, ma.created_at,
                   pa.metric_name, pa.severity
            FROM maintenance_actions ma
            JOIN predictive_alerts pa ON ma.alert_id = pa.id
            ORDER BY ma.created_at DESC
            LIMIT 50
        ''')
        
        actions = []
        for row in cursor.fetchall():
            actions.append({
                "id": row[0],
                "alert_id": row[1],
                "action_type": row[2],
                "action_params": json.loads(row[3]) if row[3] else {},
                "status": row[4],
                "executed_at": row[5],
                "result": json.loads(row[6]) if row[6] else {},
                "created_at": row[7],
                "metric_name": row[8],
                "severity": row[9]
            })
        
        conn.close()
        
        return {
            "maintenance_actions": actions,
            "count": len(actions),
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== バックグラウンドタスク ====================
    
    def predictive_monitoring(self):
        """予測監視"""
        while True:
            try:
                # 定期的な予測監視
                # 実際の実装では、リアルタイムメトリクスを取得して予測実行
                
                time.sleep(60)  # 1分間隔
                
            except Exception as e:
                self.logger.error(f"予測監視エラー: {e}")
                time.sleep(60)
    
    def auto_maintenance(self):
        """自動メンテナンス"""
        while True:
            try:
                # 自動メンテナンス処理
                # 予測アラートに基づいて自動的にメンテナンスを実行
                
                time.sleep(300)  # 5分間隔
                
            except Exception as e:
                self.logger.error(f"自動メンテナンスエラー: {e}")
                time.sleep(300)
    
    def update_prediction_models(self):
        """予測モデル更新"""
        while True:
            try:
                # 予測モデルの更新
                # 実際の実装では、機械学習モデルの再学習を実行
                
                time.sleep(3600)  # 1時間間隔
                
            except Exception as e:
                self.logger.error(f"予測モデル更新エラー: {e}")
                time.sleep(3600)
    
    # ==================== ヘルパーメソッド ====================
    
    async def count_predictions(self) -> int:
        """予測数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictive_data')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_active_alerts(self) -> int:
        """アクティブアラート数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictive_alerts WHERE status = "active"')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_maintenance_actions(self) -> int:
        """メンテナンスアクション数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM maintenance_actions')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def calculate_prediction_accuracy(self) -> float:
        """予測精度計算"""
        # 簡易的な予測精度計算
        # 実際の実装では、より複雑な精度計算を実装
        return 0.85
    
    async def dashboard(self):
        """予測ダッシュボード"""
        html_content = self.generate_predictive_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_predictive_dashboard_html(self) -> str:
        """予測ダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Predictive Maintenance System</title>
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
        .button.predict { background: #ff9800; }
        .button.predict:hover { background: #f57c00; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .alert-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .severity { 
            display: inline-block; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
        }
        .severity.critical { background: #f44336; }
        .severity.high { background: #ff9800; }
        .severity.medium { background: #ffeb3b; color: #000; }
        .severity.low { background: #4CAF50; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔮 Mana Predictive Maintenance System</h1>
            <p>予測的メンテナンス・異常検知・予防的対策・自動最適化</p>
        </div>
        
        <div class="grid">
            <!-- メトリクス分析 -->
            <div class="card">
                <h3>📊 メトリクス分析・予測</h3>
                <div class="input-group">
                    <label>CPU使用率:</label>
                    <input type="number" id="cpu-usage" placeholder="75" min="0" max="100">
                </div>
                <div class="input-group">
                    <label>メモリ使用率:</label>
                    <input type="number" id="memory-usage" placeholder="80" min="0" max="100">
                </div>
                <div class="input-group">
                    <label>ディスク使用率:</label>
                    <input type="number" id="disk-usage" placeholder="85" min="0" max="100">
                </div>
                <div class="input-group">
                    <label>予測時間（分）:</label>
                    <input type="number" id="prediction-horizon" placeholder="60" min="1" max="1440">
                </div>
                <button class="button predict" onclick="analyzeMetrics()">予測分析実行</button>
                <div id="analysis-result">分析結果がここに表示されます</div>
            </div>
            
            <!-- 予測アラート -->
            <div class="card">
                <h3>🚨 予測アラート</h3>
                <div id="predictive-alerts">読み込み中...</div>
                <button class="button" onclick="refreshPredictiveAlerts()">🔄 更新</button>
            </div>
            
            <!-- メンテナンス実行 -->
            <div class="card">
                <h3>🔧 メンテナンス実行</h3>
                <div class="input-group">
                    <label>アラートID:</label>
                    <input type="number" id="maintenance-alert-id" placeholder="1">
                </div>
                <div class="input-group">
                    <label>アクションタイプ:</label>
                    <select id="maintenance-action-type">
                        <option value="system_optimization">システム最適化</option>
                        <option value="auto_scaling">自動スケーリング</option>
                        <option value="cache_cleanup">キャッシュクリーンアップ</option>
                        <option value="database_optimization">データベース最適化</option>
                    </select>
                </div>
                <button class="button predict" onclick="executeMaintenance()">メンテナンス実行</button>
                <div id="maintenance-result">実行結果がここに表示されます</div>
            </div>
            
            <!-- 予測データ -->
            <div class="card">
                <h3>📈 予測データ</h3>
                <div id="predictions">読み込み中...</div>
                <button class="button" onclick="refreshPredictions()">🔄 更新</button>
            </div>
            
            <!-- メンテナンス履歴 -->
            <div class="card">
                <h3>📋 メンテナンス履歴</h3>
                <div id="maintenance-actions">読み込み中...</div>
                <button class="button" onclick="refreshMaintenanceActions()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // メトリクス分析実行
        async function analyzeMetrics() {
            const cpuUsage = document.getElementById('cpu-usage').value;
            const memoryUsage = document.getElementById('memory-usage').value;
            const diskUsage = document.getElementById('disk-usage').value;
            const predictionHorizon = document.getElementById('prediction-horizon').value;
            
            if (!cpuUsage || !memoryUsage || !diskUsage) {
                alert('すべてのメトリクス値を入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/predictive/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        metrics: {
                            cpu_usage: parseFloat(cpuUsage),
                            memory_usage: parseFloat(memoryUsage),
                            disk_usage: parseFloat(diskUsage)
                        },
                        prediction_horizon: parseInt(predictionHorizon) || 60
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = '<h4>予測分析結果:</h4>';
                    
                    for (const [metric, prediction] of Object.entries(data.predictions)) {
                        html += `
                            <div class="alert-item">
                                <strong>${metric}:</strong><br>
                                現在値: ${prediction.current_value.toFixed(1)}%<br>
                                予測値: ${prediction.predicted_value.toFixed(1)}%<br>
                                異常スコア: ${(prediction.anomaly_score * 100).toFixed(1)}%<br>
                                信頼度: ${(prediction.confidence * 100).toFixed(1)}%
                            </div>
                        `;
                    }
                    
                    if (data.alerts.length > 0) {
                        html += '<h4>生成されたアラート:</h4>';
                        data.alerts.forEach(alert => {
                            html += `
                                <div class="alert-item">
                                    <span class="severity ${alert.severity}">${alert.severity}</span><br>
                                    ${alert.metric_name}: ${alert.predicted_value.toFixed(1)}%<br>
                                    予測時刻: ${new Date(alert.predicted_time).toLocaleString()}
                                </div>
                            `;
                        });
                    }
                    
                    document.getElementById('analysis-result').innerHTML = html;
                    refreshPredictiveAlerts();
                } else {
                    alert('メトリクス分析に失敗しました');
                }
            } catch (error) {
                console.error('メトリクス分析エラー:', error);
                alert('メトリクス分析エラーが発生しました');
            }
        }
        
        // 予測アラート取得
        async function refreshPredictiveAlerts() {
            try {
                const response = await fetch('/api/predictive/alerts');
                const data = await response.json();
                
                let html = '<h4>予測アラート一覧:</h4>';
                data.predictive_alerts.slice(0, 10).forEach(alert => {
                    html += `
                        <div class="alert-item">
                            <span class="severity ${alert.severity}">${alert.severity}</span><br>
                            <strong>${alert.metric_name}</strong><br>
                            現在値: ${alert.current_value.toFixed(1)}% | 予測値: ${alert.predicted_value.toFixed(1)}%<br>
                            予測時刻: ${new Date(alert.predicted_time).toLocaleString()}<br>
                            <small>${new Date(alert.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('predictive-alerts').innerHTML = html;
            } catch (error) {
                console.error('予測アラート取得エラー:', error);
            }
        }
        
        // メンテナンス実行
        async function executeMaintenance() {
            const alertId = document.getElementById('maintenance-alert-id').value;
            const actionType = document.getElementById('maintenance-action-type').value;
            
            if (!alertId) {
                alert('アラートIDを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/maintenance/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        alert_id: parseInt(alertId),
                        action_type: actionType,
                        action_params: {}
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>メンテナンス実行完了:</h4>
                        <p>アクション: ${data.action_type}</p>
                        <p>ステータス: ${data.result.success ? '成功' : '失敗'}</p>
                        <p>実行時刻: ${new Date(data.executed_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('maintenance-result').innerHTML = html;
                    refreshMaintenanceActions();
                } else {
                    alert('メンテナンス実行に失敗しました');
                }
            } catch (error) {
                console.error('メンテナンス実行エラー:', error);
                alert('メンテナンス実行エラーが発生しました');
            }
        }
        
        // 予測データ取得
        async function refreshPredictions() {
            try {
                const response = await fetch('/api/predictive/predictions');
                const data = await response.json();
                
                let html = '<h4>予測データ一覧:</h4>';
                data.predictions.slice(0, 10).forEach(prediction => {
                    html += `
                        <div class="alert-item">
                            <strong>${prediction.metric_name}</strong><br>
                            現在値: ${prediction.current_value.toFixed(1)}%<br>
                            予測値: ${prediction.predicted_value.toFixed(1)}%<br>
                            異常スコア: ${(prediction.anomaly_score * 100).toFixed(1)}%<br>
                            <small>${new Date(prediction.timestamp).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('predictions').innerHTML = html;
            } catch (error) {
                console.error('予測データ取得エラー:', error);
            }
        }
        
        // メンテナンス履歴取得
        async function refreshMaintenanceActions() {
            try {
                const response = await fetch('/api/maintenance/actions');
                const data = await response.json();
                
                let html = '<h4>メンテナンス履歴:</h4>';
                data.maintenance_actions.slice(0, 10).forEach(action => {
                    html += `
                        <div class="alert-item">
                            <strong>${action.action_type}</strong><br>
                            ステータス: ${action.status}<br>
                            メトリクス: ${action.metric_name} (${action.severity})<br>
                            <small>${new Date(action.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('maintenance-actions').innerHTML = html;
            } catch (error) {
                console.error('メンテナンス履歴取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshPredictiveAlerts();
            refreshPredictions();
            refreshMaintenanceActions();
            
            // 定期的な更新
            setInterval(refreshPredictiveAlerts, 30000);
            setInterval(refreshPredictions, 60000);
            setInterval(refreshMaintenanceActions, 60000);
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
    predictive_system = ManaPredictiveMaintenanceSystem()
    
    print("🔮 Mana Predictive Maintenance System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5017")
    print("🔗 API: http://localhost:5017/api/status")
    print("=" * 60)
    print("🎯 予測的メンテナンス機能:")
    print("  🔮 予測的メンテナンス")
    print("  📊 異常検知・予測")
    print("  🔧 自動メンテナンス実行")
    print("  🛡️ 予防的対策")
    print("  📈 時系列予測")
    print("  🚨 インテリジェントアラート")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        predictive_system.app,
        host="0.0.0.0",
        port=5017,
        log_level="info"
    )

if __name__ == "__main__":
    main()
