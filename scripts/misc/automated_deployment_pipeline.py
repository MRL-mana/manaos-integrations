#!/usr/bin/env python3
"""
🚀 Automated Deployment Pipeline - 自動デプロイメントパイプライン
Git連携、自動テスト、段階的デプロイ、ロールバック
"""

import os
import json
import subprocess
import shutil
from manaos_logger import get_logger, get_service_logger
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import requests

logger = get_service_logger("automated-deployment-pipeline")


@dataclass
class DeploymentStage:
    """デプロイメントステージ"""
    stage_id: str
    name: str
    commands: List[str]
    rollback_commands: List[str]
    timeout: int
    required: bool


@dataclass
class Deployment:
    """デプロイメント"""
    deployment_id: str
    branch: str
    commit_hash: str
    target_devices: List[str]
    stages: List[DeploymentStage]
    status: str  # "pending", "running", "completed", "failed", "rolled_back"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_stage: Optional[str] = None
    error: Optional[str] = None


class AutomatedDeploymentPipeline:
    """自動デプロイメントパイプライン"""
    
    def __init__(self, config_path: str = "deployment_pipeline_config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Git設定
        self.git_repo_path = Path(self.config.get("git_repo_path", "."))
        self.git_branch = self.config.get("git_branch", "main")
        
        # デプロイメント履歴
        self.history_file = Path(self.config.get("history_file", "deployment_history.json"))
        self.deployment_history: List[Deployment] = self._load_history()
        
        # デプロイメントステージ定義
        self.stage_definitions = self.config.get("stages", [
            {
                "stage_id": "test",
                "name": "テスト実行",
                "commands": ["python -m pytest tests/"],
                "rollback_commands": [],
                "timeout": 300,
                "required": True
            },
            {
                "stage_id": "build",
                "name": "ビルド",
                "commands": ["python setup.py build"],
                "rollback_commands": [],
                "timeout": 600,
                "required": True
            },
            {
                "stage_id": "deploy",
                "name": "デプロイ",
                "commands": ["python deploy.py"],
                "rollback_commands": ["python rollback.py"],
                "timeout": 300,
                "required": True
            }
        ])
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "git_repo_path": ".",
                "git_branch": "main",
                "target_devices": ["manaos", "mothership"],
                "stages": [
                    {
                        "stage_id": "test",
                        "name": "テスト実行",
                        "commands": ["python -m pytest tests/"],
                        "rollback_commands": [],
                        "timeout": 300,
                        "required": True
                    },
                    {
                        "stage_id": "deploy",
                        "name": "デプロイ",
                        "commands": ["python deploy.py"],
                        "rollback_commands": ["python rollback.py"],
                        "timeout": 300,
                        "required": True
                    }
                ],
                "history_file": "deployment_history.json"
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def _load_history(self) -> List[Deployment]:
        """デプロイメント履歴を読み込む"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                deployments = []
                for d in history_data:
                    stages = [DeploymentStage(**s) for s in d.get("stages", [])]
                    deployment = Deployment(
                        deployment_id=d["deployment_id"],
                        branch=d["branch"],
                        commit_hash=d["commit_hash"],
                        target_devices=d["target_devices"],
                        stages=stages,
                        status=d["status"],
                        started_at=d.get("started_at"),
                        completed_at=d.get("completed_at"),
                        current_stage=d.get("current_stage"),
                        error=d.get("error")
                    )
                    deployments.append(deployment)
                return deployments
        return []
    
    def _save_history(self):
        """デプロイメント履歴を保存"""
        history_data = [asdict(d) for d in self.deployment_history]
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    
    def _run_command(self, command: str, timeout: int = 300, cwd: Optional[Path] = None) -> Dict[str, Any]:
        """
        コマンドを実行
        
        Args:
            command: 実行するコマンド
            timeout: タイムアウト（秒）
            cwd: 作業ディレクトリ
        
        Returns:
            実行結果
        """
        try:
            import shlex
            cmd = shlex.split(command) if isinstance(command, str) else command
            result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or self.git_repo_path,
                encoding='utf-8',
                errors='ignore'
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"コマンドがタイムアウトしました（{timeout}秒）"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_current_commit(self) -> Optional[str]:
        """現在のコミットハッシュを取得"""
        result = self._run_command("git rev-parse HEAD")
        if result["success"]:
            return result["stdout"].strip()
        return None
    
    def _checkout_branch(self, branch: str) -> bool:
        """ブランチをチェックアウト"""
        logger.info(f"ブランチをチェックアウト: {branch}")
        result = self._run_command(f"git checkout {branch}")
        if result["success"]:
            result = self._run_command("git pull")
            return result["success"]
        return False
    
    def _run_stage(self, stage: DeploymentStage, deployment: Deployment) -> bool:
        """
        デプロイメントステージを実行
        
        Args:
            stage: デプロイメントステージ
            deployment: デプロイメント
        
        Returns:
            成功時True
        """
        logger.info(f"ステージを実行: {stage.name}")
        deployment.current_stage = stage.stage_id
        
        for command in stage.commands:
            result = self._run_command(command, timeout=stage.timeout)
            if not result["success"]:
                error_msg = result.get("error", result.get("stderr", "Unknown error"))
                logger.error(f"ステージ実行エラー: {stage.name} - {error_msg}")
                deployment.error = error_msg
                return False
        
        logger.info(f"ステージ完了: {stage.name}")
        return True
    
    def _rollback_stage(self, stage: DeploymentStage, deployment: Deployment) -> bool:
        """
        デプロイメントステージをロールバック
        
        Args:
            stage: デプロイメントステージ
            deployment: デプロイメント
        
        Returns:
            成功時True
        """
        logger.info(f"ステージをロールバック: {stage.name}")
        
        for command in stage.rollback_commands:
            result = self._run_command(command, timeout=stage.timeout)
            if not result["success"]:
                logger.warning(f"ロールバックコマンドエラー: {command}")
        
        return True
    
    def deploy(self, branch: Optional[str] = None, target_devices: Optional[List[str]] = None) -> str:
        """
        デプロイメントを開始
        
        Args:
            branch: ブランチ名（Noneの場合は設定値を使用）
            target_devices: 対象デバイス（Noneの場合は設定値を使用）
        
        Returns:
            デプロイメントID
        """
        branch = branch or self.git_branch
        target_devices = target_devices or self.config.get("target_devices", [])
        
        # ブランチをチェックアウト
        if not self._checkout_branch(branch):
            raise Exception(f"ブランチのチェックアウトに失敗: {branch}")
        
        # コミットハッシュを取得
        commit_hash = self._get_current_commit()
        if not commit_hash:
            raise Exception("コミットハッシュの取得に失敗")
        
        # デプロイメントを作成
        deployment_id = f"deploy_{int(time.time())}_{commit_hash[:8]}"
        stages = [DeploymentStage(**s) for s in self.stage_definitions]
        
        deployment = Deployment(
            deployment_id=deployment_id,
            branch=branch,
            commit_hash=commit_hash,
            target_devices=target_devices,
            stages=stages,
            status="pending"
        )
        
        self.deployment_history.append(deployment)
        self._save_history()
        
        logger.info(f"デプロイメントを開始: {deployment_id}")
        
        # デプロイメントを実行
        try:
            deployment.status = "running"
            deployment.started_at = datetime.now().isoformat()
            
            for stage in stages:
                if not self._run_stage(stage, deployment):
                    # 失敗した場合、ロールバック
                    deployment.status = "failed"
                    logger.error(f"デプロイメント失敗: {deployment_id}")
                    
                    # ロールバックを実行
                    self._rollback_deployment(deployment)
                    break
            
            if deployment.status == "running":
                deployment.status = "completed"
                deployment.completed_at = datetime.now().isoformat()
                logger.info(f"デプロイメント完了: {deployment_id}")
            
        except Exception as e:
            deployment.status = "failed"
            deployment.error = str(e)
            logger.error(f"デプロイメントエラー: {e}")
            self._rollback_deployment(deployment)
        
        self._save_history()
        return deployment_id
    
    def _rollback_deployment(self, deployment: Deployment):
        """デプロイメントをロールバック"""
        logger.info(f"デプロイメントをロールバック: {deployment.deployment_id}")
        
        deployment.status = "rolled_back"
        
        # 各ステージをロールバック（逆順）
        for stage in reversed(deployment.stages):
            self._rollback_stage(stage, deployment)
        
        # 前のコミットに戻す
        self._run_command(f"git checkout {deployment.commit_hash}")
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Deployment]:
        """デプロイメントステータスを取得"""
        for deployment in self.deployment_history:
            if deployment.deployment_id == deployment_id:
                return deployment
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_deployments = len(self.deployment_history)
        successful_deployments = sum(1 for d in self.deployment_history if d.status == "completed")
        failed_deployments = sum(1 for d in self.deployment_history if d.status == "failed")
        
        return {
            "total_deployments": total_deployments,
            "successful_deployments": successful_deployments,
            "failed_deployments": failed_deployments,
            "success_rate": successful_deployments / max(total_deployments, 1),
            "recent_deployments": [asdict(d) for d in self.deployment_history[-10:]]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """システム状態を取得（統一インターフェース）"""
        return self.get_stats()


def main():
    """メイン関数（テスト用）"""
    pipeline = AutomatedDeploymentPipeline()
    
    # デプロイメントを実行
    try:
        deployment_id = pipeline.deploy()
        print(f"デプロイメントID: {deployment_id}")
        
        # ステータスを取得
        status = pipeline.get_deployment_status(deployment_id)
        if status:
            print(json.dumps(asdict(status), indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        print(f"デプロイメントエラー: {e}")
    
    # 統計を表示
    stats = pipeline.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    import time
    main()

