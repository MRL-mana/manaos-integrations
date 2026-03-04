#!/usr/bin/env python3
"""
Direct GPU Executor - Phase 3実装
Tailscale経由でRunPod上で直接GPU処理を実行
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from tailscale_runpod_connector import TailscaleRunPodConnector


class DirectGPUExecutor:
    """Tailscale経由でRunPod上で直接GPU処理を実行"""

    def __init__(
        self,
        connector: Optional[TailscaleRunPodConnector] = None,
        log_dir: str = "/root/logs/runpod_integration"
    ):
        self.connector = connector or TailscaleRunPodConnector()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        log_file = self.log_dir / "direct_gpu_executor.log"
        with open(log_file, "a") as f:
            f.write(log_message + "\n")

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 50,
        width: int = 1024,
        height: int = 1024,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        画像生成を直接実行

        Args:
            prompt: 生成プロンプト
            negative_prompt: ネガティブプロンプト
            steps: 生成ステップ数
            width: 画像幅
            height: 画像高さ
            output_path: 出力パス（指定しない場合は自動生成）

        Returns:
            結果辞書
        """
        self._log(f"画像生成開始: {prompt[:50]}...")

        # 出力パス決定
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/workspace/generated_images/direct_{timestamp}.png"

        # Pythonスクリプトを生成
        script = f"""
import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import os

# 作業ディレクトリ作成
os.makedirs('/workspace/generated_images', exist_ok=True)

# モデル読み込み
print('📦 モデル読み込み中...')
pipe = StableDiffusionPipeline.from_pretrained(
    'stabilityai/stable-diffusion-2-1',
    torch_dtype=torch.float16
)
pipe = pipe.to('cuda')

# 画像生成
print('🎨 画像生成中...')
image = pipe(
    prompt={repr(prompt)},
    negative_prompt={repr(negative_prompt)},
    num_inference_steps={steps},
    width={width},
    height={height}
).images[0]

# 保存
image.save({repr(output_path)})
print(f'✅ 画像生成完了: {repr(output_path)}')
print(f'📊 ファイルサイズ: {{os.path.getsize({repr(output_path)})}} bytes')
"""

        # スクリプトを一時ファイルに保存
        script_path = "/tmp/runpod_generate_image.py"
        Path(script_path).write_text(script)

        # RunPodにアップロード
        upload_result = self.connector.upload_file(
            script_path,
            "/workspace/runpod_generate_image.py"
        )

        if not upload_result.get("success"):
            return {
                "success": False,
                "error": f"スクリプトアップロード失敗: {upload_result.get('error')}"
            }

        # RunPod上で実行
        self._log("RunPod上で画像生成実行中...")
        result = self.connector.execute_command(
            "cd /workspace && python3 runpod_generate_image.py",
            timeout=600  # 10分タイムアウト
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": f"画像生成失敗: {result.get('error')}"
            }

        # 生成された画像をダウンロード
        local_output = f"/root/generated_images/direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        download_result = self.connector.download_file(output_path, local_output)

        if download_result.get("success"):
            self._log(f"✅ 画像生成完了: {local_output}")
            return {
                "success": True,
                "local_path": local_output,
                "remote_path": output_path,
                "prompt": prompt,
                "generation_params": {
                    "steps": steps,
                    "width": width,
                    "height": height
                }
            }
        else:
            # 画像は生成されたがダウンロード失敗
            self._log(f"⚠️ 画像生成成功だがダウンロード失敗: {download_result.get('error')}", "WARNING")
            return {
                "success": True,
                "remote_path": output_path,
                "local_path": None,
                "warning": "画像は生成されましたが、ダウンロードに失敗しました",
                "prompt": prompt
            }

    def execute_python_script(
        self,
        script: str,
        timeout: int = 300,
        cwd: str = "/workspace"
    ) -> Dict[str, Any]:
        """
        Pythonスクリプトを直接実行

        Args:
            script: Pythonスクリプト内容
            timeout: タイムアウト秒数
            cwd: 作業ディレクトリ

        Returns:
            結果辞書
        """
        self._log("Pythonスクリプト実行開始...")

        # 一時ファイルに保存
        script_path = f"/tmp/runpod_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        Path(script_path).write_text(script)

        # RunPodにアップロード
        remote_script_path = f"{cwd}/runpod_script.py"
        upload_result = self.connector.upload_file(script_path, remote_script_path)

        if not upload_result.get("success"):
            return {
                "success": False,
                "error": f"スクリプトアップロード失敗: {upload_result.get('error')}"
            }

        # 実行
        result = self.connector.execute_command(
            f"cd {cwd} && python3 runpod_script.py",
            timeout=timeout
        )

        # 一時ファイル削除
        Path(script_path).unlink(missing_ok=True)

        return result

    def check_gpu_status(self) -> Dict[str, Any]:
        """GPU状態を確認"""
        self._log("GPU状態確認中...")

        result = self.connector.execute_command(
            "nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu --format=csv,noheader,nounits"
        )

        if result.get("success"):
            output = result.get("stdout", "").strip()
            if output:
                # GPU情報をパース
                parts = output.split(",")
                if len(parts) >= 6:
                    return {
                        "success": True,
                        "gpu_name": parts[0].strip(),
                        "memory_total_mb": int(parts[1].strip()),
                        "memory_used_mb": int(parts[2].strip()),
                        "memory_free_mb": int(parts[3].strip()),
                        "utilization_percent": int(parts[4].strip()),
                        "temperature_c": int(parts[5].strip())
                    }

        return {
            "success": False,
            "error": "GPU状態取得失敗"
        }

    def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        self._log("ヘルスチェック開始")

        connector_health = self.connector.health_check()
        gpu_status = self.check_gpu_status()

        return {
            "success": connector_health.get("success") and gpu_status.get("success"),
            "connector": connector_health,
            "gpu": gpu_status,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("⚡ Direct GPU Executor - Test\n")

    executor = DirectGPUExecutor()

    # ヘルスチェック
    print("1️⃣ Health Check...")
    health = executor.health_check()
    print(f"Result: {json.dumps(health, indent=2, ensure_ascii=False)}\n")

    if not health.get("success"):
        print("❌ ヘルスチェック失敗。Tailscale接続とGPU環境を確認してください。")
        return

    # GPU状態確認
    print("2️⃣ GPU Status...")
    gpu_status = executor.check_gpu_status()
    print(f"Result: {json.dumps(gpu_status, indent=2, ensure_ascii=False)}\n")

    # 簡単なPythonスクリプト実行テスト
    print("3️⃣ Python Script Execution Test...")
    test_script = """
import torch
print(f"🔥 GPU利用可能: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"🎯 GPU名: {torch.cuda.get_device_name(0)}")
    print(f"💾 GPU メモリ: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
"""
    result = executor.execute_python_script(test_script)
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}\n")

    print("✅ Test completed!")
    print("\n💡 画像生成を試す場合:")
    print("   executor.generate_image('A beautiful sunset', steps=20)")


if __name__ == "__main__":
    main()









