"""
バックアップ・復旧システム
自動バックアップと復旧機能
"""

import json
import shutil
import tarfile
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import hashlib


class BackupRecovery:
    """バックアップ・復旧システム"""
    
    def __init__(self, backup_dir: str = "backups"):
        """
        初期化
        
        Args:
            backup_dir: バックアップディレクトリ
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.backup_config = {}
        self.backup_history = []
        self.storage_path = Path("backup_recovery_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.backup_config = state.get("config", {})
                    self.backup_history = state.get("history", [])[-100:]
            except:
                self.backup_config = {}
                self.backup_history = []
        else:
            self.backup_config = {}
            self.backup_history = []
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "config": self.backup_config,
                    "history": self.backup_history[-100:],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
    def configure_backup(
        self,
        name: str,
        source_paths: List[str],
        schedule: str = "daily",
        retention_days: int = 7
    ):
        """
        バックアップを設定
        
        Args:
            name: バックアップ名
            source_paths: バックアップするパスのリスト
            schedule: スケジュール（daily, weekly, monthly）
            retention_days: 保持日数
        """
        self.backup_config[name] = {
            "source_paths": source_paths,
            "schedule": schedule,
            "retention_days": retention_days,
            "last_backup": None,
            "enabled": True
        }
        self._save_state()
    
    def create_backup(self, name: str) -> Optional[str]:
        """
        バックアップを作成
        
        Args:
            name: バックアップ名
            
        Returns:
            バックアップファイルパス（成功時）、None（失敗時）
        """
        if name not in self.backup_config:
            print(f"バックアップ設定 '{name}' が見つかりません")
            return None
        
        config = self.backup_config[name]
        if not config["enabled"]:
            print(f"バックアップ '{name}' は無効です")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{name}_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_filename
        
        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                for source_path in config["source_paths"]:
                    source = Path(source_path)
                    if source.exists():
                        tar.add(source, arcname=source.name)
            
            # バックアップファイルのハッシュを計算
            backup_hash = self._calculate_hash(backup_path)
            
            # 履歴に記録
            backup_record = {
                "name": name,
                "backup_path": str(backup_path),
                "backup_hash": backup_hash,
                "size": backup_path.stat().st_size,
                "timestamp": datetime.now().isoformat(),
                "source_paths": config["source_paths"]
            }
            
            self.backup_history.append(backup_record)
            config["last_backup"] = datetime.now().isoformat()
            self._save_state()
            
            print(f"バックアップ作成完了: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            print(f"バックアップ作成エラー: {e}")
            return None
    
    def restore_backup(self, backup_path: str, target_dir: str = ".") -> bool:
        """
        バックアップを復旧
        
        Args:
            backup_path: バックアップファイルパス
            target_dir: 復旧先ディレクトリ
            
        Returns:
            成功時True
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            print(f"バックアップファイルが見つかりません: {backup_path}")
            return False
        
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(target)
            
            print(f"バックアップ復旧完了: {target}")
            return True
            
        except Exception as e:
            print(f"バックアップ復旧エラー: {e}")
            return False
    
    def list_backups(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        バックアップ一覧を取得
        
        Args:
            name: バックアップ名（オプション）
            
        Returns:
            バックアップ情報のリスト
        """
        if name:
            return [b for b in self.backup_history if b["name"] == name]
        else:
            return self.backup_history
    
    def cleanup_old_backups(self):
        """古いバックアップをクリーンアップ"""
        for name, config in self.backup_config.items():
            retention_days = config.get("retention_days", 7)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            backups = [b for b in self.backup_history if b["name"] == name]
            
            for backup in backups:
                backup_date = datetime.fromisoformat(backup["timestamp"])
                if backup_date < cutoff_date:
                    backup_path = Path(backup["backup_path"])
                    if backup_path.exists():
                        backup_path.unlink()
                        print(f"古いバックアップを削除: {backup_path}")
            
            # 履歴からも削除
            self.backup_history = [
                b for b in self.backup_history
                if not (b["name"] == name and datetime.fromisoformat(b["timestamp"]) < cutoff_date)
            ]
        
        self._save_state()
    
    def _calculate_hash(self, file_path: Path) -> str:
        """
        ファイルのハッシュを計算
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ハッシュ文字列
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def verify_backup(self, backup_path: str) -> bool:
        """
        バックアップを検証
        
        Args:
            backup_path: バックアップファイルパス
            
        Returns:
            検証成功時True
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            return False
        
        # 履歴からハッシュを取得
        backup_record = next(
            (b for b in self.backup_history if b["backup_path"] == backup_path),
            None
        )
        
        if not backup_record:
            return False
        
        # ハッシュを再計算して比較
        current_hash = self._calculate_hash(backup_file)
        return current_hash == backup_record["backup_hash"]
    
    def get_backup_status(self) -> Dict[str, Any]:
        """バックアップ状態を取得"""
        return {
            "configured_backups": len(self.backup_config),
            "total_backups": len(self.backup_history),
            "backup_dir": str(self.backup_dir),
            "total_size": sum(
                Path(b["backup_path"]).stat().st_size
                for b in self.backup_history
                if Path(b["backup_path"]).exists()
            ),
            "configs": self.backup_config,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("バックアップ・復旧システムテスト")
    print("=" * 60)
    
    backup = BackupRecovery()
    
    # バックアップを設定
    print("\nバックアップを設定中...")
    backup.configure_backup(
        name="test_backup",
        source_paths=["manaos_integrations"],
        schedule="daily",
        retention_days=7
    )
    
    # バックアップを作成
    print("\nバックアップを作成中...")
    backup_path = backup.create_backup("test_backup")
    
    if backup_path:
        print(f"バックアップ作成成功: {backup_path}")
        
        # バックアップを検証
        print("\nバックアップを検証中...")
        is_valid = backup.verify_backup(backup_path)
        print(f"検証結果: {'成功' if is_valid else '失敗'}")
    
    # 状態を表示
    status = backup.get_backup_status()
    print(f"\nバックアップ状態:")
    print(f"  設定済みバックアップ数: {status['configured_backups']}")
    print(f"  総バックアップ数: {status['total_backups']}")


if __name__ == "__main__":
    main()



















