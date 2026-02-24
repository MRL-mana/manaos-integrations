#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 ManaOSデータベース接続プール
SQLite接続の再利用と最適化
"""

import sqlite3
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager
from queue import Queue, Empty
from datetime import datetime

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_service_logger("database-connection-pool")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("DatabaseConnectionPool")


class DatabaseConnectionPool:
    """データベース接続プール"""
    
    def __init__(
        self,
        db_path: str,
        max_connections: int = 10,
        timeout: float = 5.0,
        check_same_thread: bool = False
    ):
        """
        初期化
        
        Args:
            db_path: データベースパス
            max_connections: 最大接続数
            timeout: 接続取得のタイムアウト（秒）
            check_same_thread: スレッドチェック（SQLite用）
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_connections = max_connections
        self.timeout = timeout
        self.check_same_thread = check_same_thread
        
        # 接続プール
        self.pool: Queue = Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.Lock()
        
        # 統計情報
        self.stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "connections_closed": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }
        
        logger.info(f"データベース接続プールを初期化しました: {db_path} (最大接続数: {max_connections})")
    
    def _create_connection(self) -> sqlite3.Connection:
        """新しい接続を作成"""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.timeout,
            check_same_thread=self.check_same_thread
        )
        # パフォーマンス最適化設定
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # バランスの取れた同期
        conn.execute("PRAGMA cache_size=-64000")  # 64MBキャッシュ
        conn.execute("PRAGMA foreign_keys=ON")  # 外部キー制約を有効化
        
        self.stats["connections_created"] += 1
        return conn
    
    @contextmanager
    def get_connection(self) -> Any:
        """
        接続を取得（コンテキストマネージャー）
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
        """
        conn = None
        try:
            # プールから接続を取得（タイムアウト付き）
            try:
                conn = self.pool.get(timeout=self.timeout)
                self.stats["pool_hits"] += 1
                self.stats["connections_reused"] += 1
            except Empty:
                # プールが空の場合、新しい接続を作成
                with self.lock:
                    if self.active_connections < self.max_connections:
                        conn = self._create_connection()
                        self.active_connections += 1
                        self.stats["pool_misses"] += 1
                    else:
                        # 最大接続数に達している場合、タイムアウトまで待機
                        conn = self.pool.get(timeout=self.timeout)
                        self.stats["pool_hits"] += 1
                        self.stats["connections_reused"] += 1
            
            yield conn
            
        except Exception as e:
            # エラーが発生した場合、接続を閉じて新しい接続を作成
            if conn:
                try:
                    conn.close()
                except Exception:
                    logger.debug("接続のクローズに失敗")
                with self.lock:
                    self.active_connections -= 1
                conn = self._create_connection()
                with self.lock:
                    self.active_connections += 1
            raise error_handler.handle_exception(
                e,
                context={"db_path": str(self.db_path), "action": "get_connection"},
                user_message="データベース接続の取得に失敗しました"
            )
        finally:
            # 接続をプールに返す
            if conn:
                try:
                    # 接続が有効かチェック
                    conn.execute("SELECT 1")
                    self.pool.put(conn)
                except Exception:
                    # 接続が無効な場合、閉じて新しい接続を作成
                    try:
                        conn.close()
                    except Exception:
                        logger.debug("無効な接続のクローズに失敗")
                    with self.lock:
                        self.active_connections -= 1
    
    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = True
    ) -> Optional[Any]:
        """
        クエリを実行
        
        Args:
            query: SQLクエリ
            params: パラメータ
            fetch_one: 1行のみ取得するか
            fetch_all: すべての行を取得するか
        
        Returns:
            クエリ結果
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
    
    def execute_many(
        self,
        query: str,
        params_list: list
    ) -> int:
        """
        複数のクエリを一括実行
        
        Args:
            query: SQLクエリ
            params_list: パラメータのリスト
        
        Returns:
            影響を受けた行数
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def close_all(self) -> None:
        """すべての接続を閉じる"""
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    conn.close()
                    self.stats["connections_closed"] += 1
                except Empty:
                    break
            self.active_connections = 0
        
        logger.info("すべての接続を閉じました")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_requests = self.stats["pool_hits"] + self.stats["pool_misses"]
        reuse_rate = (
            self.stats["connections_reused"] / total_requests * 100
            if total_requests > 0 else 0
        )
        
        return {
            **self.stats,
            "active_connections": self.active_connections,
            "pool_size": self.pool.qsize(),
            "reuse_rate": reuse_rate
        }


# グローバルプール管理
_pools: Dict[str, DatabaseConnectionPool] = {}
_pools_lock = threading.Lock()


def get_pool(db_path: str, max_connections: int = 10) -> DatabaseConnectionPool:
    """
    データベース接続プールを取得（シングルトン）
    
    Args:
        db_path: データベースパス
        max_connections: 最大接続数
    
    Returns:
        データベース接続プール
    """
    db_path_str = str(Path(db_path).resolve())
    
    with _pools_lock:
        if db_path_str not in _pools:
            _pools[db_path_str] = DatabaseConnectionPool(
                db_path_str,
                max_connections=max_connections
            )
        return _pools[db_path_str]


def main() -> None:
    """テスト用メイン関数"""
    print("データベース接続プールテスト")
    print("=" * 60)
    
    pool = get_pool("test.db", max_connections=5)
    
    # テストテーブル作成
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        conn.commit()
    
    # テストデータ挿入
    pool.execute_query(
        "INSERT INTO test_table (name, value) VALUES (?, ?)",
        ("test", 123),
        fetch_all=False
    )
    
    # テストデータ取得
    results = pool.execute_query("SELECT * FROM test_table")
    print(f"取得結果: {results}")
    
    # 統計情報
    print("\n統計情報:")
    stats = pool.get_stats()
    print(f"  作成された接続: {stats['connections_created']}")
    print(f"  再利用された接続: {stats['connections_reused']}")
    print(f"  再利用率: {stats['reuse_rate']:.1f}%")
    
    pool.close_all()


if __name__ == "__main__":
    main()






















