#!/usr/bin/env python3
"""
💾 Unified Backup Manager - 統合バックアップ管理システム
全デバイスのバックアップを一元管理
"""

import os
import json
import shutil
import hashlib
import schedule
import time
from manaos_logger import get_logger
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# Google Drive統合をインポート
try:
    from google_drive_integration import GoogleDriveIntegration
except ImportError:
    GoogleDriveIntegration = None

logger = get_logger(__name__)


@dataclass
class BackupJob:
    """バックアップジョブ"""
    job_id: str
    device_name: str
    source_path: str
    destination_path: str
    backup_type: str  # "full", "incremental"
    schedule: str  # cron形式
    enabled: bool
    last_run: Optional[str] = None
    last_status: Optional[str] = None


@dataclass
class BackupResult:
    """バックアップ結果"""
    job_id: str
    timestamp: str
    status: str  # "success", "failed", "partial"
    files_backed_up: int
    total_size_mb: float
    duration_seconds: float
    error_message: Optional[str] = None


class UnifiedBackupManager:
    """統合バックアップ管理システム"""
    
    def __init__(self, config_path: str = "unified_backup_config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # バックアップディレクトリ
        self.backup_base_dir = Path(self.config.get("backup_base_dir", "./backups"))
        self.backup_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Google Drive統合
        self.drive_integration = None
        if GoogleDriveIntegration and self.config.get("use_google_drive", False):
            credentials_path = self.config.get("credentials_path", "credentials.json")
            token_path = self.config.get("token_path", "token.json")
            self.drive_integration = GoogleDriveIntegration(
                credentials_path=credentials_path,
                token_path=token_path
            )
        
        # バックアップジョブ
        self.backup_jobs: List[BackupJob] = []
        for job_config in self.config.get("jobs", []):
            self.backup_jobs.append(BackupJob(**job_config))
        
        # バックアップ履歴
        self.history_file = Path(self.config.get("history_file", "backup_history.json"))
        self.backup_history: List[BackupResult] = self._load_history()
        
        # 増分バックアップの状態管理
        self.state_file = Path(self.config.get("state_file", "backup_state.json"))
        self.backup_state = self._load_state()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "backup_base_dir": "./backups",
                "use_google_drive": True,
                "credentials_path": "credentials.json",
                "token_path": "token.json",
                "jobs": [
                    {
                        "job_id": "manaos_backup",
                        "device_name": "ManaOS",
                        "source_path": "./manaos_integrations",
                        "destination_path": "ManaOS_Backups",
                        "backup_type": "incremental",
                        "schedule": "0 2 * * *",  # 毎日2時
                        "enabled": True
                    }
                ],
                "history_file": "backup_history.json",
                "state_file": "backup_state.json",
                "max_history": 1000
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def _load_history(self) -> List[BackupResult]:
        """バックアップ履歴を読み込む"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                return [BackupResult(**item) for item in history_data]
        return []
    
    def _save_history(self):
        """バックアップ履歴を保存"""
        max_history = self.config.get("max_history", 1000)
        history_data = [asdict(h) for h in self.backup_history[-max_history:]]
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    
    def _load_state(self) -> Dict[str, Any]:
        """バックアップ状態を読み込む"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_state(self):
        """バックアップ状態を保存"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.backup_state, f, indent=2, ensure_ascii=False)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュを計算"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"ファイルハッシュ計算エラー: {e}")
            return ""
    
    def _should_backup_file(self, file_path: Path, job: BackupJob) -> bool:
        """ファイルをバックアップすべきか判定（増分バックアップ用）"""
        if job.backup_type == "full":
            return True
        
        # 増分バックアップの場合、変更されたファイルのみ
        relative_path = str(file_path.relative_to(Path(job.source_path)))
        state_key = f"{job.job_id}:{relative_path}"
        
        if state_key not in self.backup_state:
            return True
        
        stored_hash = self.backup_state[state_key].get("hash")
        current_hash = self._get_file_hash(file_path)
        
        return stored_hash != current_hash
    
    def backup_job(self, job: BackupJob) -> BackupResult:
        """
        バックアップジョブを実行
        
        Args:
            job: バックアップジョブ
        
        Returns:
            バックアップ結果
        """
        start_time = time.time()
        logger.info(f"バックアップジョブを開始: {job.job_id}")
        
        source_path = Path(job.source_path)
        if not source_path.exists():
            error_msg = f"ソースパスが存在しません: {source_path}"
            logger.error(error_msg)
            result = BackupResult(
                job_id=job.job_id,
                timestamp=datetime.now().isoformat(),
                status="failed",
                files_backed_up=0,
                total_size_mb=0.0,
                duration_seconds=time.time() - start_time,
                error_message=error_msg
            )
            self.backup_history.append(result)
            self._save_history()
            return result
        
        # バックアップ先ディレクトリ
        backup_dir = self.backup_base_dir / job.device_name / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_backed_up = 0
        total_size = 0
        errors = []
        
        try:
            # ファイルをコピー
            for file_path in source_path.rglob("*"):
                if file_path.is_dir():
                    continue
                
                if not self._should_backup_file(file_path, job):
                    continue
                
                relative_path = file_path.relative_to(source_path)
                dest_path = backup_dir / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.copy2(file_path, dest_path)
                    files_backed_up += 1
                    total_size += file_path.stat().st_size
                    
                    # 状態を更新
                    if job.backup_type == "incremental":
                        state_key = f"{job.job_id}:{relative_path}"
                        self.backup_state[state_key] = {
                            "hash": self._get_file_hash(file_path),
                            "last_backup": datetime.now().isoformat()
                        }
                except Exception as e:
                    error_msg = f"ファイルコピーエラー: {file_path} - {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Google Driveにアップロード（オプション）
            if self.drive_integration and self.drive_integration.is_available():
                try:
                    drive_path = f"{job.destination_path}/{backup_dir.name}"
                    # ディレクトリをZIP化してアップロード（簡易実装）
                    logger.info(f"Google Driveにアップロード中: {drive_path}")
                    # 実装は省略（必要に応じて追加）
                except Exception as e:
                    logger.warning(f"Google Driveアップロードエラー: {e}")
            
            # 結果を記録
            status = "success" if not errors else "partial"
            result = BackupResult(
                job_id=job.job_id,
                timestamp=datetime.now().isoformat(),
                status=status,
                files_backed_up=files_backed_up,
                total_size_mb=total_size / (1024 * 1024),
                duration_seconds=time.time() - start_time,
                error_message="; ".join(errors) if errors else None
            )
            
            # ジョブの最終実行時刻を更新
            job.last_run = datetime.now().isoformat()
            job.last_status = status
            
            self.backup_history.append(result)
            self._save_history()
            self._save_state()
            
            logger.info(f"バックアップジョブ完了: {job.job_id} - {files_backed_up}ファイル、{result.total_size_mb:.2f}MB")
            
            return result
            
        except Exception as e:
            error_msg = f"バックアップジョブエラー: {str(e)}"
            logger.error(error_msg)
            result = BackupResult(
                job_id=job.job_id,
                timestamp=datetime.now().isoformat(),
                status="failed",
                files_backed_up=files_backed_up,
                total_size_mb=total_size / (1024 * 1024),
                duration_seconds=time.time() - start_time,
                error_message=error_msg
            )
            self.backup_history.append(result)
            self._save_history()
            return result
    
    def run_all_jobs(self):
        """全バックアップジョブを実行"""
        logger.info("全バックアップジョブを実行します...")
        
        for job in self.backup_jobs:
            if job.enabled:
                self.backup_job(job)
    
    def schedule_jobs(self):
        """バックアップジョブをスケジュール"""
        logger.info("バックアップジョブをスケジュールします...")
        
        for job in self.backup_jobs:
            if job.enabled:
                schedule.every().day.at(job.schedule.split()[1] + ":" + job.schedule.split()[0]).do(
                    lambda j=job: self.backup_job(j)
                )
                logger.info(f"ジョブをスケジュール: {job.job_id} - {job.schedule}")
    
    def run_scheduler(self):
        """スケジューラーを実行"""
        self.schedule_jobs()
        
        logger.info("バックアップスケジューラーを開始します...")
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_backups = len(self.backup_history)
        successful_backups = sum(1 for h in self.backup_history if h.status == "success")
        total_size_mb = sum(h.total_size_mb for h in self.backup_history)
        
        return {
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "failed_backups": total_backups - successful_backups,
            "success_rate": successful_backups / max(total_backups, 1),
            "total_size_mb": total_size_mb,
            "jobs": [asdict(job) for job in self.backup_jobs],
            "recent_backups": [asdict(h) for h in self.backup_history[-10:]]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """システム状態を取得（統一インターフェース）"""
        return self.get_stats()


def main():
    """メイン関数（テスト用）"""
    manager = UnifiedBackupManager()
    
    # 全ジョブを実行
    manager.run_all_jobs()
    
    # 統計を表示
    stats = manager.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

