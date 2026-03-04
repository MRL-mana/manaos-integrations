#!/usr/bin/env python3
"""
S3/MinIO File Manager - Phase 2実装
ファイルアップロード・ダウンロード管理
"""

import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class S3FileManager:
    """S3/MinIO互換のファイル管理"""
    
    def __init__(
        self,
        endpoint_url: str = "http://localhost:9000",
        access_key: str = "manaos",
        secret_key: str = "manaos_gpu_secure_2025",
        bucket_name: str = "manaos-gpu-results",
        region_name: str = "us-east-1",
        log_dir: str = "/root/logs/runpod_integration"
    ):
        self.bucket_name = bucket_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # S3クライアント初期化
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name
        )
        
        # バケット作成（存在しない場合）
        self._ensure_bucket_exists()
    
    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        log_file = self.log_dir / "s3_manager.log"
        with open(log_file, "a") as f:
            f.write(log_message + "\n")
    
    def _ensure_bucket_exists(self):
        """バケットが存在することを確認"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self._log(f"バケット存在確認: {self.bucket_name}")
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                self._log(f"バケット作成: {self.bucket_name}")
            except Exception as e:
                self._log(f"バケット作成失敗: {e}", "ERROR")
    
    def upload_file(
        self,
        local_path: str,
        s3_key: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        ファイルをS3にアップロード
        
        Args:
            local_path: ローカルファイルパス
            s3_key: S3キー（指定しない場合はファイル名）
            metadata: メタデータ
            
        Returns:
            結果辞書
        """
        local_file = Path(local_path)
        
        if not local_file.exists():
            self._log(f"ファイルが存在しません: {local_path}", "ERROR")
            return {
                "success": False,
                "error": f"File not found: {local_path}"
            }
        
        if not s3_key:
            s3_key = local_file.name
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(
                str(local_file),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            self._log(f"アップロード成功: {s3_key}")
            
            return {
                "success": True,
                "bucket": self.bucket_name,
                "key": s3_key,
                "size": local_file.stat().st_size
            }
            
        except Exception as e:
            self._log(f"アップロード失敗: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }
    
    def download_file(
        self,
        s3_key: str,
        local_path: str
    ) -> Dict[str, Any]:
        """
        S3からファイルをダウンロード
        
        Args:
            s3_key: S3キー
            local_path: ローカル保存先パス
            
        Returns:
            結果辞書
        """
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(local_file)
            )
            
            self._log(f"ダウンロード成功: {s3_key} -> {local_path}")
            
            return {
                "success": True,
                "bucket": self.bucket_name,
                "key": s3_key,
                "local_path": str(local_file),
                "size": local_file.stat().st_size
            }
            
        except Exception as e:
            self._log(f"ダウンロード失敗: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        署名付きURLを生成
        
        Args:
            s3_key: S3キー
            expiration: 有効期限（秒）
            
        Returns:
            署名付きURL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            self._log(f"署名付きURL生成: {s3_key}")
            return url
            
        except Exception as e:
            self._log(f"URL生成失敗: {e}", "ERROR")
            return None
    
    def list_files(self, prefix: str = "") -> Dict[str, Any]:
        """
        ファイル一覧を取得
        
        Args:
            prefix: プレフィックス（フォルダ名等）
            
        Returns:
            ファイルリスト
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
            
            self._log(f"ファイル一覧取得: {len(files)}件")
            
            return {
                "success": True,
                "files": files,
                "count": len(files)
            }
            
        except Exception as e:
            self._log(f"一覧取得失敗: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_file(self, s3_key: str) -> Dict[str, Any]:
        """
        ファイルを削除
        
        Args:
            s3_key: S3キー
            
        Returns:
            結果辞書
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            self._log(f"削除成功: {s3_key}")
            
            return {
                "success": True,
                "key": s3_key
            }
            
        except Exception as e:
            self._log(f"削除失敗: {e}", "ERROR")
            return {
                "success": False,
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            # バケット一覧取得で接続確認
            self.s3_client.list_buckets()
            
            # ファイル数確認
            files = self.list_files()
            
            return {
                "success": True,
                "s3_connected": True,
                "bucket": self.bucket_name,
                "file_count": files.get('count', 0)
            }
            
        except Exception as e:
            self._log(f"ヘルスチェック失敗: {e}", "ERROR")
            return {
                "success": False,
                "s3_connected": False,
                "error": str(e)
            }


def main():
    """テスト用"""
    print("📦 S3 File Manager - Test\n")
    
    manager = S3FileManager()
    
    # ヘルスチェック
    print("1️⃣ Health Check...")
    health = manager.health_check()
    print(f"Result: {json.dumps(health, indent=2)}\n")
    
    # テストファイル作成＆アップロード
    print("2️⃣ Upload Test...")
    test_file = Path("/tmp/test_upload.txt")
    test_file.write_text("Hello from ManaOS GPU Integration!")
    
    result = manager.upload_file(
        str(test_file),
        "test/upload.txt",
        metadata={"source": "test"}
    )
    print(f"Result: {json.dumps(result, indent=2)}\n")
    
    # ファイル一覧
    print("3️⃣ List Files...")
    files = manager.list_files()
    print(f"Result: {json.dumps(files, indent=2)}\n")
    
    print("✅ Test completed!")


if __name__ == "__main__":
    main()


