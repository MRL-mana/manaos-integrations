#!/usr/bin/env python3
"""
MRL Memory Metrics
パフォーマンス測定
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import json

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
logger = get_service_logger("mrl-memory-metrics")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MRLMemoryMetrics:
    """
    パフォーマンス測定
    
    指標:
    - Latency: 入力長に対する処理時間（p50/p95）
    - Memory slot utilization: スロット使用分布（偏りの有無）
    - Write amplification: チャンク数に対して更新回数が増えすぎてないか
    """
    
    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            metrics_dir: メトリクス保存ディレクトリ
        """
        if metrics_dir is None:
            metrics_dir = Path(__file__).parent / "mrl_memory" / "metrics"
        
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # メトリクスストレージ
        self.latency_history: List[Dict[str, Any]] = []
        self.slot_usage_history: List[Dict[str, Any]] = []
        self.write_amplification_history: List[Dict[str, Any]] = []
        
        # 観測指標
        self.write_count_per_minute: List[Dict[str, Any]] = []  # 書き込み回数/分
        self.gate_block_rate_history: List[Dict[str, Any]] = []  # ゲート遮断率
        self.conflict_detection_rate_history: List[Dict[str, Any]] = []  # 矛盾検出率
        
        # Windows(cp932)でも壊れないログにする（絵文字禁止）
        logger.info(f"[OK] MRL Memory Metrics初期化完了: {self.metrics_dir}")
    
    def record_latency(
        self,
        input_length: int,
        processing_time: float,
        operation: str = "process"
    ):
        """
        レイテンシを記録
        
        Args:
            input_length: 入力長（文字数）
            processing_time: 処理時間（秒）
            operation: 操作タイプ
        """
        self.latency_history.append({
            "timestamp": datetime.now().isoformat(),
            "input_length": input_length,
            "processing_time": processing_time,
            "operation": operation,
            "throughput": input_length / processing_time if processing_time > 0 else 0
        })
        
        # 最新100件を保持
        if len(self.latency_history) > 100:
            self.latency_history = self.latency_history[-100:]
    
    def record_slot_usage(
        self,
        slot_usage: Dict[str, int],
        total_slots: int
    ):
        """
        スロット使用分布を記録
        
        Args:
            slot_usage: スロット使用状況
            total_slots: 総スロット数
        """
        # 使用率を計算
        used_slots = sum(slot_usage.values())
        utilization = used_slots / total_slots if total_slots > 0 else 0
        
        # 分散を計算（偏りの有無）
        usage_values = list(slot_usage.values())
        if usage_values:
            import statistics
            variance = statistics.variance(usage_values) if len(usage_values) > 1 else 0
        else:
            variance = 0
        
        self.slot_usage_history.append({
            "timestamp": datetime.now().isoformat(),
            "used_slots": used_slots,
            "total_slots": total_slots,
            "utilization": utilization,
            "variance": variance,
            "slot_usage": slot_usage
        })
        
        # 最新50件を保持
        if len(self.slot_usage_history) > 50:
            self.slot_usage_history = self.slot_usage_history[-50:]
    
    def record_write_amplification(
        self,
        chunk_count: int,
        update_count: int
    ):
        """
        Write amplificationを記録
        
        Args:
            chunk_count: チャンク数
            update_count: 更新回数
        """
        amplification = update_count / chunk_count if chunk_count > 0 else 0
        
        self.write_amplification_history.append({
            "timestamp": datetime.now().isoformat(),
            "chunk_count": chunk_count,
            "update_count": update_count,
            "amplification": amplification
        })
        
        # 最新50件を保持
        if len(self.write_amplification_history) > 50:
            self.write_amplification_history = self.write_amplification_history[-50:]
    
    def get_latency_stats(self) -> Dict[str, Any]:
        """レイテンシ統計を取得"""
        if not self.latency_history:
            return {}
        
        processing_times = [h["processing_time"] for h in self.latency_history]
        processing_times.sort()
        
        p50 = processing_times[len(processing_times) // 2]
        p95 = processing_times[int(len(processing_times) * 0.95)]
        
        return {
            "count": len(processing_times),
            "p50": p50,
            "p95": p95,
            "min": min(processing_times),
            "max": max(processing_times),
            "mean": sum(processing_times) / len(processing_times)
        }
    
    def get_slot_utilization_stats(self) -> Dict[str, Any]:
        """スロット使用率統計を取得"""
        if not self.slot_usage_history:
            return {}
        
        utilizations = [h["utilization"] for h in self.slot_usage_history]
        variances = [h["variance"] for h in self.slot_usage_history]
        
        return {
            "count": len(utilizations),
            "mean_utilization": sum(utilizations) / len(utilizations),
            "mean_variance": sum(variances) / len(variances),
            "max_variance": max(variances) if variances else 0
        }
    
    def get_write_amplification_stats(self) -> Dict[str, Any]:
        """Write amplification統計を取得"""
        if not self.write_amplification_history:
            return {}
        
        amplifications = [h["amplification"] for h in self.write_amplification_history]
        
        return {
            "count": len(amplifications),
            "mean": sum(amplifications) / len(amplifications),
            "max": max(amplifications),
            "min": min(amplifications)
        }
    
    def record_write_count(self, count: int):
        """
        書き込み回数を記録（1分あたり）
        
        Args:
            count: 書き込み回数
        """
        self.write_count_per_minute.append({
            "timestamp": datetime.now().isoformat(),
            "write_count": count
        })
        
        # 最新60件を保持（1時間分）
        if len(self.write_count_per_minute) > 60:
            self.write_count_per_minute = self.write_count_per_minute[-60:]
    
    def record_gate_block_rate(
        self,
        total_entries: int,
        blocked_entries: int
    ):
        """
        ゲート遮断率を記録
        
        Args:
            total_entries: 総エントリ数
            blocked_entries: 遮断されたエントリ数
        """
        block_rate = blocked_entries / total_entries if total_entries > 0 else 0
        
        self.gate_block_rate_history.append({
            "timestamp": datetime.now().isoformat(),
            "total_entries": total_entries,
            "blocked_entries": blocked_entries,
            "block_rate": block_rate
        })
        
        # 最新100件を保持
        if len(self.gate_block_rate_history) > 100:
            self.gate_block_rate_history = self.gate_block_rate_history[-100:]
    
    def record_conflict_detection_rate(
        self,
        total_results: int,
        conflicts: int
    ):
        """
        矛盾検出率を記録
        
        Args:
            total_results: 総結果数
            conflicts: 矛盾数
        """
        conflict_rate = conflicts / total_results if total_results > 0 else 0
        
        self.conflict_detection_rate_history.append({
            "timestamp": datetime.now().isoformat(),
            "total_results": total_results,
            "conflicts": conflicts,
            "conflict_rate": conflict_rate
        })
        
        # 最新100件を保持
        if len(self.conflict_detection_rate_history) > 100:
            self.conflict_detection_rate_history = self.conflict_detection_rate_history[-100:]
    
    def get_write_count_stats(self) -> Dict[str, Any]:
        """書き込み回数統計を取得"""
        if not self.write_count_per_minute:
            return {}
        
        counts = [h["write_count"] for h in self.write_count_per_minute]
        
        return {
            "count": len(counts),
            "mean": sum(counts) / len(counts),
            "max": max(counts),
            "min": min(counts),
            "current": counts[-1] if counts else 0
        }
    
    def get_gate_block_rate_stats(self) -> Dict[str, Any]:
        """ゲート遮断率統計を取得"""
        if not self.gate_block_rate_history:
            return {}
        
        block_rates = [h["block_rate"] for h in self.gate_block_rate_history]
        
        return {
            "count": len(block_rates),
            "mean": sum(block_rates) / len(block_rates),
            "max": max(block_rates),
            "min": min(block_rates),
            "current": block_rates[-1] if block_rates else 0
        }
    
    def get_conflict_detection_rate_stats(self) -> Dict[str, Any]:
        """矛盾検出率統計を取得"""
        if not self.conflict_detection_rate_history:
            return {}
        
        conflict_rates = [h["conflict_rate"] for h in self.conflict_detection_rate_history]
        
        return {
            "count": len(conflict_rates),
            "mean": sum(conflict_rates) / len(conflict_rates),
            "max": max(conflict_rates),
            "min": min(conflict_rates),
            "current": conflict_rates[-1] if conflict_rates else 0
        }
    
    def save_metrics(self):
        """メトリクスを保存"""
        metrics_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "latency": self.get_latency_stats(),
            "slot_utilization": self.get_slot_utilization_stats(),
            "write_amplification": self.get_write_amplification_stats(),
            "write_count": self.get_write_count_stats(),
            "gate_block_rate": self.get_gate_block_rate_stats(),
            "conflict_detection_rate": self.get_conflict_detection_rate_stats()
        }
        
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        
        logger.info(f"メトリクスを保存: {metrics_file}")
