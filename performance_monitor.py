#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📈 ManaOS パフォーマンス監視システム
リアルタイムパフォーマンス監視、トレンド分析、最適化提案
"""

import asyncio
import time
import psutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """パフォーマンスメトリクス"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int
    response_time_avg: float
    error_rate: float


class PerformanceMonitor:
    """パフォーマンス監視システム"""
    
    def __init__(self, history_size: int = 1000):
        """
        初期化
        
        Args:
            history_size: 保持するメトリクスの最大数
        """
        self.history_size = history_size
        self.metrics_history: deque = deque(maxlen=history_size)
        self.monitoring = False
        self.monitor_task = None
        
        # ネットワーク統計の初期値
        self.last_network_stats = psutil.net_io_counters()
        self.last_network_time = time.time()
    
    async def start_monitoring(self, interval: int = 10):
        """
        監視を開始
        
        Args:
            interval: 監視間隔（秒）
        """
        if self.monitoring:
            logger.warning("監視は既に実行中です")
            return
        
        self.monitoring = True
        
        async def monitor_loop():
            while self.monitoring:
                try:
                    metric = await self._collect_metrics()
                    self.metrics_history.append(metric)
                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"監視エラー: {e}")
                    await asyncio.sleep(interval)
        
        self.monitor_task = asyncio.create_task(monitor_loop())
        logger.info(f"✅ パフォーマンス監視を開始しました（間隔: {interval}秒）")
    
    async def stop_monitoring(self):
        """監視を停止"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ パフォーマンス監視を停止しました")
    
    async def _collect_metrics(self) -> PerformanceMetric:
        """メトリクスを収集"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # メモリ
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # ディスク
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # ネットワーク
        network_stats = psutil.net_io_counters()
        current_time = time.time()
        time_delta = current_time - self.last_network_time
        
        if time_delta > 0:
            network_sent_mb = (network_stats.bytes_sent - self.last_network_stats.bytes_sent) / 1024 / 1024 / time_delta
            network_recv_mb = (network_stats.bytes_recv - self.last_network_stats.bytes_recv) / 1024 / 1024 / time_delta
        else:
            network_sent_mb = 0.0
            network_recv_mb = 0.0
        
        self.last_network_stats = network_stats
        self.last_network_time = current_time
        
        # アクティブ接続数（簡易実装）
        active_connections = len(psutil.net_connections())
        
        # レスポンス時間とエラー率（メトリクス収集システムから取得）
        response_time_avg = 0.0
        error_rate = 0.0
        
        try:
            from metrics_collector import get_metrics_collector
            collector = get_metrics_collector()
            response_stats = collector.get_statistics("response.time")
            if response_stats:
                response_time_avg = response_stats.get("avg", 0.0)
            
            error_stats = collector.get_statistics("errors.total")
            if error_stats:
                total_requests = collector.get_statistics("requests.total")
                if total_requests and total_requests.get("sum", 0) > 0:
                    error_rate = error_stats.get("sum", 0) / total_requests.get("sum", 1)
        except Exception:
            pass
        
        return PerformanceMetric(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            active_connections=active_connections,
            response_time_avg=response_time_avg,
            error_rate=error_rate
        )
    
    def get_current_metrics(self) -> Optional[PerformanceMetric]:
        """現在のメトリクスを取得"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_metrics_trend(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """
        メトリクストレンドを取得
        
        Args:
            duration_minutes: 期間（分）
            
        Returns:
            トレンド情報
        """
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [
            m for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        return {
            "duration_minutes": duration_minutes,
            "sample_count": len(recent_metrics),
            "cpu": {
                "avg": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
                "min": min(m.cpu_percent for m in recent_metrics),
                "max": max(m.cpu_percent for m in recent_metrics),
                "trend": self._calculate_trend([m.cpu_percent for m in recent_metrics])
            },
            "memory": {
                "avg": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
                "min": min(m.memory_percent for m in recent_metrics),
                "max": max(m.memory_percent for m in recent_metrics),
                "trend": self._calculate_trend([m.memory_percent for m in recent_metrics])
            },
            "response_time": {
                "avg": sum(m.response_time_avg for m in recent_metrics) / len(recent_metrics),
                "min": min(m.response_time_avg for m in recent_metrics),
                "max": max(m.response_time_avg for m in recent_metrics),
                "trend": self._calculate_trend([m.response_time_avg for m in recent_metrics])
            },
            "error_rate": {
                "avg": sum(m.error_rate for m in recent_metrics) / len(recent_metrics),
                "trend": self._calculate_trend([m.error_rate for m in recent_metrics])
            }
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """トレンドを計算（"increasing", "decreasing", "stable"）"""
        if len(values) < 2:
            return "stable"
        
        # 前半と後半の平均を比較
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / len(values[mid:])
        
        threshold = 0.05  # 5%の変化を閾値とする
        
        if second_half_avg > first_half_avg * (1 + threshold):
            return "increasing"
        elif second_half_avg < first_half_avg * (1 - threshold):
            return "decreasing"
        else:
            return "stable"
    
    def analyze_performance_issues(self) -> List[Dict[str, Any]]:
        """パフォーマンス問題を分析"""
        issues = []
        
        if not self.metrics_history:
            return issues
        
        recent_metrics = list(self.metrics_history)[-100:]  # 直近100件
        
        # CPU使用率が高い
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        if avg_cpu > 80:
            issues.append({
                "type": "high_cpu",
                "severity": "warning" if avg_cpu < 90 else "error",
                "message": f"CPU使用率が高い: {avg_cpu:.1f}%",
                "recommendation": "プロセスの最適化またはリソースの追加を検討"
            })
        
        # メモリ使用率が高い
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        if avg_memory > 85:
            issues.append({
                "type": "high_memory",
                "severity": "warning" if avg_memory < 95 else "error",
                "message": f"メモリ使用率が高い: {avg_memory:.1f}%",
                "recommendation": "キャッシュサイズの削減またはメモリの追加を検討"
            })
        
        # レスポンス時間が遅い
        avg_response_time = sum(m.response_time_avg for m in recent_metrics) / len(recent_metrics)
        if avg_response_time > 2.0:
            issues.append({
                "type": "slow_response",
                "severity": "warning" if avg_response_time < 5.0 else "error",
                "message": f"平均レスポンス時間が遅い: {avg_response_time:.3f}秒",
                "recommendation": "キャッシュの有効化、データベースクエリの最適化を検討"
            })
        
        # エラー率が高い
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        if avg_error_rate > 0.05:  # 5%
            issues.append({
                "type": "high_error_rate",
                "severity": "error",
                "message": f"エラー率が高い: {avg_error_rate:.2%}",
                "recommendation": "エラーログを確認し、根本原因を特定"
            })
        
        return issues
    
    def get_summary(self) -> Dict[str, Any]:
        """サマリーを取得"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        current = self.get_current_metrics()
        trend = self.get_metrics_trend(60)
        issues = self.analyze_performance_issues()
        
        return {
            "status": "monitoring" if self.monitoring else "stopped",
            "current": {
                "cpu_percent": current.cpu_percent if current else None,
                "memory_percent": current.memory_percent if current else None,
                "response_time_avg": current.response_time_avg if current else None
            },
            "trend": trend,
            "issues": issues,
            "history_size": len(self.metrics_history)
        }


# シングルトンインスタンス
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(history_size: int = 1000) -> PerformanceMonitor:
    """パフォーマンス監視システムのシングルトン取得"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(history_size=history_size)
    return _performance_monitor








