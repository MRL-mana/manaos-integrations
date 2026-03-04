#!/usr/bin/env python3
"""
RunPod Trinity Worker
Trinity達と連携するGPU処理ワーカー
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

# 画像処理用（GPU不要）
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  PILが利用できません。画像処理機能は制限されます。")

# S3保存用
try:
    import boto3
    from botocore.client import Config
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    print("⚠️  boto3が利用できません。S3保存機能は無効です。")

# GPU処理用ライブラリ
try:
    import torch
    from diffusers import StableDiffusionPipeline
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import cv2
    import numpy as np
    GPU_AVAILABLE = torch.cuda.is_available()
    print(f"🔥 GPU利用可能: {GPU_AVAILABLE}")
    if GPU_AVAILABLE:
        print(f"🎯 GPU名: {torch.cuda.get_device_name(0)}")
        print(f"💾 GPU メモリ: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
except ImportError as e:
    GPU_AVAILABLE = False
    print(f"⚠️  GPU処理ライブラリが利用できません: {e}")


class RunPodTrinityWorker:
    """RunPod Trinity GPU Worker"""

    def __init__(
        self,
        redis_host: Optional[str] = None,
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        queue_name: str = "manaos:gpu:jobs",
        result_prefix: str = "manaos:gpu:results:",
        worker_id: Optional[str] = None,
        # S3設定
        s3_enabled: bool = True,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        s3_endpoint: str = "https://s3.runpod.io",
        s3_bucket: str = "q369xyumxq"
    ):
        self.worker_id = worker_id or f"trinity_worker_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.queue_name = queue_name
        self.result_prefix = result_prefix

        # Redis接続設定（環境変数から読み込み）
        self.redis_host = redis_host or os.getenv("REDIS_HOST", "163.44.120.49")
        self.redis_port = redis_port
        self.redis_password = redis_password or os.getenv("REDIS_PASSWORD")

        # Redis接続
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            decode_responses=True
        )

        # GPUモデルキャッシュ
        self.models = {}

        # S3設定
        self.s3_enabled = s3_enabled and S3_AVAILABLE
        if self.s3_enabled:
            try:
                self.s3_access_key = s3_access_key or os.getenv("RUNPOD_S3_ACCESS_KEY", "user_30Jv2icwfZKwAKA03cn8MZ3800z")
                self.s3_secret_key = s3_secret_key or os.getenv("RUNPOD_S3_SECRET_KEY", "user_30Jv2icwfZKwAKA03cn8MZ3800z")
                self.s3_endpoint = s3_endpoint
                self.s3_bucket = s3_bucket

                # S3クライアント初期化
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=self.s3_endpoint,
                    aws_access_key_id=self.s3_access_key,
                    aws_secret_access_key=self.s3_secret_key,
                    config=Config(signature_version='s3v4')
                )
                self._log(f"✅ S3接続初期化完了: {self.s3_endpoint}")
            except Exception as e:
                self._log(f"⚠️  S3初期化失敗: {e}。S3保存機能は無効です。", "WARNING")
                self.s3_enabled = False
        else:
            self.s3_client = None

        self._log(f"🚀 Trinity Worker起動: {self.worker_id}")
        self._log(f"🔥 GPU利用可能: {GPU_AVAILABLE}")
        self._log(f"📦 S3保存機能: {'有効' if self.s3_enabled else '無効'}")

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{self.worker_id}] [{level}] {message}"
        print(log_message)

    def _load_stable_diffusion(self):
        """Stable Diffusionモデル読み込み"""
        if "stable_diffusion" not in self.models:
            self._log("📦 Stable Diffusionモデル読み込み中...")
            try:
                pipe = StableDiffusionPipeline.from_pretrained(
                    'stabilityai/stable-diffusion-2-1',
                    torch_dtype=torch.float16
                )
                pipe = pipe.to('cuda')
                self.models["stable_diffusion"] = pipe
                self._log("✅ Stable Diffusionモデル読み込み完了")
            except Exception as e:
                self._log(f"❌ Stable Diffusionモデル読み込みエラー: {e}", "ERROR")
                raise
        return self.models["stable_diffusion"]

    def generate_image(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """画像生成処理"""
        try:
            prompt = job_data.get("prompt", "A beautiful landscape")
            steps = job_data.get("steps", 50)
            width = job_data.get("width", 1024)
            height = job_data.get("height", 1024)

            self._log(f"🎨 画像生成開始: {prompt}")

            # Stable Diffusionモデル読み込み
            pipe = self._load_stable_diffusion()

            # 画像生成
            image = pipe(
                prompt,
                num_inference_steps=steps,
                width=width,
                height=height
            ).images[0]

            # 画像を保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_path = f"/workspace/trinity_generated_{timestamp}.png"
            image.save(image_path)

            # S3にアップロード
            s3_path = None
            if self.s3_enabled:
                try:
                    s3_key = f"Generated/Images/{datetime.now().strftime('%Y-%m-%d')}/trinity_{timestamp}.png"
                    self.s3_client.upload_file(
                        image_path,
                        self.s3_bucket,
                        s3_key,
                        ExtraArgs={'ContentType': 'image/png'}
                    )
                    s3_path = f"s3://{self.s3_bucket}/{s3_key}"
                    self._log(f"📤 S3アップロード完了: {s3_path}")
                except Exception as e:
                    self._log(f"⚠️  S3アップロード失敗: {e}", "WARNING")

            # 画像をBase64エンコード（小さいサイズのみ）
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode()

            self._log(f"✅ 画像生成完了: {image_path}")

            return {
                "success": True,
                "image_path": image_path,
                "image_base64": image_base64,
                "s3_path": s3_path,
                "prompt": prompt,
                "generation_params": {
                    "steps": steps,
                    "width": width,
                    "height": height
                },
                "gpu_info": {
                    "name": torch.cuda.get_device_name(0),
                    "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3
                }
            }

        except Exception as e:
            self._log(f"❌ 画像生成エラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def generate_video(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """動画生成処理"""
        try:
            frames = job_data.get("frames", 100)
            resolution = job_data.get("resolution", "1920x1080")
            width, height = map(int, resolution.split('x'))

            self._log(f"🎬 動画生成開始: {frames}フレーム, {resolution}")

            # 仮想動画フレーム生成
            video_frames = []
            device = torch.device("cuda")

            for i in range(frames):
                # フレーム生成（例：グラデーション動画）
                frame = np.zeros((height, width, 3), dtype=np.uint8)

                # グラデーション効果
                for y in range(height):
                    intensity = int(255 * (y / height))
                    frame[y, :] = [intensity, 128, 255 - intensity]

                # アニメーション効果
                offset = int(50 * np.sin(i * 0.1))
                frame = np.roll(frame, offset, axis=1)

                video_frames.append(frame)

            # GPU処理（フレーム変換）
            tensor_frames = []
            for frame in video_frames[:10]:  # 最初の10フレームのみ処理
                tensor_frame = torch.from_numpy(frame).float().to(device)
                tensor_frames.append(tensor_frame)

            # 動画保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_path = f"/workspace/trinity_video_{timestamp}.mp4"

            # OpenCVで動画作成
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))

            for frame in video_frames:
                out.write(frame)
            out.release()

            # S3にアップロード
            s3_path = None
            if self.s3_enabled:
                try:
                    s3_key = f"Generated/Videos/{datetime.now().strftime('%Y-%m-%d')}/trinity_{timestamp}.mp4"
                    self.s3_client.upload_file(
                        video_path,
                        self.s3_bucket,
                        s3_key,
                        ExtraArgs={'ContentType': 'video/mp4'}
                    )
                    s3_path = f"s3://{self.s3_bucket}/{s3_key}"
                    self._log(f"📤 S3アップロード完了: {s3_path}")
                except Exception as e:
                    self._log(f"⚠️  S3アップロード失敗: {e}", "WARNING")

            self._log(f"✅ 動画生成完了: {video_path}")

            return {
                "success": True,
                "video_path": video_path,
                "s3_path": s3_path,
                "frames_processed": len(tensor_frames),
                "total_frames": frames,
                "resolution": resolution,
                "gpu_info": {
                    "name": torch.cuda.get_device_name(0),
                    "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3
                }
            }

        except Exception as e:
            self._log(f"❌ 動画生成エラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def upload_file_to_s3(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """ファイルをS3にアップロード（GPU不要）"""
        try:
            local_path = job_data.get("local_path")
            s3_key = job_data.get("s3_key")

            if not local_path or not s3_key:
                return {"success": False, "error": "local_path and s3_key are required"}

            if not os.path.exists(local_path):
                return {"success": False, "error": f"Local file not found: {local_path}"}

            self._log(f"📤 ファイルアップロード開始: {local_path} -> s3://{self.s3_bucket}/{s3_key}")

            if not self.s3_enabled:
                return {"success": False, "error": "S3 is not enabled"}

            # S3にアップロード
            self.s3_client.upload_file(
                local_path,
                self.s3_bucket,
                s3_key
            )

            s3_path = f"s3://{self.s3_bucket}/{s3_key}"
            self._log(f"✅ ファイルアップロード完了: {s3_path}")

            return {
                "success": True,
                "local_path": local_path,
                "s3_path": s3_path,
                "s3_key": s3_key
            }

        except Exception as e:
            self._log(f"❌ ファイルアップロードエラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def download_file_from_s3(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """S3からファイルをダウンロード（GPU不要）"""
        try:
            s3_key = job_data.get("s3_key")
            local_path = job_data.get("local_path")

            if not s3_key:
                return {"success": False, "error": "s3_key is required"}

            if not local_path:
                # デフォルトパス
                filename = os.path.basename(s3_key)
                local_path = f"/workspace/downloads/{filename}"
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

            self._log(f"📥 ファイルダウンロード開始: s3://{self.s3_bucket}/{s3_key} -> {local_path}")

            if not self.s3_enabled:
                return {"success": False, "error": "S3 is not enabled"}

            # S3からダウンロード
            self.s3_client.download_file(
                self.s3_bucket,
                s3_key,
                local_path
            )

            file_size = os.path.getsize(local_path)
            self._log(f"✅ ファイルダウンロード完了: {local_path} ({file_size} bytes)")

            return {
                "success": True,
                "s3_key": s3_key,
                "local_path": local_path,
                "file_size": file_size
            }

        except Exception as e:
            self._log(f"❌ ファイルダウンロードエラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def list_s3_files(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """S3内のファイル一覧取得（GPU不要）"""
        try:
            prefix = job_data.get("prefix", "")
            max_files = job_data.get("max_files", 100)

            self._log(f"📋 S3ファイル一覧取得: prefix={prefix}")

            if not self.s3_enabled:
                return {"success": False, "error": "S3 is not enabled"}

            # S3から一覧取得
            files = []
            paginator = self.s3_client.get_paginator('list_objects_v2')

            for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            "key": obj['Key'],
                            "size": obj['Size'],
                            "modified": obj['LastModified'].isoformat()
                        })
                        if len(files) >= max_files:
                            break

                if len(files) >= max_files:
                    break

            self._log(f"✅ ファイル一覧取得完了: {len(files)}件")

            return {
                "success": True,
                "prefix": prefix,
                "files": files,
                "count": len(files)
            }

        except Exception as e:
            self._log(f"❌ ファイル一覧取得エラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def process_image(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """画像処理（リサイズ、フォーマット変換など、GPU不要）"""
        try:
            if not PIL_AVAILABLE:
                return {"success": False, "error": "PIL is not available"}

            input_path = job_data.get("input_path")
            output_path = job_data.get("output_path")
            operation = job_data.get("operation", "resize")  # resize, convert, thumbnail

            if not input_path:
                return {"success": False, "error": "input_path is required"}

            if not output_path:
                # デフォルトパス
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"/workspace/processed_{timestamp}.png"

            self._log(f"🖼️  画像処理開始: {operation} - {input_path}")

            # 画像読み込み
            if input_path.startswith("s3://"):
                # S3からダウンロードしてから処理
                s3_key = input_path.replace(f"s3://{self.s3_bucket}/", "")
                temp_input = f"/tmp/temp_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.s3_client.download_file(self.s3_bucket, s3_key, temp_input)
                input_path = temp_input

            image = Image.open(input_path)

            # 処理実行
            if operation == "resize":
                width = job_data.get("width", 1024)
                height = job_data.get("height", 1024)
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            elif operation == "thumbnail":
                size = job_data.get("size", (256, 256))
                image.thumbnail(size, Image.Resampling.LANCZOS)
            elif operation == "convert":
                format_name = job_data.get("format", "PNG")
                if image.format != format_name:
                    image = image.convert("RGB" if format_name == "JPEG" else "RGBA")

            # 保存
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            image.save(output_path)

            # S3にアップロード（指定があれば）
            s3_path = None
            if self.s3_enabled and job_data.get("upload_to_s3", False):
                s3_key = job_data.get("s3_key") or f"Processed/{datetime.now().strftime('%Y-%m-%d')}/processed_{os.path.basename(output_path)}"
                self.s3_client.upload_file(
                    output_path,
                    self.s3_bucket,
                    s3_key,
                    ExtraArgs={'ContentType': f'image/{image.format.lower()}'}
                )
                s3_path = f"s3://{self.s3_bucket}/{s3_key}"

            self._log(f"✅ 画像処理完了: {output_path}")

            return {
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "s3_path": s3_path,
                "operation": operation,
                "size": image.size
            }

        except Exception as e:
            self._log(f"❌ 画像処理エラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """ジョブ処理のメイン関数"""
        job_id = job.get("job_id")
        # ジョブタイプは job["type"] から取得（互換性のため data["type"] も確認）
        job_type = job.get("type") or job.get("data", {}).get("type")

        if not job_type:
            self._log(f"❌ ジョブタイプが不明: {job}", "ERROR")
            return {"success": False, "error": "Job type not found"}

        self._log(f"📝 Trinityジョブ処理開始: {job_id} - Type: {job_type}")

        # ステータス更新
        self.redis_client.setex(
            f"{self.result_prefix}{job_id}:status",
            3600,
            "processing"
        )

        try:
            # ジョブタイプに応じて処理
            if job_type == "image_generation":
                if not GPU_AVAILABLE:
                    result = {"success": False, "error": "GPU is not available"}
                else:
                    result = self.generate_image(job.get("data", {}))
            elif job_type == "video_generation":
                if not GPU_AVAILABLE:
                    result = {"success": False, "error": "GPU is not available"}
                else:
                    result = self.generate_video(job.get("data", {}))
            elif job_type == "file_upload":
                result = self.upload_file_to_s3(job.get("data", {}))
            elif job_type == "file_download":
                result = self.download_file_from_s3(job.get("data", {}))
            elif job_type == "file_list":
                result = self.list_s3_files(job.get("data", {}))
            elif job_type == "image_process":
                result = self.process_image(job.get("data", {}))
            else:
                result = {"success": False, "error": f"Unknown job type: {job_type}"}

            # 結果を保存
            if result.get("success"):
                self.redis_client.setex(
                    f"{self.result_prefix}{job_id}:status",
                    3600,
                    "completed"
                )
                self.redis_client.setex(
                    f"{self.result_prefix}{job_id}:result",
                    3600,
                    json.dumps(result)
                )
                self._log(f"✅ Trinityジョブ完了: {job_id}")
            else:
                self.redis_client.setex(
                    f"{self.result_prefix}{job_id}:status",
                    3600,
                    "failed"
                )
                self.redis_client.setex(
                    f"{self.result_prefix}{job_id}:error",
                    3600,
                    result.get("error", "Unknown error")
                )
                self._log(f"❌ Trinityジョブ失敗: {job_id}", "ERROR")

            return result

        except Exception as e:
            self._log(f"💥 Trinityジョブ処理エラー: {e}", "ERROR")
            traceback.print_exc()

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

            return {"success": False, "error": str(e)}

    def run(self, poll_interval: float = 2.0):
        """ワーカーメインループ"""
        self._log("🔄 Trinityワーカーループ開始")

        try:
            while True:
                try:
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
                    self._log(f"💥 Trinityワーカーエラー: {e}", "ERROR")
                    traceback.print_exc()
                    time.sleep(5)

        except KeyboardInterrupt:
            self._log("🛑 Trinityワーカー停止")


def main():
    """メイン関数"""
    print("🚀 RunPod Trinity GPU Worker - Starting\n")

    # 環境変数から設定を読み込む
    redis_host = os.getenv("REDIS_HOST", "163.44.120.49")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    worker = RunPodTrinityWorker(
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

    # Trinityワーカー起動
    print("🔄 Trinityジョブ監視開始...\n")
    worker.run()


if __name__ == "__main__":
    main()
