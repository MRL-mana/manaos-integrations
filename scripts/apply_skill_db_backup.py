#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースバックアップ処理スクリプト
YAML形式のデータベースバックアップ設定を読み込み、バックアップ/リストアを実行
"""

import os
import sys
import json
import yaml
import requests
import subprocess
import gzip
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_db_backup_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_history() -> Dict[str, Any]:
    """処理履歴を読み込む"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  履歴ファイルの読み込みエラー: {e}")
    return {"processed": []}


def save_history(history: Dict[str, Any]):
    """処理履歴を保存"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_processed(
    idempotency_key: str, history: Dict[str, Any]
) -> bool:
    """既に処理済みかチェック"""
    processed_keys = [
        item.get("idempotency_key")
        for item in history.get("processed", [])
    ]
    return idempotency_key in processed_keys


def mark_as_processed(
    idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]
):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []

    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def backup_postgresql(data: Dict[str, Any]) -> Dict[str, Any]:
    """PostgreSQLバックアップ"""
    database_name = data.get("database_name", "")
    backup_path = Path(data.get("backup_path", ""))
    compress = data.get("compress", False)
    connection_string = data.get("connection_string", "")
    
    if not database_name:
        return {"success": False, "error": "database_nameが指定されていません"}
    
    if not backup_path:
        return {"success": False, "error": "backup_pathが指定されていません"}
    
    try:
        # バックアップディレクトリを作成
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # pg_dumpコマンドを構築
        cmd = ["pg_dump"]
        
        # 接続文字列から情報を抽出（簡易版）
        if connection_string:
            # postgresql://user:pass@host:port/db 形式を処理
            if "://" in connection_string:
                # 簡易的な処理（実際の実装では適切にパースする）
                cmd.extend(["-d", database_name])
            else:
                cmd.extend(["-d", database_name])
        else:
            cmd.extend(["-d", database_name])
        
        # ファイルに出力
        output_file = str(backup_path)
        if compress:
            output_file = str(backup_path) + ".gz"
            with open(output_file, 'wb') as f:
                with gzip.open(f, 'wb') as gz:
                    result = subprocess.run(
                        cmd, stdout=gz, stderr=subprocess.PIPE, text=True
                    )
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd, stdout=f, stderr=subprocess.PIPE, text=True
                )
        
        if result.returncode != 0:
            return {"success": False, "error": f"pg_dumpエラー: {result.stderr}"}
        
        backup_size = Path(output_file).stat().st_size
        
        return {
            "success": True,
            "backup_path": output_file,
            "backup_size": backup_size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_mongodb(data: Dict[str, Any]) -> Dict[str, Any]:
    """MongoDBバックアップ"""
    database_name = data.get("database_name", "")
    backup_path = Path(data.get("backup_path", ""))
    compress = data.get("compress", False)
    connection_string = data.get("connection_string", "")
    
    if not database_name:
        return {"success": False, "error": "database_nameが指定されていません"}
    
    if not backup_path:
        return {"success": False, "error": "backup_pathが指定されていません"}
    
    try:
        # バックアップディレクトリを作成
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # mongodumpコマンドを構築
        cmd = ["mongodump", "--db", database_name]
        
        if connection_string:
            cmd.extend(["--uri", connection_string])
        
        # 出力ディレクトリを指定
        output_dir = backup_path.parent / backup_path.stem
        cmd.extend(["--out", str(output_dir)])
        
        # 実行
        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return {"success": False, "error": f"mongodumpエラー: {result.stderr}"}
        
        # 圧縮する場合
        if compress:
            archive_path = str(backup_path) + ".gz"
            shutil.make_archive(
                str(backup_path), 'gztar', str(output_dir)
            )
            backup_size = Path(archive_path).stat().st_size
            final_path = archive_path
        else:
            backup_size = sum(
                f.stat().st_size for f in output_dir.rglob('*') if f.is_file()
            )
            final_path = str(output_dir)
        
        return {
            "success": True,
            "backup_path": final_path,
            "backup_size": backup_size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_sqlite(data: Dict[str, Any]) -> Dict[str, Any]:
    """SQLiteバックアップ"""
    database_name = data.get("database_name", "")
    backup_path = Path(data.get("backup_path", ""))
    
    if not database_name:
        return {"success": False, "error": "database_nameが指定されていません"}
    
    if not backup_path:
        return {"success": False, "error": "backup_pathが指定されていません"}
    
    try:
        # データベースファイルのパス
        db_path = Path(database_name)
        if not db_path.exists():
            return {"success": False, "error": f"データベースファイルが見つかりません: {database_name}"}
        
        # バックアップディレクトリを作成
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ファイルをコピー
        shutil.copy2(db_path, backup_path)
        
        backup_size = backup_path.stat().st_size
        
        return {
            "success": True,
            "backup_path": str(backup_path),
            "backup_size": backup_size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_database(data: Dict[str, Any]) -> Dict[str, Any]:
    """データベースバックアップ"""
    database_type = data.get("database_type", "").lower()
    
    if database_type == "postgresql":
        return backup_postgresql(data)
    elif database_type == "mongodb":
        return backup_mongodb(data)
    elif database_type == "sqlite":
        return backup_sqlite(data)
    else:
        return {"success": False, "error": f"不明なデータベースタイプ: {database_type}"}


def restore_postgresql(data: Dict[str, Any]) -> Dict[str, Any]:
    """PostgreSQLリストア"""
    database_name = data.get("database_name", "")
    backup_path = Path(data.get("backup_path", ""))
    
    if not database_name or not backup_path.exists():
        return {"success": False, "error": "database_nameまたはbackup_pathが無効です"}
    
    try:
        # psqlコマンドを構築
        cmd = ["psql", "-d", database_name]
        
        # 圧縮ファイルの場合は解凍してから
        if backup_path.suffix == ".gz":
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd, stdin=f, stderr=subprocess.PIPE, text=True
                )
        else:
            with open(backup_path, 'r', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd, stdin=f, stderr=subprocess.PIPE, text=True
                )
        
        if result.returncode != 0:
            return {"success": False, "error": f"psqlエラー: {result.stderr}"}
        
        return {"success": True, "database_name": database_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


def restore_mongodb(data: Dict[str, Any]) -> Dict[str, Any]:
    """MongoDBリストア"""
    database_name = data.get("database_name", "")
    backup_path = Path(data.get("backup_path", ""))
    connection_string = data.get("connection_string", "")
    
    if not database_name or not backup_path.exists():
        return {"success": False, "error": "database_nameまたはbackup_pathが無効です"}
    
    try:
        # mongorestoreコマンドを構築
        cmd = ["mongorestore", "--db", database_name]
        
        if connection_string:
            cmd.extend(["--uri", connection_string])
        
        # バックアップディレクトリを指定
        if backup_path.is_dir():
            cmd.extend([str(backup_path)])
        elif backup_path.suffix == ".gz":
            # アーカイブを展開
            extract_dir = backup_path.parent / backup_path.stem
            shutil.unpack_archive(backup_path, extract_dir)
            cmd.extend([str(extract_dir)])
        else:
            cmd.extend([str(backup_path)])
        
        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return {"success": False, "error": f"mongorestoreエラー: {result.stderr}"}
        
        return {"success": True, "database_name": database_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


def restore_sqlite(data: Dict[str, Any]) -> Dict[str, Any]:
    """SQLiteリストア"""
    database_name = data.get("database_name", "")
    backup_path = Path(data.get("backup_path", ""))
    
    if not database_name or not backup_path.exists():
        return {"success": False, "error": "database_nameまたはbackup_pathが無効です"}
    
    try:
        # ファイルをコピー
        db_path = Path(database_name)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, db_path)
        
        return {"success": True, "database_name": database_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


def restore_database(data: Dict[str, Any]) -> Dict[str, Any]:
    """データベースリストア"""
    database_type = data.get("database_type", "").lower()
    
    if database_type == "postgresql":
        return restore_postgresql(data)
    elif database_type == "mongodb":
        return restore_mongodb(data)
    elif database_type == "sqlite":
        return restore_sqlite(data)
    else:
        return {"success": False, "error": f"不明なデータベースタイプ: {database_type}"}


def list_backups(data: Dict[str, Any]) -> Dict[str, Any]:
    """バックアップリストを取得"""
    backup_directory = Path(data.get("backup_directory", ""))
    
    if not backup_directory or not backup_directory.exists():
        return {"success": False, "error": "backup_directoryが無効です"}
    
    try:
        backups = []
        for backup_file in backup_directory.glob("*"):
            if backup_file.is_file():
                backups.append({
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size": backup_file.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        backup_file.stat().st_mtime
                    ).isoformat()
                })
        
        backups.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "success": True,
            "backups": backups,
            "count": len(backups)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "backup": "データベースバックアップ",
            "restore": "データベースリストア",
            "list": "バックアップリスト取得"
        }
        action_name = action_names.get(action, action)
        
        message = f"💾 *データベースバックアップ: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "backup_path" in result:
                message += f"バックアップパス: {result['backup_path']}\n"
            if "backup_size" in result:
                size_mb = result["backup_size"] / (1024 * 1024)
                message += f"サイズ: {size_mb:.2f} MB\n"
            if "count" in result:
                message += f"バックアップ数: {result['count']}件\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS DB Backup",
            "icon_emoji": ":floppy_disk:"
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return False


def process_yaml_file(yaml_file: Path) -> bool:
    """YAMLファイルを処理"""
    print(f"\n📁 処理開始: {yaml_file}")
    
    # YAML読み込み
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAMLファイル読み込みエラー: {e}")
        return False
    
    # バリデーション
    if data.get("kind") != "db_backup":
        print("⚠️  kindが'db_backup'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False
    
    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True
    
    # 処理実行
    action = data.get("action")
    result = {"success": False, "error": "不明なアクション"}
    
    try:
        if action == "backup":
            result = backup_database(data)
        elif action == "restore":
            result = restore_database(data)
        elif action == "list":
            result = list_backups(data)
        else:
            result = {"success": False, "error": f"不明なアクション: {action}"}
    except Exception as e:
        result = {"success": False, "error": str(e)}
        print(f"❌ 処理エラー: {e}")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(action, result)
    else:
        print("⏭️  Slack通知はスキップされます")
    
    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)
    
    if result.get("success"):
        print(f"✅ 処理完了: {yaml_file}")
        return True
    else:
        print(f"❌ 処理失敗: {yaml_file} - {result.get('error', '')}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_db_backup.py "
            "<yaml_file> [yaml_file2 ...]"
        )
        sys.exit(1)
    
    yaml_files = [Path(f) for f in sys.argv[1:]]
    
    success_count = 0
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            print(f"❌ ファイルが見つかりません: {yaml_file}")
            continue
        
        if process_yaml_file(yaml_file):
            success_count += 1
    
    print(f"\n🎉 処理完了: {success_count}/{len(yaml_files)} ファイル")
    
    if success_count < len(yaml_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
