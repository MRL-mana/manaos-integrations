#!/usr/bin/env python3
"""
🔄 Cross-Platform File Sync - デバイス間ファイル同期システム
リアルタイム同期、競合解決、バージョン管理
"""

import os
import json
import hashlib
import shutil
import time
from manaos_logger import get_logger, get_service_logger
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Google Drive統合をインポート
try:
    from google_drive_integration import GoogleDriveIntegration
except ImportError:
    GoogleDriveIntegration = None

logger = get_service_logger("cross-platform-file-sync")


@dataclass
class SyncRule:
    """同期ルール"""
    rule_id: str
    local_path: str
    sync_path: str  # Google Drive上のパス
    devices: List[str]  # 同期対象デバイス
    sync_mode: str  # "bidirectional", "upload_only", "download_only"
    conflict_resolution: str  # "newest", "manual", "local", "remote"
    enabled: bool


@dataclass
class FileVersion:
    """ファイルバージョン"""
    file_path: str
    version: int
    hash: str
    timestamp: str
    device: str
    size: int


@dataclass
class SyncConflict:
    """同期競合"""
    file_path: str
    local_version: FileVersion
    remote_version: FileVersion
    conflict_type: str  # "modified_both", "deleted_local", "deleted_remote"


class FileChangeHandler(FileSystemEventHandler):
    """ファイル変更イベントハンドラー"""
    
    def __init__(self, sync_manager):
        self.sync_manager = sync_manager
        self.debounce_time = 2  # 2秒のデバウンス
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
        file_path = Path(file_path)  # type: ignore
        current_time = time.time()
        
        if file_path in self.pending_changes:
            last_time, last_type = self.pending_changes[file_path]
            if current_time - last_time < self.debounce_time:
                return
        
        self.pending_changes[file_path] = (current_time, event_type)
        self.sync_manager.schedule_sync(file_path, event_type)


class CrossPlatformFileSync:
    """デバイス間ファイル同期システム"""
    
    def __init__(self, config_path: str = "cross_platform_sync_config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Google Drive統合
        self.drive_integration = None
        if GoogleDriveIntegration:
            credentials_path = self.config.get("credentials_path", "credentials.json")
            token_path = self.config.get("token_path", "token.json")
            self.drive_integration = GoogleDriveIntegration(
                credentials_path=credentials_path,
                token_path=token_path
            )
        
        # 同期ルール
        self.sync_rules: List[SyncRule] = []
        for rule_config in self.config.get("sync_rules", []):
            self.sync_rules.append(SyncRule(**rule_config))
        
        # ファイルバージョン管理
        self.version_file = Path(self.config.get("version_file", "sync_versions.json"))
        self.file_versions: Dict[str, List[FileVersion]] = self._load_versions()
        
        # 競合管理
        self.conflicts_file = Path(self.config.get("conflicts_file", "sync_conflicts.json"))
        self.conflicts: List[SyncConflict] = self._load_conflicts()
        
        # 同期キュー
        self.sync_queue: List[Dict[str, Any]] = []
        
        # ファイル監視
        self.observers: List[Observer] = []
    
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
                "version_file": "sync_versions.json",
                "conflicts_file": "sync_conflicts.json",
                "sync_rules": [
                    {
                        "rule_id": "manaos_sync",
                        "local_path": "./manaos_integrations",
                        "sync_path": "ManaOS_Sync",
                        "devices": ["mothership", "x280", "konoha"],
                        "sync_mode": "bidirectional",
                        "conflict_resolution": "newest",
                        "enabled": True
                    }
                ]
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def _load_versions(self) -> Dict[str, List[FileVersion]]:
        """ファイルバージョンを読み込む"""
        if self.version_file.exists():
            with open(self.version_file, 'r', encoding='utf-8') as f:
                versions_data = json.load(f)
                return {
                    path: [FileVersion(**v) for v in versions]
                    for path, versions in versions_data.items()
                }
        return {}
    
    def _save_versions(self):
        """ファイルバージョンを保存"""
        versions_data = {
            path: [asdict(v) for v in versions]
            for path, versions in self.file_versions.items()
        }
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(versions_data, f, indent=2, ensure_ascii=False)
    
    def _load_conflicts(self) -> List[SyncConflict]:
        """競合を読み込む"""
        if self.conflicts_file.exists():
            with open(self.conflicts_file, 'r', encoding='utf-8') as f:
                conflicts_data = json.load(f)
                return [
                    SyncConflict(
                        file_path=c["file_path"],
                        local_version=FileVersion(**c["local_version"]),
                        remote_version=FileVersion(**c["remote_version"]),
                        conflict_type=c["conflict_type"]
                    )
                    for c in conflicts_data
                ]
        return []
    
    def _save_conflicts(self):
        """競合を保存"""
        conflicts_data = [
            {
                "file_path": c.file_path,
                "local_version": asdict(c.local_version),
                "remote_version": asdict(c.remote_version),
                "conflict_type": c.conflict_type
            }
            for c in self.conflicts
        ]
        with open(self.conflicts_file, 'w', encoding='utf-8') as f:
            json.dump(conflicts_data, f, indent=2, ensure_ascii=False)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュを計算"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"ファイルハッシュ計算エラー: {e}")
            return ""
    
    def _get_latest_version(self, file_path: str) -> Optional[FileVersion]:
        """最新バージョンを取得"""
        if file_path not in self.file_versions:
            return None
        
        versions = self.file_versions[file_path]
        if not versions:
            return None
        
        return max(versions, key=lambda v: v.version)
    
    def _add_version(self, file_path: str, device: str, file_hash: str, size: int):
        """ファイルバージョンを追加"""
        if file_path not in self.file_versions:
            self.file_versions[file_path] = []
        
        latest_version = self._get_latest_version(file_path)
        new_version = latest_version.version + 1 if latest_version else 1
        
        version = FileVersion(
            file_path=file_path,
            version=new_version,
            hash=file_hash,
            timestamp=datetime.now().isoformat(),
            device=device,
            size=size
        )
        
        self.file_versions[file_path].append(version)
        self._save_versions()
    
    def schedule_sync(self, file_path: Path, event_type: str):
        """同期をスケジュール"""
        self.sync_queue.append({
            "file_path": str(file_path),
            "event_type": event_type,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"同期をスケジュール: {file_path} ({event_type})")
    
    def sync_file(self, file_path: Path, rule: SyncRule) -> bool:
        """ファイルを同期"""
        if not self.drive_integration or not self.drive_integration.is_available():
            logger.error("Google Drive統合が利用できません")
            return False
        
        try:
            local_path = Path(rule.local_path)
            relative_path = file_path.relative_to(local_path)
            sync_path = f"{rule.sync_path}/{relative_path}"
            
            # ファイルが存在する場合
            if file_path.exists():
                file_hash = self._get_file_hash(file_path)
                file_size = file_path.stat().st_size
                
                # 最新バージョンを確認
                latest_version = self._get_latest_version(str(relative_path))
                
                # 競合チェック
                if latest_version and latest_version.hash != file_hash:
                    # 競合が発生
                    if latest_version.device != "local":
                        conflict = SyncConflict(
                            file_path=str(relative_path),
                            local_version=FileVersion(
                                file_path=str(relative_path),
                                version=latest_version.version + 1,
                                hash=file_hash,
                                timestamp=datetime.now().isoformat(),
                                device="local",
                                size=file_size
                            ),
                            remote_version=latest_version,
                            conflict_type="modified_both"
                        )
                        self.conflicts.append(conflict)
                        self._save_conflicts()
                        
                        # 競合解決
                        return self._resolve_conflict(conflict, rule)
                
                # Google Driveにアップロード
                result = self.drive_integration.upload_file(
                    str(file_path),
                    sync_path,
                    overwrite=True
                )
                
                if result:
                    # バージョンを追加
                    self._add_version(str(relative_path), "local", file_hash, file_size)
                    logger.info(f"ファイルを同期しました: {file_path} -> {sync_path}")
                    return True
            else:
                # ファイルが削除された場合
                logger.info(f"ファイルが削除されました: {file_path}")
                # 削除処理は実装が必要
            
            return False
            
        except Exception as e:
            logger.error(f"ファイル同期エラー: {e}")
            return False
    
    def _resolve_conflict(self, conflict: SyncConflict, rule: SyncRule) -> bool:
        """競合を解決"""
        resolution = rule.conflict_resolution
        
        if resolution == "newest":
            # 新しい方を選択
            local_time = datetime.fromisoformat(conflict.local_version.timestamp)
            remote_time = datetime.fromisoformat(conflict.remote_version.timestamp)
            use_local = local_time > remote_time
        elif resolution == "local":
            use_local = True
        elif resolution == "remote":
            use_local = False
        else:  # "manual"
            logger.warning(f"手動解決が必要: {conflict.file_path}")
            return False
        
        if use_local:
            # ローカル版を使用
            file_path = Path(rule.local_path) / conflict.file_path
            if file_path.exists():
                return self.sync_file(file_path, rule)
        else:
            # リモート版をダウンロード
            # 実装は省略
            pass
        
        return True
    
    def process_sync_queue(self):
        """同期キューを処理"""
        while self.sync_queue:
            sync_item = self.sync_queue.pop(0)
            file_path = Path(sync_item["file_path"])
            
            # 該当する同期ルールを探す
            for rule in self.sync_rules:
                if not rule.enabled:
                    continue
                
                local_path = Path(rule.local_path)
                try:
                    if file_path.is_relative_to(local_path):
                        self.sync_file(file_path, rule)
                        break
                except ValueError:
                    continue
    
    def start_watching(self):
        """ファイル監視を開始"""
        logger.info("ファイル監視を開始します...")
        
        for rule in self.sync_rules:
            if not rule.enabled:
                continue
            
            local_path = Path(rule.local_path)
            if local_path.exists():
                observer = Observer()
                handler = FileChangeHandler(self)
                observer.schedule(handler, str(local_path), recursive=True)
                observer.start()
                self.observers.append(observer)
                logger.info(f"監視を開始: {local_path}")
        
        try:
            while True:
                time.sleep(1)
                self.process_sync_queue()
        except KeyboardInterrupt:
            logger.info("監視を停止します...")
            for observer in self.observers:
                observer.stop()
        
        for observer in self.observers:
            observer.join()
    
    def sync_all(self):
        """全同期ルールを実行"""
        logger.info("全同期ルールを実行します...")
        
        for rule in self.sync_rules:
            if not rule.enabled:
                continue
            
            local_path = Path(rule.local_path)
            if not local_path.exists():
                continue
            
            for file_path in local_path.rglob("*"):
                if file_path.is_file():
                    self.sync_file(file_path, rule)
        
        logger.info("全同期が完了しました")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_files = sum(len(versions) for versions in self.file_versions.values())
        total_conflicts = len(self.conflicts)
        
        return {
            "total_files": len(self.file_versions),
            "total_versions": total_files,
            "total_conflicts": total_conflicts,
            "sync_rules": len(self.sync_rules),
            "enabled_rules": sum(1 for r in self.sync_rules if r.enabled),
            "conflicts": [asdict(c) for c in self.conflicts]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """システム状態を取得（統一インターフェース）"""
        return self.get_stats()


def main():
    """メイン関数（テスト用）"""
    sync = CrossPlatformFileSync()
    
    # 全同期を実行
    sync.sync_all()
    
    # 統計を表示
    stats = sync.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 監視を開始する場合は以下をコメントアウト
    # sync.start_watching()


if __name__ == "__main__":
    main()

