#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Prometheusメトリクス統合
Prometheus形式のメトリクスをエクスポート
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_clientがインストールされていません。pip install prometheus-client を実行してください。")


class PrometheusMetrics:
    """Prometheusメトリクス"""
    
    def __init__(self):
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_clientが必要です")
        
        # カウンター
        self.request_count = Counter(
            'manaos_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status']
        )
        
        self.error_count = Counter(
            'manaos_errors_total',
            'Total number of errors',
            ['error_type', 'service']
        )
        
        # ヒストグラム
        self.request_duration = Histogram(
            'manaos_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.llm_call_duration = Histogram(
            'manaos_llm_call_duration_seconds',
            'LLM call duration in seconds',
            ['model', 'task_type']
        )
        
        # ゲージ
        self.active_connections = Gauge(
            'manaos_active_connections',
            'Number of active connections'
        )
        
        self.gpu_usage = Gauge(
            'manaos_gpu_usage_percent',
            'GPU usage percentage',
            ['gpu_id']
        )
        
        self.cpu_usage = Gauge(
            'manaos_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        self.memory_usage = Gauge(
            'manaos_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        self.cache_hit_rate = Gauge(
            'manaos_cache_hit_rate',
            'Cache hit rate (0-1)'
        )
        
        self.service_health = Gauge(
            'manaos_service_health',
            'Service health status (1=healthy, 0=unhealthy)',
            ['service_name']
        )
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """リクエストを記録"""
        status = 'success' if 200 <= status_code < 400 else 'error'
        self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_error(self, error_type: str, service: str):
        """エラーを記録"""
        self.error_count.labels(error_type=error_type, service=service).inc()
    
    def record_llm_call(self, model: str, task_type: str, duration: float):
        """LLM呼び出しを記録"""
        self.llm_call_duration.labels(model=model, task_type=task_type).observe(duration)
    
    def update_system_metrics(self, cpu_percent: float, memory_bytes: int):
        """システムメトリクスを更新"""
        self.cpu_usage.set(cpu_percent)
        self.memory_usage.set(memory_bytes)
    
    def update_gpu_metrics(self, gpu_id: str, usage_percent: float):
        """GPUメトリクスを更新"""
        self.gpu_usage.labels(gpu_id=gpu_id).set(usage_percent)
    
    def update_cache_metrics(self, hit_rate: float):
        """キャッシュメトリクスを更新"""
        self.cache_hit_rate.set(hit_rate)
    
    def update_service_health(self, service_name: str, is_healthy: bool):
        """サービスヘルスを更新"""
        self.service_health.labels(service_name=service_name).set(1 if is_healthy else 0)
    
    def get_metrics(self) -> bytes:
        """メトリクスを取得（Prometheus形式）"""
        return generate_latest()


# Flask統合
def setup_prometheus_endpoint(app, prometheus_metrics: PrometheusMetrics):
    """Prometheusエンドポイントを設定"""
    from flask import Response
    
    @app.route('/metrics', methods=['GET'])
    def metrics():
        """Prometheusメトリクスエンドポイント"""
        return Response(
            prometheus_metrics.get_metrics(),
            mimetype=CONTENT_TYPE_LATEST
        )


# シングルトンインスタンス
_prometheus_metrics: PrometheusMetrics = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """Prometheusメトリクスのシングルトン取得"""
    global _prometheus_metrics
    if _prometheus_metrics is None:
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus統合は利用できません")
            return None
        _prometheus_metrics = PrometheusMetrics()
    return _prometheus_metrics








