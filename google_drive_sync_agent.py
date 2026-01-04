#!/usr/bin/env python3
"""
📁 Google Drive Sync Agent - ファイル同期エージェント
指定フォルダをGoogle Driveと自動同期
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

# Google Drive統合をインポート
try:
    from google_drive_integration import GoogleDriveIntegration
except ImportError:
    print("google_drive_integrationモジュールが見つかりません")
    GoogleDriveIntegration = None

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """ファイル変更イベントハンドラー"""
    
    def __init__(self, sync_agent):
        self.sync_agent = sync_agent
        self.debounce_time = 5  # 5秒のデバウンス
        self.pending_changes = {}
    
    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_change(event.src_path, "modified")
    
    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_change(event.src_path, "created")
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        self._handle_change(event.src_path, "deleted")
    
    def _handle_change(self, file_path: str, event_type: str):
        """変更を処理（デバウンス付き）"""
        file_path = Path(file_path)
        
        # デバウンス処理
        current_time = time.time()
        if file_path in self.pending_changes:
            last_time, last_type = self.pending_changes[file_path]
            if current_time - last_time < self.debounce_time:
                return
        
        self.pending_changes[file_path] = (current_time, event_type)
        
        # 同期をスケジュール
        self.sync_agent.schedule_sync(file_path, event_type)


class GoogleDriveSyncAgent:
    """Google Drive同期エージェント"""
    
    def __init__(self, config_path: str = "google_drive_sync_config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.sync_rules = self.config.get("sync_rules", [])
        self.drive_integration = None
        self.observer = None
        self.sync_queue = []
        
        # Google Drive統合を初期化
        if GoogleDriveIntegration:
            credentials_path = self.config.get("credentials_path", "credentials.json")
            token_path = self.config.get("token_path", "token.json")
            self.drive_integration = GoogleDriveIntegration(
                credentials_path=credentials_path,
                token_path=token_path
            )
        
        # 同期状態を管理するファイル
        self.state_file = Path(self.config.get("state_file", "sync_state.json"))
        self.sync_state = self._load_state()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "credentials_path": "credentials.json",
                "token_path": "token.json",
                "state_file": "sync_state.json",
                "sync_rules": [
                    {
                        "local_path": "./backups",
                        "drive_folder": "ManaOS_Backups",
                        "sync_mode": "bidirectional",  # "upload_only", "download_only", "bidirectional"
                        "include_patterns": ["*"],
                        "exclude_patterns": [".git", "__pycache__", "*.pyc"]
                    }
                ],
                "sync_interval": 60,  # 秒
                "auto_sync": True
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def _load_state(self) -> Dict[str, Any]:
        """同期状態を読み込む"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_sync": None,
            "synced_files": {},
            "conflicts": []
        }
    
    def _save_state(self):
        """同期状態を保存"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.sync_state, f, indent=2, ensure_ascii=False)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュを計算"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"ファイルハッシュ計算エラー: {e}")
            return ""
    
    def schedule_sync(self, file_path: Path, event_type: str):
        """同期をスケジュール"""
        self.sync_queue.append({
            "file_path": str(file_path),
            "event_type": event_type,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"同期をスケジュール: {file_path} ({event_type})")
    
    def sync_file(self, file_path: Path, sync_rule: Dict[str, Any]) -> bool:
        """ファイルを同期"""
        if not self.drive_integration or not self.drive_integration.is_available():
            logger.error("Google Drive統合が利用できません")
            return False
        
        try:
            local_path = Path(sync_rule["local_path"])
            relative_path = file_path.relative_to(local_path)
            drive_folder = sync_rule["drive_folder"]
            sync_mode = sync_rule.get("sync_mode", "upload_only")
            
            # ファイルが存在する場合
            if file_path.exists():
                # ハッシュを計算
                file_hash = self._get_file_hash(file_path)
                
                # 既に同期済みかチェック
                sync_key = str(relative_path)
                if sync_key in self.sync_state["synced_files"]:
                    stored_hash = self.sync_state["synced_files"][sync_key].get("hash")
                    if stored_hash == file_hash:
                        logger.debug(f"ファイルは既に同期済み: {file_path}")
                        return True
                
                # Google Driveにアップロード
                drive_path = f"{drive_folder}/{relative_path}"
                result = self.drive_integration.upload_file(
                    str(file_path),
                    drive_path,
                    overwrite=True
                )
                
                if result:
                    # 同期状態を更新
                    self.sync_state["synced_files"][sync_key] = {
                        "hash": file_hash,
                        "last_sync": datetime.now().isoformat(),
                        "drive_path": drive_path
                    }
                    self._save_state()
                    logger.info(f"ファイルを同期しました: {file_path} -> {drive_path}")
                    return True
                else:
                    logger.error(f"ファイルの同期に失敗: {file_path}")
                    return False
            else:
                # ファイルが削除された場合
                sync_key = str(relative_path)
                if sync_key in self.sync_state["synced_files"]:
                    drive_path = self.sync_state["synced_files"][sync_key].get("drive_path")
                    if drive_path:
                        # Google Driveから削除（オプション）
                        logger.info(f"ファイルが削除されました: {file_path}")
                        # 削除処理は実装が必要
                
                # 同期状態から削除
                if sync_key in self.sync_state["synced_files"]:
                    del self.sync_state["synced_files"][sync_key]
                    self._save_state()
                
                return True
                
        except Exception as e:
            logger.error(f"ファイル同期エラー: {e}")
            return False
    
    def sync_rule(self, sync_rule: Dict[str, Any]):
        """同期ルールに従って同期"""
        local_path = Path(sync_rule["local_path"])
        
        if not local_path.exists():
            logger.warning(f"ローカルパスが存在しません: {local_path}")
            return
        
        # ファイルをスキャン
        include_patterns = sync_rule.get("include_patterns", ["*"])
        exclude_patterns = sync_rule.get("exclude_patterns", [])
        
        for file_path in local_path.rglob("*"):
            if file_path.is_dir():
                continue
            
            # パターンマッチング
            relative_path = file_path.relative_to(local_path)
            should_include = any(
                file_path.match(pattern) for pattern in include_patterns
            )
            should_exclude = any(
                file_path.match(pattern) for pattern in exclude_patterns
            )
            
            if should_include and not should_exclude:
                self.sync_file(file_path, sync_rule)
    
    def sync_all(self):
        """全同期ルールを実行"""
        logger.info("全同期ルールを実行します...")
        
        for sync_rule in self.sync_rules:
            logger.info(f"同期ルールを実行: {sync_rule['local_path']} -> {sync_rule['drive_folder']}")
            self.sync_rule(sync_rule)
        
        self.sync_state["last_sync"] = datetime.now().isoformat()
        self._save_state()
        logger.info("全同期が完了しました")
    
    def process_sync_queue(self):
        """同期キューを処理"""
        if not self.sync_queue:
            return
        
        # キューから取り出して処理
        while self.sync_queue:
            sync_item = self.sync_queue.pop(0)
            file_path = Path(sync_item["file_path"])
            event_type = sync_item["event_type"]
            
            # 該当する同期ルールを探す
            for sync_rule in self.sync_rules:
                local_path = Path(sync_rule["local_path"])
                try:
                    if file_path.is_relative_to(local_path):
                        self.sync_file(file_path, sync_rule)
                        break
                except ValueError:
                    continue
    
    def start_watching(self):
        """ファイル監視を開始"""
        if not self.config.get("auto_sync", True):
            logger.info("自動同期が無効になっています")
            return
        
        logger.info("ファイル監視を開始します...")
        
        self.observer = Observer()
        handler = FileChangeHandler(self)
        
        # 各同期ルールのローカルパスを監視
        for sync_rule in self.sync_rules:
            local_path = Path(sync_rule["local_path"])
            if local_path.exists():
                self.observer.schedule(handler, str(local_path), recursive=True)
                logger.info(f"監視を開始: {local_path}")
        
        self.observer.start()
        
        try:
            while True:
                time.sleep(1)
                self.process_sync_queue()
        except KeyboardInterrupt:
            logger.info("監視を停止します...")
            self.observer.stop()
        
        self.observer.join()
    
    def run(self):
        """エージェントを実行"""
        # 初回同期
        self.sync_all()
        
        # 監視を開始
        if self.config.get("auto_sync", True):
            self.start_watching()
        else:
            # 定期同期モード
            sync_interval = self.config.get("sync_interval", 60)
            while True:
                time.sleep(sync_interval)
                self.sync_all()


def main():
    """メイン関数"""
    agent = GoogleDriveSyncAgent()
    
    # 一度だけ同期
    agent.sync_all()
    
    # 監視モードを開始する場合は以下をコメントアウト
    # agent.run()


if __name__ == "__main__":
    main()

