#!/usr/bin/env python3
"""
RunPod Trinity Worker (Updated)
最新モデル + 永続ボリューム保存対応
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

# GPU処理用ライブラリ
try:
    import torch
    from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
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
    """RunPod Trinity GPU Worker (Updated)"""
    
    def __init__(
        self,
        redis_host: str = "163.44.120.49",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        queue_name: str = "manaos:gpu:jobs",
        result_prefix: str = "manaos:gpu:results:",
        worker_id: Optional[str] = None
    ):
        self.worker_id = worker_id or f"trinity_worker_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.queue_name = queue_name
        self.result_prefix = result_prefix
        
        # Redis接続
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True
        )
        
        # GPUモデルキャッシュ
        self.models = {}
        
        # 永続保存ディレクトリの作成
        self.persistent_dir = "/workspace/trinity_generated_images"
        os.makedirs(self.persistent_dir, exist_ok=True)
        self._log(f"📁 永続保存ディレクトリ作成: {self.persistent_dir}")
        
        self._log(f"🚀 Trinity Worker起動: {self.worker_id}")
        self._log(f"🔥 GPU利用可能: {GPU_AVAILABLE}")
    
    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{self.worker_id}] [{level}] {message}"
        print(log_message)
    
    def _load_stable_diffusion_xl(self):
        """Stable Diffusion XLモデル読み込み（最新・高品質）"""
        if "stable_diffusion_xl" not in self.models:
            self._log("📦 Stable Diffusion XLモデル読み込み中...")
            try:
                pipe = StableDiffusionXLPipeline.from_pretrained(  # type: ignore[possibly-unbound]
                    'stabilityai/stable-diffusion-xl-base-1.0', 
                    torch_dtype=torch.float16,  # type: ignore[possibly-unbound]
                    use_safetensors=True
                )
                pipe = pipe.to('cuda')
                pipe.enable_attention_slicing()  # メモリ効率化
                self.models["stable_diffusion_xl"] = pipe
                self._log("✅ Stable Diffusion XLモデル読み込み完了")
            except Exception as e:
                self._log(f"❌ Stable Diffusion XLモデル読み込みエラー: {e}", "ERROR")
                # フォールバック: 古いモデル
                self._log("🔄 フォールバック: SD 2.1を使用...")
                pipe = StableDiffusionPipeline.from_pretrained(  # type: ignore[possibly-unbound]
                    'stabilityai/stable-diffusion-2-1', 
                    torch_dtype=torch.float16  # type: ignore[possibly-unbound]
                )
                pipe = pipe.to('cuda')
                self.models["stable_diffusion_xl"] = pipe
                self._log("✅ Stable Diffusion 2.1モデル読み込み完了（フォールバック）")
        return self.models["stable_diffusion_xl"]
    
    def generate_image(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """画像生成処理（最新モデル + 永続保存）"""
        try:
            prompt = job_data.get("prompt", "A beautiful landscape")
            steps = job_data.get("steps", 50)
            width = job_data.get("width", 1024)
            height = job_data.get("height", 1024)
            model_type = job_data.get("model", "xl")  # xl or v2.1
            
            self._log(f"🎨 画像生成開始: {prompt}")
            self._log(f"📏 サイズ: {width}x{height}, ステップ: {steps}")
            
            # モデル読み込み
            if model_type == "xl":
                pipe = self._load_stable_diffusion_xl()
            else:
                # 古いモデルも選択可能
                pipe = self._load_stable_diffusion()
            
            # 画像生成
            image = pipe(
                prompt,
                num_inference_steps=steps,
                width=width,
                height=height
            ).images[0]
            
            # 永続ボリュームに保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"trinity_xl_{timestamp}.png"
            image_path = os.path.join(self.persistent_dir, image_filename)
            
            image.save(image_path)
            self._log(f"💾 永続保存完了: {image_path}")
            
            # 画像をBase64エンコード
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # ファイルサイズ確認
            file_size = os.path.getsize(image_path)
            self._log(f"📊 ファイルサイズ: {file_size / 1024:.1f}KB")
            
            self._log(f"✅ 画像生成完了: {image_path}")
            
            return {
                "success": True,
                "image_path": image_path,
                "image_filename": image_filename,
                "image_base64": image_base64,
                "prompt": prompt,
                "generation_params": {
                    "model": model_type,
                    "steps": steps,
                    "width": width,
                    "height": height
                },
                "file_info": {
                    "size_bytes": file_size,
                    "size_kb": round(file_size / 1024, 1),
                    "persistent": True,
                    "volume_path": self.persistent_dir
                },
                "gpu_info": {
                    "name": torch.cuda.get_device_name(0),  # type: ignore[possibly-unbound]
                    "memory_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3  # type: ignore[possibly-unbound]
                }
            }
            
        except Exception as e:
            self._log(f"❌ 画像生成エラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}
    
    def _load_stable_diffusion(self):
        """Stable Diffusion 2.1モデル読み込み（フォールバック）"""
        if "stable_diffusion" not in self.models:
            self._log("📦 Stable Diffusion 2.1モデル読み込み中...")
            try:
                pipe = StableDiffusionPipeline.from_pretrained(  # type: ignore[possibly-unbound]
                    'stabilityai/stable-diffusion-2-1', 
                    torch_dtype=torch.float16  # type: ignore[possibly-unbound]
                )
                pipe = pipe.to('cuda')
                self.models["stable_diffusion"] = pipe
                self._log("✅ Stable Diffusion 2.1モデル読み込み完了")
            except Exception as e:
                self._log(f"❌ Stable Diffusion 2.1モデル読み込みエラー: {e}", "ERROR")
                raise
        return self.models["stable_diffusion"]
    
    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """ジョブ処理のメイン関数"""
        job_id = job.get("job_id")
        job_type = job.get("data", {}).get("type")
        
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
                result = self.generate_image(job.get("data", {}))
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
    print("🚀 RunPod Trinity GPU Worker (Updated) - Starting\n")
    
    # 環境変数から設定を読み込む
    worker = RunPodTrinityWorker(
        redis_host="163.44.120.49",
        redis_port=6379
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
