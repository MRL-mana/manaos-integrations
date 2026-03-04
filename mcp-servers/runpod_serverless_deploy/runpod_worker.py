#!/usr/bin/env python3
"""
🚀 RunPod Serverless Worker
ManaOS用RunPod Serverlessエンドポイントのワーカー関数
"""
import runpod
import torch
import base64
import io
from PIL import Image
from typing import Dict, Any

# RunPod Serverless Handler
def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod Serverlessジョブハンドラー

    Args:
        job: RunPodから送られてくるジョブデータ
            {
                "id": "job_id",
                "input": {
                    "task": "image_generation",
                    "prompt": "...",
                    "model": "...",
                    ...
                }
            }

    Returns:
        処理結果
    """
    try:
        job_id = job.get("id", "unknown")
        input_data = job.get("input", {})
        task = input_data.get("task", "")

        print(f"🚀 RunPod Serverless: ジョブ {job_id} 処理開始 ({task})")

        # タスク別処理
        if task == "image_generation":
            result = handle_image_generation(input_data)
        elif task == "gpu_test":
            result = handle_gpu_test(input_data)
        elif task == "deep_learning":
            result = handle_deep_learning(input_data)
        else:
            result = {
                "error": f"Unknown task: {task}",
                "available_tasks": ["image_generation", "gpu_test", "deep_learning"]
            }

        print(f"✅ ジョブ {job_id} 完了")
        return {
            "id": job_id,
            "status": "completed",
            "output": result
        }

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return {
            "id": job.get("id", "unknown"),
            "status": "failed",
            "error": str(e)
        }


def handle_image_generation(input_data: Dict) -> Dict:
    """画像生成処理"""
    prompt = input_data.get("prompt", "")
    model_name = input_data.get("model", "stable_diffusion")
    width = input_data.get("width", 1024)
    height = input_data.get("height", 1024)
    steps = input_data.get("steps", 30)

    print(f"🎨 画像生成: {prompt[:50]}...")

    # GPU確認
    if not torch.cuda.is_available():
        return {"error": "CUDA not available", "fallback": "cpu"}

    try:
        # 簡易版画像生成（実際はdiffusers等を使用）
        # ここではダミー画像を生成
        image = Image.new('RGB', (width, height), color=(100, 150, 200))

        # Base64エンコード
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return {
            "success": True,
            "image_base64": image_base64,
            "format": "png",
            "width": width,
            "height": height,
            "prompt": prompt
        }

    except Exception as e:
        return {"error": str(e)}


def handle_gpu_test(input_data: Dict) -> Dict:
    """GPUテスト処理"""
    print("🔍 GPU状態確認...")

    gpu_available = torch.cuda.is_available()
    result = {
        "gpu_available": gpu_available,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

    if gpu_available:
        result.update({
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_count": torch.cuda.device_count(),
            "memory_total": torch.cuda.get_device_properties(0).total_memory / 1024**3,
            "memory_allocated": torch.cuda.memory_allocated(0) / 1024**3,
        })

    return result


def handle_deep_learning(input_data: Dict) -> Dict:
    """深層学習処理"""
    print("🧠 深層学習処理開始...")

    if not torch.cuda.is_available():
        return {"error": "CUDA not available"}

    # サンプル処理（実際のモデル推論をここに実装）
    device = torch.device('cuda')
    x = torch.randn(10, 3, 224, 224).to(device)

    return {
        "success": True,
        "device": str(device),
        "tensor_shape": list(x.shape),
        "memory_used": torch.cuda.memory_allocated(0) / 1024**3
    }


# RunPod Serverlessエントリーポイント
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})























