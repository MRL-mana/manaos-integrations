#!/usr/bin/env python3
"""
ManaOS RunPod Client - Phase 2実装
Redis + S3/MinIOを使ったPull型ワーカー統合
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from job_queue_manager import JobQueueManager
from s3_file_manager import S3FileManager


class ManaOSRunPodClient:
    """RunPod GPU処理のためのManaOSクライアント"""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        s3_endpoint: str = "http://localhost:9000",
        s3_access_key: str = "manaos",
        s3_secret_key: str = "manaos_gpu_secure_2025",
        s3_bucket: str = "manaos-gpu-results",
        log_dir: str = "/root/logs/runpod_integration"
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # キュー管理初期化
        self.queue_manager = JobQueueManager(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            log_dir=log_dir
        )

        # S3管理初期化
        self.s3_manager = S3FileManager(
            endpoint_url=s3_endpoint,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            bucket_name=s3_bucket,
            log_dir=log_dir
        )

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        log_file = self.log_dir / "runpod_client.log"
        with open(log_file, "a") as f:
            f.write(log_message + "\n")

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 50,
        width: int = 1024,
        height: int = 1024,
        wait_for_result: bool = True,
        timeout: int = 600
    ) -> Dict[str, Any]:
        """
        画像生成ジョブを投入

        Args:
            prompt: 生成する画像の説明
            negative_prompt: 避けたい要素
            steps: 生成ステップ数
            width: 画像幅
            height: 画像高さ
            wait_for_result: 結果を待つかどうか
            timeout: タイムアウト秒数

        Returns:
            結果辞書
        """
        self._log(f"画像生成ジョブ投入: {prompt[:50]}...")

        # ジョブデータ作成
        job_data = {
            "type": "image_generation",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "width": width,
            "height": height
        }

        # ジョブ投入
        job_id = self.queue_manager.submit_job(job_data)

        if not wait_for_result:
            return {
                "success": True,
                "job_id": job_id,
                "status": "submitted",
                "message": "ジョブを投入しました。結果は後で取得してください。"
            }

        # 結果を待機
        self._log(f"ジョブ完了待機: {job_id}")
        result = self.queue_manager.wait_for_result(job_id, timeout=timeout)

        if not result.get("success"):
            return result

        # 結果からS3パスを取得
        job_result = result.get("result", {})
        s3_path = job_result.get("s3_path")

        # S3からダウンロード（必要に応じて）
        local_path = None
        if s3_path:
            # S3キーを抽出
            s3_key = s3_path.replace(f"s3://{self.s3_manager.bucket_name}/", "")

            # ローカル保存先
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_path = f"/root/generated_images/runpod_{timestamp}.png"
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            # ダウンロード
            download_result = self.s3_manager.download_file(s3_key, local_path)

            if download_result.get("success"):
                self._log(f"画像ダウンロード完了: {local_path}")
            else:
                self._log(f"画像ダウンロード失敗: {download_result.get('error')}", "WARNING")

        return {
            "success": True,
            "job_id": job_id,
            "result": job_result,
            "local_path": local_path,
            "s3_path": s3_path
        }

    def generate_video(
        self,
        frames: int = 100,
        resolution: str = "1920x1080",
        wait_for_result: bool = True,
        timeout: int = 1800
    ) -> Dict[str, Any]:
        """
        動画生成ジョブを投入

        Args:
            frames: フレーム数
            resolution: 解像度（例: "1920x1080"）
            wait_for_result: 結果を待つかどうか
            timeout: タイムアウト秒数

        Returns:
            結果辞書
        """
        self._log(f"動画生成ジョブ投入: {frames}フレーム, {resolution}")

        job_data = {
            "type": "video_generation",
            "frames": frames,
            "resolution": resolution
        }

        job_id = self.queue_manager.submit_job(job_data)

        if not wait_for_result:
            return {
                "success": True,
                "job_id": job_id,
                "status": "submitted"
            }

        result = self.queue_manager.wait_for_result(job_id, timeout=timeout)

        if result.get("success"):
            job_result = result.get("result", {})
            s3_path = job_result.get("s3_path")

            # S3からダウンロード（必要に応じて）
            local_path = None
            if s3_path:
                s3_key = s3_path.replace(f"s3://{self.s3_manager.bucket_name}/", "")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                local_path = f"/root/generated_videos/runpod_{timestamp}.mp4"
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)

                download_result = self.s3_manager.download_file(s3_key, local_path)
                if download_result.get("success"):
                    self._log(f"動画ダウンロード完了: {local_path}")

        return result

    def upload_file(
        self,
        local_path: str,
        s3_key: Optional[str] = None,
        wait_for_result: bool = True,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        ファイルアップロードジョブを投入

        Args:
            local_path: アップロードするローカルファイルパス
            s3_key: S3キー（指定しない場合は自動生成）
            wait_for_result: 結果を待つかどうか
            timeout: タイムアウト秒数

        Returns:
            結果辞書
        """
        if not Path(local_path).exists():
            return {
                "success": False,
                "error": f"ファイルが見つかりません: {local_path}"
            }

        if not s3_key:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            filename = Path(local_path).name
            s3_key = f"Uploads/{timestamp}/{filename}"

        self._log(f"ファイルアップロードジョブ投入: {local_path} -> {s3_key}")

        # まずローカルからS3に直接アップロード（GPU不要なので即実行）
        upload_result = self.s3_manager.upload_file(local_path, s3_key)

        if upload_result.get("success"):
            return {
                "success": True,
                "s3_path": f"s3://{self.s3_manager.bucket_name}/{s3_key}",
                "local_path": local_path
            }
        else:
            return upload_result

    def process_image(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        operation: str = "resize",
        width: int = 1024,
        height: int = 1024,
        wait_for_result: bool = True,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        画像処理ジョブを投入

        Args:
            input_path: 入力画像パス（S3パスも可）
            output_path: 出力画像パス（指定しない場合は自動生成）
            operation: 処理タイプ（resize, convert, thumbnail）
            width: リサイズ幅
            height: リサイズ高さ
            wait_for_result: 結果を待つかどうか
            timeout: タイムアウト秒数

        Returns:
            結果辞書
        """
        self._log(f"画像処理ジョブ投入: {operation} - {input_path}")

        job_data = {
            "type": "image_process",
            "input_path": input_path,
            "output_path": output_path,
            "operation": operation,
            "width": width,
            "height": height
        }

        job_id = self.queue_manager.submit_job(job_data)

        if not wait_for_result:
            return {
                "success": True,
                "job_id": job_id,
                "status": "submitted"
            }

        result = self.queue_manager.wait_for_result(job_id, timeout=timeout)
        return result

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """ジョブの状態を取得"""
        status = self.queue_manager.get_job_status(job_id)
        result = self.queue_manager.get_job_result(job_id)

        return {
            "job_id": job_id,
            "status": status or "not_found",
            "result": result
        }

    def list_s3_files(self, prefix: str = "") -> Dict[str, Any]:
        """S3内のファイル一覧を取得"""
        return self.s3_manager.list_files(prefix)

    def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        self._log("ヘルスチェック開始")

        queue_health = self.queue_manager.health_check()
        s3_health = self.s3_manager.health_check()

        return {
            "success": queue_health.get("success") and s3_health.get("success"),
            "redis": queue_health,
            "s3": s3_health,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("🚀 ManaOS RunPod Client - Test\n")

    client = ManaOSRunPodClient()

    # ヘルスチェック
    print("1️⃣ Health Check...")
    health = client.health_check()
    print(f"Result: {json.dumps(health, indent=2, ensure_ascii=False)}\n")

    if not health.get("success"):
        print("❌ ヘルスチェック失敗。RedisとMinIOが起動しているか確認してください。")
        return

    # ジョブ投入テスト（結果待機なし）
    print("2️⃣ Submit Test Job (no wait)...")
    result = client.generate_image(
        prompt="A beautiful sunset over mountains",
        steps=20,
        wait_for_result=False
    )
    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}\n")

    if result.get("success"):
        job_id = result.get("job_id")
        print(f"3️⃣ Check Job Status: {job_id}...")
        status = client.get_job_status(job_id)
        print(f"Status: {json.dumps(status, indent=2, ensure_ascii=False)}\n")

    # S3ファイル一覧
    print("4️⃣ List S3 Files...")
    files = client.list_s3_files()
    print(f"Files: {json.dumps(files, indent=2, ensure_ascii=False)}\n")

    print("✅ Test completed!")


if __name__ == "__main__":
    main()

