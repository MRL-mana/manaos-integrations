#!/usr/bin/env python3
"""
RunPod Trinity Worker - 簡易版
Redis接続ができない場合でも動作するようにエラーハンドリング強化
"""

import redis
import json
import time
from datetime import datetime

try:
    import torch
    from diffusers import StableDiffusionPipeline
    GPU_AVAILABLE = torch.cuda.is_available()
    print(f"🔥 GPU利用可能: {GPU_AVAILABLE}")
except ImportError as e:
    GPU_AVAILABLE = False
    print(f"⚠️  GPU処理ライブラリが利用できません: {e}")

try:
    import boto3
    from botocore.client import Config
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    print("⚠️  boto3が利用できません")

class Worker:
    def __init__(self):
        self.redis_host = "163.44.120.49"
        self.redis_port = 6379
        self.queue_name = "manaos:gpu:jobs"
        self.result_prefix = "manaos:gpu:results:"

        # Redis接続（エラーハンドリング付き）
        self.redis = None
        self._connect_redis()

        # S3設定
        if S3_AVAILABLE:
            try:
                self.s3 = boto3.client(  # type: ignore[possibly-unbound]
                    's3',
                    endpoint_url="https://s3.runpod.io",
                    aws_access_key_id="user_30Jv2icwfZKwAKA03cn8MZ3800z",
                    aws_secret_access_key="user_30Jv2icwfZKwAKA03cn8MZ3800z",
                    config=Config(signature_version='s3v4')  # type: ignore[possibly-unbound]
                )
                self.bucket = "q369xyumxq"
                print("✅ S3接続初期化完了")
            except Exception as e:
                print(f"⚠️  S3初期化失敗: {e}")
                self.s3 = None
        else:
            self.s3 = None

    def _connect_redis(self):
        """Redis接続を試行"""
        try:
            self.redis = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30
            )
            self.redis.ping()
            print(f"✅ Redis接続成功: {self.redis_host}:{self.redis_port}")
            return True
        except Exception as e:
            print(f"⚠️  Redis接続失敗: {e}")
            print("   接続を再試行します...")
            self.redis = None
            return False

    def _log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def generate_image(self, data):
        """画像生成"""
        try:
            prompt = data.get("prompt", "A beautiful landscape")
            steps = data.get("steps", 50)
            width = data.get("width", 1024)
            height = data.get("height", 1024)

            self._log(f"🎨 画像生成開始: {prompt}")

            if not GPU_AVAILABLE:
                return {"success": False, "error": "GPU is not available"}

            pipe = StableDiffusionPipeline.from_pretrained(  # type: ignore[possibly-unbound]
                'stabilityai/stable-diffusion-2-1',
                torch_dtype=torch.float16  # type: ignore[possibly-unbound]
            ).to('cuda')

            image = pipe(
                prompt,
                num_inference_steps=steps,
                width=width,
                height=height
            ).images[0]

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_path = f"/workspace/generated_{timestamp}.png"
            image.save(image_path)

            self._log(f"✅ 画像保存: {image_path}")

            # S3にアップロード
            s3_path = None
            if self.s3:
                try:
                    s3_key = f"Generated/{timestamp}.png"
                    self.s3.upload_file(image_path, self.bucket, s3_key)
                    s3_path = f"s3://{self.bucket}/{s3_key}"
                    self._log(f"📤 S3アップロード完了: {s3_path}")
                except Exception as e:
                    self._log(f"⚠️  S3アップロード失敗: {e}")

            return {
                "success": True,
                "image_path": image_path,
                "s3_path": s3_path,
                "prompt": prompt
            }
        except Exception as e:
            self._log(f"❌ 画像生成エラー: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def process_job(self, job):
        """ジョブ処理"""
        job_id = job.get("job_id")
        job_type = job.get("type") or job.get("data", {}).get("type")

        self._log(f"📝 ジョブ処理開始: {job_id} - {job_type}")

        # ステータス更新
        if self.redis:
            try:
                self.redis.setex(f"{self.result_prefix}{job_id}:status", 3600, "processing")
            except Exception:
                pass

        try:
            if job_type == "image_generation":
                result = self.generate_image(job.get("data", {}))
            else:
                result = {"success": False, "error": f"Unknown job type: {job_type}"}

            # 結果保存
            if self.redis:
                try:
                    if result.get("success"):
                        self.redis.setex(f"{self.result_prefix}{job_id}:status", 3600, "completed")
                        self.redis.setex(f"{self.result_prefix}{job_id}:result", 3600, json.dumps(result))
                    else:
                        self.redis.setex(f"{self.result_prefix}{job_id}:status", 3600, "failed")
                        self.redis.setex(f"{self.result_prefix}{job_id}:error", 3600, result.get("error", "Unknown"))
                except Exception as e:
                    self._log(f"⚠️  Redis結果保存エラー: {e}")

            if result.get("success"):
                self._log(f"✅ ジョブ完了: {job_id}")
            else:
                self._log(f"❌ ジョブ失敗: {job_id} - {result.get('error')}")

            return result
        except Exception as e:
            self._log(f"💥 処理エラー: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def run(self):
        """ワーカーメインループ"""
        self._log("🔄 Worker開始")

        while True:
            # Redis接続確認
            if not self.redis:
                if not self._connect_redis():
                    self._log("   10秒後に再接続を試みます...")
                    time.sleep(10)
                    continue

            try:
                # ジョブ取得
                job_data = self.redis.blpop(self.queue_name, timeout=5)  # type: ignore[union-attr]

                if job_data:
                    _, job_json = job_data
                    job = json.loads(job_json)
                    self.process_job(job)

            except redis.exceptions.ConnectionError:
                self._log("🔌 Redis接続エラー")
                self.redis = None
                time.sleep(10)
            except Exception as e:
                self._log(f"💥 エラー: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)

if __name__ == "__main__":
    print("🚀 RunPod Trinity Worker - Starting\n")

    worker = Worker()

    if not worker.redis:
        print("⚠️  Redis接続できませんが、接続を試行しながら続行します\n")

    try:
        worker.run()
    except KeyboardInterrupt:
        print("\n🛑 Worker停止")








