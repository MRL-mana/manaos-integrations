#!/usr/bin/env python3
"""
学習レイヤー → バックアップ系 連携モジュール
学習ログを自動バックアップ
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

import importlib.util

# learning_api
spec1 = importlib.util.spec_from_file_location("learning_api", "/root/scripts/learning_api.py")
learning_api = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(learning_api)

BASE_DIR = "/root/manaos_learning"
LOG_FILE = f"{BASE_DIR}/learning_log.jsonl"
BACKUP_DIR = "/root/.mana_vault/learning_backups"


def backup_learning_logs(destination: Optional[str] = None) -> bool:
    """
    学習ログをバックアップ

    Args:
        destination: バックアップ先（Noneならデフォルト）

    Returns:
        成功したかどうか
    """
    if not Path(LOG_FILE).exists():
        return False

    # バックアップ先を決定
    if destination is None:
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = str(backup_path / f"learning_log_{timestamp}.jsonl")

    try:
        # ファイルをコピー
        shutil.copy2(LOG_FILE, destination)

        # メタデータを保存
        meta_file = f"{destination}.meta.json"
        meta = {
            "backup_time": datetime.now().isoformat(),
            "source": LOG_FILE,
            "destination": destination,
            "size": Path(LOG_FILE).stat().st_size
        }
        with open(meta_file, 'w') as f:
            json.dump(meta, f, indent=2)

        return True
    except Exception as e:
        print(f"❌ バックアップエラー: {e}")
        return False


def backup_to_gdrive() -> bool:
    """Google Driveにバックアップ（既存のバックアップシステムを使用）"""
    try:
        # 既存のバックアップシステムを呼び出す
        sys.path.insert(0, '/root/scripts')
        backup_module = importlib.util.spec_from_file_location(
            "backup_manager",
            "/root/scripts/backup_management_system.py"
        )
        # 簡易実装: 直接コピー
        gdrive_path = Path("/root/GoogleDrive/backups/learning_logs")
        gdrive_path.mkdir(parents=True, exist_ok=True)

        return backup_learning_logs(str(gdrive_path / f"learning_log_{datetime.now().strftime('%Y%m%d')}.jsonl"))
    except Exception:
        return False


if __name__ == "__main__":
    print("💾 学習ログバックアップ")
    print("=" * 60)

    if backup_learning_logs():
        print("✅ バックアップ成功")
    else:
        print("❌ バックアップ失敗")








