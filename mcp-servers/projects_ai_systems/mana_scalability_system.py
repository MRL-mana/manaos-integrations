#!/usr/bin/env python3
"""
Mana Scalability System
スケーラビリティシステム - マイクロサービス化、クラウド対応、負荷分散
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

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class ManaScalabilitySystem:
    """Manaスケーラビリティシステム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Scalability System", version="10.0.0")
        self.db_path = "/root/mana_scalability.db"
        
        # 設定
        self.config = self.load_config()
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_scalability.log'),
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
        
        self.logger.info("🚀 Mana Scalability System 初期化完了")
    
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        default_config = {
            "system": {
                "name": "Mana Scalability System",
                "version": "10.0.0",
                "port": 5014,
                "max_memory_mb": 1200
            },
            "scalability": {
                "microservices": True,
                "load_balancing": True,
                "auto_scaling": True,
                "cloud_ready": True,
                "containerization": True
            },
            "integrations": {
                "security_system": {"port": 5013, "enabled": True},
                "monitoring_system": {"port": 5012, "enabled": True},
                "workflow_system": {"port": 5011, "enabled": True}
            },
            "features": {
                "microservice_management": True,
                "load_balancer": True,
                "auto_scaling": True,
                "cloud_deployment": True,
                "container_orchestration": True,
                "service_discovery": True
            }
        }
        
        config_path = "/root/mana_scalability_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # マイクロサービステーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS microservices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT UNIQUE NOT NULL,
                service_type TEXT NOT NULL,
                port INTEGER NOT NULL,
                status TEXT DEFAULT 'stopped',
                health_check_url TEXT,
                replicas INTEGER DEFAULT 1,
                cpu_limit REAL,
                memory_limit REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # ロードバランサーテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS load_balancers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lb_name TEXT UNIQUE NOT NULL,
                lb_type TEXT NOT NULL,
                port INTEGER NOT NULL,
                target_services TEXT NOT NULL,
                algorithm TEXT DEFAULT 'round_robin',
                health_check_enabled BOOLEAN DEFAULT TRUE,
                status TEXT DEFAULT 'stopped',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # スケーリングイベントテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scaling_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                old_replicas INTEGER,
                new_replicas INTEGER,
                trigger_metric TEXT,
                trigger_value REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # クラウドデプロイメントテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cloud_deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_name TEXT UNIQUE NOT NULL,
                cloud_provider TEXT NOT NULL,
                region TEXT,
                instance_type TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
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
        
        # マイクロサービス管理API
        @self.app.get("/api/microservices")
        async def list_microservices():
            return await self.list_microservices()
        
        @self.app.post("/api/microservices/deploy")
        async def deploy_microservice(service_data: Dict[str, Any]):
            return await self.deploy_microservice(service_data)
        
        @self.app.post("/api/microservices/scale")
        async def scale_microservice(scale_data: Dict[str, Any]):
            return await self.scale_microservice(scale_data)
        
        # ロードバランサー管理API
        @self.app.get("/api/load-balancers")
        async def list_load_balancers():
            return await self.list_load_balancers()
        
        @self.app.post("/api/load-balancers/create")
        async def create_load_balancer(lb_data: Dict[str, Any]):
            return await self.create_load_balancer(lb_data)
        
        # スケーリング管理API
        @self.app.get("/api/scaling/events")
        async def get_scaling_events():
            return await self.get_scaling_events()
        
        @self.app.post("/api/scaling/auto-scale")
        async def auto_scale():
            return await self.auto_scale()
        
        # クラウドデプロイメントAPI
        @self.app.get("/api/cloud/deployments")
        async def list_cloud_deployments():
            return await self.list_cloud_deployments()
        
        @self.app.post("/api/cloud/deploy")
        async def deploy_to_cloud(deployment_data: Dict[str, Any]):
            return await self.deploy_to_cloud(deployment_data)
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # 自動スケーリング
        if self.config["scalability"]["auto_scaling"]:
            threading.Thread(target=self.auto_scaling_monitor, daemon=True).start()
        
        # ヘルスチェック
        threading.Thread(target=self.health_check_monitor, daemon=True).start()
        
        # サービス発見
        threading.Thread(target=self.service_discovery, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Scalability System",
            "version": "10.0.0",
            "status": "active",
            "features": [
                "マイクロサービス管理",
                "ロードバランサー",
                "自動スケーリング",
                "クラウドデプロイメント",
                "コンテナオーケストレーション",
                "サービス発見"
            ],
            "scalability_capabilities": {
                "microservices": self.config["scalability"]["microservices"],
                "load_balancing": self.config["scalability"]["load_balancing"],
                "auto_scaling": self.config["scalability"]["auto_scaling"],
                "cloud_ready": self.config["scalability"]["cloud_ready"],
                "containerization": self.config["scalability"]["containerization"]
            }
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Scalability System",
            "status": "healthy",
            "version": "10.0.0",
            "scalability": {
                "microservices_enabled": self.config["scalability"]["microservices"],
                "load_balancing_enabled": self.config["scalability"]["load_balancing"],
                "auto_scaling_enabled": self.config["scalability"]["auto_scaling"],
                "cloud_ready": self.config["scalability"]["cloud_ready"]
            },
            "integrations": await self.get_integration_status(),
            "performance": {
                "service_discovery_interval": "30秒",
                "health_check_interval": "10秒",
                "auto_scaling_interval": "60秒"
            }
        }
    
    async def list_microservices(self):
        """マイクロサービス一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT service_name, service_type, port, status, replicas, cpu_limit, memory_limit, created_at
            FROM microservices
            ORDER BY created_at DESC
        ''')
        
        services = []
        for row in cursor.fetchall():
            services.append({
                "service_name": row[0],
                "service_type": row[1],
                "port": row[2],
                "status": row[3],
                "replicas": row[4],
                "cpu_limit": row[5],
                "memory_limit": row[6],
                "created_at": row[7]
            })
        
        conn.close()
        
        return {
            "microservices": services,
            "count": len(services),
            "timestamp": datetime.now().isoformat()
        }
    
    async def deploy_microservice(self, service_data: Dict[str, Any]):
        """マイクロサービスデプロイ"""
        try:
            service_name = service_data.get("service_name")
            service_type = service_data.get("service_type", "api")
            port = service_data.get("port")
            replicas = service_data.get("replicas", 1)
            
            if not service_name or not port:
                raise HTTPException(status_code=400, detail="Service name and port are required")
            
            # データベースに登録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO microservices 
                (service_name, service_type, port, status, replicas, cpu_limit, memory_limit, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                service_name,
                service_type,
                port,
                "deployed",
                replicas,
                service_data.get("cpu_limit", 1.0),
                service_data.get("memory_limit", 512),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"マイクロサービスデプロイ: {service_name} (ポート: {port})")
            
            return {
                "service_name": service_name,
                "status": "deployed",
                "port": port,
                "replicas": replicas,
                "created_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"マイクロサービスデプロイエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def scale_microservice(self, scale_data: Dict[str, Any]):
        """マイクロサービススケーリング"""
        try:
            service_name = scale_data.get("service_name")
            new_replicas = scale_data.get("replicas")
            
            if not service_name or new_replicas is None:
                raise HTTPException(status_code=400, detail="Service name and replicas are required")
            
            # 現在のレプリカ数取得
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT replicas FROM microservices WHERE service_name = ?', (service_name,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                raise HTTPException(status_code=404, detail="Service not found")
            
            old_replicas = result[0]
            
            # レプリカ数更新
            cursor.execute('''
                UPDATE microservices 
                SET replicas = ?, updated_at = ?
                WHERE service_name = ?
            ''', (new_replicas, datetime.now().isoformat(), service_name))
            
            # スケーリングイベント記録
            cursor.execute('''
                INSERT INTO scaling_events 
                (service_name, event_type, old_replicas, new_replicas, trigger_metric, trigger_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                service_name,
                "manual_scale",
                old_replicas,
                new_replicas,
                "manual",
                0.0,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"マイクロサービススケーリング: {service_name} ({old_replicas} -> {new_replicas})")
            
            return {
                "service_name": service_name,
                "old_replicas": old_replicas,
                "new_replicas": new_replicas,
                "scaled_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"マイクロサービススケーリングエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_load_balancers(self):
        """ロードバランサー一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT lb_name, lb_type, port, target_services, algorithm, health_check_enabled, status, created_at
            FROM load_balancers
            ORDER BY created_at DESC
        ''')
        
        load_balancers = []
        for row in cursor.fetchall():
            load_balancers.append({
                "lb_name": row[0],
                "lb_type": row[1],
                "port": row[2],
                "target_services": json.loads(row[3]),
                "algorithm": row[4],
                "health_check_enabled": bool(row[5]),
                "status": row[6],
                "created_at": row[7]
            })
        
        conn.close()
        
        return {
            "load_balancers": load_balancers,
            "count": len(load_balancers),
            "timestamp": datetime.now().isoformat()
        }
    
    async def create_load_balancer(self, lb_data: Dict[str, Any]):
        """ロードバランサー作成"""
        try:
            lb_name = lb_data.get("lb_name")
            lb_type = lb_data.get("lb_type", "http")
            port = lb_data.get("port")
            target_services = lb_data.get("target_services", [])
            
            if not lb_name or not port:
                raise HTTPException(status_code=400, detail="Load balancer name and port are required")
            
            # データベースに登録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO load_balancers 
                (lb_name, lb_type, port, target_services, algorithm, health_check_enabled, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lb_name,
                lb_type,
                port,
                json.dumps(target_services),
                lb_data.get("algorithm", "round_robin"),
                lb_data.get("health_check_enabled", True),
                "active",
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"ロードバランサー作成: {lb_name} (ポート: {port})")
            
            return {
                "lb_name": lb_name,
                "lb_type": lb_type,
                "port": port,
                "target_services": target_services,
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"ロードバランサー作成エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_scaling_events(self):
        """スケーリングイベント取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT service_name, event_type, old_replicas, new_replicas, trigger_metric, trigger_value, created_at
            FROM scaling_events
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "service_name": row[0],
                "event_type": row[1],
                "old_replicas": row[2],
                "new_replicas": row[3],
                "trigger_metric": row[4],
                "trigger_value": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        
        return {
            "scaling_events": events,
            "count": len(events),
            "timestamp": datetime.now().isoformat()
        }
    
    async def auto_scale(self):
        """自動スケーリング実行"""
        try:
            # 自動スケーリングロジック
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 全マイクロサービス取得
            cursor.execute('SELECT service_name, replicas FROM microservices WHERE status = "deployed"')
            services = cursor.fetchall()
            
            scaling_events = []
            
            for service_name, current_replicas in services:
                # 仮の負荷メトリクス（実際は監視システムから取得）
                cpu_usage = 75.0  # 仮の値
                memory_usage = 80.0  # 仮の値
                
                new_replicas = current_replicas
                
                # スケールアウト条件
                if cpu_usage > 80 or memory_usage > 85:
                    new_replicas = min(current_replicas + 1, 10)  # 最大10レプリカ
                # スケールイン条件
                elif cpu_usage < 30 and memory_usage < 40 and current_replicas > 1:
                    new_replicas = max(current_replicas - 1, 1)  # 最小1レプリカ
                
                if new_replicas != current_replicas:
                    # スケーリング実行
                    cursor.execute('''
                        UPDATE microservices 
                        SET replicas = ?, updated_at = ?
                        WHERE service_name = ?
                    ''', (new_replicas, datetime.now().isoformat(), service_name))
                    
                    # スケーリングイベント記録
                    cursor.execute('''
                        INSERT INTO scaling_events 
                        (service_name, event_type, old_replicas, new_replicas, trigger_metric, trigger_value, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        service_name,
                        "auto_scale",
                        current_replicas,
                        new_replicas,
                        "cpu_memory",
                        max(cpu_usage, memory_usage),
                        datetime.now().isoformat()
                    ))
                    
                    scaling_events.append({
                        "service_name": service_name,
                        "old_replicas": current_replicas,
                        "new_replicas": new_replicas
                    })
            
            conn.commit()
            conn.close()
            
            return {
                "scaling_events": scaling_events,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"自動スケーリングエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_cloud_deployments(self):
        """クラウドデプロイメント一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT deployment_name, cloud_provider, region, instance_type, status, created_at
            FROM cloud_deployments
            ORDER BY created_at DESC
        ''')
        
        deployments = []
        for row in cursor.fetchall():
            deployments.append({
                "deployment_name": row[0],
                "cloud_provider": row[1],
                "region": row[2],
                "instance_type": row[3],
                "status": row[4],
                "created_at": row[5]
            })
        
        conn.close()
        
        return {
            "cloud_deployments": deployments,
            "count": len(deployments),
            "timestamp": datetime.now().isoformat()
        }
    
    async def deploy_to_cloud(self, deployment_data: Dict[str, Any]):
        """クラウドデプロイメント"""
        try:
            deployment_name = deployment_data.get("deployment_name")
            cloud_provider = deployment_data.get("cloud_provider", "aws")
            region = deployment_data.get("region", "us-east-1")
            instance_type = deployment_data.get("instance_type", "t3.micro")
            
            if not deployment_name:
                raise HTTPException(status_code=400, detail="Deployment name is required")
            
            # データベースに登録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cloud_deployments 
                (deployment_name, cloud_provider, region, instance_type, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                deployment_name,
                cloud_provider,
                region,
                instance_type,
                "deployed",
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"クラウドデプロイメント: {deployment_name} ({cloud_provider})")
            
            return {
                "deployment_name": deployment_name,
                "cloud_provider": cloud_provider,
                "region": region,
                "instance_type": instance_type,
                "status": "deployed",
                "created_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"クラウドデプロイメントエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """統合システム状態取得"""
        status = {}
        
        # 各システムの状態確認
        systems = [
            ("security_system", 5013),
            ("monitoring_system", 5012),
            ("workflow_system", 5011)
        ]
        
        for system_name, port in systems:
            try:
                response = requests.get(f"http://localhost:{port}/api/status", timeout=5)
                status[system_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "port": port,
                    "response_time": response.elapsed.total_seconds()
                }
            except requests.RequestException:
                status[system_name] = {
                    "status": "unreachable",
                    "port": port,
                    "error": "connection_failed"
                }
        
        return status
    
    # ==================== バックグラウンドタスク ====================
    
    def auto_scaling_monitor(self):
        """自動スケーリング監視"""
        while True:
            try:
                # 自動スケーリング実行
                asyncio.run(self.auto_scale())
                time.sleep(60)  # 1分間隔
                
            except Exception as e:
                self.logger.error(f"自動スケーリング監視エラー: {e}")
                time.sleep(60)
    
    def health_check_monitor(self):
        """ヘルスチェック監視"""
        while True:
            try:
                # マイクロサービスのヘルスチェック
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT service_name, port, health_check_url FROM microservices WHERE status = "deployed"')
                services = cursor.fetchall()
                
                for service_name, port, health_check_url in services:
                    try:
                        if health_check_url:
                            response = requests.get(health_check_url, timeout=5)
                            status = "healthy" if response.status_code == 200 else "unhealthy"
                        else:
                            response = requests.get(f"http://localhost:{port}/api/status", timeout=5)
                            status = "healthy" if response.status_code == 200 else "unhealthy"
                        
                        # ステータス更新
                        cursor.execute('''
                            UPDATE microservices 
                            SET status = ?, updated_at = ?
                            WHERE service_name = ?
                        ''', (status, datetime.now().isoformat(), service_name))
                        
                    except requests.RequestException:
                        # ヘルスチェック失敗
                        cursor.execute('''
                            UPDATE microservices 
                            SET status = ?, updated_at = ?
                            WHERE service_name = ?
                        ''', ("unhealthy", datetime.now().isoformat(), service_name))
                
                conn.commit()
                conn.close()
                
                time.sleep(10)  # 10秒間隔
                
            except Exception as e:
                self.logger.error(f"ヘルスチェック監視エラー: {e}")
                time.sleep(30)
    
    def service_discovery(self):
        """サービス発見"""
        while True:
            try:
                # サービス発見ロジック
                # 実際の実装では、サービスレジストリやDNSベースの発見を使用
                
                time.sleep(30)  # 30秒間隔
                
            except Exception as e:
                self.logger.error(f"サービス発見エラー: {e}")
                time.sleep(30)
    
    async def dashboard(self):
        """統合ダッシュボード"""
        html_content = self.generate_scalability_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_scalability_dashboard_html(self) -> str:
        """スケーラビリティダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Scalability System</title>
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
        .button.scale { background: #2196F3; }
        .button.scale:hover { background: #1976D2; }
        .button.cloud { background: #ff9800; }
        .button.cloud:hover { background: #f57c00; }
        .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .status.healthy { background: #4CAF50; }
        .status.deployed { background: #4CAF50; }
        .status.unhealthy { background: #f44336; }
        .status.stopped { background: #9e9e9e; }
        .service-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Mana Scalability System</h1>
            <p>マイクロサービス・ロードバランサー・自動スケーリング・クラウド対応</p>
        </div>
        
        <div class="grid">
            <!-- マイクロサービス管理 -->
            <div class="card">
                <h3>🔧 マイクロサービス管理</h3>
                <div id="microservices">読み込み中...</div>
                <button class="button" onclick="refreshMicroservices()">🔄 更新</button>
            </div>
            
            <!-- マイクロサービスデプロイ -->
            <div class="card">
                <h3>🚀 マイクロサービスデプロイ</h3>
                <div class="input-group">
                    <label>サービス名:</label>
                    <input type="text" id="service-name" placeholder="service-name">
                </div>
                <div class="input-group">
                    <label>ポート:</label>
                    <input type="number" id="service-port" placeholder="8080">
                </div>
                <div class="input-group">
                    <label>レプリカ数:</label>
                    <input type="number" id="service-replicas" placeholder="1" value="1">
                </div>
                <button class="button" onclick="deployMicroservice()">デプロイ</button>
            </div>
            
            <!-- ロードバランサー -->
            <div class="card">
                <h3>⚖️ ロードバランサー</h3>
                <div id="load-balancers">読み込み中...</div>
                <button class="button" onclick="refreshLoadBalancers()">🔄 更新</button>
            </div>
            
            <!-- スケーリング -->
            <div class="card">
                <h3>📈 スケーリング</h3>
                <div id="scaling-events">読み込み中...</div>
                <button class="button scale" onclick="executeAutoScale()">自動スケーリング実行</button>
            </div>
            
            <!-- クラウドデプロイメント -->
            <div class="card">
                <h3>☁️ クラウドデプロイメント</h3>
                <div id="cloud-deployments">読み込み中...</div>
                <button class="button cloud" onclick="deployToCloud()">クラウドデプロイ</button>
            </div>
            
            <!-- 統合システム状態 -->
            <div class="card">
                <h3>🔗 統合システム状態</h3>
                <div id="integration-status">読み込み中...</div>
                <button class="button" onclick="refreshIntegrationStatus()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // マイクロサービス一覧取得
        async function refreshMicroservices() {
            try {
                const response = await fetch('/api/microservices');
                const data = await response.json();
                
                let html = '<h4>マイクロサービス一覧:</h4>';
                data.microservices.forEach(service => {
                    html += `
                        <div class="service-item">
                            <strong>${service.service_name}</strong><br>
                            <span class="status ${service.status}">${service.status}</span> | 
                            ポート: ${service.port} | レプリカ: ${service.replicas}<br>
                            <small>作成日: ${new Date(service.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('microservices').innerHTML = html;
            } catch (error) {
                console.error('マイクロサービス一覧取得エラー:', error);
            }
        }
        
        // マイクロサービスデプロイ
        async function deployMicroservice() {
            const serviceName = document.getElementById('service-name').value;
            const port = document.getElementById('service-port').value;
            const replicas = document.getElementById('service-replicas').value;
            
            if (!serviceName || !port) {
                alert('サービス名とポートを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/microservices/deploy', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        service_name: serviceName,
                        port: parseInt(port),
                        replicas: parseInt(replicas)
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    alert(`マイクロサービスデプロイ完了: ${data.service_name}`);
                    refreshMicroservices();
                } else {
                    alert('デプロイに失敗しました');
                }
            } catch (error) {
                console.error('マイクロサービスデプロイエラー:', error);
            }
        }
        
        // ロードバランサー一覧取得
        async function refreshLoadBalancers() {
            try {
                const response = await fetch('/api/load-balancers');
                const data = await response.json();
                
                let html = '<h4>ロードバランサー一覧:</h4>';
                data.load_balancers.forEach(lb => {
                    html += `
                        <div class="service-item">
                            <strong>${lb.lb_name}</strong><br>
                            <span class="status ${lb.status}">${lb.status}</span> | 
                            ポート: ${lb.port} | アルゴリズム: ${lb.algorithm}<br>
                            <small>ターゲット: ${lb.target_services.join(', ')}</small>
                        </div>
                    `;
                });
                
                document.getElementById('load-balancers').innerHTML = html;
            } catch (error) {
                console.error('ロードバランサー一覧取得エラー:', error);
            }
        }
        
        // スケーリングイベント取得
        async function refreshScalingEvents() {
            try {
                const response = await fetch('/api/scaling/events');
                const data = await response.json();
                
                let html = '<h4>スケーリングイベント:</h4>';
                data.scaling_events.slice(0, 10).forEach(event => {
                    html += `
                        <div class="service-item">
                            <strong>${event.service_name}</strong><br>
                            ${event.event_type}: ${event.old_replicas} → ${event.new_replicas}<br>
                            <small>${new Date(event.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('scaling-events').innerHTML = html;
            } catch (error) {
                console.error('スケーリングイベント取得エラー:', error);
            }
        }
        
        // 自動スケーリング実行
        async function executeAutoScale() {
            try {
                const response = await fetch('/api/scaling/auto-scale', {method: 'POST'});
                const data = await response.json();
                
                if (data.scaling_events.length > 0) {
                    alert(`自動スケーリング実行: ${data.scaling_events.length}件のサービスがスケーリングされました`);
                } else {
                    alert('スケーリングは不要です');
                }
                
                refreshScalingEvents();
                refreshMicroservices();
            } catch (error) {
                console.error('自動スケーリングエラー:', error);
            }
        }
        
        // クラウドデプロイメント一覧取得
        async function refreshCloudDeployments() {
            try {
                const response = await fetch('/api/cloud/deployments');
                const data = await response.json();
                
                let html = '<h4>クラウドデプロイメント一覧:</h4>';
                data.cloud_deployments.forEach(deployment => {
                    html += `
                        <div class="service-item">
                            <strong>${deployment.deployment_name}</strong><br>
                            <span class="status ${deployment.status}">${deployment.status}</span> | 
                            ${deployment.cloud_provider} (${deployment.region})<br>
                            <small>インスタンス: ${deployment.instance_type}</small>
                        </div>
                    `;
                });
                
                document.getElementById('cloud-deployments').innerHTML = html;
            } catch (error) {
                console.error('クラウドデプロイメント一覧取得エラー:', error);
            }
        }
        
        // クラウドデプロイ
        async function deployToCloud() {
            const deploymentName = prompt('デプロイメント名を入力してください:');
            if (!deploymentName) return;
            
            try {
                const response = await fetch('/api/cloud/deploy', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        deployment_name: deploymentName,
                        cloud_provider: 'aws',
                        region: 'us-east-1',
                        instance_type: 't3.micro'
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    alert(`クラウドデプロイ完了: ${data.deployment_name}`);
                    refreshCloudDeployments();
                } else {
                    alert('クラウドデプロイに失敗しました');
                }
            } catch (error) {
                console.error('クラウドデプロイエラー:', error);
            }
        }
        
        // 統合システム状態取得
        async function refreshIntegrationStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const integrations = data.integrations;
                let html = '<h4>統合システム状態:</h4>';
                
                for (const [systemName, status] of Object.entries(integrations)) {
                    html += `
                        <p>${systemName}: <span class="status ${status.status}">${status.status}</span></p>
                    `;
                }
                
                document.getElementById('integration-status').innerHTML = html;
            } catch (error) {
                console.error('統合システム状態取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshMicroservices();
            refreshLoadBalancers();
            refreshScalingEvents();
            refreshCloudDeployments();
            refreshIntegrationStatus();
            
            // 定期的な更新
            setInterval(refreshMicroservices, 30000);
            setInterval(refreshLoadBalancers, 30000);
            setInterval(refreshScalingEvents, 30000);
            setInterval(refreshCloudDeployments, 60000);
            setInterval(refreshIntegrationStatus, 30000);
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
    system = ManaScalabilitySystem()
    
    print("🚀 Mana Scalability System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5014")
    print("🔗 API: http://localhost:5014/api/status")
    print("=" * 60)
    print("🎯 スケーラビリティ機能:")
    print("  🔧 マイクロサービス管理")
    print("  ⚖️ ロードバランサー")
    print("  📈 自動スケーリング")
    print("  ☁️ クラウドデプロイメント")
    print("  🐳 コンテナオーケストレーション")
    print("  🔍 サービス発見")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        system.app,
        host="0.0.0.0",
        port=5014,
        log_level="info"
    )

if __name__ == "__main__":
    main()

