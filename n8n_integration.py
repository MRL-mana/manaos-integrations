#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
n8n統合モジュール
n8nワークフローエンジンとの統合
"""

import os
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime

# ベースクラスのインポート
from base_integration import BaseIntegration

try:
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class N8NIntegration(BaseIntegration):
    """n8n統合クラス"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            base_url: n8nサーバーのベースURL
            api_key: n8n APIキー
        """
        super().__init__("N8N")
        
        # 環境変数から読み込む（.envファイルから）
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            env_file = Path(__file__).parent / '.env'
            if env_file.exists():
                load_dotenv(env_file)
        except ImportError:
            pass
        
        self.base_url = (base_url or os.getenv("N8N_BASE_URL", "http://127.0.0.1:5678")).rstrip("/")
        self.api_key = api_key or os.getenv("N8N_API_KEY")
        self.session = None
        
        if REQUESTS_AVAILABLE and self.api_key:
            self.session = requests.Session()
            self.session.headers.update({
                "X-N8N-API-KEY": self.api_key,
                "Content-Type": "application/json"
            })
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not REQUESTS_AVAILABLE:
            self.logger.warning("requestsライブラリがインストールされていません")
            return False
        
        if not self.api_key:
            self.logger.warning("n8n APIキーが設定されていません")
            return False
        
        # 接続テスト
        try:
            response = self.session.get(f"{self.base_url}/api/v1/workflows", timeout=5)
            if response.status_code == 200:
                self.logger.info(f"n8nサーバーに接続しました: {self.base_url}")
                return True
            else:
                self.logger.warning(f"n8nサーバーへの接続に失敗: {response.status_code}")
                return False
        except Exception as e:
            self.logger.warning(f"n8nサーバーへの接続テストに失敗: {e}")
            return False
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return REQUESTS_AVAILABLE and self.api_key is not None and self.session is not None
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        ワークフロー一覧を取得
        
        Returns:
            ワークフロー情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/workflows", timeout=10)
            if response.status_code == 200:
                workflows = response.json()
                self.logger.info(f"ワークフロー一覧を取得しました: {len(workflows)}件")
                return workflows if isinstance(workflows, list) else []
            else:
                self.logger.warning(f"ワークフロー一覧の取得に失敗: {response.status_code}")
                return []
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"action": "list_workflows"},
                user_message="ワークフロー一覧の取得に失敗しました"
            )
            self.logger.error(f"ワークフロー一覧取得エラー: {error.message}")
            return []
    
    def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        ワークフローを実行
        
        Args:
            workflow_id: ワークフローID
            data: ワークフローに渡すデータ
            
        Returns:
            実行結果
        """
        if not self.is_available():
            return None
        
        try:
            payload = data or {}
            response = self.session.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/execute",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"ワークフローを実行しました: {workflow_id}")
                return result
            else:
                self.logger.warning(f"ワークフローの実行に失敗: {response.status_code}")
                return None
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"workflow_id": workflow_id, "action": "execute_workflow"},
                user_message="ワークフローの実行に失敗しました"
            )
            self.logger.error(f"ワークフロー実行エラー: {error.message}")
            return None
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        ワークフロー情報を取得
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            ワークフロー情報
        """
        if not self.is_available():
            return None
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/workflows/{workflow_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"ワークフロー情報の取得に失敗: {response.status_code}")
                return None
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"workflow_id": workflow_id, "action": "get_workflow"},
                user_message="ワークフロー情報の取得に失敗しました"
            )
            self.logger.error(f"ワークフロー情報取得エラー: {error.message}")
            return None
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """
        ワークフローを有効化
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/activate",
                timeout=10
            )
            if response.status_code == 200:
                self.logger.info(f"ワークフローを有効化しました: {workflow_id}")
                return True
            else:
                self.logger.warning(f"ワークフローの有効化に失敗: {response.status_code}")
                return False
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"workflow_id": workflow_id, "action": "activate_workflow"},
                user_message="ワークフローの有効化に失敗しました"
            )
            self.logger.error(f"ワークフロー有効化エラー: {error.message}")
            return False
    
    def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        ワークフローを無効化
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/deactivate",
                timeout=10
            )
            if response.status_code == 200:
                self.logger.info(f"ワークフローを無効化しました: {workflow_id}")
                return True
            else:
                self.logger.warning(f"ワークフローの無効化に失敗: {response.status_code}")
                return False
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"workflow_id": workflow_id, "action": "deactivate_workflow"},
                user_message="ワークフローの無効化に失敗しました"
            )
            self.logger.error(f"ワークフロー無効化エラー: {error.message}")
            return False

