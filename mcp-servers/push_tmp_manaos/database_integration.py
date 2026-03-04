"""
データベース統合システム
PostgreSQL/MongoDB統合
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    print("PostgreSQLライブラリがインストールされていません。")
    print("インストール: pip install psycopg2-binary")

try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("MongoDBライブラリがインストールされていません。")
    print("インストール: pip install pymongo")


class PostgreSQLIntegration:
    """PostgreSQL統合クラス"""
    
    def __init__(self, connection_string: str):
        """
        初期化
        
        Args:
            connection_string: 接続文字列
        """
        self.connection_string = connection_string
        self.conn = None
        
        if POSTGRESQL_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """接続"""
        try:
            self.conn = psycopg2.connect(self.connection_string)
        except Exception as e:
            print(f"PostgreSQL接続エラー: {e}")
    
    def is_available(self) -> bool:
        """利用可能かチェック"""
        return POSTGRESQL_AVAILABLE and self.conn is not None
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        クエリを実行
        
        Args:
            query: SQLクエリ
            params: パラメータ（オプション）
            
        Returns:
            結果のリスト
        """
        if not self.is_available():
            return []
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    self.conn.commit()
                    return []
        except Exception as e:
            print(f"クエリ実行エラー: {e}")
            return []
    
    def insert_data(self, table: str, data: Dict[str, Any]) -> bool:
        """
        データを挿入
        
        Args:
            table: テーブル名
            data: データ
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, tuple(data.values()))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"データ挿入エラー: {e}")
            return False


class MongoDBIntegration:
    """MongoDB統合クラス"""
    
    def __init__(self, connection_string: str, database_name: str):
        """
        初期化
        
        Args:
            connection_string: 接続文字列
            database_name: データベース名
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """接続"""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
        except Exception as e:
            print(f"MongoDB接続エラー: {e}")
    
    def is_available(self) -> bool:
        """利用可能かチェック"""
        return MONGODB_AVAILABLE and self.db is not None
    
    def insert_document(self, collection: str, document: Dict[str, Any]) -> Optional[str]:
        """
        ドキュメントを挿入
        
        Args:
            collection: コレクション名
            document: ドキュメント
            
        Returns:
            ドキュメントID（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            result = self.db[collection].insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            print(f"ドキュメント挿入エラー: {e}")
            return None
    
    def find_documents(
        self,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        ドキュメントを検索
        
        Args:
            collection: コレクション名
            filter: フィルタ（オプション）
            limit: 取得数
            
        Returns:
            ドキュメントのリスト
        """
        if not self.is_available():
            return []
        
        try:
            cursor = self.db[collection].find(filter or {}).limit(limit)
            return [doc for doc in cursor]
        except Exception as e:
            print(f"ドキュメント検索エラー: {e}")
            return []


class DatabaseIntegration:
    """データベース統合クラス"""
    
    def __init__(self):
        """初期化"""
        self.postgresql = None
        self.mongodb = None
    
    def configure_postgresql(self, connection_string: str):
        """
        PostgreSQLを設定
        
        Args:
            connection_string: 接続文字列
        """
        self.postgresql = PostgreSQLIntegration(connection_string)
    
    def configure_mongodb(self, connection_string: str, database_name: str):
        """
        MongoDBを設定
        
        Args:
            connection_string: 接続文字列
            database_name: データベース名
        """
        self.mongodb = MongoDBIntegration(connection_string, database_name)
    
    def save_metrics(self, metrics: Dict[str, Any], db_type: str = "mongodb"):
        """
        メトリクスを保存
        
        Args:
            metrics: メトリクス
            db_type: データベースタイプ（postgresql, mongodb）
        """
        if db_type == "postgresql" and self.postgresql and self.postgresql.is_available():
            self.postgresql.insert_data("metrics", metrics)
        elif db_type == "mongodb" and self.mongodb and self.mongodb.is_available():
            self.mongodb.insert_document("metrics", metrics)
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "postgresql_available": self.postgresql.is_available() if self.postgresql else False,
            "mongodb_available": self.mongodb.is_available() if self.mongodb else False,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("データベース統合システムテスト")
    print("=" * 60)
    
    db = DatabaseIntegration()
    
    # PostgreSQL設定（接続文字列が必要）
    # db.configure_postgresql("postgresql://user:password@localhost/dbname")
    
    # MongoDB設定（接続文字列が必要）
    # db.configure_mongodb("mongodb://localhost:27017/", "manaos_db")
    
    # 状態を表示
    status = db.get_status()
    print(f"\n状態:")
    print(f"  PostgreSQL: {'利用可能' if status['postgresql_available'] else '利用不可'}")
    print(f"  MongoDB: {'利用可能' if status['mongodb_available'] else '利用不可'}")


if __name__ == "__main__":
    main()



















