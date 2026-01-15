#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ManaOS メトリクス収集システム
パフォーマンスメトリクス、エラーメトリクス、リソースメトリクスの収集
"""

import time
import psutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """メトリクス"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


class MetricsCollector:
    """メトリクス収集システム"""
    
    def __init__(self, max_history: int = 10000):
        """
        初期化
        
        Args:
            max_history: 保持するメトリクスの最大数
        """
        self.max_history = max_history
        self.metrics: deque = deque(maxlen=max_history)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # メトリクスストレージ
        self.storage_path = Path(__file__).parent / "data" / "metrics"
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None, unit: str = ""):
        """
        メトリクスを記録
        
        Args:
            name: メトリクス名
            value: 値
            tags: タグ
            unit: 単位
        """
        metric = Metric(
            name=name,
            value=value,
            tags=tags or {},
            unit=unit
        )
        self.metrics.append(metric)
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """カウンターを増加"""
        key = self._get_key(name, tags)
        self.counters[key] += value
        self.record(name, self.counters[key], tags, "count")
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """ゲージを設定"""
        key = self._get_key(name, tags)
        self.gauges[key] = value
        self.record(name, value, tags, "gauge")
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """ヒストグラムを記録"""
        key = self._get_key(name, tags)
        self.histograms[key].append(value)
        # 最大1000件まで保持
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        self.record(name, value, tags, "histogram")
    
    def _get_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """メトリクスキーを生成"""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}:{tag_str}"
        return name
    
    def get_metrics(self, name: Optional[str] = None, tags: Optional[Dict[str, str]] = None, 
                   start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[Metric]:
        """
        メトリクスを取得
        
        Args:
            name: メトリクス名（フィルタ）
            tags: タグ（フィルタ）
            start_time: 開始時刻
            end_time: 終了時刻
            
        Returns:
            メトリクスリスト
        """
        filtered = list(self.metrics)
        
        if name:
            filtered = [m for m in filtered if m.name == name]
        
        if tags:
            filtered = [m for m in filtered if all(m.tags.get(k) == v for k, v in tags.items())]
        
        if start_time:
            filtered = [m for m in filtered if m.timestamp >= start_time]
        
        if end_time:
            filtered = [m for m in filtered if m.timestamp <= end_time]
        
        return filtered
    
    def get_statistics(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Args:
            name: メトリクス名
            tags: タグ
            
        Returns:
            統計情報
        """
        metrics = self.get_metrics(name=name, tags=tags)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values)
        }
    
    def collect_system_metrics(self):
        """システムメトリクスを収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.set_gauge("system.cpu.percent", cpu_percent, {"type": "total"})
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            self.set_gauge("system.memory.percent", memory.percent)
            self.set_gauge("system.memory.used_mb", memory.used / 1024 / 1024)
            self.set_gauge("system.memory.available_mb", memory.available / 1024 / 1024)
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            self.set_gauge("system.disk.percent", disk.percent)
            self.set_gauge("system.disk.used_gb", disk.used / 1024 / 1024 / 1024)
            self.set_gauge("system.disk.free_gb", disk.free / 1024 / 1024 / 1024)
            
        except Exception as e:
            logger.error(f"システムメトリクス収集エラー: {e}")
    
    def save_metrics(self, file_path: Optional[Path] = None):
        """メトリクスを保存"""
        file_path = file_path or self.storage_path / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            metrics_data = [asdict(m) for m in self.metrics]
            
            # タイムスタンプを文字列に変換
            for m in metrics_data:
                m['timestamp'] = m['timestamp'].isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "metrics": metrics_data,
                    "counters": dict(self.counters),
                    "gauges": dict(self.gauges),
                    "histograms": {k: v[-100:] for k, v in self.histograms.items()}
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ メトリクスを保存しました: {file_path}")
            
        except Exception as e:
            logger.error(f"メトリクス保存エラー: {e}")
    
    def load_metrics(self, file_path: Path):
        """メトリクスを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # メトリクスを復元
            for m_data in data.get("metrics", []):
                m_data['timestamp'] = datetime.fromisoformat(m_data['timestamp'])
                metric = Metric(**m_data)
                self.metrics.append(metric)
            
            # カウンター、ゲージ、ヒストグラムを復元
            self.counters.update(data.get("counters", {}))
            self.gauges.update(data.get("gauges", {}))
            self.histograms.update(data.get("histograms", {}))
            
            logger.info(f"✅ メトリクスを読み込みました: {file_path}")
            
        except Exception as e:
            logger.error(f"メトリクス読み込みエラー: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """サマリーを取得"""
        return {
            "total_metrics": len(self.metrics),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histogram_count": len(self.histograms),
            "recent_metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in list(self.metrics)[-10:]
            ]
        }


# シングルトンインスタンス
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(max_history: int = 10000) -> MetricsCollector:
    """メトリクス収集システムのシングルトン取得"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(max_history=max_history)
    return _metrics_collector
