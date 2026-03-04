#!/usr/bin/env python3
"""
Job Queue Manager - Phase 2実装
Redisベースのジョブキュー管理
"""

import redis
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class JobQueueManager:
    """Redisベースのジョブキュー管理"""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        queue_name: str = "manaos:gpu:jobs",
        result_prefix: str = "manaos:gpu:results:",
        log_dir: str = "/root/logs/runpod_integration"
    ):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
        self.queue_name = queue_name
        self.result_prefix = result_prefix
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        log_file = self.log_dir / "queue_manager.log"
        with open(log_file, "a") as f:
            f.write(log_message + "\n")
    
    def submit_job(self, job_data: Dict[str, Any]) -> str:
        """
        ジョブをキューに投入
        
        Args:
            job_data: ジョブデータ（type, parameters等）
            
        Returns:
            job_id: ジョブID
        """
        job_id = str(uuid.uuid4())
        
        job = {
            "job_id": job_id,
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
            "data": job_data
        }
        
        # Redisキューに追加
        self.redis_client.rpush(self.queue_name, json.dumps(job))
        
        # ジョブ状態を保存
        self.redis_client.setex(
            f"{self.result_prefix}{job_id}:status",
            3600,  # 1時間TTL
            "pending"
        )
        
        self._log(f"ジョブ投入: {job_id} - Type: {job_data.get('type', 'unknown')}")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """ジョブの状態を取得"""
        status = self.redis_client.get(f"{self.result_prefix}{job_id}:status")
        return status
    
    def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """ジョブの結果を取得"""
        result_json = self.redis_client.get(f"{self.result_prefix}{job_id}:result")
        if result_json:
            return json.loads(result_json)
        return None
    
    def wait_for_result(
        self,
        job_id: str,
        timeout: int = 600,
        poll_interval: float = 2.0
    ) -> Dict[str, Any]:
        """
        ジョブの完了を待機して結果を取得
        
        Args:
            job_id: ジョブID
            timeout: タイムアウト秒数
            poll_interval: ポーリング間隔
            
        Returns:
            結果辞書
        """
        self._log(f"ジョブ完了待機: {job_id}")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status == "completed":
                result = self.get_job_result(job_id)
                if result:
                    self._log(f"ジョブ完了: {job_id}")
                    return {
                        "success": True,
                        "job_id": job_id,
                        "result": result
                    }
            
            elif status == "failed":
                error = self.redis_client.get(f"{self.result_prefix}{job_id}:error")
                self._log(f"ジョブ失敗: {job_id} - {error}", "ERROR")
                return {
                    "success": False,
                    "job_id": job_id,
                    "error": error or "Unknown error"
                }
            
            elif status is None:
                self._log(f"ジョブが見つかりません: {job_id}", "ERROR")
                return {
                    "success": False,
                    "job_id": job_id,
                    "error": "Job not found"
                }
            
            time.sleep(poll_interval)
        
        # タイムアウト
        self._log(f"ジョブタイムアウト: {job_id}", "ERROR")
        return {
            "success": False,
            "job_id": job_id,
            "error": "Timeout"
        }
    
    def get_queue_length(self) -> int:
        """キューの長さを取得"""
        return self.redis_client.llen(self.queue_name)
    
    def get_pending_jobs(self) -> List[str]:
        """待機中のジョブIDリストを取得"""
        jobs = self.redis_client.lrange(self.queue_name, 0, -1)
        job_ids = []
        for job_json in jobs:
            job = json.loads(job_json)
            job_ids.append(job["job_id"])
        return job_ids
    
    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセル"""
        status = self.get_job_status(job_id)
        
        if status == "pending":
            # キューから削除
            jobs = self.redis_client.lrange(self.queue_name, 0, -1)
            for i, job_json in enumerate(jobs):
                job = json.loads(job_json)
                if job["job_id"] == job_id:
                    self.redis_client.lrem(self.queue_name, 1, job_json)
                    self.redis_client.setex(
                        f"{self.result_prefix}{job_id}:status",
                        3600,
                        "cancelled"
                    )
                    self._log(f"ジョブキャンセル: {job_id}")
                    return True
            
        return False
    
    def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            self.redis_client.ping()
            queue_length = self.get_queue_length()
            
            return {
                "success": True,
                "redis_connected": True,
                "queue_length": queue_length,
                "pending_jobs": self.get_pending_jobs()
            }
        except Exception as e:
            self._log(f"ヘルスチェック失敗: {e}", "ERROR")
            return {
                "success": False,
                "redis_connected": False,
                "error": str(e)
            }


def main():
    """テスト用"""
    print("🔧 Job Queue Manager - Test\n")
    
    manager = JobQueueManager()
    
    # ヘルスチェック
    print("1️⃣ Health Check...")
    health = manager.health_check()
    print(f"Result: {json.dumps(health, indent=2)}\n")
    
    # ジョブ投入テスト
    print("2️⃣ Submit Test Job...")
    job_id = manager.submit_job({
        "type": "test",
        "message": "Hello from queue manager"
    })
    print(f"Job ID: {job_id}")
    print(f"Queue Length: {manager.get_queue_length()}\n")
    
    # ステータス確認
    print("3️⃣ Check Status...")
    status = manager.get_job_status(job_id)
    print(f"Status: {status}\n")
    
    print("✅ Test completed!")


if __name__ == "__main__":
    main()


