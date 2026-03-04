#!/usr/bin/env python3
"""
Tailscale RunPod Connector - Phase 3実装
Tailscale VPN経由でRunPodに直接接続
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class TailscaleRunPodConnector:
    """Tailscale経由でRunPodに接続するクラス"""

    def __init__(
        self,
        tailscale_ip: str = "100.84.82.112",
        ssh_port: int = 22,
        ssh_user: str = "root",
        ssh_key_path: Optional[str] = None,
        config_file: str = "/root/runpod_integration/runpod_config.json",
        log_dir: str = "/root/logs/runpod_integration"
    ):
        self.tailscale_ip = tailscale_ip
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_key_path = ssh_key_path
        self.config_file = Path(config_file)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 設定ファイルから読み込み
        self._load_config()

        # SSHクライアント（必要に応じて）
        self.ssh_client = None

    def _load_config(self):
        """設定ファイルから読み込み"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    runpod_config = config.get("runpod", {})
                    if runpod_config.get("tailscale_ip"):
                        self.tailscale_ip = runpod_config["tailscale_ip"]
                    if runpod_config.get("ssh_port"):
                        self.ssh_port = runpod_config["ssh_port"]
                    if runpod_config.get("ssh_user"):
                        self.ssh_user = runpod_config["ssh_user"]
            except Exception as e:
                self._log(f"設定ファイル読み込みエラー: {e}", "WARNING")

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        log_file = self.log_dir / "tailscale_connector.log"
        with open(log_file, "a") as f:
            f.write(log_message + "\n")

    def test_connection(self) -> Dict[str, Any]:
        """接続テスト"""
        self._log(f"Tailscale接続テスト開始: {self.tailscale_ip}")

        results = {
            "ping": False,
            "ssh": False,
            "tailscale_ip": self.tailscale_ip
        }

        # Pingテスト
        try:
            result = subprocess.run(
                ["ping", "-c", "3", "-W", "2", self.tailscale_ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                results["ping"] = True
                self._log(f"✅ Ping成功: {self.tailscale_ip}")
            else:
                self._log(f"❌ Ping失敗: {self.tailscale_ip}", "ERROR")
        except Exception as e:
            self._log(f"❌ Pingエラー: {e}", "ERROR")

        # SSH接続テスト
        try:
            ssh_cmd = [
                "ssh",
                "-o", "ConnectTimeout=5",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-p", str(self.ssh_port),
                f"{self.ssh_user}@{self.tailscale_ip}",
                "echo 'SSH接続成功'"
            ]

            if self.ssh_key_path:
                ssh_cmd.extend(["-i", self.ssh_key_path])

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                results["ssh"] = True
                self._log(f"✅ SSH接続成功: {self.tailscale_ip}")
            else:
                self._log(f"❌ SSH接続失敗: {result.stderr}", "ERROR")
        except Exception as e:
            self._log(f"❌ SSH接続エラー: {e}", "ERROR")

        results["success"] = results["ping"] and results["ssh"]
        return results

    def execute_command(
        self,
        command: str,
        timeout: int = 30,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        RunPod上でコマンドを実行

        Args:
            command: 実行するコマンド
            timeout: タイムアウト秒数
            cwd: 作業ディレクトリ

        Returns:
            結果辞書
        """
        self._log(f"コマンド実行: {command[:50]}...")

        try:
            ssh_cmd = [
                "ssh",
                "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=no",
                "-p", str(self.ssh_port),
                f"{self.ssh_user}@{self.tailscale_ip}",
                command
            ]

            if self.ssh_key_path:
                ssh_cmd.extend(["-i", self.ssh_key_path])

            if cwd:
                command = f"cd {cwd} && {command}"
                ssh_cmd[-1] = command

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                self._log("✅ コマンド実行成功")
                return {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            else:
                self._log(f"❌ コマンド実行失敗: {result.stderr}", "ERROR")
                return {
                    "success": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "error": result.stderr
                }

        except subprocess.TimeoutExpired:
            self._log(f"❌ コマンドタイムアウト: {command[:50]}", "ERROR")
            return {
                "success": False,
                "error": "Timeout"
            }
        except Exception as e:
            self._log(f"❌ コマンド実行エラー: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }

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
        self._log(f"ファイルアップロード: {local_path} -> {remote_path}")

        if not Path(local_path).exists():
            return {
                "success": False,
                "error": f"ローカルファイルが見つかりません: {local_path}"
            }

        try:
            scp_cmd = [
                "scp",
                "-o", "StrictHostKeyChecking=no",
                "-P", str(self.ssh_port),
                local_path,
                f"{self.ssh_user}@{self.tailscale_ip}:{remote_path}"
            ]

            if self.ssh_key_path:
                scp_cmd.extend(["-i", self.ssh_key_path])

            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                self._log(f"✅ ファイルアップロード成功: {remote_path}")
                return {
                    "success": True,
                    "local_path": local_path,
                    "remote_path": remote_path
                }
            else:
                self._log(f"❌ ファイルアップロード失敗: {result.stderr}", "ERROR")
                return {
                    "success": False,
                    "error": result.stderr
                }

        except Exception as e:
            self._log(f"❌ ファイルアップロードエラー: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }

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
        self._log(f"ファイルダウンロード: {remote_path} -> {local_path}")

        try:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            scp_cmd = [
                "scp",
                "-o", "StrictHostKeyChecking=no",
                "-P", str(self.ssh_port),
                f"{self.ssh_user}@{self.tailscale_ip}:{remote_path}",
                local_path
            ]

            if self.ssh_key_path:
                scp_cmd.extend(["-i", self.ssh_key_path])

            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                self._log(f"✅ ファイルダウンロード成功: {local_path}")
                return {
                    "success": True,
                    "local_path": local_path,
                    "remote_path": remote_path
                }
            else:
                self._log(f"❌ ファイルダウンロード失敗: {result.stderr}", "ERROR")
                return {
                    "success": False,
                    "error": result.stderr
                }

        except Exception as e:
            self._log(f"❌ ファイルダウンロードエラー: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }

    def get_gpu_info(self) -> Dict[str, Any]:
        """GPU情報を取得"""
        self._log("GPU情報取得中...")

        result = self.execute_command(
            "nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits"
        )

        if result.get("success"):
            gpu_info = result.get("stdout", "").strip()
            if gpu_info:
                # GPU情報をパース
                parts = gpu_info.split(",")
                if len(parts) >= 4:
                    return {
                        "success": True,
                        "gpu_name": parts[0].strip(),
                        "memory_total_mb": int(parts[1].strip()),
                        "memory_used_mb": int(parts[2].strip()),
                        "utilization_percent": int(parts[3].strip())
                    }

        return {
            "success": False,
            "error": "GPU情報取得失敗"
        }

    def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        self._log("ヘルスチェック開始")

        connection_test = self.test_connection()
        gpu_info = self.get_gpu_info()

        return {
            "success": connection_test.get("success") and gpu_info.get("success"),
            "connection": connection_test,
            "gpu": gpu_info,
            "tailscale_ip": self.tailscale_ip,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("🔗 Tailscale RunPod Connector - Test\n")

    connector = TailscaleRunPodConnector()

    # ヘルスチェック
    print("1️⃣ Health Check...")
    health = connector.health_check()
    print(f"Result: {json.dumps(health, indent=2, ensure_ascii=False)}\n")

    if not health.get("success"):
        print("❌ ヘルスチェック失敗。Tailscale接続を確認してください。")
        return

    # コマンド実行テスト
    print("2️⃣ Command Execution Test...")
    result = connector.execute_command("echo 'Hello from RunPod via Tailscale'")
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}\n")

    # GPU情報取得
    print("3️⃣ GPU Info...")
    gpu_info = connector.get_gpu_info()
    print(f"Result: {json.dumps(gpu_info, indent=2, ensure_ascii=False)}\n")

    print("✅ Test completed!")


if __name__ == "__main__":
    main()









