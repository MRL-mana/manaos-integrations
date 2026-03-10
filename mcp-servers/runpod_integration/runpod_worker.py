#!/usr/bin/env python3
"""
RunPod Worker - Phase 2実装
RunPodポッド上で動作するワーカー
Redisからジョブを取得してGPU処理を実行
"""

import redis
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

# GPU処理用ライブラリ（RunPod環境でインポート）
try:
    import torch
    from diffusers import StableDiffusionPipeline
    from transformers import AutoTokenizer, AutoModelForCausalLM
    GPU_AVAILABLE = torch.cuda.is_available()
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️  GPU処理ライブラリが利用できません（開発環境）")


class RunPodWorker:
    """RunPod GPU Worker"""
    
    def __init__(
        self,
        redis_host: str = "manaos_server_tailscale_ip",  # TailscaleまたはパブリックIP
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        queue_name: str = "manaos:gpu:jobs",
        result_prefix: str = "manaos:gpu:results:",
        s3_endpoint: str = "http://manaos_server_ip:9000",
        s3_access_key: str = "manaos",
        s3_secret_key: str = "manaos_gpu_secure_2025",
        worker_id: Optional[str] = None
    ):
        self.worker_id = worker_id or f"worker_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.queue_name = queue_name
        self.result_prefix = result_prefix
        
        # Redis接続
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
        
        # S3/MinIO設定（ファイルアップロード用）
        self.s3_config = {
            "endpoint": s3_endpoint,
            "access_key": s3_access_key,
            "secret_key": s3_secret_key
        }
        
        # GPUモデルキャッシュ
        self.models = {}
        
        self._log(f"Worker起動: {self.worker_id}")
        self._log(f"GPU利用可能: {GPU_AVAILABLE}")
    
    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{self.worker_id}] [{level}] {message}"
        print(log_message)
    
    def _load_sd_model(self):
        """Stable Diffusionモデルをロード"""
        if "stable_diffusion" not in self.models:
            self._log("Stable Diffusionモデルをロード中...")
            pipe = StableDiffusionPipeline.from_pretrained(  # type: ignore[possibly-unbound]
                "stabilityai/stable-diffusion-2-1",
                torch_dtype=torch.float16  # type: ignore[possibly-unbound]
            )
            pipe = pipe.to("cuda")
            self.models["stable_diffusion"] = pipe
            self._log("Stable Diffusionモデルロード完了")
        return self.models["stable_diffusion"]
    
    def process_image_generation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """画像生成処理"""
        try:
            prompt = params.get("prompt", "")
            negative_prompt = params.get("negative_prompt", "")
            steps = params.get("steps", 30)
            
            self._log(f"画像生成開始: {prompt[:50]}...")
            
            pipe = self._load_sd_model()
            image = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps
            ).images[0]
            
            # 画像を保存
            output_path = f"/tmp/{params.get('job_id', 'output')}.png"
            image.save(output_path)
            
            # S3にアップロード（実装省略、s3_file_manager.pyを使用）
            # upload_to_s3(output_path, params['job_id'])
            
            self._log("画像生成完了")
            
            return {
                "success": True,
                "output_path": output_path,
                "s3_key": f"results/{params.get('job_id', 'output')}.png"
            }
            
        except Exception as e:
            self._log(f"画像生成エラー: {e}", "ERROR")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """ジョブ処理のメイン関数"""
        job_id = job.get("job_id")
        job_type = job.get("data", {}).get("type")
        
        self._log(f"ジョブ処理開始: {job_id} - Type: {job_type}")
        
        # ステータス更新
        self.redis_client.setex(
            f"{self.result_prefix}{job_id}:status",
            3600,
            "processing"
        )
        
        try:
            # ジョブタイプに応じて処理
            if job_type == "image_generation":
                result = self.process_image_generation(job["data"])
            elif job_type == "text_generation":
                result = {"success": True, "text": "Text generation not implemented yet"}
            elif job_type == "test":
                result = {"success": True, "message": "Test job processed"}
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
                self._log(f"ジョブ完了: {job_id}")
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
                self._log(f"ジョブ失敗: {job_id}", "ERROR")
            
            return result
            
        except Exception as e:
            self._log(f"ジョブ処理エラー: {e}", "ERROR")
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
        self._log("ワーカーループ開始")
        
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
                    self._log(f"Redis接続エラー: {e}", "ERROR")
                    time.sleep(10)
                except Exception as e:
                    self._log(f"ワーカーエラー: {e}", "ERROR")
                    traceback.print_exc()
                    time.sleep(5)
                
        except KeyboardInterrupt:
            self._log("ワーカー停止")


def main():
    """メイン関数"""
    print("🚀 RunPod GPU Worker - Starting\n")
    
    # 環境変数から設定を読み込む（実際の運用では環境変数を使用）
    worker = RunPodWorker(
        redis_host="localhost",  # 開発環境用、本番では変更
        redis_port=6379
    )
    
    # ヘルスチェック
    try:
        worker.redis_client.ping()
        print("✅ Redis接続成功\n")
    except Exception as e:
        print(f"❌ Redis接続失敗: {e}\n")
        sys.exit(1)
    
    # ワーカー起動
    print("🔄 ジョブ監視開始...\n")
    worker.run()


if __name__ == "__main__":
    main()


