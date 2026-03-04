#!/usr/bin/env python3
"""
RunPod Trinity Worker (Enhanced)
実用レベル対応版：ハートビート、エラーハンドリング強化、リトライ機能
"""

import redis
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
import base64
from io import BytesIO
import signal

# 既存のインポート
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import boto3
    from botocore.client import Config
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

try:
    import torch
    from diffusers import StableDiffusionPipeline
    GPU_AVAILABLE = torch.cuda.is_available()
except ImportError:
    GPU_AVAILABLE = False

# 元のWorkerクラスをインポート（再利用）
# 相対インポートを試行、失敗した場合は絶対パス
try:
    from runpod_trinity_worker import RunPodTrinityWorker
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from runpod_trinity_worker import RunPodTrinityWorker


class RunPodTrinityWorkerEnhanced(RunPodTrinityWorker):
    """RunPod Trinity Worker（実用レベル対応版）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ハートビート設定
        self.heartbeat_interval = 30  # 30秒ごとにハートビート
        self.heartbeat_key = "manaos:gpu:worker:heartbeat"
        self.last_heartbeat = 0

        # エラー統計
        self.error_count = 0
        self.success_count = 0
        self.last_error_time = None

        # シグナルハンドラ設定
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self.running = True
        self._log("🚀 Enhanced Worker起動完了")

    def _signal_handler(self, signum, frame):
        """シグナルハンドラ（Graceful shutdown）"""
        self._log(f"🛑 シグナル受信: {signum}。終了処理を開始します...")
        self.running = False

    def _send_heartbeat(self):
        """ハートビートを送信"""
        try:
            heartbeat_data = {
                "worker_id": self.worker_id,
                "timestamp": datetime.now().isoformat(),
                "status": "running",
                "error_count": self.error_count,
                "success_count": self.success_count,
                "queue_length": self.redis_client.llen(self.queue_name)
            }

            self.redis_client.setex(
                self.heartbeat_key,
                120,  # 2分間有効
                json.dumps(heartbeat_data, ensure_ascii=False)
            )

            self.last_heartbeat = time.time()
        except Exception as e:
            self._log(f"⚠️  ハートビート送信エラー: {e}", "WARNING")

    def _retry_job(self, job: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """ジョブをリトライ"""
        job_id = job.get("job_id")
        retry_count = job.get("retry_count", 0)

        if retry_count >= max_retries:
            self._log(f"❌ ジョブリトライ上限到達: {job_id} ({retry_count}/{max_retries})", "ERROR")
            return {"success": False, "error": "Max retries exceeded", "retry_count": retry_count}

        # 指数バックオフ
        wait_time = 2 ** retry_count
        self._log(f"🔄 ジョブリトライ: {job_id} ({retry_count + 1}/{max_retries}) - {wait_time}秒待機")
        time.sleep(wait_time)

        # リトライカウントを増やして再処理
        job["retry_count"] = retry_count + 1
        return self.process_job(job)

    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """ジョブ処理（エラーハンドリング強化版）"""
        job_id = job.get("job_id")
        job_type = job.get("type") or job.get("data", {}).get("type")

        if not job_type:
            self._log(f"❌ ジョブタイプが不明: {job}", "ERROR")
            return {"success": False, "error": "Job type not found"}

        self._log(f"📝 ジョブ処理開始: {job_id} - Type: {job_type}")

        # ステータス更新
        try:
            self.redis_client.setex(
                f"{self.result_prefix}{job_id}:status",
                3600,
                "processing"
            )
        except Exception as e:
            self._log(f"⚠️  ステータス更新エラー: {e}", "WARNING")

        try:
            # 元の処理を実行
            result = super().process_job(job)

            # 結果に基づいて統計更新
            if result.get("success"):
                self.success_count += 1
            else:
                self.error_count += 1
                self.last_error_time = datetime.now().isoformat()

                # リトライ可能なエラーの場合
                error = result.get("error", "")
                retryable_errors = [
                    "GPU_OOM",
                    "REDIS_CONNECTION_ERROR",
                    "MODEL_LOAD_ERROR",
                    "S3_UPLOAD_ERROR",
                    "TIMEOUT"
                ]

                if any(err in error for err in retryable_errors):
                    self._log(f"🔄 リトライ可能なエラー: {error}")
                    return self._retry_job(job)

            return result

        except redis.exceptions.ConnectionError as e:
            self._log(f"🔌 Redis接続エラー: {e}", "ERROR")
            self.error_count += 1

            # Redis接続エラーはリトライ
            return self._retry_job(job)

        except Exception as e:
            self._log(f"💥 ジョブ処理エラー: {e}", "ERROR")
            self._log(traceback.format_exc(), "ERROR")
            self.error_count += 1
            self.last_error_time = datetime.now().isoformat()

            # エラー結果を保存
            try:
                self.redis_client.setex(
                    f"{self.result_prefix}{job_id}:status",
                    3600,
                    "failed"
                )
                self.redis_client.setex(
                    f"{self.result_prefix}{job_id}:error",
                    3600,
                    str(e)
                )
            except:
                pass

            return {"success": False, "error": str(e)}

    def run(self, poll_interval: float = 2.0):
        """ワーカーメインループ（ハートビート対応）"""
        self._log("🔄 Enhanced Workerループ開始")

        try:
            while self.running:
                try:
                    # ハートビート送信
                    if time.time() - self.last_heartbeat > self.heartbeat_interval:
                        self._send_heartbeat()

                    # Redisキューからジョブを取得（ブロッキング）
                    job_data = self.redis_client.blpop(self.queue_name, timeout=5)

                    if job_data:
                        _, job_json = job_data
                        job = json.loads(job_json)
                        self.process_job(job)

                except redis.exceptions.ConnectionError as e:
                    self._log(f"🔌 Redis接続エラー: {e}", "ERROR")
                    time.sleep(10)
                except Exception as e:
                    self._log(f"💥 Workerエラー: {e}", "ERROR")
                    traceback.print_exc()
                    time.sleep(5)

        except KeyboardInterrupt:
            self._log("🛑 Worker停止（KeyboardInterrupt）")
        finally:
            self._log("🛑 Enhanced Worker終了")
            # 最終ハートビート
            self._send_heartbeat()


def main():
    """メイン関数"""
    print("🚀 RunPod Trinity GPU Worker (Enhanced) - Starting\n")

    # 環境変数から設定を読み込む
    redis_host = os.getenv("REDIS_HOST", "163.44.120.49")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    worker = RunPodTrinityWorkerEnhanced(
        redis_host=redis_host,
        redis_port=redis_port
    )

    # ヘルスチェック
    try:
        worker.redis_client.ping()
        print("✅ Redis接続成功\n")
    except Exception as e:
        print(f"❌ Redis接続失敗: {e}\n")
        sys.exit(1)

    # Worker起動
    print("🔄 Enhanced Workerジョブ監視開始...\n")
    worker.run()


if __name__ == "__main__":
    main()

