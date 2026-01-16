#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 ログローテーション・バックアップスクリプト
- ログファイルのローテーション（サイズ・日付ベース）
- Obsidian Vaultのバックアップ
- メトリクスファイルのローテーション
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import json
import gzip
from typing import List, Dict, Any

# 設定（環境変数から取得、デフォルト値あり）
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"))
INTEGRATIONS_DIR = Path(os.getenv("MANAOS_INTEGRATIONS_DIR", r"C:\Users\mana4\Desktop\manaos_integrations"))
LOGS_DIR = INTEGRATIONS_DIR / "logs"
BACKUP_DIR = INTEGRATIONS_DIR / "backups"

# 保持ポリシー（日数）
RETENTION_POLICIES = {
    "daily_logs": 30,  # 日次ログ: 30日
    "weekly_reviews": 84,  # 週次レビュー: 12週（84日）
    "error_logs": 7,  # エラーログ: 7日
    "metrics": 30,  # メトリクス: 30日
    "jsonl": 30,  # JSONL: 30日
}

# ログファイルサイズ上限（MB）
MAX_LOG_SIZE_MB = 10


def rotate_logs_by_date(log_dir: Path, pattern: str, retention_days: int) -> List[str]:
    """日付ベースでログをローテーション"""
    rotated = []
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    for log_file in log_dir.glob(pattern):
        try:
            # ファイルの更新日時を確認
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

            if mtime < cutoff_date:
                # アーカイブディレクトリに移動
                archive_dir = log_dir / "archive"
                archive_dir.mkdir(exist_ok=True)

                archive_path = archive_dir / f"{log_file.stem}_{mtime.strftime('%Y%m%d')}{log_file.suffix}"

                # 既にアーカイブ済みならスキップ
                if archive_path.exists():
                    log_file.unlink()
                else:
                    shutil.move(str(log_file), str(archive_path))

                rotated.append(str(log_file.name))
        except Exception as e:
            print(f"Warning: Failed to rotate {log_file}: {e}")

    return rotated


def rotate_logs_by_size(log_file: Path, max_size_mb: int) -> bool:
    """サイズベースでログをローテーション"""
    if not log_file.exists():
        return False

    size_mb = log_file.stat().st_size / (1024 * 1024)

    if size_mb > max_size_mb:
        # ローテーション: タイムスタンプ付きでリネーム
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
        rotated_path = log_file.parent / rotated_name

        shutil.move(str(log_file), str(rotated_path))

        # 圧縮（オプション）
        if rotated_path.suffix == ".log":
            with open(rotated_path, 'rb') as f_in:
                with gzip.open(f"{rotated_path}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            rotated_path.unlink()

        return True

    return False


def backup_obsidian_vault(vault_path: Path, backup_dir: Path) -> str:
    """Obsidian Vaultのバックアップ"""
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"obsidian_vault_backup_{timestamp}"
    backup_path = backup_dir / backup_name

    # System3関連のみバックアップ
    system_dirs = [
        "ManaOS/System/Daily",
        "ManaOS/System/Playbook_Review",
        "ManaOS/System/System3_Status.md",
        "ManaOS/System/Runbook_System3.md",
    ]

    backup_path.mkdir(exist_ok=True)

    for rel_path in system_dirs:
        src = vault_path / rel_path
        if src.exists():
            if src.is_file():
                dst = backup_path / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
            elif src.is_dir():
                dst = backup_path / rel_path
                shutil.copytree(str(src), str(dst), dirs_exist_ok=True)

    # ZIP圧縮
    zip_path = backup_dir / f"{backup_name}.zip"
    shutil.make_archive(str(backup_path), 'zip', str(backup_path))
    shutil.rmtree(str(backup_path))

    return str(zip_path)


def rotate_metrics_files(metrics_dir: Path, retention_days: int) -> List[str]:
    """メトリクスファイル（JSON/JSONL）のローテーション"""
    rotated = []
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    patterns = ["*.json", "*.jsonl"]

    for pattern in patterns:
        for metrics_file in metrics_dir.glob(pattern):
            # System3関連のみ
            if "system3" in metrics_file.name.lower() or "score" in metrics_file.name.lower():
                try:
                    mtime = datetime.fromtimestamp(metrics_file.stat().st_mtime)

                    if mtime < cutoff_date:
                        archive_dir = metrics_dir / "archive"
                        archive_dir.mkdir(exist_ok=True)

                        archive_path = archive_dir / f"{metrics_file.stem}_{mtime.strftime('%Y%m%d')}{metrics_file.suffix}"

                        if archive_path.exists():
                            metrics_file.unlink()
                        else:
                            shutil.move(str(metrics_file), str(archive_path))

                        rotated.append(str(metrics_file.name))
                except Exception as e:
                    print(f"Warning: Failed to rotate {metrics_file}: {e}")

    return rotated


def cleanup_old_backups(backup_dir: Path, retention_days: int = 30) -> List[str]:
    """古いバックアップを削除"""
    cleaned = []
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    for backup_file in backup_dir.glob("*.zip"):
        try:
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)

            if mtime < cutoff_date:
                backup_file.unlink()
                cleaned.append(str(backup_file.name))
        except Exception as e:
            print(f"Warning: Failed to cleanup {backup_file}: {e}")

    return cleaned


def main():
    """メイン処理"""
    print("=" * 60)
    print("System 3 Log Rotation & Backup")
    print("=" * 60)
    print()

    results = {
        "rotated_logs": [],
        "rotated_metrics": [],
        "backup_created": None,
        "cleaned_backups": [],
    }

    # 1. エラーログのローテーション（7日）
    if LOGS_DIR.exists():
        print("[1] Rotating error logs...")
        rotated = rotate_logs_by_date(LOGS_DIR, "*_error.log", RETENTION_POLICIES["error_logs"])
        results["rotated_logs"].extend(rotated)
        print(f"    Rotated {len(rotated)} error log files")

    # 2. 通常ログのサイズチェック
    if LOGS_DIR.exists():
        print("[2] Checking log file sizes...")
        for log_file in LOGS_DIR.glob("*.log"):
            if rotate_logs_by_size(log_file, MAX_LOG_SIZE_MB):
                results["rotated_logs"].append(str(log_file.name))
                print(f"    Rotated large log: {log_file.name}")

    # 3. メトリクスファイルのローテーション
    print("[3] Rotating metrics files...")
    rotated = rotate_metrics_files(INTEGRATIONS_DIR, RETENTION_POLICIES["metrics"])
    results["rotated_metrics"].extend(rotated)
    print(f"    Rotated {len(rotated)} metrics files")

    # 4. Obsidian Vaultのバックアップ
    print("[4] Backing up Obsidian Vault...")
    if VAULT_PATH.exists():
        backup_path = backup_obsidian_vault(VAULT_PATH, BACKUP_DIR)
        results["backup_created"] = backup_path
        print(f"    Backup created: {backup_path}")

    # 5. 古いバックアップのクリーンアップ
    print("[5] Cleaning up old backups...")
    cleaned = cleanup_old_backups(BACKUP_DIR)
    results["cleaned_backups"] = cleaned
    print(f"    Cleaned {len(cleaned)} old backup files")

    # 6. 日次ログのローテーション（Obsidian内）
    print("[6] Rotating daily logs in Obsidian...")
    daily_dir = VAULT_PATH / "ManaOS" / "System" / "Daily"
    if daily_dir.exists():
        rotated = rotate_logs_by_date(daily_dir, "System3_Daily_*.md", RETENTION_POLICIES["daily_logs"])
        print(f"    Rotated {len(rotated)} daily log files")

    # 7. 週次レビューのローテーション
    print("[7] Rotating weekly reviews...")
    review_dir = VAULT_PATH / "ManaOS" / "System" / "Playbook_Review"
    if review_dir.exists():
        rotated = rotate_logs_by_date(review_dir, "Playbook_Review_*.md", RETENTION_POLICIES["weekly_reviews"])
        print(f"    Rotated {len(rotated)} weekly review files")

    print()
    print("=" * 60)
    print("Rotation & Backup Complete")
    print("=" * 60)
    print()
    print(f"Rotated logs: {len(results['rotated_logs'])}")
    print(f"Rotated metrics: {len(results['rotated_metrics'])}")
    print(f"Backup created: {results['backup_created']}")
    print(f"Cleaned backups: {len(results['cleaned_backups'])}")

    return results


if __name__ == "__main__":
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    main()
