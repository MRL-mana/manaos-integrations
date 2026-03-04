#!/usr/bin/env python3
"""
Enhanced Job Queue Manager
動的サイズ調整、優先度付きキュー、自動クリーンアップ機能を提供
"""

import os
import queue
import threading
import time
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from enum import IntEnum

logger = logging.getLogger(__name__)

class JobPriority(IntEnum):
    """ジョブ優先度"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0

class EnhancedJobQueue:
    """強化されたジョブキュー管理システム"""

    def __init__(
        self,
        initial_size: int = 10,
        min_size: int = 5,
        max_size: int = 50,
        auto_cleanup: bool = True,
        cleanup_interval: int = 300,  # 5分
        job_timeout: int = 3600  # 1時間
    ):
        self.min_size = min_size
        self.max_size = max_size
        self.current_size = initial_size
        self.auto_cleanup = auto_cleanup
        self.cleanup_interval = cleanup_interval
        self.job_timeout = job_timeout

        # 優先度付きキュー（優先度が低いほど先に処理）
        self.queues = {
            JobPriority.URGENT: queue.Queue(maxsize=max_size),
            JobPriority.HIGH: queue.Queue(maxsize=max_size),
            JobPriority.NORMAL: queue.Queue(maxsize=max_size),
            JobPriority.LOW: queue.Queue(maxsize=max_size)
        }

        # ジョブ情報管理
        self.job_info: Dict[str, Dict[str, Any]] = {}
        self.job_lock = threading.Lock()

        # 統計情報
        self.stats = {
            "total_added": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_timeout": 0,
            "avg_duration": 0.0,
            "max_queue_size": 0
        }

        # 自動クリーンアップスレッド
        if self.auto_cleanup:
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()

        # 動的サイズ調整スレッド
        self.adjust_thread = threading.Thread(target=self._adjust_size_loop, daemon=True)
        self.adjust_thread.start()

        logger.info(f"✅ Enhanced Job Queue初期化完了 (初期サイズ: {initial_size}, 範囲: {min_size}-{max_size})")

    def put(self, job_id: str, job_type: str, data: Dict[str, Any], priority: JobPriority = JobPriority.NORMAL, timeout: Optional[float] = None) -> bool:
        """
        ジョブをキューに追加

        Args:
            job_id: ジョブID
            job_type: ジョブタイプ
            data: ジョブデータ
            priority: 優先度
            timeout: タイムアウト（秒）

        Returns:
            True: 成功, False: キューが満杯
        """
        try:
            job_queue = self.queues[priority]

            # ノンブロッキングで追加を試行
            job_queue.put_nowait((job_id, job_type, data))

            # ジョブ情報を記録
            with self.job_lock:
                self.job_info[job_id] = {
                    "job_type": job_type,
                    "priority": priority.name,
                    "data": data,
                    "added_at": datetime.now().isoformat(),
                    "timeout_at": (datetime.now() + timedelta(seconds=timeout or self.job_timeout)).isoformat(),
                    "status": "queued"
                }

            # 統計更新
            self.stats["total_added"] += 1
            total_size = sum(q.qsize() for q in self.queues.values())
            if total_size > self.stats["max_queue_size"]:
                self.stats["max_queue_size"] = total_size

            logger.info(f"📥 ジョブ追加: {job_id} (優先度: {priority.name}, キューサイズ: {total_size})")
            return True

        except queue.Full:
            logger.warning(f"⚠️ キューが満杯: {job_id} (優先度: {priority.name})")
            return False

    def get(self, timeout: float = 1.0) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """
        優先度順にジョブを取得

        Args:
            timeout: タイムアウト（秒）

        Returns:
            (job_id, job_type, data) または None
        """
        # 優先度順に取得を試行
        for priority in [JobPriority.URGENT, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
            try:
                job_queue = self.queues[priority]
                job_id, job_type, data = job_queue.get(timeout=timeout)

                # ジョブ情報を更新
                with self.job_lock:
                    if job_id in self.job_info:
                        self.job_info[job_id]["status"] = "processing"
                        self.job_info[job_id]["started_at"] = datetime.now().isoformat()

                return job_id, job_type, data
            except queue.Empty:
                continue

        return None

    def complete_job(self, job_id: str, result: Any = None, duration: float = 0.0):
        """ジョブ完了を記録"""
        with self.job_lock:
            if job_id in self.job_info:
                self.job_info[job_id].update({
                    "status": "completed",
                    "result": result,
                    "duration": duration,
                    "completed_at": datetime.now().isoformat()
                })

        # 統計更新
        self.stats["total_completed"] += 1
        if duration > 0:
            # 移動平均で平均処理時間を更新
            completed_count = self.stats["total_completed"]
            old_avg = self.stats["avg_duration"]
            self.stats["avg_duration"] = (old_avg * (completed_count - 1) + duration) / completed_count

    def fail_job(self, job_id: str, error: str):
        """ジョブ失敗を記録"""
        with self.job_lock:
            if job_id in self.job_info:
                self.job_info[job_id].update({
                    "status": "failed",
                    "error": error,
                    "failed_at": datetime.now().isoformat()
                })

        self.stats["total_failed"] += 1

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """ジョブ状態を取得"""
        with self.job_lock:
            return self.job_info.get(job_id)

    def get_queue_stats(self) -> Dict[str, Any]:
        """キュー統計を取得"""
        queue_sizes = {
            priority.name: q.qsize()
            for priority, q in self.queues.items()
        }
        total_size = sum(queue_sizes.values())

        return {
            "queue_sizes": queue_sizes,
            "total_size": total_size,
            "job_stats": self.stats.copy(),
            "current_max_size": self.current_size,
            "min_size": self.min_size,
            "max_size": self.max_size
        }

    def _cleanup_loop(self):
        """タイムアウトしたジョブを自動クリーンアップ"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_timeout_jobs()
            except Exception as e:
                logger.error(f"❌ クリーンアップロープエラー: {e}")

    def _cleanup_timeout_jobs(self):
        """タイムアウトしたジョブをクリーンアップ"""
        now = datetime.now()
        timeout_count = 0

        with self.job_lock:
            for job_id, info in list(self.job_info.items()):
                if info.get("status") == "processing":
                    try:
                        timeout_at = datetime.fromisoformat(info.get("timeout_at", ""))
                        if now > timeout_at:
                            info.update({
                                "status": "timeout",
                                "timeout_at": now.isoformat()
                            })
                            timeout_count += 1
                            self.stats["total_timeout"] += 1
                            logger.warning(f"⏰ ジョブタイムアウト: {job_id}")
                    except Exception as e:
                        logger.error(f"❌ タイムアウトチェックエラー ({job_id}): {e}")

        if timeout_count > 0:
            logger.info(f"🧹 タイムアウトジョブをクリーンアップ: {timeout_count}件")

    def _adjust_size_loop(self):
        """システム負荷に応じてキューサイズを動的調整"""
        while True:
            try:
                time.sleep(60)  # 1分ごとにチェック
                self._adjust_queue_size()
            except Exception as e:
                logger.error(f"❌ サイズ調整ループエラー: {e}")

    def _adjust_queue_size(self):
        """キューサイズを動的に調整"""
        try:
            # CPUとメモリ使用率を取得
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent

            # 現在のキューサイズ
            current_queue_size = sum(q.qsize() for q in self.queues.values())

            # システム負荷が低い場合、キューサイズを拡張
            if cpu_percent < 50 and memory_percent < 70:
                if current_queue_size > self.current_size * 0.8:
                    # キューが80%以上埋まっている場合、サイズを拡張
                    new_size = min(self.current_size + 5, self.max_size)
                    if new_size > self.current_size:
                        self.current_size = new_size
                        logger.info(f"📈 キューサイズ拡張: {self.current_size} (CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%)")

            # システム負荷が高い場合、キューサイズを縮小
            elif cpu_percent > 80 or memory_percent > 85:
                if current_queue_size < self.current_size * 0.5:
                    # キューが50%未満の場合、サイズを縮小
                    new_size = max(self.current_size - 5, self.min_size)
                    if new_size < self.current_size:
                        self.current_size = new_size
                        logger.info(f"📉 キューサイズ縮小: {self.current_size} (CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%)")

        except Exception as e:
            logger.error(f"❌ キューサイズ調整エラー: {e}")

    def resize_queue(self, new_size: int):
        """手動でキューサイズを変更"""
        new_size = max(self.min_size, min(new_size, self.max_size))
        old_size = self.current_size
        self.current_size = new_size

        logger.info(f"🔧 キューサイズ変更: {old_size} → {new_size}")
        return new_size

# グローバルインスタンス
_enhanced_queue: Optional[EnhancedJobQueue] = None

def get_enhanced_queue() -> EnhancedJobQueue:
    """Enhanced Job Queueのシングルトンインスタンスを取得"""
    global _enhanced_queue
    if _enhanced_queue is None:
        initial_size = int(os.getenv("GALLERY_JOB_QUEUE_SIZE", "10"))
        _enhanced_queue = EnhancedJobQueue(
            initial_size=initial_size,
            min_size=5,
            max_size=50
        )
    return _enhanced_queue

