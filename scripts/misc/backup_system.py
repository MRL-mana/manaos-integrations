#!/usr/bin/env python3
"""
💾 ManaOS 自動バックアップ・復旧システム
定期的な自動バックアップ・増分バックアップ・バックアップの検証・自動復旧
"""

import os
import json
import shutil
import sqlite3
import tarfile
import gzip
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
import schedule
import time

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_service_logger("backup-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("BackupSystem")


@dataclass
class BackupInfo:
    """バックアップ情報"""
    backup_id: str
    backup_type: str  # "full" or "incremental"
    backup_path: Path
    created_at: str
    size_bytes: int
    checksum: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BackupSystem:
    """自動バックアップ・復旧システム"""
    
    def __init__(
        self,
        backup_dir: Optional[Path] = None,
        retention_days: int = 30,
        backup_interval_hours: int = 24
    ):
        """
        初期化
        
        Args:
            backup_dir: バックアップディレクトリ
            retention_days: 保持日数
            backup_interval_hours: バックアップ間隔（時間）
        """
        self.backup_dir = backup_dir or Path(__file__).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.retention_days = retention_days
        self.backup_interval_hours = backup_interval_hours
        
        # バックアップ対象
        self.backup_targets = [
            Path(__file__).parent / "*.db",  # データベースファイル
            Path(__file__).parent / "*.json",  # 設定ファイル
            Path(__file__).parent / "logs",  # ログディレクトリ
        ]
        
        # バックアップ履歴
        self.backup_history: List[BackupInfo] = []
        self._load_backup_history()
        
        # スケジューラー
        self.scheduler_thread = None
        self.scheduling = False
        
        logger.info(f"✅ Backup System初期化完了")
    
    def _load_backup_history(self):
        """バックアップ履歴を読み込む"""
        history_file = self.backup_dir / "backup_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    self.backup_history = []
                    for info in history_data:
                        # 文字列をPathオブジェクトに変換
                        if "backup_path" in info and isinstance(info["backup_path"], str):
                            info["backup_path"] = Path(info["backup_path"])
                        self.backup_history.append(BackupInfo(**info))
            except Exception as e:
                logger.warning(f"バックアップ履歴読み込みエラー: {e}")
    
    def _save_backup_history(self):
        """バックアップ履歴を保存"""
        history_file = self.backup_dir / "backup_history.json"
        try:
            # Pathオブジェクトを文字列に変換
            history_data = []
            for info in self.backup_history:
                info_dict = asdict(info)
                # Pathオブジェクトを文字列に変換
                if isinstance(info_dict.get("backup_path"), Path):
                    info_dict["backup_path"] = str(info_dict["backup_path"])
                history_data.append(info_dict)
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "save_backup_history"},
                user_message="バックアップ履歴の保存に失敗しました"
            )
            logger.error(f"バックアップ履歴保存エラー: {error.message}")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """ファイルのチェックサムを計算"""
        import hashlib
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def create_backup(
        self,
        backup_type: str = "full",
        target_paths: Optional[List[Path]] = None
    ) -> BackupInfo:
        """
        バックアップを作成
        
        Args:
            backup_type: バックアップタイプ（"full" or "incremental"）
            target_paths: バックアップ対象パス（Noneの場合はデフォルト）
        
        Returns:
            バックアップ情報
        """
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_filename = f"{backup_id}.tar.gz"
        backup_path = self.backup_dir / backup_filename
        
        target_paths = target_paths or self.backup_targets
        
        try:
            # バックアップアーカイブを作成
            with tarfile.open(backup_path, 'w:gz') as tar:
                base_dir = Path(__file__).parent
                
                for target in target_paths:
                    if isinstance(target, str):
                        target = Path(target)
                    
                    # ワイルドカード対応
                    if '*' in str(target):
                        import glob
                        for path in glob.glob(str(target)):
                            path_obj = Path(path)
                            if path_obj.exists():
                                tar.add(path_obj, arcname=path_obj.relative_to(base_dir))
                    else:
                        if target.exists():
                            if target.is_dir():
                                tar.add(target, arcname=target.relative_to(base_dir))
                            else:
                                tar.add(target, arcname=target.name)
            
            # バックアップ情報を作成
            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_type=backup_type,
                backup_path=backup_path,
                created_at=datetime.now().isoformat(),
                size_bytes=backup_path.stat().st_size,
                checksum=self._calculate_checksum(backup_path)
            )
            
            # 履歴に追加
            self.backup_history.append(backup_info)
            self._save_backup_history()
            
            logger.info(f"✅ バックアップ作成完了: {backup_id} ({backup_info.size_bytes} bytes)")
            return backup_info
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "create_backup", "backup_id": backup_id},
                user_message="バックアップの作成に失敗しました"
            )
            logger.error(f"バックアップ作成エラー: {error.message}")
            raise
    
    def verify_backup(self, backup_info: BackupInfo) -> bool:
        """
        バックアップを検証
        
        Args:
            backup_info: バックアップ情報
        
        Returns:
            検証成功時True
        """
        if not backup_info.backup_path.exists():
            logger.error(f"バックアップファイルが見つかりません: {backup_info.backup_path}")
            return False
        
        # サイズチェック
        if backup_info.backup_path.stat().st_size != backup_info.size_bytes:
            logger.error(f"バックアップサイズが一致しません: {backup_info.backup_path}")
            return False
        
        # チェックサムチェック
        current_checksum = self._calculate_checksum(backup_info.backup_path)
        if current_checksum != backup_info.checksum:
            logger.error(f"バックアップチェックサムが一致しません: {backup_info.backup_path}")
            return False
        
        # アーカイブの整合性チェック
        try:
            with tarfile.open(backup_info.backup_path, 'r:gz') as tar:
                tar.getmembers()  # メンバーを読み込んで整合性をチェック
        except Exception as e:
            logger.error(f"バックアップアーカイブの整合性チェック失敗: {e}")
            return False
        
        logger.info(f"✅ バックアップ検証成功: {backup_info.backup_id}")
        return True
    
    def restore_backup(
        self,
        backup_info: BackupInfo,
        restore_dir: Optional[Path] = None
    ) -> bool:
        """
        バックアップから復旧
        
        Args:
            backup_info: バックアップ情報
            restore_dir: 復旧先ディレクトリ（Noneの場合は元の場所）
        
        Returns:
            復旧成功時True
        """
        if not self.verify_backup(backup_info):
            return False
        
        restore_dir = restore_dir or Path(__file__).parent
        
        try:
            with tarfile.open(backup_info.backup_path, 'r:gz') as tar:
                tar.extractall(restore_dir)
            
            logger.info(f"✅ バックアップ復旧完了: {backup_info.backup_id}")
            return True
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "restore_backup", "backup_id": backup_info.backup_id},
                user_message="バックアップからの復旧に失敗しました"
            )
            logger.error(f"バックアップ復旧エラー: {error.message}")
            return False
    
    def cleanup_old_backups(self):
        """古いバックアップを削除"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        removed_count = 0
        for backup_info in self.backup_history[:]:
            backup_date = datetime.fromisoformat(backup_info.created_at)
            if backup_date < cutoff_date:
                try:
                    if backup_info.backup_path.exists():
                        backup_info.backup_path.unlink()
                    self.backup_history.remove(backup_info)
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"バックアップ削除エラー: {e}")
        
        if removed_count > 0:
            self._save_backup_history()
            logger.info(f"✅ 古いバックアップ削除完了: {removed_count}件")
        
        return removed_count
    
    def start_auto_backup(self):
        """自動バックアップを開始"""
        if self.scheduling:
            return
        
        self.scheduling = True
        
        # スケジュール設定
        schedule.every(self.backup_interval_hours).hours.do(self._auto_backup_job)
        
        def scheduler_loop():
            while self.scheduling:
                schedule.run_pending()
                time.sleep(60)  # 1分ごとにチェック
        
        self.scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info(f"✅ 自動バックアップ開始（間隔: {self.backup_interval_hours}時間）")
    
    def stop_auto_backup(self):
        """自動バックアップを停止"""
        self.scheduling = False
        schedule.clear()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("🛑 自動バックアップ停止")
    
    def _auto_backup_job(self):
        """自動バックアップジョブ"""
        try:
            logger.info("🔄 自動バックアップ開始...")
            backup_info = self.create_backup(backup_type="full")
            
            # 検証
            if self.verify_backup(backup_info):
                logger.info("✅ 自動バックアップ完了")
            else:
                logger.error("❌ 自動バックアップ検証失敗")
            
            # 古いバックアップを削除
            self.cleanup_old_backups()
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "auto_backup"},
                user_message="自動バックアップに失敗しました"
            )
            logger.error(f"自動バックアップエラー: {error.message}")


# グローバルインスタンス
backup_system = BackupSystem()

