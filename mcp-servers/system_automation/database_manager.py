#!/usr/bin/env python3
"""
データベース統合システム
SQLite/PostgreSQL統合、データ管理、クエリ実行
"""

import sqlite3
import json
import psycopg2
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """データベース統合システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".database_config.json"
        
        self.default_config = {
            "enabled": True,
            "databases": {
                "sqlite": {
                    "enabled": True,
                    "path": "/root/manaos_automation.db",
                    "auto_create": True
                },
                "postgresql": {
                    "enabled": False,
                    "host": "localhost",
                    "port": 5432,
                    "database": "manaos",
                    "user": "postgres",
                    "password": ""
                }
            },
            "tables": {
                "system_metrics": {
                    "columns": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "timestamp TEXT NOT NULL",
                        "cpu_percent REAL",
                        "memory_percent REAL",
                        "disk_percent REAL",
                        "network_sent_mb REAL",
                        "network_recv_mb REAL"
                    ]
                },
                "alerts": {
                    "columns": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "timestamp TEXT NOT NULL",
                        "severity TEXT NOT NULL",
                        "type TEXT NOT NULL",
                        "message TEXT NOT NULL",
                        "resolved INTEGER DEFAULT 0"
                    ]
                },
                "maintenance_log": {
                    "columns": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "timestamp TEXT NOT NULL",
                        "task_type TEXT NOT NULL",
                        "status TEXT NOT NULL",
                        "duration_seconds INTEGER",
                        "details TEXT"
                    ]
                },
                "backup_history": {
                    "columns": [
                        "id INTEGER PRIMARY KEY AUTOINCREMENT",
                        "timestamp TEXT NOT NULL",
                        "backup_type TEXT NOT NULL",
                        "size_mb REAL",
                        "status TEXT NOT NULL",
                        "file_path TEXT"
                    ]
                }
            }
        }
        
        self.config = self.load_config()
        self.connections = {}
        
    def load_config(self) -> dict:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def get_sqlite_connection(self):
        """SQLite接続取得"""
        if "sqlite" in self.connections:
            return self.connections["sqlite"]
        
        db_path = self.config["databases"]["sqlite"]["path"]
        
        # データベース作成
        if self.config["databases"]["sqlite"]["auto_create"]:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        self.connections["sqlite"] = conn
        
        # テーブル作成
        self._create_tables(conn)
        
        return conn
    
    def get_postgresql_connection(self):
        """PostgreSQL接続取得"""
        if "postgresql" in self.connections:
            return self.connections["postgresql"]
        
        config = self.config["databases"]["postgresql"]
        
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        
        self.connections["postgresql"] = conn
        
        return conn
    
    def _create_tables(self, conn):
        """テーブル作成"""
        for table_name, table_config in self.config["tables"].items():
            columns = ", ".join(table_config["columns"])
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
            
            try:
                conn.execute(create_sql)
                conn.commit()
                logger.info(f"✅ テーブル作成: {table_name}")
            except Exception as e:
                logger.error(f"テーブル作成エラー {table_name}: {e}")
    
    def insert_metric(self, cpu_percent: float, memory_percent: float, 
                     disk_percent: float, network_sent: float, network_recv: float):
        """メトリクス挿入"""
        conn = self.get_sqlite_connection()
        
        sql = """
        INSERT INTO system_metrics 
        (timestamp, cpu_percent, memory_percent, disk_percent, network_sent_mb, network_recv_mb)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        values = (
            datetime.now().isoformat(),
            cpu_percent,
            memory_percent,
            disk_percent,
            network_sent,
            network_recv
        )
        
        try:
            conn.execute(sql, values)
            conn.commit()
            logger.info("✅ メトリクス挿入完了")
        except Exception as e:
            logger.error(f"メトリクス挿入エラー: {e}")
    
    def insert_alert(self, severity: str, type_: str, message: str):
        """アラート挿入"""
        conn = self.get_sqlite_connection()
        
        sql = """
        INSERT INTO alerts (timestamp, severity, type, message)
        VALUES (?, ?, ?, ?)
        """
        
        values = (
            datetime.now().isoformat(),
            severity,
            type_,
            message
        )
        
        try:
            conn.execute(sql, values)
            conn.commit()
            logger.info("✅ アラート挿入完了")
        except Exception as e:
            logger.error(f"アラート挿入エラー: {e}")
    
    def insert_maintenance_log(self, task_type: str, status: str, 
                              duration: int, details: dict = None):  # type: ignore
        """メンテナンスログ挿入"""
        conn = self.get_sqlite_connection()
        
        sql = """
        INSERT INTO maintenance_log (timestamp, task_type, status, duration_seconds, details)
        VALUES (?, ?, ?, ?, ?)
        """
        
        values = (
            datetime.now().isoformat(),
            task_type,
            status,
            duration,
            json.dumps(details, ensure_ascii=False) if details else None
        )
        
        try:
            conn.execute(sql, values)
            conn.commit()
            logger.info("✅ メンテナンスログ挿入完了")
        except Exception as e:
            logger.error(f"メンテナンスログ挿入エラー: {e}")
    
    def insert_backup_history(self, backup_type: str, size_mb: float, 
                             status: str, file_path: str):
        """バックアップ履歴挿入"""
        conn = self.get_sqlite_connection()
        
        sql = """
        INSERT INTO backup_history (timestamp, backup_type, size_mb, status, file_path)
        VALUES (?, ?, ?, ?, ?)
        """
        
        values = (
            datetime.now().isoformat(),
            backup_type,
            size_mb,
            status,
            file_path
        )
        
        try:
            conn.execute(sql, values)
            conn.commit()
            logger.info("✅ バックアップ履歴挿入完了")
        except Exception as e:
            logger.error(f"バックアップ履歴挿入エラー: {e}")
    
    def query_metrics(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """メトリクスクエリ"""
        conn = self.get_sqlite_connection()
        
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        sql = """
        SELECT * FROM system_metrics 
        WHERE timestamp > datetime(?, 'unixepoch')
        ORDER BY timestamp DESC 
        LIMIT ?
        """
        
        try:
            cursor = conn.execute(sql, (cutoff_time, limit))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"メトリクスクエリエラー: {e}")
            return []
    
    def query_alerts(self, severity: str = None, unresolved: bool = True,  # type: ignore
                    limit: int = 100) -> List[Dict]:
        """アラートクエリ"""
        conn = self.get_sqlite_connection()
        
        sql = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if severity:
            sql += " AND severity = ?"
            params.append(severity)
        
        if unresolved:
            sql += " AND resolved = 0"
        
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"アラートクエリエラー: {e}")
            return []
    
    def query_maintenance_log(self, task_type: str = None,  # type: ignore
                             limit: int = 100) -> List[Dict]:
        """メンテナンスログクエリ"""
        conn = self.get_sqlite_connection()
        
        sql = "SELECT * FROM maintenance_log WHERE 1=1"
        params = []
        
        if task_type:
            sql += " AND task_type = ?"
            params.append(task_type)
        
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"メンテナンスログクエリエラー: {e}")
            return []
    
    def query_backup_history(self, backup_type: str = None,  # type: ignore
                           limit: int = 100) -> List[Dict]:
        """バックアップ履歴クエリ"""
        conn = self.get_sqlite_connection()
        
        sql = "SELECT * FROM backup_history WHERE 1=1"
        params = []
        
        if backup_type:
            sql += " AND backup_type = ?"
            params.append(backup_type)
        
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"バックアップ履歴クエリエラー: {e}")
            return []
    
    def execute_custom_query(self, query: str, params: tuple = None) -> List[Dict]:  # type: ignore
        """カスタムクエリ実行"""
        conn = self.get_sqlite_connection()
        
        try:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            
            rows = cursor.fetchall()
            conn.commit()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"カスタムクエリエラー: {e}")
            return []
    
    def get_database_stats(self) -> Dict:
        """データベース統計取得"""
        conn = self.get_sqlite_connection()
        
        stats = {}
        
        for table_name in self.config["tables"].keys():
            try:
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                row = cursor.fetchone()
                stats[table_name] = row["count"]
            except Exception as e:
                logger.error(f"統計取得エラー {table_name}: {e}")
                stats[table_name] = 0
        
        return stats
    
    def optimize_database(self):
        """データベース最適化"""
        conn = self.get_sqlite_connection()
        
        try:
            # VACUUM
            conn.execute("VACUUM")
            
            # ANALYZE
            conn.execute("ANALYZE")
            
            conn.commit()
            
            logger.info("✅ データベース最適化完了")
        except Exception as e:
            logger.error(f"データベース最適化エラー: {e}")
    
    def close_connections(self):
        """接続を閉じる"""
        for name, conn in self.connections.items():
            try:
                conn.close()
                logger.info(f"✅ 接続を閉じました: {name}")
            except Exception as e:
                logger.error(f"接続クローズエラー {name}: {e}")


def main():
    """メイン実行"""
    db = DatabaseManager()
    
    print("=" * 60)
    print("📊 データベース統合システム")
    print("=" * 60)
    
    print("\n📊 データベース設定:")
    print(f"  SQLite: {'✅' if db.config['databases']['sqlite']['enabled'] else '❌'}")
    print(f"  PostgreSQL: {'✅' if db.config['databases']['postgresql']['enabled'] else '❌'}")
    
    # 統計表示
    stats = db.get_database_stats()
    print("\n📈 データベース統計:")
    for table, count in stats.items():
        print(f"  {table}: {count}件")
    
    print("\n実行する操作を選択:")
    print("  1. メトリクス挿入（テスト）")
    print("  2. メトリクスクエリ")
    print("  3. アラートクエリ")
    print("  4. メンテナンスログクエリ")
    print("  5. データベース最適化")
    print("  0. 終了")
    
    choice = input("\n選択 (0-5): ").strip()
    
    if choice == "1":
        print("\n📊 メトリクス挿入中...")
        db.insert_metric(45.2, 62.8, 73.1, 100.5, 200.3)
        print("✅ 完了")
    
    elif choice == "2":
        print("\n📊 メトリクスクエリ中...")
        metrics = db.query_metrics(hours=24, limit=10)
        print(f"✅ {len(metrics)}件のメトリクス")
        for metric in metrics[:3]:
            print(f"  {metric['timestamp']}: CPU {metric['cpu_percent']:.1f}%")
    
    elif choice == "3":
        print("\n⚠️ アラートクエリ中...")
        alerts = db.query_alerts(unresolved=True, limit=10)
        print(f"✅ {len(alerts)}件のアラート")
        for alert in alerts[:3]:
            print(f"  [{alert['severity']}] {alert['message']}")
    
    elif choice == "4":
        print("\n🔧 メンテナンスログクエリ中...")
        logs = db.query_maintenance_log(limit=10)
        print(f"✅ {len(logs)}件のログ")
        for log in logs[:3]:
            print(f"  {log['task_type']}: {log['status']}")
    
    elif choice == "5":
        print("\n🔧 データベース最適化中...")
        db.optimize_database()
        print("✅ 完了")
    
    # 接続を閉じる
    db.close_connections()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

