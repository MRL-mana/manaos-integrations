"""
クラウド統合システム
AWS/Azure/GCP統合
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    print("AWS SDKがインストールされていません。")
    print("インストール: pip install boto3")

try:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("Azure SDKがインストールされていません。")
    print("インストール: pip install azure-identity azure-storage-blob")

try:
    from google.cloud import storage
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    print("GCP SDKがインストールされていません。")
    print("インストール: pip install google-cloud-storage")


class AWSIntegration:
    """AWS統合クラス"""
    
    def __init__(self, region_name: str = "us-east-1"):
        """
        初期化
        
        Args:
            region_name: リージョン名
        """
        self.region_name = region_name
        self.s3_client = None
        self.ec2_client = None
        
        if AWS_AVAILABLE:
            self._initialize_clients()
    
    def _initialize_clients(self):
        """クライアントを初期化"""
        try:
            self.s3_client = boto3.client('s3', region_name=self.region_name)
            self.ec2_client = boto3.client('ec2', region_name=self.region_name)
        except Exception as e:
            print(f"AWSクライアント初期化エラー: {e}")
    
    def is_available(self) -> bool:
        """利用可能かチェック"""
        return AWS_AVAILABLE and self.s3_client is not None
    
    def upload_to_s3(
        self,
        bucket_name: str,
        file_path: str,
        object_name: Optional[str] = None
    ) -> bool:
        """
        S3にファイルをアップロード
        
        Args:
            bucket_name: バケット名
            file_path: ファイルパス
            object_name: オブジェクト名（オプション）
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        if object_name is None:
            object_name = Path(file_path).name
        
        try:
            self.s3_client.upload_file(file_path, bucket_name, object_name)
            return True
        except ClientError as e:
            print(f"S3アップロードエラー: {e}")
            return False
    
    def download_from_s3(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str
    ) -> bool:
        """
        S3からファイルをダウンロード
        
        Args:
            bucket_name: バケット名
            object_name: オブジェクト名
            file_path: 保存先パス
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            self.s3_client.download_file(bucket_name, object_name, file_path)
            return True
        except ClientError as e:
            print(f"S3ダウンロードエラー: {e}")
            return False
    
    def list_s3_objects(self, bucket_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """
        S3オブジェクト一覧を取得
        
        Args:
            bucket_name: バケット名
            prefix: プレフィックス（オプション）
            
        Returns:
            オブジェクト情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat()
                })
            
            return objects
        except ClientError as e:
            print(f"S3一覧取得エラー: {e}")
            return []


class AzureIntegration:
    """Azure統合クラス"""
    
    def __init__(self, account_url: Optional[str] = None):
        """
        初期化
        
        Args:
            account_url: ストレージアカウントURL（オプション）
        """
        self.account_url = account_url
        self.blob_service_client = None
        
        if AZURE_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """クライアントを初期化"""
        try:
            if self.account_url:
                credential = DefaultAzureCredential()
                self.blob_service_client = BlobServiceClient(
                    account_url=self.account_url,
                    credential=credential
                )
            else:
                # 環境変数から取得
                account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
                if account_name:
                    account_url = f"https://{account_name}.blob.core.windows.net"
                    credential = DefaultAzureCredential()
                    self.blob_service_client = BlobServiceClient(
                        account_url=account_url,
                        credential=credential
                    )
        except Exception as e:
            print(f"Azureクライアント初期化エラー: {e}")
    
    def is_available(self) -> bool:
        """利用可能かチェック"""
        return AZURE_AVAILABLE and self.blob_service_client is not None
    
    def upload_to_blob(
        self,
        container_name: str,
        file_path: str,
        blob_name: Optional[str] = None
    ) -> bool:
        """
        Blob Storageにファイルをアップロード
        
        Args:
            container_name: コンテナ名
            file_path: ファイルパス
            blob_name: Blob名（オプション）
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        if blob_name is None:
            blob_name = Path(file_path).name
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            return True
        except Exception as e:
            print(f"Blobアップロードエラー: {e}")
            return False
    
    def download_from_blob(
        self,
        container_name: str,
        blob_name: str,
        file_path: str
    ) -> bool:
        """
        Blob Storageからファイルをダウンロード
        
        Args:
            container_name: コンテナ名
            blob_name: Blob名
            file_path: 保存先パス
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            with open(file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            
            return True
        except Exception as e:
            print(f"Blobダウンロードエラー: {e}")
            return False


class GCPIntegration:
    """GCP統合クラス"""
    
    def __init__(self, project_id: Optional[str] = None):
        """
        初期化
        
        Args:
            project_id: プロジェクトID（オプション）
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.storage_client = None
        
        if GCP_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """クライアントを初期化"""
        try:
            # 環境変数でGCP認証情報が設定されているかチェック
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.getenv("GOOGLE_CLOUD_PROJECT"):
                # ローカル環境では警告のみ（エラーにしない）
                import logging
                logger = logging.getLogger(__name__)
                logger.debug("GCP認証情報が設定されていません。ローカル環境では問題ありません。")
                return
            
            self.storage_client = storage.Client(project=self.project_id)
        except Exception as e:
            # ローカル環境では警告のみ
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"GCPクライアント初期化エラー（ローカル環境では問題ありません）: {e}")
    
    def is_available(self) -> bool:
        """利用可能かチェック"""
        return GCP_AVAILABLE and self.storage_client is not None
    
    def upload_to_gcs(
        self,
        bucket_name: str,
        file_path: str,
        blob_name: Optional[str] = None
    ) -> bool:
        """
        Google Cloud Storageにファイルをアップロード
        
        Args:
            bucket_name: バケット名
            file_path: ファイルパス
            blob_name: Blob名（オプション）
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        if blob_name is None:
            blob_name = Path(file_path).name
        
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(file_path)
            return True
        except Exception as e:
            print(f"GCSアップロードエラー: {e}")
            return False
    
    def download_from_gcs(
        self,
        bucket_name: str,
        blob_name: str,
        file_path: str
    ) -> bool:
        """
        Google Cloud Storageからファイルをダウンロード
        
        Args:
            bucket_name: バケット名
            blob_name: Blob名
            file_path: 保存先パス
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_filename(file_path)
            return True
        except Exception as e:
            print(f"GCSダウンロードエラー: {e}")
            return False
    
    def list_gcs_objects(self, bucket_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """
        GCSオブジェクト一覧を取得
        
        Args:
            bucket_name: バケット名
            prefix: プレフィックス（オプション）
            
        Returns:
            オブジェクト情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            
            objects = []
            for blob in blobs:
                objects.append({
                    "name": blob.name,
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None
                })
            
            return objects
        except Exception as e:
            print(f"GCS一覧取得エラー: {e}")
            return []


class CloudIntegration:
    """クラウド統合クラス"""
    
    def __init__(self):
        """初期化"""
        self.aws = AWSIntegration()
        self.azure = AzureIntegration()
        self.gcp = GCPIntegration()
    
    def upload_to_cloud(
        self,
        provider: str,
        file_path: str,
        destination: str,
        **kwargs
    ) -> bool:
        """
        クラウドにファイルをアップロード
        
        Args:
            provider: プロバイダー（aws, azure, gcp）
            file_path: ファイルパス
            destination: 送信先（バケット名/コンテナ名）
            **kwargs: 追加引数
            
        Returns:
            成功時True
        """
        if provider == "aws":
            return self.aws.upload_to_s3(
                bucket_name=destination,
                file_path=file_path,
                object_name=kwargs.get("object_name")
            )
        elif provider == "azure":
            return self.azure.upload_to_blob(
                container_name=destination,
                file_path=file_path,
                blob_name=kwargs.get("blob_name")
            )
        elif provider == "gcp":
            return self.gcp.upload_to_gcs(
                bucket_name=destination,
                file_path=file_path,
                blob_name=kwargs.get("blob_name")
            )
        else:
            return False
    
    def download_from_cloud(
        self,
        provider: str,
        source: str,
        object_name: str,
        file_path: str
    ) -> bool:
        """
        クラウドからファイルをダウンロード
        
        Args:
            provider: プロバイダー（aws, azure, gcp）
            source: ソース（バケット名/コンテナ名）
            object_name: オブジェクト名
            file_path: 保存先パス
            
        Returns:
            成功時True
        """
        if provider == "aws":
            return self.aws.download_from_s3(source, object_name, file_path)
        elif provider == "azure":
            return self.azure.download_from_blob(source, object_name, file_path)
        elif provider == "gcp":
            return self.gcp.download_from_gcs(source, object_name, file_path)
        else:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "aws_available": self.aws.is_available(),
            "azure_available": self.azure.is_available(),
            "gcp_available": self.gcp.is_available(),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("クラウド統合システムテスト")
    print("=" * 60)
    
    cloud = CloudIntegration()
    
    status = cloud.get_status()
    print("\nクラウドプロバイダー状態:")
    print(f"  AWS: {'利用可能' if status['aws_available'] else '利用不可'}")
    print(f"  Azure: {'利用可能' if status['azure_available'] else '利用不可'}")
    print(f"  GCP: {'利用可能' if status['gcp_available'] else '利用不可'}")


if __name__ == "__main__":
    main()
