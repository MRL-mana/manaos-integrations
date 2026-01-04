#!/usr/bin/env python3
"""
📊 ManaOS メトリクス収集システム
パフォーマンス監視・メトリクス収集・分析
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, jsonify, request
from flask_cors import CORS
from collections import defaultdict, deque
import threading
import time

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("MetricsCollector")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("MetricsCollector")


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


class MetricsCollector:
    """メトリクス収集システム"""
    
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
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "metrics.db"
        self.retention_days = retention_days
        self._init_database()
        
        # メモリ内バッファ（高速書き込み用）
        self.metric_buffer: deque = deque(maxlen=1000)
        self.buffer_lock = threading.Lock()
        
        # バッファフラッシュスレッド
        self.flush_thread = None
        self.flushing = False
        
        logger.info(f"✅ Metrics Collector初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": [],
                    "fields": {
                        "flush_interval_seconds": {"type": int, "default": 10},
                        "buffer_size": {"type": int, "default": 1000}
                    }
                }
                
                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                    default_config = self._get_default_config()
                    default_config.update(config)
                    return default_config
                
                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "flush_interval_seconds": 10,
            "buffer_size": 1000
        }
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
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
        conn.close()
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def record_metric(
        self,
        service_name: str,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        メトリクスを記録
        
        Args:
            service_name: サービス名
            metric_type: メトリクスタイプ
            value: 値
            metadata: メタデータ
        """
        metric = Metric(
            metric_id=f"{service_name}_{metric_type.value}_{datetime.now().timestamp()}",
            service_name=service_name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        # バッファに追加
        with self.buffer_lock:
            self.metric_buffer.append(metric)
        
        # バッファが満杯の場合は即座にフラッシュ
        if len(self.metric_buffer) >= self.config.get("buffer_size", 1000):
            self._flush_buffer()
    
    def _flush_buffer(self):
        """バッファをデータベースにフラッシュ"""
        if not self.metric_buffer:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metrics_to_flush = []
            with self.buffer_lock:
                while self.metric_buffer:
                    metrics_to_flush.append(self.metric_buffer.popleft())
            
            for metric in metrics_to_flush:
                cursor.execute("""
                    INSERT OR REPLACE INTO metrics
                    (metric_id, service_name, metric_type, value, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metric.metric_id,
                    metric.service_name,
                    metric.metric_type.value,
                    metric.value,
                    metric.timestamp,
                    json.dumps(metric.metadata, ensure_ascii=False) if metric.metadata else None
                ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✅ メトリクスフラッシュ完了: {len(metrics_to_flush)}件")
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "flush_buffer"},
                user_message="メトリクスの保存に失敗しました"
            )
            logger.error(f"メトリクスフラッシュエラー: {error.message}")
    
    def start_background_flush(self):
        """バックグラウンドフラッシュを開始"""
        if self.flushing:
            return
        
        self.flushing = True
        
        def flush_loop():
            while self.flushing:
                time.sleep(self.config.get("flush_interval_seconds", 10))
                if self.metric_buffer:
                    self._flush_buffer()
        
        self.flush_thread = threading.Thread(target=flush_loop, daemon=True)
        self.flush_thread.start()
        logger.info("✅ バックグラウンドフラッシュ開始")
    
    def stop_background_flush(self):
        """バックグラウンドフラッシュを停止"""
        self.flushing = False
        if self.flush_thread:
            self.flush_thread.join(timeout=5)
        # 最後のフラッシュ
        self._flush_buffer()
        logger.info("✅ バックグラウンドフラッシュ停止")
    
    def get_metrics(
        self,
        service_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Metric]:
        """
        メトリクスを取得
        
        Args:
            service_name: サービス名（フィルタ）
            metric_type: メトリクスタイプ（フィルタ）
            start_time: 開始時刻
            end_time: 終了時刻
            limit: 取得件数
        
        Returns:
            メトリクスのリスト
        """
        # バッファも含めて取得
        self._flush_buffer()
        
        conn = sqlite3.connect(self.db_path)
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
            metric = Metric(
                metric_id=row[0],
                service_name=row[1],
                metric_type=MetricType(row[2]),
                value=row[3],
                timestamp=row[4],
                metadata=json.loads(row[5]) if row[5] else {}
            )
            metrics.append(metric)
        
        conn.close()
        return metrics
    
    def get_statistics(
        self,
        service_name: str,
        metric_type: MetricType,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Args:
            service_name: サービス名
            metric_type: メトリクスタイプ
            hours: 時間範囲（時間）
        
        Returns:
            統計情報
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = self.get_metrics(
            service_name=service_name,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        if not metrics:
            return {
                "service_name": service_name,
                "metric_type": metric_type.value,
                "count": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0
            }
        
        values = [m.value for m in metrics]
        values.sort()
        
        return {
            "service_name": service_name,
            "metric_type": metric_type.value,
            "count": len(values),
            "avg": sum(values) / len(values) if values else 0,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "p50": values[len(values) // 2] if values else 0,
            "p95": values[int(len(values) * 0.95)] if values else 0,
            "p99": values[int(len(values) * 0.99)] if values else 0,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    
    def cleanup_old_metrics(self):
        """古いメトリクスを削除"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_date.isoformat(),))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 古いメトリクス削除完了: {deleted_count}件")
            return deleted_count
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "cleanup_old_metrics"},
                user_message="古いメトリクスの削除に失敗しました"
            )
            logger.error(f"メトリクス削除エラー: {error.message}")
            return 0


# Flask APIサーバー
app = Flask(__name__)
CORS(app)

# グローバルメトリクスコレクターインスタンス
metrics_collector = None

def init_metrics_collector():
    """メトリクスコレクターを初期化"""
    global metrics_collector
    if metrics_collector is None:
        metrics_collector = MetricsCollector()
        metrics_collector.start_background_flush()
    return metrics_collector

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Metrics Collector"})

@app.route('/api/metrics', methods=['POST'])
def record_metric():
    """メトリクスを記録"""
    try:
        data = request.get_json() or {}
        service_name = data.get("service_name")
        metric_type = data.get("metric_type")
        value = data.get("value")
        metadata = data.get("metadata")
        
        if not all([service_name, metric_type, value is not None]):
            error = error_handler.handle_exception(
                ValueError("service_name, metric_type, value are required"),
                context={"endpoint": "/api/metrics"},
                user_message="必須パラメータが不足しています"
            )
            return jsonify(error.to_json_response()), 400
        
        collector = init_metrics_collector()
        collector.record_metric(
            service_name=service_name,
            metric_type=MetricType(metric_type),
            value=float(value),
            metadata=metadata
        )
        
        return jsonify({"status": "recorded"})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/metrics"},
            user_message="メトリクスの記録に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """メトリクスを取得"""
    try:
        service_name = request.args.get("service_name")
        metric_type = request.args.get("metric_type")
        hours = request.args.get("hours", 24, type=int)
        limit = request.args.get("limit", 1000, type=int)
        
        collector = init_metrics_collector()
        
        if service_name and metric_type:
            # 統計情報を取得
            stats = collector.get_statistics(
                service_name=service_name,
                metric_type=MetricType(metric_type),
                hours=hours
            )
            return jsonify(stats)
        else:
            # メトリクス一覧を取得
            start_time = datetime.now() - timedelta(hours=hours) if hours else None
            metrics = collector.get_metrics(
                service_name=service_name,
                metric_type=MetricType(metric_type) if metric_type else None,
                start_time=start_time,
                limit=limit
            )
            return jsonify({
                "metrics": [asdict(m) for m in metrics],
                "count": len(metrics)
            })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/metrics"},
            user_message="メトリクスの取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """統計情報を取得"""
    try:
        service_name = request.args.get("service_name")
        metric_type = request.args.get("metric_type")
        hours = request.args.get("hours", 24, type=int)
        
        if not service_name or not metric_type:
            error = error_handler.handle_exception(
                ValueError("service_name and metric_type are required"),
                context={"endpoint": "/api/statistics"},
                user_message="service_nameとmetric_typeが必要です"
            )
            return jsonify(error.to_json_response()), 400
        
        collector = init_metrics_collector()
        stats = collector.get_statistics(
            service_name=service_name,
            metric_type=MetricType(metric_type),
            hours=hours
        )
        
        return jsonify(stats)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/statistics"},
            user_message="統計情報の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_metrics():
    """古いメトリクスを削除"""
    try:
        collector = init_metrics_collector()
        deleted_count = collector.cleanup_old_metrics()
        return jsonify({"deleted_count": deleted_count})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/cleanup"},
            user_message="メトリクスのクリーンアップに失敗しました"
        )
        return jsonify(error.to_json_response()), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5127))
    logger.info(f"📊 Metrics Collector起動中... (ポート: {port})")
    init_metrics_collector()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

