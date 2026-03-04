#!/usr/bin/env python3
"""
ManaOS Tailscale Client - Phase 3実装
Tailscale経由でRunPod GPU処理を直接実行するクライアント
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from tailscale_runpod_connector import TailscaleRunPodConnector
from direct_gpu_executor import DirectGPUExecutor


class ManaOSTailscaleClient:
    """Tailscale経由でRunPod GPU処理を実行するManaOSクライアント"""

    def __init__(
        self,
        tailscale_ip: Optional[str] = None,
        ssh_port: int = 22,
        ssh_user: str = "root",
        ssh_key_path: Optional[str] = None,
        config_file: str = "/root/runpod_integration/runpod_config.json",
        log_dir: str = "/root/logs/runpod_integration"
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Tailscale接続初期化
        self.connector = TailscaleRunPodConnector(
            tailscale_ip=tailscale_ip,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_key_path=ssh_key_path,
            config_file=config_file,
            log_dir=log_dir
        )

        # GPU実行器初期化
        self.executor = DirectGPUExecutor(
            connector=self.connector,
            log_dir=log_dir
        )

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        log_file = self.log_dir / "tailscale_client.log"
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
        画像生成（Tailscale経由で直接実行）

        Args:
            prompt: 生成プロンプト
            negative_prompt: ネガティブプロンプト
            steps: 生成ステップ数
            width: 画像幅
            height: 画像高さ
            output_path: 出力パス

        Returns:
            結果辞書
        """
        self._log(f"画像生成開始: {prompt[:50]}...")

        return self.executor.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            width=width,
            height=height,
            output_path=output_path
        )

    def execute_python_script(
        self,
        script: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Pythonスクリプトを直接実行

        Args:
            script: Pythonスクリプト内容
            timeout: タイムアウト秒数

        Returns:
            結果辞書
        """
        self._log("Pythonスクリプト実行開始...")
        return self.executor.execute_python_script(script, timeout=timeout)

    def upload_file(
        self,
        local_path: str,
        remote_path: str
    ) -> Dict[str, Any]:
        """
        ファイルをアップロード

        Args:
            local_path: ローカルファイルパス
            remote_path: リモートファイルパス

        Returns:
            結果辞書
        """
        self._log(f"ファイルアップロード: {local_path}")
        return self.connector.upload_file(local_path, remote_path)

    def download_file(
        self,
        remote_path: str,
        local_path: str
    ) -> Dict[str, Any]:
        """
        ファイルをダウンロード

        Args:
            remote_path: リモートファイルパス
            local_path: ローカル保存先パス

        Returns:
            結果辞書
        """
        self._log(f"ファイルダウンロード: {remote_path}")
        return self.connector.download_file(remote_path, local_path)

    def execute_command(
        self,
        command: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        コマンドを実行

        Args:
            command: 実行するコマンド
            timeout: タイムアウト秒数

        Returns:
            結果辞書
        """
        self._log(f"コマンド実行: {command[:50]}...")
        return self.connector.execute_command(command, timeout=timeout)

    def get_gpu_info(self) -> Dict[str, Any]:
        """GPU情報を取得"""
        self._log("GPU情報取得中...")
        return self.connector.get_gpu_info()

    def check_gpu_status(self) -> Dict[str, Any]:
        """GPU状態を確認"""
        self._log("GPU状態確認中...")
        return self.executor.check_gpu_status()

    def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        self._log("ヘルスチェック開始")

        connector_health = self.connector.health_check()
        executor_health = self.executor.health_check()

        return {
            "success": connector_health.get("success") and executor_health.get("success"),
            "connector": connector_health,
            "executor": executor_health,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("🔗 ManaOS Tailscale Client - Test\n")

    client = ManaOSTailscaleClient()

    # ヘルスチェック
    print("1️⃣ Health Check...")
    health = client.health_check()
    print(f"Result: {json.dumps(health, indent=2, ensure_ascii=False)}\n")

    if not health.get("success"):
        print("❌ ヘルスチェック失敗。Tailscale接続を確認してください。")
        return

    # GPU情報取得
    print("2️⃣ GPU Info...")
    gpu_info = client.get_gpu_info()
    print(f"Result: {json.dumps(gpu_info, indent=2, ensure_ascii=False)}\n")

    # GPU状態確認
    print("3️⃣ GPU Status...")
    gpu_status = client.check_gpu_status()
    print(f"Result: {json.dumps(gpu_status, indent=2, ensure_ascii=False)}\n")

    # 簡単なコマンド実行テスト
    print("4️⃣ Command Execution Test...")
    result = client.execute_command("echo 'Hello from RunPod via Tailscale'")
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}\n")

    print("✅ Test completed!")
    print("\n💡 画像生成を試す場合:")
    print("   client.generate_image('A beautiful sunset', steps=20)")


if __name__ == "__main__":
    main()









