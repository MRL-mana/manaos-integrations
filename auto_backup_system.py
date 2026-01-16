#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 ManaOS 自動バックアップシステム
データベース・設定ファイルの自動バックアップ
"""

import os
import shutil
import json
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import schedule
import threading
import time

logger = logging.getLogger(__name__)


class AutoBackupSystem:
    """自動バックアップシステム"""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            backup_dir: バックアップディレクトリ
        """
        self.backup_dir = backup_dir or Path(__file__).parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # バックアップ対象
        self.backup_targets = {
            "databases": [
                "revenue_tracker.db",
                "task_queue.db",
                "content_generation.db",
                "prompt_optimizer.db",
            ],
            "configs": [
                "llm_routing_config.yaml",
                "notification_hub_config.yaml",
                "manaos_timeout_config.json",
            ],
            "logs": [
                "logs",
            ]
        }
        
        # バックアップ設定
        self.config = {
            "retention_days": 30,  # 30日間保持
            "compress": True,  # 圧縮するか
            "verify": True,  # 検証するか
        }
        
        self.running = False
        self.backup_thread = None
    
    def create_backup(self, target_type: str = "all") -> Dict[str, Any]:
        """
        バックアップを作成
        
        Args:
            target_type: バックアップ対象（"all", "databases", "configs", "logs"）
            
        Returns:
            バックアップ結果
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)
        
        results = {
            "timestamp": timestamp,
            "backup_path": str(backup_path),
            "files": [],
            "errors": []
        }
        
        targets = self.backup_targets.get(target_type, {})
        if target_type == "all":
            targets = self.backup_targets
        
        try:
            # データベースのバックアップ
            if target_type == "all" or "databases" in targets:
                for db_file in self.backup_targets["databases"]:
                    db_path = Path(db_file)
                    if db_path.exists():
                        backup_file = backup_path / db_path.name
                        shutil.copy2(db_path, backup_file)
                        results["files"].append(str(backup_file))
                        logger.info(f"✅ データベースをバックアップ: {db_file}")
            
            # 設定ファイルのバックアップ
            if target_type == "all" or "configs" in targets:
                for config_file in self.backup_targets["configs"]:
                    config_path = Path(config_file)
                    if config_path.exists():
                        backup_file = backup_path / config_path.name
                        shutil.copy2(config_path, backup_file)
                        results["files"].append(str(backup_file))
                        logger.info(f"✅ 設定ファイルをバックアップ: {config_file}")
            
            # ログのバックアップ
            if target_type == "all" or "logs" in targets:
                for log_dir in self.backup_targets["logs"]:
                    log_path = Path(log_dir)
                    if log_path.exists() and log_path.is_dir():
                        backup_log_dir = backup_path / log_path.name
                        shutil.copytree(log_path, backup_log_dir, dirs_exist_ok=True)
                        results["files"].append(str(backup_log_dir))
                        logger.info(f"✅ ログをバックアップ: {log_dir}")
            
            # 圧縮
            if self.config["compress"]:
                compressed_path = f"{backup_path}.tar.gz"
                self._compress_directory(backup_path, compressed_path)
                shutil.rmtree(backup_path)
                results["backup_path"] = compressed_path
                results["compressed"] = True
            
            # 検証
            if self.config["verify"]:
                verify_result = self.verify_backup(results["backup_path"])
                results["verified"] = verify_result
            
            # バックアップ情報を保存
            info_file = Path(results["backup_path"]).parent / f"{timestamp}_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ バックアップ完了: {results['backup_path']}")
            return results
            
        except Exception as e:
            error_msg = str(e)
            results["errors"].append(error_msg)
            logger.error(f"❌ バックアップエラー: {error_msg}")
            return results
    
    def _compress_directory(self, source_dir: Path, output_file: str):
        """ディレクトリを圧縮"""
        import tarfile
        
        with tarfile.open(output_file, 'w:gz') as tar:
            tar.add(source_dir, arcname=source_dir.name)
    
    def verify_backup(self, backup_path: str) -> bool:
        """
        バックアップを検証
        
        Args:
            backup_path: バックアップパス
            
        Returns:
            検証結果
        """
        try:
            backup_file = Path(backup_path)
            
            # ファイルが存在するか
            if not backup_file.exists():
                return False
            
            # 圧縮ファイルの場合、展開して検証
            if backup_path.endswith('.tar.gz'):
                import tarfile
                with tarfile.open(backup_path, 'r:gz') as tar:
                    members = tar.getmembers()
                    if not members:
                        return False
            else:
                # 通常のファイル/ディレクトリの場合
                if backup_file.is_file():
                    if backup_file.stat().st_size == 0:
                        return False
                elif backup_file.is_dir():
                    if not any(backup_file.iterdir()):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"バックアップ検証エラー: {e}")
            return False
    
    def cleanup_old_backups(self):
        """古いバックアップを削除"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config["retention_days"])
            deleted_count = 0
            
            for backup_item in self.backup_dir.iterdir():
                if backup_item.is_file() or backup_item.is_dir():
                    # タイムスタンプから日付を取得
                    try:
                        if backup_item.name.endswith('.tar.gz'):
                            timestamp_str = backup_item.stem
                        else:
                            timestamp_str = backup_item.name
                        
                        backup_date = datetime.strptime(timestamp_str[:15], "%Y%m%d_%H%M%S")
                        
                        if backup_date < cutoff_date:
                            if backup_item.is_file():
                                backup_item.unlink()
                            else:
                                shutil.rmtree(backup_item)
                            deleted_count += 1
                            logger.info(f"✅ 古いバックアップを削除: {backup_item.name}")
                    except ValueError:
                        # タイムスタンプ形式でない場合はスキップ
                        pass
            
            if deleted_count > 0:
                logger.info(f"✅ {deleted_count}個の古いバックアップを削除しました")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"バックアップクリーンアップエラー: {e}")
            return 0
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """バックアップ一覧を取得"""
        backups = []
        
        for backup_item in sorted(self.backup_dir.iterdir(), reverse=True):
            if backup_item.is_file() or backup_item.is_dir():
                try:
                    if backup_item.name.endswith('.tar.gz'):
                        timestamp_str = backup_item.stem
                        size = backup_item.stat().st_size
                    else:
                        timestamp_str = backup_item.name
                        if backup_item.is_file():
                            size = backup_item.stat().st_size
                        else:
                            size = sum(f.stat().st_size for f in backup_item.rglob('*') if f.is_file())
                    
                    backup_date = datetime.strptime(timestamp_str[:15], "%Y%m%d_%H%M%S")
                    
                    backups.append({
                        "name": backup_item.name,
                        "path": str(backup_item),
                        "date": backup_date.isoformat(),
                        "size_mb": size / 1024 / 1024,
                        "compressed": backup_item.name.endswith('.tar.gz')
                    })
                except ValueError:
                    pass
        
        return backups
    
    def restore_backup(self, backup_path: str, target_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        バックアップから復元
        
        Args:
            backup_path: バックアップパス
            target_dir: 復元先ディレクトリ
            
        Returns:
            復元結果
        """
        result = {
            "success": False,
            "restored_files": [],
            "errors": []
        }
        
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                result["errors"].append("バックアップファイルが見つかりません")
                return result
            
            restore_dir = target_dir or Path(__file__).parent
            
            # 圧縮ファイルの場合、展開
            if backup_path.endswith('.tar.gz'):
                import tarfile
                with tarfile.open(backup_path, 'r:gz') as tar:
                    tar.extractall(restore_dir)
                    result["restored_files"] = tar.getnames()
            else:
                # 通常のファイル/ディレクトリの場合
                if backup_file.is_file():
                    target_file = restore_dir / backup_file.name
                    shutil.copy2(backup_file, target_file)
                    result["restored_files"].append(str(target_file))
                elif backup_file.is_dir():
                    for item in backup_file.iterdir():
                        target_item = restore_dir / item.name
                        if item.is_file():
                            shutil.copy2(item, target_item)
                        else:
                            shutil.copytree(item, target_item, dirs_exist_ok=True)
                        result["restored_files"].append(str(target_item))
            
            result["success"] = True
            logger.info(f"✅ バックアップから復元完了: {backup_path}")
            
        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"❌ バックアップ復元エラー: {e}")
        
        return result
    
    def start_scheduled_backups(self, schedule_time: str = "02:00"):
        """
        スケジュールバックアップを開始
        
        Args:
            schedule_time: バックアップ時刻（HH:MM形式）
        """
        if self.running:
            logger.warning("スケジュールバックアップは既に実行中です")
            return
        
        # 毎日のバックアップ
        schedule.every().day.at(schedule_time).do(self.create_backup)
        
        # 週次クリーンアップ
        schedule.every().sunday.at("03:00").do(self.cleanup_old_backups)
        
        def run_schedule():
            self.running = True
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        
        self.backup_thread = threading.Thread(target=run_schedule, daemon=True)
        self.backup_thread.start()
        logger.info(f"✅ スケジュールバックアップを開始しました（毎日{schedule_time}）")
    
    def stop_scheduled_backups(self):
        """スケジュールバックアップを停止"""
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        logger.info("✅ スケジュールバックアップを停止しました")


# シングルトンインスタンス
_backup_system: Optional[AutoBackupSystem] = None


def get_backup_system(backup_dir: Optional[Path] = None) -> AutoBackupSystem:
    """バックアップシステムのシングルトン取得"""
    global _backup_system
    if _backup_system is None:
        _backup_system = AutoBackupSystem(backup_dir=backup_dir)
    return _backup_system








