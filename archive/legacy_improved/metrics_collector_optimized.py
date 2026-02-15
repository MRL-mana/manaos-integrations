#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ManaOS メトリクス収集システム（最適化版）
データベース接続プールとキャッシュシステムを使用
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import threading
import time

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# 最適化モジュールのインポート
from database_connection_pool import get_pool
from unified_cache_system import get_unified_cache
from config_cache import get_config_cache

# ロガーの初期化
logger = get_service_logger("metrics-collector-optimized")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("MetricsCollector")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# キャッシュシステムの取得
cache_system = get_unified_cache()
config_cache = get_config_cache()


class MetricType(str, Enum):
    """メトリクスタイプ"""
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    REQUEST_COUNT = "request_count"
    RESOURCE_USAGE = "resource_usage"
    SUCCESS_RATE = "success_rate"


@dataclass
class Metric:
    """メトリクス"""
    metric_id: str
    service_name: str
    metric_type: MetricType
    value: float
    timestamp: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MetricsCollectorOptimized:
    """メトリクス収集システム（最適化版）"""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        retention_days: int = 30
    ):
        """
        初期化
        
        Args:
            db_path: データベースパス
            config_path: 設定ファイルのパス
            retention_days: メトリクス保持日数
        """
        self.config_path = config_path or Path(__file__).parent / "metrics_collector_config.json"
        self.config = self._load_config()
        
        # データベース初期化（接続プール使用）
        self.db_path = db_path or Path(__file__).parent / "metrics.db"
        self.db_pool = get_pool(str(self.db_path), max_connections=10)
        self.retention_days = retention_days
        self._init_database()
        
        # メモリ内バッファ（高速書き込み用）
        self.metric_buffer: deque = deque(maxlen=1000)
        self.buffer_lock = threading.Lock()
        
        logger.info(f"✅ Metrics Collector（最適化版）初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む（キャッシュ使用）"""
        return config_cache.get_config(
            str(self.config_path),
            default=self._get_default_config()
        )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "flush_interval_seconds": 10,
            "buffer_size": 1000
        }
    
    def _init_database(self):
        """データベースを初期化（接続プール使用）"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # メトリクステーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    metric_id TEXT PRIMARY KEY,
                    service_name TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # インデックス作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_service_name ON metrics(service_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric_type ON metrics(metric_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_service_timestamp ON metrics(service_name, timestamp DESC)")
            
            conn.commit()
        
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def record_metric(
        self,
        service_name: str,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        メトリクスを記録（最適化版）
        
        Args:
            service_name: サービス名
            metric_type: メトリクスタイプ
            value: 値
            metadata: メタデータ
        """
        metric_id = f"{service_name}_{metric_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        metric = Metric(
            metric_id=metric_id,
            service_name=service_name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        # バッファに追加
        with self.buffer_lock:
            self.metric_buffer.append(metric)
        
        # バッファが一定サイズに達したらフラッシュ
        if len(self.metric_buffer) >= self.config.get("buffer_size", 1000):
            self._flush_buffer()
    
    def _flush_buffer(self):
        """バッファをデータベースにフラッシュ（接続プール使用）"""
        if not self.metric_buffer:
            return
        
        metrics_to_flush = []
        with self.buffer_lock:
            while self.metric_buffer:
                metrics_to_flush.append(self.metric_buffer.popleft())
        
        if not metrics_to_flush:
            return
        
        # バッチ挿入
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            for metric in metrics_to_flush:
                cursor.execute("""
                    INSERT INTO metrics (
                        metric_id, service_name, metric_type, value, timestamp, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metric.metric_id,
                    metric.service_name,
                    metric.metric_type.value,
                    metric.value,
                    metric.timestamp,
                    json.dumps(metric.metadata)
                ))
            
            conn.commit()
        
        logger.debug(f"メトリクスをフラッシュ: {len(metrics_to_flush)}件")
    
    def get_metrics(
        self,
        service_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Metric]:
        """
        メトリクスを取得（最適化版）
        
        Args:
            service_name: サービス名（Noneの場合はすべて）
            metric_type: メトリクスタイプ（Noneの場合はすべて）
            start_time: 開始時刻
            end_time: 終了時刻
            limit: 最大件数
        
        Returns:
            メトリクスのリスト
        """
        # キャッシュキーを生成
        cache_key = f"{service_name}:{metric_type}:{start_time}:{end_time}:{limit}"
        cached = cache_system.get("metrics", cache_key=cache_key)
        if cached:
            return [Metric(**m) for m in cached]
        
        # バッファをフラッシュ
        self._flush_buffer()
        
        # データベースから取得
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM metrics WHERE 1=1"
            params = []
            
            if service_name:
                query += " AND service_name = ?"
                params.append(service_name)
            
            if metric_type:
                query += " AND metric_type = ?"
                params.append(metric_type.value)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            metrics = []
            for row in cursor.fetchall():
                metrics.append(Metric(
                    metric_id=row[0],
                    service_name=row[1],
                    metric_type=MetricType(row[2]),
                    value=row[3],
                    timestamp=row[4],
                    metadata=json.loads(row[5] or "{}")
                ))
        
        # キャッシュに保存
        cache_system.set("metrics", [asdict(m) for m in metrics], cache_key=cache_key, ttl_seconds=60)
        
        return metrics
    
    def get_statistics(
        self,
        service_name: str,
        metric_type: MetricType,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        統計情報を取得（最適化版）
        
        Args:
            service_name: サービス名
            metric_type: メトリクスタイプ
            hours: 時間範囲
        
        Returns:
            統計情報
        """
        start_time = datetime.now() - timedelta(hours=hours)
        metrics = self.get_metrics(service_name, metric_type, start_time=start_time)
        
        if not metrics:
            return {
                "service_name": service_name,
                "metric_type": metric_type.value,
                "count": 0
            }
        
        values = [m.value for m in metrics]
        
        return {
            "service_name": service_name,
            "metric_type": metric_type.value,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("メトリクス収集システム（最適化版）テスト")
    print("=" * 60)
    
    collector = MetricsCollectorOptimized()
    
    # メトリクスを記録
    collector.record_metric(
        service_name="test_service",
        metric_type=MetricType.RESPONSE_TIME,
        value=0.5
    )
    
    # メトリクスを取得
    metrics = collector.get_metrics(service_name="test_service", limit=10)
    print(f"取得したメトリクス: {len(metrics)}件")


if __name__ == "__main__":
    main()






















