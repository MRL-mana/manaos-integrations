#!/usr/bin/env python3
"""
RunPod Worker - HTTP版
HTTP経由でこのはサーバーのRedisプロキシにアクセス
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# GPU処理用ライブラリ
try:
    import torch
    from diffusers import StableDiffusionPipeline
    from transformers import AutoTokenizer, AutoModelForCausalLM
    GPU_AVAILABLE = torch.cuda.is_available()
    print(f"🔥 GPU利用可能: {GPU_AVAILABLE}")
    if GPU_AVAILABLE:
        print(f"🎯 GPU名: {torch.cuda.get_device_name(0)}")
        print(f"💾 GPU メモリ: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️  GPU処理ライブラリが利用できません")


class RunPodWorkerHTTP:
    """RunPod GPU Worker (HTTP版)"""
    
    def __init__(
        self,
        proxy_url: str = "http://163.44.120.49:8081",  # RedisプロキシURL
        worker_id: Optional[str] = None
    ):
        self.proxy_url = proxy_url.rstrip('/')
        self.worker_id = worker_id or f"worker_http_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        self._log(f"🚀 HTTP Worker起動: {self.worker_id}")
        self._log(f"🔥 GPU利用可能: {GPU_AVAILABLE}")
        self._log(f"🌐 プロキシURL: {self.proxy_url}")
    
    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{self.worker_id}] [{level}] {message}"
        print(log_message)
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """HTTP リクエスト実行"""
        url = f"{self.proxy_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._log(f"HTTP リクエストエラー: {e}", "ERROR")
            return {"error": str(e)}
    
    def check_proxy_health(self) -> bool:
        """プロキシヘルスチェック"""
        result = self._make_request("/health")
        if result.get("status") == "ok":
            self._log("✅ プロキシ接続成功")
            return True
        else:
            self._log(f"❌ プロキシ接続失敗: {result}", "ERROR")
            return False
    
    def get_queue_length(self) -> int:
        """キュー長取得"""
        result = self._make_request("/queue/length")
        return result.get("length", 0)
    
    def submit_test_job(self) -> Optional[str]:
        """テストジョブ投入"""
        job_data = {
            "type": "gpu_test",
            "description": "RTX 4090 GPU性能テスト"
        }
        
        result = self._make_request("/job/submit", "POST", job_data)
        if "job_id" in result:
            self._log(f"📝 テストジョブ投入: {result['job_id']}")
            return result["job_id"]
        else:
            self._log(f"❌ ジョブ投入失敗: {result}", "ERROR")
            return None
    
    def get_job_status(self, job_id: str) -> str:
        """ジョブステータス取得"""
        result = self._make_request(f"/job/status/{job_id}")
        return result.get("status", "unknown")
    
    def get_job_result(self, job_id: str) -> Dict:
        """ジョブ結果取得"""
        result = self._make_request(f"/job/result/{job_id}")
        return result.get("result", {})
    
    def test_gpu(self) -> Dict[str, Any]:
        """GPUテスト処理"""
        try:
            if not GPU_AVAILABLE:
                return {"success": False, "error": "GPU not available"}
            
            self._log("🧪 GPUテスト開始...")
            
            # 簡単なGPU演算テスト
            device = torch.device("cuda")
            x = torch.randn(1000, 1000).to(device)
            y = torch.randn(1000, 1000).to(device)
            z = torch.mm(x, y)
            
            result = z.sum().item()
            
            self._log(f"✅ GPUテスト完了: 結果={result:.2f}")
            
            return {
                "success": True,
                "gpu_test_result": result,
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_memory_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3
            }
            
        except Exception as e:
            self._log(f"❌ GPUテストエラー: {e}", "ERROR")
            return {"success": False, "error": str(e)}


def main():
    """メイン関数"""
    print("🚀 RunPod GPU Worker (HTTP版) - Starting\n")
    
    # ワーカー初期化
    worker = RunPodWorkerHTTP()
    
    # プロキシヘルスチェック
    if not worker.check_proxy_health():
        print("❌ プロキシ接続失敗")
        sys.exit(1)
    
    # キュー状況確認
    queue_length = worker.get_queue_length()
    print(f"📊 キュー長: {queue_length}")
    
    # GPUテスト実行
    print("🧪 GPUテスト実行...")
    test_result = worker.test_gpu()
    if test_result.get("success"):
        print(f"✅ GPUテスト成功: {test_result}")
    else:
        print(f"❌ GPUテスト失敗: {test_result}")
    
    # テストジョブ投入
    print("\n📝 テストジョブ投入...")
    job_id = worker.submit_test_job()
    
    if job_id:
        print(f"🔄 ジョブ処理状況監視: {job_id}")
        
        # ジョブ処理状況監視
        for i in range(10):
            status = worker.get_job_status(job_id)
            print(f"📊 [{i+1}/10] ステータス: {status}")
            
            if status == "completed":
                result = worker.get_job_result(job_id)
                print(f"🎯 ジョブ結果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                break
            elif status == "failed":
                print("❌ ジョブ失敗")
                break
            
            time.sleep(3)
    
    print("\n🎉 テスト完了!")


if __name__ == "__main__":
    main()
